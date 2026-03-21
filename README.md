# lakehouse-mlops-aiops-lab

Data Engineering → MLOps → (향후) AIOps/LLM Apps 까지
한 리포지토리에서 점진적으로 확장하는 실전형 프로젝트입니다.

이 프로젝트는 단순 기능 구현이 아니라,
**실무에서 바로 사용 가능한 개발/테스트/CI 구조를 구축하는 것**을 목표로 합니다.

---

## 🚀 Quickstart

### 1. Requirements

- Python 3.12.x
- uv installed
- Optional: Task CLI (`go-task`) for task-based local entrypoints

Python 버전 확인:

```bash
python --version
```

### 2. Install dependencies (dev 포함)

```bash
uv sync --dev
```

### 3. Verify environment

```bash
uv run python -c "import lakehouse_mlops_aiops_lab; print('ok')"
```

정상이라면 `ok`가 출력됩니다.

`Taskfile.yml`를 사용하는 경우, Task CLI 설치:

Windows example:

```powershell
winget install Task.Task
```

Task는 선택 사항입니다. 기존 `uv run ...` 및 PowerShell 명령은 그대로 유효합니다.

---

## 🧪 Development Loop (Team Standard)

로컬과 CI가 항상 동일한 방식으로 실행되도록
모든 명령은 `uv run` 기준으로 통일합니다.

### Format

```bash
uv run ruff format .
```

### Lint

```bash
uv run ruff check .
```

### Test

```bash
uv run pytest -q
```

---

## 🧭 Thin Task Entry Points

기존 `uv run ...` / `powershell ...` 명령은 그대로 유지합니다.  
`Taskfile.yml`은 이를 대체하는 새 실행 로직이 아니라, **자주 쓰는 로컬 진입점을 정리한 얇은 인덱스**입니다.

이 설계의 목적:

- 로컬 개인 Docker 환경에서 리소스 사용을 예측 가능하게 유지
- 전체 파이프라인을 기본 명령으로 강제하지 않기
- 기존 smoke scripts를 그대로 재사용하기
- 실행 순서를 README와 더 쉽게 연결하기

### Before using task entrypoints

Task 기반 로컬 워크플로우를 사용하기 전에 먼저 환경 파일을 준비합니다.

```bash
cp infra/.env.example infra/.env
```

Windows PowerShell example:

```powershell
Copy-Item .\infra\.env.example .\infra\.env
```

현재 PowerShell 기반 task는 **Windows PowerShell** 로컬 실행 기준으로 제공합니다.
기존 `uv run ...` / `powershell ...` 명령은 계속 직접 사용할 수 있습니다.

### Fast local loop

아래는 여전히 기본 개발 루프입니다.

```bash
task dev:fmt
task dev:lint
task dev:test
```

### Stage-oriented local workflows

필요한 단계만 명시적으로 실행합니다.

```bash
task infra:up
task smoke:minio
task smoke:mlflow
task raw
task silver
task iceberg
task iceberg:ops
task quality
task gold
task shared-catalog
task analytics
task infra:down
```

### Notes

- 이 Taskfile은 만능 통합 실행기가 아닙니다.
- 기본으로 전체 파이프라인을 모두 실행하는 full-smoke 태스크는 이번 단계에서 추가하지 않습니다.
- 다른 날짜나 커스텀 파라미터가 필요하면 기존 스크립트를 직접 실행합니다.

---

## 📦 Project Structure

이 프로젝트는 **src-layout**을 사용합니다.

```
src/lakehouse_mlops_aiops_lab/
tests/
docs/
```

### Why src-layout?

- 테스트에서 우연히 import 되는 문제 방지
- 프로젝트가 커졌을 때 import 경로 안정성 확보
- 실무에서 일반적으로 사용하는 구조

---

## ⚙ Packaging & Build System

이 프로젝트는 `src/` 아래 코드를 패키지로 사용하기 위해
`pyproject.toml`에 build-system을 명시합니다.

의존성 설치와 패키지 설치는 다릅니다.

- `uv sync --dev` → 의존성 설치
- build-system 설정 → 프로젝트 자체를 import 가능하게 설치

---

## 🛠 Troubleshooting

### ModuleNotFoundError

아래로 먼저 확인합니다:

```bash
uv run python -c "import lakehouse_mlops_aiops_lab; print('ok')"
```

실패한다면:

- `pyproject.toml`의 build-system 설정 확인
- `src/lakehouse_mlops_aiops_lab/__init__.py` 존재 여부 확인
- `uv sync --dev` 재실행

---

## 📚 Documentation

