# Onboarding Guide

이 문서는 lakehouse-mlops-aiops-lab 프로젝트에
처음 참여하는 팀원을 위한 안내서입니다.

목표는 다음입니다:

1. 동일한 방식으로 로컬 실행
2. 동일한 방식으로 CI 통과
3. 패키징/구조 이해

---

## 1️⃣ 기본 원칙

- 모든 실행은 `uv run`으로 통일
- 로컬과 CI는 동일 명령 사용
- src-layout 구조 유지

---

## 2️⃣ 초기 세팅

### Python 버전

```bash
python --version
```

3.12.x 사용

### 의존성 설치

```bash
uv sync --dev
```

---

## 3️⃣ 개발 루프

### 포맷

```bash
uv run ruff format .
```

### 린트

```bash
uv run ruff check .
```

### 테스트

```bash
uv run pytest -q
```

---

## 4️⃣ 패키지 import 확인

```bash
uv run python -c "import lakehouse_mlops_aiops_lab; print('ok')"
```

이 테스트는 다음을 검증합니다:

- src-layout이 올바른가?
- build-system 설정이 있는가?
- 프로젝트가 설치되었는가?

---

## 5️⃣ 왜 src-layout인가?

이 프로젝트는 다음 구조를 사용합니다:

```
src/lakehouse_mlops_aiops_lab/
tests/
```

이 구조는:

- 테스트 경로 문제 방지
- 패키징 안정성 확보
- 실무 표준 구조

---

## 6️⃣ 의존성 설치 ≠ 패키지 설치

의존성만 설치하면 import가 실패할 수 있습니다.

패키지 설치는 build-system 설정에 의해 이루어집니다.

---

## 7️⃣ 스모크 테스트의 목적

PR #1에서는 기능이 거의 없습니다.
스모크 테스트는 다음을 확인합니다:

- import 가능 여부
- pytest 실행 확인
- CI 파이프라인 검증

---

## 8️⃣ 협업 규칙

- feature branch에서 작업
- PR 생성 후 CI 통과 필수
- 빨간 CI는 merge하지 않음