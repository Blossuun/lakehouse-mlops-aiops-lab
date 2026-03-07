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

향후 확장 예정:

- quarantine dataset
- audit Iceberg table
- WARN / FAIL 레벨 분리

---

# 📊 Gold Layer (Business Metrics)

PR #8에서는 Silver Iceberg 테이블을 기반으로 **Gold metrics 레이어**를 구축합니다.

목적:

- 비즈니스에서 바로 사용할 수 있는 지표 제공
- 분석/대시보드/ML 입력 데이터 생성

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

## 🎯 Project Goal

이 리포지토리는 단순 코드 저장소가 아니라

- 실무형 개발 루프 구축
- 패키징 이해
- CI 자동화
- 점진적 데이터/ML/AI 플랫폼 확장

을 위한 학습 기록 저장소입니다.

