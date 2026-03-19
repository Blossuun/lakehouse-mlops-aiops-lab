# ADR-0008: Metric Layer Ownership (Spark Gold vs dbt Analytics Marts)

## Status

Accepted

---

## Context

현재 프로젝트에는 지표를 다루는 두 개의 레이어가 존재한다.

1. Spark가 생성하는 Gold metrics 테이블
2. Trino + dbt가 생성하는 analytics marts

현재 구조:

```text
Raw ingestion
  -> Silver transform
  -> Iceberg table
  -> Data quality gate
  -> Gold metrics
  -> Shared Iceberg catalog
  -> dbt analytics layer
```

이 두 레이어는 모두 일별 이벤트/매출/전환 관련 지표를 다룰 수 있기 때문에,
문서상 책임 경계가 불분명하면 다음과 같은 혼란이 생긴다.

- 어떤 레이어가 어떤 소비자를 위한 것인지 불명확
- 비슷한 지표가 두 군데 있을 때 어느 쪽을 참조해야 하는지 불명확
- 이후 PR에서 새로운 지표를 어느 레이어에 추가해야 하는지 판단 기준 부족

즉, 현재 프로젝트에는 “지표 레이어가 2개 있다”는 사실보다
“각 레이어의 소유권과 역할이 다르다”는 점을 명시적으로 정의할 필요가 있다.

---

## Decision

### 1. Spark Gold는 platform-owned aggregate layer 로 정의한다

Spark Gold 테이블은 다음 역할을 가진다.

- Spark 배치 파이프라인이 생성하는 집계 결과
- `dt` 파티션 기반으로 반복 실행 가능한 운영 집계 테이블
- 데이터 플랫폼 내부의 프로그램적 소비 대상
- 이후 batch, downstream pipeline, feature preparation 에 활용 가능한 aggregate layer

즉, Spark Gold는 **pipeline-owned / platform-owned aggregate layer** 이다.

---

### 2. dbt marts는 analytics-owned semantic layer 로 정의한다

dbt marts는 다음 역할을 가진다.

- analyst / BI / ad hoc query 친화적 모델
- Trino + dbt 기반 analytics engineering workflow 의 결과물
- 모델 테스트, 의존성 관리, lineage, semantic presentation 을 담당하는 레이어

즉, dbt marts는 **analytics-owned semantic presentation layer** 이다.

---

### 3. 현재 dbt marts는 Spark Gold를 직접 감싸지 않는다

현재 프로젝트에서 dbt marts의 source는 Spark Gold가 아니라 Silver Iceberg 테이블이다.

이 선택은 의도적이다.

이유:

- analytics layer 를 Spark Gold 산출물에 직접 종속시키지 않기 위함
- shared catalog 위에서 Trino + dbt 모델링을 독립적으로 검증하기 위함
- Spark pipeline ownership 과 analytics modeling ownership 을 분리하기 위함

따라서 현재 구조에서 Spark Gold 와 dbt marts 는
“같은 테이블의 다른 표현”이 아니라,
**서로 다른 ownership 과 목적을 가진 두 개의 레이어**이다.

---

### 4. 소비 원칙을 다음과 같이 정의한다

#### Spark Gold를 우선적으로 사용하는 경우

- Spark / batch / pipeline 기반 후속 처리
- programmatic consumption 이 중요한 경우
- 플랫폼 내부 aggregate artifact 가 필요한 경우
- 운영 파이프라인 관점의 안정적 집계 출력이 필요한 경우

#### dbt marts를 우선적으로 사용하는 경우

- analyst / BI / ad hoc SQL 사용
- semantic naming / analytics-friendly schema 가 중요한 경우
- dbt tests / lineage / model dependency 가 중요한 경우
- dashboard / reporting / analytics presentation 이 목적일 경우

---

### 5. 개념상 겹치는 지표가 있어도 ownership 은 분리한다

Spark Gold 와 dbt marts 에서 비슷한 일별 지표를 다룰 수 있다.

하지만 이는 현재 프로젝트에서 허용되는 중복이다.

이 중복은 우연한 중복이 아니라 다음을 위한 구조적 선택이다.

- 플랫폼 레이어와 analytics 레이어 분리
- Spark 와 dbt 각각의 워크플로우 검증
- multi-engine lakehouse 학습 목적 유지

단, 개념적으로 같은 비즈니스 지표를 다루는 경우에는
정의와 의미가 불필요하게 어긋나지 않도록 문서화해야 한다.

---

## Consequences

### 장점

- Spark Gold 와 dbt marts 의 책임 경계가 명확해진다
- 이후 지표 추가 PR 에서 어느 레이어에 넣어야 하는지 판단 기준이 생긴다
- 플랫폼 지표와 analytics 지표를 같은 것으로 오해하는 일을 줄일 수 있다
- 현재 프로젝트의 multi-layer / multi-engine 설계 의도가 더 분명해진다

### 단점

- 비슷한 개념의 지표가 두 레이어에 모두 존재할 수 있다
- 지표 의미를 문서로 계속 정렬해야 한다
- “하나의 절대적 단일 지표 레이어”를 기대하는 사람에겐 다소 복잡해 보일 수 있다

하지만 현재 프로젝트 단계에서는
하나의 레이어로 통합하는 것보다
ownership 을 분리해 두는 편이 더 현실적이다.

---

## Non-Goals

이 ADR은 다음을 하지 않는다.

- Spark Gold 를 제거하지 않는다
- dbt marts 를 Spark Gold 기반으로 재설계하지 않는다
- 어느 한쪽만 “유일한 전체 시스템의 단일 source of truth” 라고 선언하지 않는다
- 실제 지표 계산 로직을 변경하지 않는다

이 ADR의 목적은 **역할과 소유권을 명확히 하는 것**이다.

---

## Notes

향후 다음과 같은 방향은 다시 검토할 수 있다.

- dbt marts 가 Spark Gold 를 source 로 사용하도록 재구성
- semantic metric definition layer 추가
- BI / dashboard 레이어의 canonical dataset 재정의
- Gold / marts 간 중복 지표 축소

하지만 현재 단계에서는 다음 원칙을 유지한다.

- Spark Gold = platform aggregate layer
- dbt marts = analytics semantic layer
- 둘은 다른 소비자와 다른 워크플로우를 위한 레이어다