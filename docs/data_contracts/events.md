# Raw 이벤트 계약서 (Event Contract)

이 문서는 Raw 이벤트(JSON Lines, `.jsonl`)의 **스키마/규칙/저장 경로**를 정의합니다.  
Raw 계층은 “정제”가 아니라 **원본에 가까운 형태로 보존**하는 것이 목적입니다.

---

## 목표

- 원본 이벤트 payload를 최소 변형으로 저장
- 시간 필드/포맷을 통일해 파싱 가능하게 유지
- 스키마 진화(schema evolution)를 허용하면서도 하위 호환 유지
- 현실적인 수집 문제(지연/중복/결측/타입 드리프트)를 일부 포함

---

## 저장 레이아웃 (Object Storage: MinIO/S3)

Bucket: `datalake`

Prefix 규칙:

```
raw/events/dt=YYYY-MM-DD/events-<shard>.jsonl
```

예시:

```
s3://datalake/raw/events/dt=2026-02-27/events-00.jsonl
```

- `dt=YYYY-MM-DD`는 파티션 키입니다.
- `shard`는 파일 분할 단위입니다(병렬 처리/재처리 대비). 초기에는 `00` 하나만 써도 됩니다.

---

## 공통 필드 (모든 이벤트에 존재)

| 필드 | 타입 | 설명 |
|---|---|---|
| event_id | string(UUID) | 중복 제거 키(재전송될 수 있음) |
| schema_version | int | 스키마 버전(1, 2, ...) |
| event_type | string | 이벤트 타입(view, search, add_to_cart, purchase, refund) |
| event_time | string(ISO8601, UTC) | 실제 이벤트 발생 시각(UTC) |
| ingest_time | string(ISO8601, UTC) | 수집/적재 시각(UTC, 지연 가능) |
| user_id | string \| null | 내부 사용자 식별자(더티 데이터로 null 가능) |
| session_id | string \| null | 세션 식별자(더티 데이터로 null 가능) |
| device | object | 디바이스/앱 정보(버전업 가능) |
| geo | object | 대략적 지역 정보 |
| source | object | 유입/캠페인 정보 |

### 시간 규칙(Time Convention)

- 모든 시각은 **UTC** 기준
- ISO8601 문자열이며 `Z` 접미사를 사용  
  예: `2026-02-27T06:12:34.123Z`

**이유**
- 로컬 타임존(Asia/Seoul)과 서버 타임존(UTC) 혼용 방지
- 파티션/지연 도착(late arriving) 처리 단순화
- 파싱/쿼리 일관성 유지

---

## 이벤트별 Payload (event_type 별 가변)

Raw 이벤트는 `payload`를 유연하게 유지합니다.  
정규화는 Silver/Gold에서 수행합니다.

### view

```json
{
  "payload": {
    "product_id": "P000123",
    "category_id": "C01",
    "brand": "Nova",
    "price": 12900,
    "page": "search",
    "position": 7
  }
}
```

### search

```json
{
  "payload": {
    "query": "headphones",
    "results_count": 42
  }
}
```

### add_to_cart

```json
{
  "payload": {
    "product_id": "P000123",
    "category_id": "C01",
    "brand": "Nova",
    "price": 12900,
    "quantity": 2
  }
}
```

### purchase

```json
{
  "payload": {
    "product_id": "P000123",
    "category_id": "C01",
    "brand": "Nova",
    "price": 12900,
    "quantity": 2,
    "order_id": "O01234567",
    "total_amount": 25800,
    "payment_method": "card",
    "coupon_id": "CP10"
  }
}
```

### refund

```json
{
  "payload": {
    "order_id": "O01234567",
    "refund_amount": 25000,
    "reason_code": "late_delivery"
  }
}
```

---

## 스키마 진화 (Schema Evolution)

`schema_version`는 필드 추가/변경이 발생할 때 증가합니다.

예:
- v1: `device`에 `os`, `app_version`, `device_model`만 존재
- v2: `device.os_version` 필드 추가

Downstream(Silver/Gold)은 다음을 보장해야 합니다.
- 구버전 이벤트에서 필드가 없어도 처리 가능(기본값/nullable)
- 버전별 차이를 명시적으로 처리(예: v1에는 os_version 없음)

---

## 더티 데이터/현실적 수집 이슈 (Expected Anomalies)

현업 유사성을 위해 다음 이상치가 일부 포함될 수 있습니다.

- **지연 도착(Late arriving):** `ingest_time`이 `event_time`보다 수 시간 이후
- **중복 재전송(Duplicate resend):** 동일 `event_id`가 2회 이상 등장 가능
- **결측(Missing):** user_id/session_id/product_id가 null일 수 있음
- **타입 드리프트(Type drift):** 숫자 필드가 문자열로 들어올 수 있음(예: `"price": "12900"`)
- **참조 무결성 깨짐:** catalog에 존재하지 않는 product_id가 일부 포함될 수 있음

Downstream 파이프라인은 위 케이스를 “예외”가 아닌 “정상적으로 발생 가능한 입력”으로 취급해야 합니다.