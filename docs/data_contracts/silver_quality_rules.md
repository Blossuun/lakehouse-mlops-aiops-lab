# Silver 데이터 품질 규칙

대상 테이블:

- `local.lakehouse.silver_events`

검증 단위:

- `dt=YYYY-MM-DD` 파티션 단위

---

## 규칙 목록

### Rule 1. 파티션 데이터가 비어 있지 않아야 한다
- 조건: `count(*) > 0`
- 실패 시: FAIL

### Rule 2. event_id 중복이 없어야 한다
- 조건: `count(event_id) == count(distinct event_id)`
- 실패 시: FAIL

### Rule 3. event_type은 허용 집합 안에 있어야 한다
허용 값:
- `view`
- `search`
- `add_to_cart`
- `purchase`
- `refund`

- 실패 조건: 허용 집합 외 값 존재
- 실패 시: FAIL

### Rule 4. schema_version은 허용 범위 안에 있어야 한다
허용 값:
- `1`
- `2`

- 실패 조건: null 또는 허용 범위 외 값 존재
- 실패 시: FAIL

### Rule 5. event_time, ingest_time null 비율은 0이어야 한다
- 실패 조건: null count > 0
- 실패 시: FAIL

### Rule 6. event_time > ingest_time 비율은 허용 임계치 이하여야 한다
- 조건: `event_time <= ingest_time` 가 대부분이어야 함
- 허용 임계치: 5%
- 실패 시: FAIL

### Rule 7. price / total_amount / refund_amount는 음수가 아니어야 한다
- 실패 조건: 음수 값 존재
- 실패 시: FAIL

### Rule 8. purchase 이벤트는 order_id가 있어야 한다
- 실패 조건: `event_type='purchase' and order_id is null`
- 실패 시: FAIL

### Rule 9. search 이벤트는 search_query가 있어야 한다
- 실패 조건: `event_type='search' and search_query is null`
- 실패 시: FAIL

### Rule 10. refund 이벤트는 refund_amount가 있어야 한다
- 실패 조건: `event_type='refund' and refund_amount is null`
- 실패 시: FAIL

---

## 결과 처리 방식

- 각 규칙은 개별 pass/fail 결과를 가진다
- 하나라도 FAIL이면 전체 품질 게이트는 실패한다
- 결과는 JSON report로 object storage에 저장한다