# ADR-0010: Read-Only Analysis Dashboard

## Status

Accepted

---

## Context

현재 프로젝트는 다음 레이어를 이미 갖고 있다.

- raw ingestion
- Silver transform
- Iceberg storage
- quality gate
- Gold metrics
- dbt analytics layer
- Trino query layer

하지만 실제 사용 관점에서 보면 아직 한 단계가 빠져 있다.

즉, 사용자는 현재:

- SQL 파일을 직접 선택하고
- 스크립트로 실행하고
- 결과를 텍스트로 확인해야 한다

이 구조는 query layer로는 충분하지만,
실제 분석 소비 계층으로는 불편하다.

프로젝트 목적상 이제는
"데이터를 만드는 시스템"을 넘어
"데이터를 실제로 소비하는 시스템"까지 보여줄 필요가 있다.

---

## Decision

다음 원칙으로 read-only 분석 대시보드를 추가한다.

### 1. UI는 Streamlit을 사용한다

이유:

- 로컬 실행이 쉽다
- 빠르게 분석용 UI를 만들 수 있다
- Python 기반이라 현재 프로젝트와 자연스럽게 연결된다

### 2. 데이터 조회는 Trino를 통해 수행한다

대시보드는 Spark나 MinIO 파일을 직접 읽지 않는다.

대신:

- Trino를 단일 query engine으로 사용
- 기존 query layer와 동일한 소비 경로를 유지

즉, dashboard는 query layer 위에 놓이는 소비 계층이다.

### 3. 대시보드는 read-only로 유지한다

이번 단계에서는 다음을 하지 않는다.

- 데이터 수정
- write-back
- 운영 제어
- pipeline trigger

즉, dashboard는 관찰과 조회만 담당한다.

### 4. 대시보드는 Gold + Silver를 함께 소비할 수 있다

- overview / funnel 같은 요약 지표는 Gold 사용
- top products 같은 raw-ish 분석은 Silver 사용

즉, dashboard는 현재 프로젝트의 레이어 구성을 실제 사용 시나리오로 드러낸다.

---

## Consequences

### 장점

- 프로젝트가 실제 소비 계층까지 완성된다
- SQL query layer 위에 사용자 친화적인 인터페이스가 생긴다
- Gold / Silver 사용 위치가 더 명확해진다
- 이후 BI/API 레이어로 확장하기 쉬워진다

### 단점

- dashboard 실행을 위한 추가 dependency가 생긴다
- Streamlit이라는 UI 계층을 유지해야 한다
- local 환경에서는 Trino가 반드시 실행 중이어야 한다

---

## Non-Goals

이번 ADR은 다음을 목표로 하지 않는다.

- production-grade dashboard
- auth / RBAC
- multi-user serving
- alerting / scheduling
- write-enabled control panel

현재 목표는
**프로젝트의 read-only 소비 계층 완성**이다.

---

## Notes

현재 dashboard는 local baseline을 기준으로 한다.

즉:

- Trino가 실행 중이어야 한다
- local Docker / WSL 기준으로 사용한다
- 이후 필요하면 API layer나 BI integration으로 확장할 수 있다