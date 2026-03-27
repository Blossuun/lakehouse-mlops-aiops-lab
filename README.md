# Lakehouse Lab

## Overview

이 프로젝트는 로컬 Docker 환경에서 **데이터 파이프라인부터 데이터 소비까지의 전체 lakehouse 아키텍처를 end-to-end로 구현한 실습형 프로젝트**입니다.

구현 범위:

* 데이터 생성 (synthetic events)
* Silver 변환
* Iceberg 기반 데이터 레이크
* 데이터 품질 검증 (quality gate)
* Gold 집계 레이어
* dbt 기반 분석 모델링
* Trino query layer
* Streamlit 대시보드
* FastAPI 기반 API

👉 단순 ETL이 아니라
👉 **"데이터를 실제로 사용하는 시스템"까지 포함한 구조**를 목표로 합니다.

---

## Architecture

```
Raw → Silver → Iceberg → Quality → Gold → dbt → Trino → Dashboard / API
```

핵심 특징:

* Storage: Iceberg + MinIO
* Compute: Spark
* Query: Trino
* Modeling: dbt
* Consumption: Dashboard + API

---

## Quick Start

### 1. 사전 준비

* uv 설치
* Task CLI 설치
* 환경 파일 생성

```
copy .\infra\.env.example .\infra\.env
```

---

### 2. 전체 시스템 실행

```
task infra:up
powershell -ExecutionPolicy Bypass -File .\scripts\api\run_api_server.ps1
task validate:all
```

이 과정에서:

* 전체 pipeline 실행
* query layer 검증
* API 검증

까지 한 번에 수행됩니다.

---

## Pipeline

```
task raw
task silver
task iceberg
task quality
task gold
```

역할:

* Raw → 이벤트 생성
* Silver → 정제
* Iceberg → 저장
* Quality → 데이터 검증
* Gold → 집계 지표 생성

---

## Query Layer (Trino)

```
powershell -ExecutionPolicy Bypass -File .\scripts\query\run_trino_query.ps1 -QueryFile .\analytics\queries\daily_business_overview.sql
```

특징:

* SQL 기반 데이터 접근
* reproducible query 실행
* Gold / Silver 데이터 활용

---

## Dashboard

```
uv sync --group dashboard
powershell -ExecutionPolicy Bypass -File .\scripts\dashboard\run_analysis_dashboard.ps1
```

제공 기능:

* 일별 비즈니스 개요 (Gold)
* 전환 퍼널 (Gold)
* 상위 상품 (Silver)

특징:

* Trino 기반 read-only 조회
* Streamlit UI
* 빠른 탐색 중심

---

## API Layer

```
uv sync --group api
powershell -ExecutionPolicy Bypass -File .\scripts\api\run_api_server.ps1
```

접속:

```
http://localhost:8000/docs
```

특징:

* FastAPI 기반
* read-only endpoint
* Trino를 통한 데이터 접근

---

## End-to-End Validation

```
task validate:all
```

검증 범위:

* pipeline 실행
* query 정상 동작
* API 응답 확인

👉 전체 시스템이 실제로 동작하는지 검증합니다.

---

## Runbook

전체 실행 절차:

* docs/runbook.md 참고

---

## Key Design Decisions

* local-first (Docker / WSL 기반)
* read-only consumption layer
* Trino 단일 query engine
* stability > aggressive optimization

---

## What This Project Demonstrates

이 프로젝트는 다음 역량을 보여줍니다.

* 데이터 파이프라인 설계 (Spark)
* 데이터 레이크 설계 (Iceberg)
* 데이터 품질 관리
* 집계 레이어 설계 (Gold)
* query engine 활용 (Trino)
* 분석 레이어 (dbt)
* 데이터 소비 계층 (Dashboard + API)

👉 즉,

**"데이터를 만들고, 검증하고, 소비하는 전체 흐름"**을 구현합니다.

---

## Limitations

* production deployment 고려하지 않음
* authentication / authorization 없음
* multi-user 환경 미지원
* real-time 처리 없음

👉 학습 및 구조 설계 중심 프로젝트입니다.
