# Silver 데이터 품질 규칙

대상 테이블:

- `local.lakehouse.silver_events`

검증 단위:

- `dt=YYYY-MM-DD` 파티션 단위

---

## 현재 설계 원칙

현재 품질 게이트는 **파티션 단위 fail-fast 검증**을 목표로 한다.

즉:

- 특정 `dt` 파티션이 downstream 사용에 적합한지 검사한다
- 하나라도 FAIL이면 전체 품질 게이트는 실패한다
- 결과는 JSON report로 object storage에 기록한다

또한 현재 구현은 로컬 Spark / Docker / WSL 환경에서도 재실행 가능하도록,
가능한 한 **단일 집계 기반(single-pass aggregate 중심)** 으로 규칙 수치를 계산하는 방향을 따른다.

이 문서의 목적은 규칙 의미를 정의하는 것이며,
물리적 실행 계획이나 엔진 내부 최적화를 규정하지는 않는다.

---

## 규칙 목록

### Rule 1. 파티션 데이터가 비어 있지 않아야 한다

- 조건: `count(*) > 0`
- 실패 시: FAIL

### Rule 2. event_id 중복이 없어야 한다

- 조건: `select event_id distinct count` 기준으로 중복이 없어야 한다
- 해석:
  - non-null `event_id`는 중복 없이 유일해야 한다
  - `null`은 현재 별도의 not-null 규칙으로 강제하지 않으며,
    distinct 계산에서는 하나의 값처럼 취급한다
- 실패 시: FAIL

현재 Rule 2의 목적은 uniqueness 검증이다.
즉, `event_id`의 non-null 강제는 이 규칙의 범위가 아니다.
`event_id` 자체의 not-null 강제가 필요하면 별도 규칙으로 추가한다.

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

---

## Non-Goals

현재 품질 게이트는 다음을 하지 않는다.

- 데이터를 자동 수정하지 않는다
- quarantine dataset 을 생성하지 않는다
- WARN / FAIL 을 다단계로 나누지 않는다
- full-table validation 을 기본 경로로 사용하지 않는다

현재 단계의 목표는 **파티션 단위 신뢰성 검증**이다.