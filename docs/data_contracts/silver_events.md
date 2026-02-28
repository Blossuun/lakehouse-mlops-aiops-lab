# Silver 이벤트 계약서 (Parquet)

이 문서는 Raw(JSONL) 이벤트를 정제하여 Silver(Parquet)로 저장할 때의
**스키마(고정 컬럼)**, **정제 규칙**, **저장 경로**를 정의합니다.

Silver 레이어의 목적은 “원본 보존”이 아니라,
**분석/처리 가능한 구조화(typed, columnar) 데이터**를 만드는 것입니다.

---

## 저장 레이아웃

Bucket: `datalake`

Prefix 규칙:

```
silver/events/dt=YYYY-MM-DD/part-00000.parquet
```

예시:

```
s3://datalake/silver/events/dt=2026-02-27/part-00000.parquet
```

- `dt=YYYY-MM-DD`는 파티션 키(UTC 기준)입니다.
- Silver는 데이터량에 따라 `part-00000.parquet`, `part-00001.parquet`처럼 여러 파일(part)로 저장됩니다.
- 초기에는 part가 1개일 수도 있으며, row batch size 설정에 따라 파트 수가 결정됩니다.

---

## Silver 스키마 (고정 컬럼)

### 공통 컬럼

| 컬럼 | 타입 | 설명 |
|---|---|---|
| event_id | string | Raw의 event_id (중복 제거 키) |
| schema_version | int32 | Raw schema_version |
| event_type | string | view/search/add_to_cart/purchase/refund |
| event_time | timestamp(ms, UTC) | Raw event_time 파싱 결과 |
| ingest_time | timestamp(ms, UTC) | Raw ingest_time 파싱 결과 |
| user_id | string (nullable) | Raw user_id |
| session_id | string (nullable) | Raw session_id |
| device_os | string (nullable) | device.os |
| device_os_version | string (nullable) | device.os_version (v2에서만 존재 가능) |
| device_app_version | string (nullable) | device.app_version |
| geo_country | string (nullable) | geo.country |
| geo_region | string (nullable) | geo.region |
| geo_city | string (nullable) | geo.city |
| source_referrer | string (nullable) | source.referrer |
| source_utm_campaign | string (nullable) | source.utm_campaign |
| source_utm_medium | string (nullable) | source.utm_medium |

### Payload 핵심 컬럼(실무형)

payload는 event_type별로 가변이지만,
분석/ML에 자주 쓰는 핵심 필드는 컬럼으로 승격합니다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| product_id | string (nullable) | payload.product_id |
| category_id | string (nullable) | payload.category_id |
| brand | string (nullable) | payload.brand |
| price | int64 (nullable) | payload.price (문자열이면 정수로 캐스팅) |
| quantity | int32 (nullable) | payload.quantity |
| order_id | string (nullable) | payload.order_id |
| total_amount | int64 (nullable) | payload.total_amount |
| payment_method | string (nullable) | payload.payment_method |
| coupon_id | string (nullable) | payload.coupon_id |
| search_query | string (nullable) | payload.query (search 이벤트) |
| results_count | int32 (nullable) | payload.results_count |
| refund_amount | int64 (nullable) | payload.refund_amount |
| reason_code | string (nullable) | payload.reason_code |

### 원본 payload 보존(선택)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| payload_json | string (nullable) | payload 전체를 JSON 문자열로 보관(디버깅/추후 확장용) |

> payload_json은 “나중에 컬럼을 더 뽑고 싶을 때” 유용합니다.
> Silver에선 컬럼화를 우선하지만, 과한 손실을 피하기 위해 남겨둡니다.

---

## 정제 규칙 (Raw → Silver)

### 1) 중복 제거 (Dedup)

- 기준: `event_id`
- 정책: 같은 `event_id`가 여러 번 나오면 **가장 빠른 ingest_time(또는 첫 등장)** 을 1개만 남깁니다.

> Raw는 at-least-once 전달을 흉내내기 때문에 중복이 존재할 수 있습니다.
> Silver에서 중복을 제거하여 분석/모델링의 안정성을 확보합니다.

### 2) 시간 파싱

- Raw의 `event_time`, `ingest_time`은 ISO8601(UTC) 문자열
- Silver에서는 timestamp(ms, UTC)로 변환해 저장합니다.
- 파싱 불가/결측 시 null 허용(단, 향후 품질 테스트에서 관리)

### 3) 타입 정규화 (Type normalization)

- 예: `"price": "12900"` → `price=12900` (int64)
- 변환 실패 시 null로 저장(향후 품질 규칙에서 관리)

### 4) 스키마 진화 대응

- schema_version이 달라도 Silver 스키마는 고정
- 없는 필드는 null로 저장
  - 예: v1에는 device_os_version이 없을 수 있음

### 5) 더티 데이터 허용

Raw에는 결측/타입 드리프트가 일부 존재합니다.
Silver는 가능한 범위에서 정규화하되,
완전 배제(drop)보다는 “null 처리 + 품질 규칙”으로 관리합니다.

---

## 기대 효과

- JSONL 대비 훨씬 빠른 스캔/필터/집계(컬럼 포맷: Parquet)
- 스키마 고정으로 downstream SQL/ML 작업 단순화
- 중복/타입 문제의 영향 축소
- Iceberg/Spark/dbt로 이어지는 구조화 레이어 확보