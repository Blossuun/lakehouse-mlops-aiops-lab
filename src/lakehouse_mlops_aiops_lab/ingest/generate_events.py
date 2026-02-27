from __future__ import annotations

import argparse
import json
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
from faker import Faker

from lakehouse_mlops_aiops_lab.catalog.load_products import load_products
from lakehouse_mlops_aiops_lab.utils.timeutil import iso


fake = Faker()


@dataclass
class GenConfig:
    date: str  # YYYY-MM-DD in UTC 기준으로 생성
    rows: int
    out: Path
    seed: int
    purchase_rate: float
    late_rate: float
    duplicate_rate: float
    dirty_rate: float
    schema_v2_rate: float


EVENT_TYPES = ["view", "search", "add_to_cart", "purchase", "refund"]


def parse_date_utc(date_str: str) -> datetime:
    # date_str: YYYY-MM-DD → 해당 일 00:00 UTC
    y, m, d = [int(x) for x in date_str.split("-")]
    return datetime(y, m, d, tzinfo=timezone.utc)


def weighted_choice(rng: np.random.Generator, items: list[str], probs: list[float]) -> str:
    idx = rng.choice(len(items), p=probs)
    return items[int(idx)]


def make_user_id(rng: np.random.Generator) -> str:
    # 내부 식별자(PII 아님)
    return f"U{rng.integers(1, 20000):06d}"


def make_session_id() -> str:
    return uuid.uuid4().hex


def pick_product(rng: np.random.Generator, products: list[dict[str, Any]], allow_unknown_rate: float = 0.01) -> dict[str, Any]:
    # 참조 무결성 깨짐(unknown product) 재현
    if rng.random() < allow_unknown_rate:
        return {
            "product_id": f"P{rng.integers(900000, 999999)}",
            "category_id": None,
            "base_price": None,
            "brand": None,
            "shipping_class": None,
            "is_fragile": None,
            "_unknown": True,
        }
    return products[int(rng.integers(0, len(products)))]


def make_device(rng: np.random.Generator, schema_version: int) -> dict[str, Any]:
    os_name = rng.choice(["android", "ios", "windows", "macos"])
    device = {
        "os": str(os_name),
        "app_version": f"{rng.integers(1, 5)}.{rng.integers(0, 20)}.{rng.integers(0, 50)}",
        "device_model": fake.user_agent(),
    }
    # schema v2에서만 os_version 제공(스키마 진화)
    if schema_version >= 2:
        device["os_version"] = f"{rng.integers(10, 15)}.{rng.integers(0, 9)}"
    return device


def make_geo(rng: np.random.Generator) -> dict[str, Any]:
    # 현실성을 위해 대략적 지역만
    return {
        "country": "KR",
        "region": rng.choice(["Seoul", "Gyeonggi", "Busan", "Incheon", "Daegu"]),
        "city": rng.choice(["Seoul", "Suwon", "Seongnam", "Busan", "Incheon"]),
    }


def make_source(rng: np.random.Generator) -> dict[str, Any]:
    return {
        "referrer": rng.choice(["direct", "search", "ad", "email", "social"]),
        "utm_campaign": rng.choice(["none", "brand", "promo", "retarget", "influencer"]),
        "utm_medium": rng.choice(["none", "cpc", "organic", "newsletter", "social"]),
    }


def maybe_make_dirty(rng: np.random.Generator, event: dict[str, Any], dirty_rate: float) -> None:
    """실무에서 흔한 결측/형식 오류를 일부 주입."""
    if rng.random() >= dirty_rate:
        return

    # 몇 가지 대표적인 더티 케이스를 랜덤 적용
    choice = rng.choice(["missing_user", "null_product", "price_string", "negative_qty", "missing_session"])
    if choice == "missing_user":
        event["user_id"] = None
    elif choice == "null_product":
        if "payload" in event:
            event["payload"]["product_id"] = None
    elif choice == "price_string":
        if "payload" in event and "price" in event["payload"]:
            event["payload"]["price"] = str(event["payload"]["price"])
    elif choice == "negative_qty":
        if "payload" in event and "quantity" in event["payload"]:
            event["payload"]["quantity"] = -abs(int(event["payload"]["quantity"]))
    elif choice == "missing_session":
        event["session_id"] = None


def maybe_late_ingest(rng: np.random.Generator, event_time: datetime, late_rate: float) -> datetime:
    """late arriving data: event_time은 과거인데 ingest_time은 이후."""
    if rng.random() >= late_rate:
        return event_time + timedelta(seconds=int(rng.integers(0, 30)))
    # 1시간~36시간 지연
    delay_hours = int(rng.integers(1, 36))
    return event_time + timedelta(hours=delay_hours, seconds=int(rng.integers(0, 60)))


