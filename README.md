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

## 🎯 Project Goal

이 리포지토리는 단순 코드 저장소가 아니라

- 실무형 개발 루프 구축
- 패키징 이해
- CI 자동화
- 점진적 데이터/ML/AI 플랫폼 확장

을 위한 학습 기록 저장소입니다.