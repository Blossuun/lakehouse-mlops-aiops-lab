Learning note

# 0012 - dbt + Trino Analytics Layer

## 배경

현재 프로젝트는 다음 구조의 lakehouse를 기반으로 한다.

    Spark  -> write engine
    Trino  -> query engine
    HMS    -> shared Iceberg catalog
    MinIO  -> object storage

이 구조에서 Spark는 데이터 처리 파이프라인을 담당한다.

    Raw ingestion
    -> Silver transform
    -> Iceberg table
    -> Data quality gate
    -> Gold metrics

하지만 analytics 모델을 Spark job으로 계속 작성하는 것은 몇 가지 문제가 있다.

- SQL 모델 의존성 관리 어려움
- 분석 모델 테스트 어려움
- 모델 lineage 확인 어려움
- 데이터 파이프라인 코드와 분석 모델 혼합

그래서 analytics modeling layer를 별도로 두기로 했다.

---

## 선택

analytics layer는 다음 구조로 구성했다.

    Trino -> query engine
    dbt   -> analytics modeling

모델 계층

    source
    -> staging
    -> marts

---

## 이번 단계에서 한 일

1. dbt project bootstrap

    uv run dbt init analytics

2. dbt profile template 구성

    analytics/profiles/profiles.yml.template

3. dbt profile render script 작성

    scripts/render_dbt_profile.ps1

4. dbt source 정의

    iceberg.lakehouse.silver_events

5. staging 모델 작성

    stg_silver_events

6. mart 모델 작성

    fct_daily_events
    fct_daily_revenue
    fct_daily_conversion

7. analytics smoke test 작성

    scripts/smoke_dbt_trino_analytics.ps1

---

## 구현 과정에서 겪은 문제

### 1. dbt init 실행 위치 문제

처음 dbt 프로젝트를 생성할 때 다음 문제가 발생했다.

    analytics/analytics/

같은 중첩 디렉토리가 생성되었다.

원인

    dbt init analytics

명령을 이미 analytics 디렉토리 안에서 실행했기 때문이다.

즉

    analytics/
        -> dbt init analytics

구조가 되었다.

해결

프로젝트 root에서 실행

    uv run dbt init analytics

배운 점

dbt init은 항상 **프로젝트 root에서 실행**하는 것이 안전하다.

---

### 2. dbt catalog not found 오류

초기 dbt 실행 시 다음 오류가 발생했다.

    Catalog 'local' not found

원인

Trino catalog 설정이 template 상태였다.

    infra/trino/catalog/iceberg.properties.template

실제 catalog 파일이 생성되지 않았다.

해결

다음 스크립트를 실행

    scripts/render_catalog_configs.ps1

그리고 Trino 재시작

배운 점

template 기반 config 구조에서는  
컨테이너 시작 전에 **render 단계가 반드시 필요하다.**

---

### 3. Iceberg schema가 존재하지 않는 문제

Trino 확인

    SHOW SCHEMAS FROM iceberg

결과

    default
    system
    test

lakehouse schema 없음

원인

Silver transform은 Iceberg 테이블을 생성하지 않는다.

다음 명령은

    raw_to_silver_events

Parquet 파일만 생성한다.

---

### 4. Silver Parquet -> Iceberg table 승격 과정

Silver transform

    uv run python -m lakehouse_mlops_aiops_lab.transform.raw_to_silver_events

이 단계는 다음 위치에 Parquet만 생성한다.

    s3://datalake/silver/events/

Iceberg table은 다음 스크립트로 생성한다.

    scripts/smoke_iceberg_table.ps1

이 스크립트가 실행되어야

    iceberg.lakehouse.silver_events

테이블이 생성된다.

배운 점

lakehouse 파이프라인은 다음 단계를 따른다.

    Raw
    -> Silver Parquet
    -> Iceberg table
    -> Query engine
    -> Analytics layer

---

### 5. dbt source schema 문제

처음 dbt source를 다음으로 정의했다.

    local.lakehouse.silver_events

하지만 실제 Trino catalog 이름은

    iceberg

였다.

그래서 dbt source를 다음으로 수정했다.

    iceberg.lakehouse.silver_events

---

### 6. dbt test generic syntax 변경

dbt 실행 시 다음 경고가 발생했다.

    MissingArgumentsPropertyInGenericTestDeprecation

원인

generic test 문법이 변경되었다.

기존

    accepted_values:
        values: [...]

수정

    accepted_values:
        arguments:
            values: [...]

---

## 궁금증

### dbt mart SQL이 성능을 고려하지 않은 이유

작성한 mart SQL은 다음 특징이 있다.

    count(distinct ...)
    case when ...
    반복 조건 집계

이 SQL은 성능 최적화된 형태는 아니다.

하지만 현재 단계에서는 문제가 없다.

이유

1. 데이터 규모가 작다
2. PR 목표는 analytics layer 구조 검증
3. 성능 최적화는 이후 단계에서 가능

즉 현재 SQL은

    구조 검증용 analytics 모델

이다.

---

## 최종 결과

dbt analytics layer 정상 동작

    dbt run
    dbt test

성공

Trino에서 다음 mart 조회 가능

    iceberg.analytics.fct_daily_events
    iceberg.analytics.fct_daily_revenue
    iceberg.analytics.fct_daily_conversion

---

## 이번 단계의 의미

현재 프로젝트 구조

    Raw ingestion
    -> Silver transform
    -> Iceberg table
    -> Data quality gate
    -> Gold metrics
    -> Shared Iceberg catalog
    -> dbt analytics layer

이 단계가 끝나면서 프로젝트는

    multi-engine lakehouse + analytics modeling

구조로 발전했다.