def build_event(
    rng: np.random.Generator,
    base_day: datetime,
    products: list[dict[str, Any]],
    user_id: str,
    session_id: str,
    event_type: str,
    schema_version: int,
    purchase_bias: float,
    config: GenConfig,
) -> dict[str, Any]:
    # 세션 내 시간 흐름: base_day + random seconds
    event_time = base_day + timedelta(seconds=int(rng.integers(0, 86400)))
    ingest_time = maybe_late_ingest(rng, event_time, config.late_rate)

    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "schema_version": schema_version,
        "event_type": event_type,
        "event_time": iso(event_time),
        "ingest_time": iso(ingest_time),
        "user_id": user_id,
        "session_id": session_id,
        "device": make_device(rng, schema_version),
        "geo": make_geo(rng),
        "source": make_source(rng),
    }

    # payload는 이벤트별로 다르게(가변 스키마)
    if event_type in ("view", "add_to_cart", "purchase"):
        p = pick_product(rng, products, allow_unknown_rate=0.015)
        base_price = p.get("base_price") or int(rng.integers(5000, 200000))
        price = int(max(100, rng.normal(loc=base_price, scale=max(500, base_price * 0.15))))

        payload: dict[str, Any] = {
            "product_id": p.get("product_id"),
            "category_id": p.get("category_id"),
            "brand": p.get("brand"),
            "price": price,
        }

        if event_type == "view":
            payload.update(
                {
                    "page": rng.choice(["home", "search", "product", "category"]),
                    "position": int(rng.integers(1, 40)),
                }
            )
        elif event_type == "add_to_cart":
            payload.update(
                {
                    "quantity": int(rng.integers(1, 4)),
                }
            )
        elif event_type == "purchase":
            # 주문/결제는 더 “업무 느낌”이 나게
            order_id = f"O{rng.integers(1, 30000000):08d}"
            qty = int(rng.integers(1, 4))
            total = price * qty
            # 구매 편향(유저 성향) 반영: purchase_bias가 높을수록 쿠폰/프로모션 가능성↑ 같은 구조도 가능
            payload.update(
                {
                    "order_id": order_id,
                    "quantity": qty,
                    "total_amount": total,
                    "payment_method": rng.choice(["card", "kakao_pay", "naver_pay", "bank_transfer"]),
                    "coupon_id": rng.choice([None, "CP10", "CP20", "FREESHIP"]) if purchase_bias > 0.5 else None,
                }
            )
        event["payload"] = payload

    elif event_type == "search":
        event["payload"] = {
            "query": fake.word(),
            "results_count": int(max(0, rng.normal(loc=30, scale=20))),
        }

    elif event_type == "refund":
        event["payload"] = {
            "order_id": f"O{rng.integers(1, 30000000):08d}",
            "refund_amount": int(max(100, rng.normal(loc=25000, scale=15000))),
            "reason_code": rng.choice(["changed_mind", "defect", "late_delivery", "wrong_item"]),
        }

    maybe_make_dirty(rng, event, config.dirty_rate)
    return event


def generate_events(config: GenConfig) -> list[dict[str, Any]]:
    rng = np.random.default_rng(config.seed)
    products = load_products()
    base_day = parse_date_utc(config.date)

    # 전체 이벤트 타입 분포(현실적으로 view/search가 대부분)
    base_probs = {
        "view": 0.70,
        "search": 0.20,
        "add_to_cart": 0.07,
        "purchase": config.purchase_rate,  # 예: 0.01~0.02
        "refund": 0.02,
    }
    # 합이 1이 되도록 보정(구성 변경 시 안전)
    total = sum(base_probs.values())
    items = list(base_probs.keys())
    probs = [base_probs[k] / total for k in items]

    events: list[dict[str, Any]] = []

    # “세션 느낌”을 내기 위해 세션을 먼저 만들고 그 안에서 이벤트를 생성
    # 간단하게: 유저를 뽑고, 각 유저가 여러 세션을 갖는 식으로
    for _ in range(config.rows):
        user_id = make_user_id(rng)
        session_id = make_session_id()

        # 유저 성향(구매 편향) 부여: 0~1
        purchase_bias = float(rng.beta(1.2, 8.0))  # 대부분 낮고 일부만 높게

        schema_version = 2 if rng.random() < config.schema_v2_rate else 1
        event_type = weighted_choice(rng, items, probs)

        # purchase_bias가 낮으면 purchase를 view로 “밀어내는” 식으로 현실성 부여
        if event_type == "purchase" and purchase_bias < 0.1:
            event_type = "view"

        ev = build_event(
            rng=rng,
            base_day=base_day,
            products=products,
            user_id=user_id,
            session_id=session_id,
            event_type=event_type,
            schema_version=schema_version,
            purchase_bias=purchase_bias,
            config=config,
        )
        events.append(ev)

        # duplicate resend: 동일 event_id로 한 번 더 넣기
        if rng.random() < config.duplicate_rate:
            dup = dict(ev)
            # 재전송이므로 ingest_time만 약간 뒤로
            dup["ingest_time"] = iso(parse_date_utc(config.date) + timedelta(days=1, seconds=int(rng.integers(0, 3600))))
            events.append(dup)

    # out-of-order(순서 뒤틀림)를 파일 레벨에서 재현: 일부 섞어서 shuffle
    rng.shuffle(events)
    return events


def write_jsonl(events: list[dict[str, Any]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def parse_args() -> GenConfig:
    p = argparse.ArgumentParser(description="Generate realistic raw events (jsonl).")
    p.add_argument("--date", required=True, help="UTC date YYYY-MM-DD (partition key).")
    p.add_argument("--rows", type=int, default=20000)
    p.add_argument("--out", type=Path, default=Path("./tmp/events.jsonl"))
    p.add_argument("--seed", type=int, default=42)

    p.add_argument("--purchase-rate", type=float, default=0.015)
    p.add_argument("--late-rate", type=float, default=0.05)
    p.add_argument("--duplicate-rate", type=float, default=0.005)
    p.add_argument("--dirty-rate", type=float, default=0.01)
    p.add_argument("--schema-v2-rate", type=float, default=0.20)

    a = p.parse_args()
    return GenConfig(
        date=a.date,
        rows=a.rows,
        out=a.out,
        seed=a.seed,
        purchase_rate=a.purchase_rate,
        late_rate=a.late_rate,
        duplicate_rate=a.duplicate_rate,
        dirty_rate=a.dirty_rate,
        schema_v2_rate=a.schema_v2_rate,
    )


def main() -> int:
    cfg = parse_args()
    events = generate_events(cfg)
    write_jsonl(events, cfg.out)
    print(f"OK: wrote {len(events)} events to {cfg.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())