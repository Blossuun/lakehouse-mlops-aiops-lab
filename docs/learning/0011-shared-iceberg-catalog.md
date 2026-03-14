Learning note

# 0011 - Shared Iceberg Catalog (Spark + Trino)

## 배경

기존 프로젝트는 Spark를 중심으로 Iceberg를 사용했다.

구조

    Spark
      -> Iceberg (SparkCatalog, type=hadoop)
      -> MinIO

이 구조는 Spark 단독으로는 잘 동작했다.  
하지만 Trino나 dbt 같은 다른 엔진을 붙여 같은 Iceberg 테이블을 읽으려면  
공유 가능한 catalog가 필요했다.

---

## 문제

기존 Spark의 Hadoop catalog는  
Spark 단독 사용에는 편하지만  
다른 query engine이 바로 공유해서 읽기엔 적합하지 않았다.

즉

- Spark는 write 가능
- Trino는 같은 Iceberg를 바로 read 하기 어려움

이 문제가 있었다.

---

## 해결

Iceberg catalog를 Hive Metastore 기반 shared catalog로 전환했다.

구조

    Spark  -> write
    Trino  -> read
    HMS    -> shared Iceberg catalog
    MinIO  -> object storage

---

## 이번 단계에서 한 일

1. Hive Metastore 추가
2. Postgres에 metastore DB 준비
3. Spark catalog를 type=hive 로 전환
4. Trino Iceberg catalog를 Hive Metastore에 연결
5. Spark write / Trino read smoke test 성공

---

## 구현 과정에서 겪은 문제

### 1. spark-sql에서 Iceberg classpath 문제

spark-sql 실행 시 다음 클래스가 로드되지 않았다.

- IcebergSparkSessionExtensions
- SparkCatalog

원인  
spark-sql 실행 시 Iceberg runtime jar가 자동으로 classpath에 올라오지 않았다.

해결  
interactive spark-sql 대신  
spark-submit --packages 기반 smoke job 사용

배운 점

- 로컬 PoC에서는 spark-sql보다 spark-submit 기반 테스트가 더 안정적이다.

---

### 2. Hive Metastore가 S3A filesystem을 찾지 못함

초기 실행 시 다음 오류가 발생했다.

    Class org.apache.hadoop.fs.s3a.S3AFileSystem not found

원인

- Spark는 --packages 로 S3A 사용 가능
- Hive Metastore 컨테이너는 해당 jar가 없음

해결

- Hive 컨테이너에 hadoop-aws
- aws-java-sdk-bundle
- core-site.xml S3A 설정 추가

배운 점

shared catalog 구조에서는  
Spark만 storage를 이해하면 충분하지 않다.

catalog backend(HMS)도 동일한 storage access를 이해해야 한다.

---

### 3. Hive dependency 캐시는 컨테이너가 아니라 호스트에서 준비

처음에는 Hive 컨테이너 시작 시 curl로 JAR를 다운로드하려 했다.

하지만 다음 문제가 있었다.

- apache/hive:4.0.0 이미지에는 curl이 없음
- 컨테이너 entrypoint 흐름과 충돌 가능

그래서 방식을 변경했다.

구조

    host script
        -> infra/hive/cache/ 에 JAR 다운로드

    docker compose
        -> cache directory mount

장점

- 컨테이너 내부 도구에 의존하지 않음
- docker compose down/up 에도 캐시 유지
- Git repo에 큰 바이너리를 커밋할 필요 없음

배운 점

의존성 캐시는  
컨테이너 내부 다운로드보다

    host cache + volume mount

방식이 단순하고 안정적이다.

---

### 4. 대용량 JAR이 Git 커밋에 포함되면서 push 실패

Hive 의존성 문제를 해결하는 과정에서  
다음 파일이 Git 커밋에 포함되었다.

    aws-java-sdk-bundle-1.12.262.jar

GitHub push 시 용량 제한으로 push가 실패했다.

이 문제를 해결하기 위해 git filter-branch 로 히스토리에서 파일을 제거했는데  
이 과정에서 모든 커밋 SHA가 변경되었다.

그 결과

    main [origin/main: ahead 88, behind 88]

상태가 되었고  
GitHub에서 PR 비교가 정상적으로 되지 않았다.

---

### 해결

히스토리를 복구하려 하지 않고  
다음 방식으로 브랜치를 재구성했다.

1. origin/main 기준 새 브랜치 생성

    git fetch origin
    git checkout -b new-branch origin/main

2. 기존 브랜치의 파일 상태만 가져오기

    git checkout broken-branch -- .

3. 문제 JAR 제거 후 새 커밋

    git rm --cached infra/hive/lib/aws-java-sdk-bundle-1.12.262.jar
    git commit
    git push

이 방식으로 PR을 정상적으로 생성할 수 있었다.

---

## Git 관련 교훈

1. 대용량 바이너리는 Git에 커밋하지 않는다

예

- JAR
- dataset
- cache
- build artifact

2. 히스토리 재작성(filter-branch)은 매우 위험하다

특히 --all 옵션은  
모든 브랜치 커밋 SHA를 변경한다.

3. Git 문제 해결 시 기준점은 항상 origin/main 이다

---

## 왜 DuckDB를 이번 단계의 주 경로로 선택하지 않았는가

DuckDB는 dbt와 잘 맞고 로컬 분석 엔진으로 훌륭하다.

하지만 이번 프로젝트의 목표는 다음 구조다.

    Spark + MinIO + Iceberg + shared catalog

즉 여러 엔진이 같은 lakehouse를 공유하는 구조다.

이 역할에는 Trino가 더 적합하다.

---

## 이번 단계의 의미

현재 프로젝트 구조

    Raw ingestion
    -> Silver transform
    -> Iceberg table
    -> Iceberg ops
    -> Data quality gate
    -> Gold metrics
    -> Shared Iceberg catalog

이 단계가 끝나면서 프로젝트는

Spark 단일 파이프라인 → multi-engine lakehouse

구조로 발전했다.

다음 단계

    Trino + dbt-trino