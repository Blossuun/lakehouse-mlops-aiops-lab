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

## 🎯 Project Goal

이 리포지토리는 단순 코드 저장소가 아니라

- 실무형 개발 루프 구축
- 패키징 이해
- CI 자동화
- 점진적 데이터/ML/AI 플랫폼 확장

을 위한 학습 기록 저장소입니다.