- Onboarding Guide → `docs/onboarding.md`
- Architecture Decision Records → `docs/adr/`
- Contribution Guide → `CONTRIBUTING.md`

---

## 🐳 Local Infrastructure

Start services:

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d
```

Stop services:

```bash
docker compose -f infra/docker-compose.yml down
```

### Verify MinIO

PowerShell example:

```powershell
$env:MINIO_ENDPOINT="http://localhost:9000"
$env:AWS_ACCESS_KEY_ID="minioadmin"
$env:AWS_SECRET_ACCESS_KEY="minioadmin123"
$env:AWS_DEFAULT_REGION="ap-northeast-2"
uv run python scripts/smoke_minio.py
```

### Verify MLflow

```powershell
$env:MLFLOW_TRACKING_URI="http://localhost:5000"
uv run python scripts/smoke_mlflow.py
```

MLflow UI:
http://localhost:5000

MinIO Console:
http://localhost:9001

---

## ⚡ Local Spark Runtime Tuning

이 프로젝트는 Spark를 로컬 Docker / WSL 환경에서 반복 실행하는 실전형 랩이다.  
기본 Spark 설정은 범용 클러스터에는 무난할 수 있지만,
현재처럼 단일 컨테이너 기반 local smoke 실행에는 과한 경우가 있다.

현재 로컬 기본 튜닝:

- shuffle partitions 축소
- adaptive query execution 활성화
- 보수적인 driver / executor memory 고정

목적은 최대 성능이 아니라 **로컬 재실행 안정성**이다.

관련 배경과 이유는 다음 문서에 정리했다.

- `docs/learning/0013-local-spark-runtime-tuning.md`

---

## 📦 Raw Data Ingest (MinIO Data Lake)

이 프로젝트는 MinIO(S3 호환)를 Data Lake처럼 사용합니다.

### ⚠ 실행 전 필수 조건

로컬 인프라가 반드시 실행 중이어야 합니다:

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d
```

MinIO Console: http://localhost:9001  
MLflow UI: http://localhost:5000  

---

## 1️⃣ Raw 이벤트 생성

```bash
uv run python -m lakehouse_mlops_aiops_lab.ingest.generate_events \
  --date 2026-02-27 \
  --rows 20000 \
  --out ./tmp/events.jsonl
```

생성된 파일은 JSON Lines 형식입니다.

---

## 2️⃣ MinIO 업로드

PowerShell 예시:

```powershell
$env:MINIO_ENDPOINT="http://localhost:9000"
$env:AWS_ACCESS_KEY_ID="minioadmin"
$env:AWS_SECRET_ACCESS_KEY="minioadmin123"
$env:AWS_DEFAULT_REGION="ap-northeast-2"

uv run python -m lakehouse_mlops_aiops_lab.ingest.upload_raw_events \
  --date 2026-02-27 \
  --infile ./tmp/events.jsonl
```

저장 경로:

```
s3://datalake/raw/events/dt=2026-02-27/events.jsonl
```

---

## 3️⃣ End-to-End Smoke Test

```bash
uv run python scripts/smoke_raw_ingest.py
```

검증 내용:

- 이벤트 생성
- S3 업로드
- S3 다운로드
- 라인 수 비교

---

## 🔎 Raw 데이터 설계 특징

- UTC 기반 event_time / ingest_time
- late arriving 데이터 포함
- duplicate resend 포함
- dirty data (결측/타입 드리프트) 일부 포함
- schema_version 기반 스키마 진화

이 설계는 이후 Spark/Iceberg/dbt 단계에서
현실적인 데이터 처리 문제를 재현하기 위한 것입니다.

---

## 🪙 Silver 변환 (Raw JSONL → Parquet, PyArrow)

Raw(JSONL)는 원본 보존과 유연성이 장점이지만, 컬럼형 처리/분석에는 비효율적입니다.  
Silver 레이어에서는 **스키마를 고정**하고 **최소 정제**를 수행한 뒤 **Parquet**로 저장합니다.

### ⚠ 실행 전 필수 조건

1) 로컬 인프라 실행 (MinIO 필요)

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d
```

2) Raw 데이터가 MinIO에 존재해야 합니다(PR #3)

- `s3://datalake/raw/events/dt=YYYY-MM-DD/*.jsonl`

---

### Transform 실행

PowerShell 예시:

```powershell
$env:MINIO_ENDPOINT="http://localhost:9000"
$env:AWS_ACCESS_KEY_ID="minioadmin"
$env:AWS_SECRET_ACCESS_KEY="minioadmin123"
$env:AWS_DEFAULT_REGION="ap-northeast-2"

uv run python -m lakehouse_mlops_aiops_lab.transform.raw_to_silver_events --date 2026-02-27
```

