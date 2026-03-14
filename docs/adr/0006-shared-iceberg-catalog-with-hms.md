# ADR 0006 - Shared Iceberg Catalog via Hive Metastore

## 배경

현재 프로젝트는 Spark + Iceberg + MinIO 기반으로 동작한다.

기존 Spark 설정은 다음과 같았다.

- SparkCatalog
- type = hadoop
- warehouse = s3a://datalake/warehouse

이 방식은 Spark 단독으로는 단순하고 잘 동작한다.
하지만 Trino를 붙여 같은 Iceberg 테이블을 읽으려면
공유 가능한 catalog가 필요하다.

## 문제

기존 Spark의 Hadoop catalog는 Spark 내부 catalog 설정에 가깝고,
Trino의 Iceberg connector는 별도의 catalog/metastore 구성을 요구한다.

즉, 현재 상태에서는:

- Spark는 읽고 쓸 수 있음
- Trino는 같은 Iceberg를 바로 읽기 어려움

## 결정

공유 가능한 Iceberg catalog로 Hive Metastore(HMS)를 도입한다.

이번 PR에서:
- Hive Metastore 추가
- Spark catalog를 `type=hive`로 전환
- Trino Iceberg catalog를 HMS에 연결
- smoke로 Spark write / Trino read 확인

## 왜 Hive Metastore인가

REST catalog도 좋은 방향이지만,
현재 로컬 PoC에서는 별도 REST catalog 서비스 구성까지 들어가면 복잡도가 높아진다.

Hive Metastore는:
- Spark + Iceberg 구성에 익숙하고
- Trino에서도 바로 연결 가능하며
- 지금 목표인 "shared catalog 확인"에 가장 직접적이다.

## 왜 dbt-trino를 지금 같이 하지 않는가

shared catalog가 안정화되기 전에는
문제의 원인이 catalog인지, Trino인지, dbt인지 분리하기 어렵다.

따라서 이번 PR은:
- Spark write
- Trino read

까지로 범위를 제한한다.

그 다음 PR에서:
- dbt-trino
- Gold 모델 이식
을 진행한다.

## 이번 PR에서 하지 않는 것

- dbt-trino 도입
- Gold Spark job 제거
- REST catalog / Nessie 도입