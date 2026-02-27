from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("src/lakehouse_mlops_aiops_lab/catalog/products.json"),
    )
    args = p.parse_args()

    rng = random.Random(args.seed)

    categories = [
        ("C01", "electronics"),
        ("C02", "home"),
        ("C03", "beauty"),
        ("C04", "fashion"),
        ("C05", "sports"),
        ("C06", "grocery"),
        ("C07", "pet"),
        ("C08", "books"),
    ]
    brands = [
        "Nova",
        "Orbi",
        "Kairo",
        "Lumen",
        "Mori",
        "Aster",
        "Pico",
        "Hanul",
        "Darae",
        "Bori",
    ]
    shipping_classes = ["economy", "standard", "express"]

    # 카테고리별 대략적 가격대(현업 느낌)
    price_ranges = {
        "C01": (15000, 450000),  # electronics
        "C02": (8000, 250000),  # home
        "C03": (7000, 180000),  # beauty
        "C04": (9000, 220000),  # fashion
        "C05": (12000, 300000),  # sports
        "C06": (1000, 60000),  # grocery
        "C07": (5000, 120000),  # pet
        "C08": (8000, 80000),  # books
    }

    products: list[dict] = []
    for i in range(1, args.n + 1):
        category_id, _ = rng.choice(categories)
        lo, hi = price_ranges[category_id]

        base_price = rng.randint(lo, hi)
        # 보기 좋은 가격(천원 단위 근사) 느낌
        base_price = int(round(base_price / 100) * 100)

        shipping_class = rng.choices(
            shipping_classes,
            weights=[0.25, 0.60, 0.15],
            k=1,
        )[0]

        is_fragile = rng.random() < (0.18 if category_id in ("C01", "C02") else 0.08)

        products.append(
            {
                "product_id": f"P{i:06d}",
                "category_id": category_id,
                "base_price": base_price,
                "brand": rng.choice(brands),
                "shipping_class": shipping_class,
                "is_fragile": is_fragile,
            }
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(products, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OK: wrote {len(products)} products -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