출력 경로(멀티 파트):

```
s3://datalake/silver/events/dt=2026-02-27/part-*.parquet
```

- Raw JSONL을 스트리밍으로 읽고
- `event_id` 기준 dedup을 수행하며
- 일정 row 단위로 Parquet 파트를 생성합니다.

---

### Smoke Test (Raw → Silver)

```bash
uv run python scripts/smoke_silver_transform.py
```

검증 내용:
- Raw 파일 존재 확인
- 변환 실행
- Silver Parquet 파트 파일 존재 확인
- Silver 전체에서 event_id 중복이 없는지 확인

---

## 🧊 Spark + Iceberg (Silver → Lakehouse Table)

Silver(Parquet) 파일을 Iceberg 테이블로 적재하여
파일 레벨 데이터를 테이블 레벨(Lakehouse)로 승격합니다.

---

*bitnami는 더이상 무료 이미지를 제공하지 않으므로, 공식 apache/spark 이미지를 사용하도록 변경했습니다.*

---

### ⚠ 실행 전 조건

1) 로컬 인프라 실행

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d
```

2) Silver Parquet 존재

```
s3://datalake/silver/events/dt=YYYY-MM-DD/part-*.parquet
```

---

### Spark Job 실행 (Windows PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_iceberg_table.ps1 -Date 2026-02-27
```

---

### 실행 로그 확인

- PowerShell 콘솔에 spark-submit 로그 출력
- 성공 시 예시:

```
OK: wrote iceberg table=local.lakehouse.silver_events dt=2026-02-27 rows=12345
OK: smoke_iceberg_table completed
```

---

### Spark UI (선택)

실행 중에는 아래 주소에서 Spark UI 확인 가능:

```
http://localhost:4040
```

---

### 중요한 구현 포인트

- Ivy 캐시는 `/tmp/ivy`로 지정하여 컨테이너 권한 문제를 회피
- Spark 내부 Hadoop 버전과 동일한 `hadoop-aws` 버전 사용
- 기존 `part-*.parquet` 삭제 후 재작성하여 rerun 안정성 확보
- Iceberg는 Hadoop catalog 기반으로 MinIO(S3a)를 warehouse로 사용

설정값 선택 이유는 다음 ADR에 정리했습니다:

- `docs/adr/0002-local-spark-iceberg.md`

---

## 🧪 Iceberg Ops (Snapshots / Time Travel / Schema Evolution)

PR #6에서는 Iceberg를 “운영 가능한 테이블”로 다루기 위해 아래를 검증합니다.

- 스냅샷/히스토리 확인
- 타임 트래블(과거 스냅샷 조회)
- 스키마 진화(컬럼 추가) 후 호환성 확인

### 실행

1) 로컬 인프라 실행

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d
```

2) Iceberg 테이블이 이미 존재해야 합니다(PR #5 완료)

3) Smoke 실행 (Windows PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_iceberg_ops.ps1 -Date 2026-02-27
```

### 로그 확인

- PowerShell 콘솔에 spark-submit 로그가 출력됩니다.
- 실패 시 exit code로 원인 추적이 가능합니다.

---

## 🛡️ Data Quality Gate (Silver Table)

PR #7에서는 Iceberg Silver 테이블에 대한 **데이터 품질 검증(Data Quality Gate)**을 도입합니다.

목적:

- Iceberg 테이블이 **분석/ML에 사용 가능한 상태인지 검증**
- 품질 규칙 위반 시 **downstream 작업 중단**
- 품질 결과를 Spark가 생성한 text output directory에 **JSON 리포트로 기록**

검증 대상 테이블:

```
local.lakehouse.silver_events
```

검증 범위:

- 특정 `dt` 파티션 단위

---

## 실행 방법

### 1️⃣ 로컬 인프라 실행

```bash
docker compose -f infra/docker-compose.yml --env-file infra/.env up -d
```

### 2️⃣ Silver 데이터 존재 확인

```
s3://datalake/silver/events/dt=YYYY-MM-DD/part-*.parquet
```

