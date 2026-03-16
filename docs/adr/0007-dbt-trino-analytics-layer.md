# ADR-0007: dbt + Trino Analytics Layer

## Status

Accepted

---

## Context

현재 데이터 플랫폼 구조

```
Spark → Iceberg write engine
Trino → query engine
Hive Metastore → shared catalog
```

Silver 데이터는 Iceberg 테이블에 저장된다.

기존 방식에서는 analytics 모델을 Spark job으로 구현할 수 있다.

하지만 Spark 기반 모델링은 다음 문제가 있다.

- SQL 모델 의존성 관리 어려움
- analytics 모델 테스트 어려움
- lineage 확인 어려움
- 데이터 처리 코드와 분석 모델이 혼합됨

---

## Decision

analytics layer는 다음 구조로 구성한다.

```
Trino → query engine
dbt → analytics modeling
```

dbt는 다음 역할을 수행한다.

- analytics SQL 모델 관리
- 모델 dependency graph 관리
- 데이터 테스트 수행
- lineage 제공

모델 계층

```
source → staging → intermediate → marts
```

---

## Consequences

장점

- analytics engineering workflow 확립
- SQL 중심 분석 모델 개발
- 데이터 테스트 가능
- lineage 자동 생성

단점

- Trino query 비용 증가 가능
- dbt toolchain 관리 필요

하지만 analytics workflow 측면에서 장점이 더 크다.

---

## Notes

이 결정은 다음 단계에서 확장될 수 있다.

- dbt incremental 모델
- dbt docs lineage
- CI 기반 dbt validation