# assistant_context.md

**Project Context Snapshot for AI Assistants**

이 문서는 ChatGPT 또는 다른 LLM 기반 도구에서
현재 프로젝트의 컨텍스트를 복원하기 위한 문서이다.

새로운 스레드에서 이 문서를 제공하면
이전 대화 맥락 없이도 프로젝트를 이어서 진행할 수 있다.

---

# 1. Project Overview

프로젝트 이름

lakehouse-mlops-aiops-lab

프로젝트 목적

데이터 엔지니어 → ML 엔지니어 → AI 엔지니어로 이어지는
실무형 데이터 플랫폼 구축 프로젝트.

특징

* 프로젝트 기반 학습
* 실제 업무 환경을 모방한 데이터 플랫폼 구축
* GitHub PR 단위 개발
* 재현 가능한 로컬 인프라
* 최신 데이터 엔지니어링 스택 사용

---

# 2. Core Technology Stack

현재 프로젝트의 핵심 기술 스택

Spark
Iceberg
Trino
Hive Metastore
MinIO (S3 compatible object storage)
Postgres
dbt (Trino 기반 analytics layer)

---

# 3. Current Architecture

현재 로컬 환경의 Lakehouse 구조

Spark → write engine
Trino → query engine
Hive Metastore → shared Iceberg catalog
MinIO → object storage
Postgres → Hive Metastore database

데이터 흐름

Raw data
→ Spark ingestion
→ Silver transform
→ Iceberg tables
→ Shared catalog
→ Trino queries

---

# 4. Repository Structure (important parts)

프로젝트 핵심 디렉터리 구조

project root

infra

* docker-compose.yml
* hive
* trino
* spark

scripts

* smoke scripts
* environment preparation scripts

jobs

* spark jobs

docs

* adr (architecture decision records)
* learning (learning notes)

---

# 5. Infrastructure Design Principles

이 프로젝트의 인프라 설계 원칙

1. reproducible local environment
2. GitHub repository clean 유지
3. large binary artifacts commit 금지
4. infra configuration는 코드로 관리
5. smoke test 기반 검증

---

# 6. Hive Metastore Dependency Handling

Hive Metastore는 S3A filesystem 접근을 위해 다음 의존성이 필요하다.

hadoop-aws
aws-java-sdk-bundle

하지만 이 파일들은 매우 크기 때문에 Git에 포함하지 않는다.

대신 다음 방식으로 처리한다.

* 호스트 캐시 디렉터리 사용

infra/hive/cache

* 스크립트가 필요한 파일을 다운로드

scripts/prepare_hive_cache.ps1

이 방식의 장점

* Git repository clean 유지
* 대용량 바이너리 commit 방지
* docker compose down/up 반복 시 재다운로드 방지

---

# 7. Configuration Template System

민감한 credential이나 환경 의존 설정은
template 기반으로 생성한다.

예

core-site.xml.template
iceberg.properties.template

실제 파일은 다음 스크립트로 생성

scripts/render_catalog_configs.ps1

환경 변수는 다음 파일에서 관리

infra/.env

---

# 8. Smoke Test

Shared Iceberg catalog 검증용 smoke script

scripts/smoke_shared_catalog_spark_trino.ps1

검증 내용

1. Spark가 Iceberg 테이블 생성 및 write
2. Trino가 같은 테이블 read

예상 결과

OK: Shared Iceberg catalog smoke passed

테스트 테이블

local.test.catalog_smoke

테이블은 smoke 실행 시마다 재생성되므로
deterministic 하게 동작한다.

---

# 9. Major Implementation Milestones

현재까지 완료된 단계

1. project bootstrap
2. local infra 구축
3. raw ingestion pipeline
4. silver transform pipeline
5. Iceberg operations 구현
6. data quality gate 구현
7. gold metrics (Spark 기반)
8. shared Iceberg catalog (Spark + Trino)

---

# 10. Git Incident (Important History)

개발 중 대용량 JAR 파일이 commit되는 문제가 발생했다.

aws-java-sdk-bundle-1.12.262.jar

GitHub push 실패 후

git filter-branch

로 제거했으나
모든 commit SHA가 변경되었다.

결과

main [origin/main: ahead 88, behind 88]

상태 발생.

해결

origin/main 기준 새 브랜치 생성 후
작업 상태만 가져와 새 commit 생성.

이 과정은 learning 문서에 기록되어 있다.

---

# 11. Current Latest Milestone

현재 최신 단계

dbt-trino analytics layer

내용

dbt project init
Trino profile 연결
Silver source 선언
staging / marts 모델 추가
dbt run / dbt test
analytics smoke test 구축

---

# 12. Communication Style Preference

이 프로젝트에서는 다음 원칙을 따른다.

* 실제 실무 구조 기반 설계
* PR 단위 개발
* 재현성 있는 환경 구성
* 문서화 중심 진행
* 과도한 설계 지양
* 문제 해결 과정 기록

---

# 13. Instructions for AI Assistant

이 문서를 읽은 AI는 다음 전제를 기반으로 대화해야 한다.

1. 사용자는 데이터 엔지니어링 학습 프로젝트를 진행 중이다
2. Spark / Iceberg / Trino 기반 Lakehouse 구축이 이미 완료되었다
3. shared catalog 구조가 구현되어 있다
4. 다음 단계는 dbt-trino 기반 analytics layer이다
5. 답변은 실무 workflow 중심으로 제공해야 한다

---

# End of Context

이 문서는 ChatGPT 또는 다른 LLM과의 새로운 세션에서
프로젝트 맥락을 복원하기 위한 컨텍스트 파일이다.