### 3️⃣ 품질 게이트 실행 (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_silver_quality.ps1 -Date 2026-02-27
```

---

## 실행 결과

성공 시 콘솔 출력 예:

```
INFO: Running quality gate
OK: silver quality gate passed
INFO: report written to s3a://datalake/audit/quality_checks/dt=2026-02-27
```

---

## 품질 검증 규칙

검증 규칙은 다음 문서에 정의되어 있습니다.

```
docs/data_contracts/silver_quality_rules.md
```

주요 규칙:

- event_id 중복 없음
- event_type 허용 값 확인
- event_time / ingest_time null 금지
- event_time <= ingest_time
- 금액 컬럼 음수 금지
- purchase 이벤트는 order_id 필수

---

## 품질 리포트 위치

검증 결과는 Spark output directory 형태의 JSON 리포트로 저장됩니다.

```
s3a://datalake/audit/quality_checks/dt=YYYY-MM-DD/
```

리포트에는 다음 정보가 포함됩니다.

- 검사 대상 테이블
- 검사 시간
- row count
- 규칙별 pass/fail 결과

---

## 현재 설계의 특징

현재 품질 게이트는:

- 파티션 단위 검증
- fail-fast 방식
- 데이터 수정 없이 검증만 수행
- 로컬 Spark / Docker 환경을 고려해 가능한 한 집계 중심 방식으로 품질 수치를 계산

현재 quality gate 는 `dt` 파티션 하나를 대상으로 downstream 사용 가능 여부를 빠르게 판단하는 데 목적이 있습니다.  
즉, 이 단계의 우선순위는 full-table 정밀 감사보다 **로컬에서 재실행 가능한 partition-scoped validation** 입니다.

향후 확장 예정:

- quarantine dataset
- audit Iceberg table
- WARN / FAIL 레벨 분리

---

# 📊 Gold Layer (Business Metrics)

PR #8에서는 Silver Iceberg 테이블을 기반으로 **Gold metrics 레이어**를 구축합니다.

목적:

- Spark가 생성하는 platform-owned aggregate layer 제공
- batch / pipeline / programmatic consumption 을 위한 지표 테이블 생성
- rerunnable Spark aggregate artifact 유지

이 레이어는 analyst / BI / ad hoc query 용 최종 semantic presentation layer 를 직접 목표로 하지 않는다.
Gold 와 dbt marts 의 역할 차이는 아래 `Metric Layer Ownership` 섹션을 따른다.

Source:

```
local.lakehouse.silver_events
```

생성되는 테이블:

```
local.gold.daily_event_metrics
local.gold.daily_revenue_metrics
local.gold.daily_conversion_metrics
```

---

## Gold Metrics 생성

PowerShell에서 실행:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_gold_metrics.ps1 -Date 2026-02-27
```

---

## 생성되는 지표

### daily_event_metrics

| column | description |
|------|-------------|
| dt | 날짜 |
| total_events | 전체 이벤트 수 |
| view_events | view 이벤트 |
| search_events | search 이벤트 |
| add_to_cart_events | 장바구니 이벤트 |
| purchase_events | 구매 이벤트 |
| refund_events | 환불 이벤트 |

---

### daily_revenue_metrics

| column | description |
|------|-------------|
| dt | 날짜 |
| gross_revenue | 총 매출 |
| refund_amount | 총 환불 |
| net_revenue | 순매출 |

---

### daily_conversion_metrics

| column | description |
|------|-------------|
| dt | 날짜 |
| view_events | 조회 |
| add_to_cart_events | 장바구니 |
| purchase_events | 구매 |
| view_to_cart_rate | 조회→장바구니 전환율 |
| cart_to_purchase_rate | 장바구니→구매 전환율 |
| view_to_purchase_rate | 조회→구매 전환율 |

---

## 데이터 흐름

```
Raw (JSONL)
   ↓
Silver (Clean Events)
   ↓
Iceberg Table
   ↓
Data Quality Gate
   ↓
Gold Metrics
```

---

## Gold 레이어 특징

- dt 파티션 기반 집계
- Iceberg snapshot 기반 이력 관리
- rerun-safe 파이프라인

---

## 🔗 Shared Iceberg Catalog (Spark + Trino)

PR #9에서는 Iceberg catalog를 **Spark 전용 Hadoop catalog**에서
**Hive Metastore 기반 shared catalog**로 전환했습니다.

이 변경의 목적은:

- Spark가 Iceberg 테이블을 계속 write 할 수 있고
- Trino가 같은 Iceberg 테이블을 read 할 수 있게 만드는 것

입니다.

즉, 역할이 다음처럼 분리됩니다.

```text
Spark  -> write engine
Trino  -> read/query engine
```

---

## 왜 shared catalog가 필요한가

기존 Spark 설정은 `SparkCatalog + type=hadoop` 기반이었습니다.

이 방식은 Spark 단독 사용에는 단순하고 잘 동작하지만,
Trino와 같은 별도 query engine이 같은 Iceberg 테이블을 읽으려면
공유 가능한 metastore/catalog가 필요합니다.

그래서 이번 단계에서:

