# ADR-0007: dbt + Trino Analytics Layer

## Status

Accepted

---

## Context

현재 데이터 플랫폼 구조

```text
Spark -> Iceberg write engine
Trino -> query engine
Hive Metastore -> shared catalog
```

Silver 데이터는 Iceberg 테이블에 저장된다.

기존 방식에서는 analytics 모델을 Spark job 으로 구현할 수 있다.

하지만 Spark 기반 모델링은 다음 문제가 있다.

- SQL 모델 의존성 관리 어려움
- analytics 모델 테스트 어려움
- lineage 확인 어려움
- 데이터 처리 코드와 분석 모델이 혼합됨

또한 이 프로젝트는 이미 Spark 기반 Gold aggregate layer 를 갖고 있다.

하지만 Gold 레이어의 존재가 곧 analytics workflow 를 Spark 안에 모두 두어야 한다는 의미는 아니다.

현재 프로젝트는 다음 두 가지를 동시에 달성하려 한다.

1. Spark 기반 pipeline aggregate layer 유지
2. Trino + dbt 기반 analytics engineering workflow 확립

---

## Decision

analytics layer 는 다음 구조로 구성한다.

```text
Trino -> query engine
dbt -> analytics modeling
```

dbt 는 다음 역할을 수행한다.

- analytics SQL 모델 관리
- 모델 dependency graph 관리
- 데이터 테스트 수행
- lineage 제공

모델 계층

```text
source -> staging -> intermediate -> marts
```

현재 기준에서 dbt marts 는 다음 원칙을 따른다.

- analyst / BI / ad hoc query 친화적 semantic layer 를 제공한다
- shared Iceberg catalog 위에서 Trino 를 통해 모델을 구성한다
- Spark Gold 를 직접 감싸는 구조로 두지 않는다
- 현재 source 는 `iceberg.lakehouse.silver_events` 이다

즉, dbt marts 는 **analytics-owned semantic layer** 이며,
Spark Gold aggregate layer 와는 ownership 이 다르다.

---

## Consequences

장점

- analytics engineering workflow 확립
- SQL 중심 분석 모델 개발
- 데이터 테스트 가능
- lineage 자동 생성
- Spark pipeline aggregate 와 analytics semantic layer 를 분리 가능

단점

- Trino query 비용 증가 가능
- dbt toolchain 관리 필요
- Spark Gold 와 개념적으로 겹치는 지표가 존재할 수 있음

하지만 analytics workflow 측면에서 장점이 더 크다.

---

## Relationship to Spark Gold

이 ADR은 Spark Gold aggregate layer 를 대체하지 않는다.

현재 프로젝트에서:

- Spark Gold = platform-owned aggregate layer
- dbt marts = analytics-owned semantic layer

두 레이어는 비슷한 일별 지표를 다룰 수 있지만,
현재는 서로 다른 목적과 소비자를 위한 별도 레이어로 유지한다.

소비 원칙:

- Spark Gold: pipeline / batch / programmatic consumption 우선
- dbt marts: analyst / BI / ad hoc analytics consumption 우선

---

## Notes

이 결정은 다음 단계에서 확장될 수 있다.

- dbt incremental 모델
- dbt docs lineage
- CI 기반 dbt validation
- Spark Gold 와 dbt marts 의 관계 재조정
- 특정 aggregate 를 Gold 기반 source 로 재구성할지 여부 재검토

하지만 현재 단계에서는
dbt marts 를 Spark Gold 의 단순 래퍼로 만들지 않고,
shared catalog 위에서 독립적인 analytics layer 로 유지한다.