- Hive Metastore 추가
- Spark catalog를 `type=hive`로 전환
- Trino Iceberg catalog를 Hive Metastore에 연결

하는 방식으로 구조를 바꿨습니다.

---

## 현재 로컬 구성

```text
MinIO            : object storage
Postgres         : Hive Metastore DB
Hive Metastore   : shared Iceberg catalog backend
Spark            : write / transform engine
Trino            : query / analytics engine
```

---

## Smoke Test

공유 catalog가 제대로 작동하는지 검증하는 smoke script:

```text
scripts/smoke_shared_catalog_spark_trino.ps1
```

실행:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_shared_catalog_spark_trino.ps1
```

이 smoke는 다음을 검증합니다.

1. Spark가 shared catalog를 통해 Iceberg 테이블 생성 및 write
2. Trino가 같은 catalog를 통해 해당 테이블 read

성공 시 기대 결과:

```text
OK: Shared Iceberg catalog smoke passed
```

---

## Smoke 대상 테이블

Smoke는 아래 테스트 테이블을 사용합니다.

```text
local.test.catalog_smoke
```

이 테이블은 smoke 실행 시마다 다시 생성되므로,
결과는 항상 결정적(deterministic)이고 재실행 가능합니다.

---

## 이번 단계의 의미

이제 프로젝트는 단순히 Spark로만 데이터를 다루는 상태가 아니라,
여러 엔진이 같은 Iceberg catalog를 공유하는 구조가 되었습니다.

즉, 다음 단계에서 다음이 가능해집니다.

- Trino 기반 쿼리
- dbt-trino 도입
- analytics engineering 레이어 확장

---

## dbt + Trino Analytics Layer

이 프로젝트는 Spark 기반 Lakehouse 위에 **dbt + Trino 기반 analytics layer**를 구축한다.

전체 구조

```text
Spark  -> Iceberg write engine
Trino  -> query engine
dbt    -> analytics modeling layer
```

analytics 프로젝트 위치

```text
analytics/
  models/
    sources/
    staging/
    intermediate/
    marts/
```

모델 계층

| Layer | 역할 |
|------|------|
| source | Iceberg 테이블 선언 |
| staging | analytics 친화적 컬럼 구조 |
| intermediate | 재사용 가능한 계산 |
| marts | 비즈니스 지표 모델 |

---

## Analytics Smoke Test

사전 준비

```powershell
uv sync --dev --group analytics
```

analytics layer가 정상 동작하는지 확인

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_dbt_trino_analytics.ps1
```

검증 항목

- dbt profile render
- dbt run
- dbt test
- Trino mart 조회

성공 시

```text
OK: dbt-trino analytics smoke passed
```

---

## Query 예시

Trino에서 mart 조회

```sql
SELECT * FROM iceberg.analytics.fct_daily_events;
SELECT * FROM iceberg.analytics.fct_daily_revenue;
SELECT * FROM iceberg.analytics.fct_daily_conversion;
```

---

## Metric Layer Ownership

현재 프로젝트에는 지표를 다루는 두 개의 레이어가 있다.

### 1. Spark Gold metrics

역할:

- Spark가 생성하는 platform-owned aggregate layer
- batch / pipeline / programmatic consumption 을 위한 집계 테이블
- 운영 파이프라인 관점의 rerunnable aggregate artifact

대표 테이블:

- `local.gold.daily_event_metrics`
- `local.gold.daily_revenue_metrics`
- `local.gold.daily_conversion_metrics`

### 2. dbt analytics marts

역할:

- Trino + dbt 기반 analytics-owned semantic layer
- analyst / BI / ad hoc query 친화적 모델
- tests / lineage / dependency 관리가 포함된 analytics engineering 결과물

대표 테이블:

- `iceberg.analytics.fct_daily_events`
- `iceberg.analytics.fct_daily_revenue`
- `iceberg.analytics.fct_daily_conversion`

### 현재 원칙

중요한 점은, 현재 dbt marts 가 Spark Gold 를 직접 source 로 사용하지 않는다는 것이다.

현재 구조에서는:

- Spark Gold = platform aggregate layer
- dbt marts = analytics semantic layer

즉, 비슷한 일별 지표가 존재할 수 있어도
현재는 서로 다른 ownership 과 소비자를 위한 별도 레이어로 유지한다.

---

## 🎯 Project Goal

이 리포지토리는 단순 코드 저장소가 아니라

- 실무형 개발 루프 구축
- 패키징 이해
- CI 자동화
- 점진적 데이터/ML/AI 플랫폼 확장

을 위한 학습 기록 저장소입니다.

