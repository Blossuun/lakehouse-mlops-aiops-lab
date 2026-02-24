# 0001 - Packaging and Build System

## Problem

`uv sync --dev` 이후 다음 명령이 실패했다:

```
uv run python -c "import lakehouse_mlops_aiops_lab; print('ok')"
```

에러:

```
ModuleNotFoundError: No module named 'lakehouse_mlops_aiops_lab'
```

디렉토리 구조는 다음과 같았다:

```
src/lakehouse_mlops_aiops_lab/
tests/
```

하지만 import가 되지 않았다.

---

## Root Cause

의존성 설치와 프로젝트 설치는 다르다.

`uv sync --dev`는 개발 의존성(ruff, pytest 등)만 설치한다.

그러나 현재 `pyproject.toml`에는 `[build-system]`이 정의되어 있지 않았다.

즉, 이 프로젝트는 “설치 가능한 패키지”로 선언되지 않은 상태였다.

src-layout을 사용하면,
프로젝트 자체를 패키지로 설치해야 import가 가능하다.

build-system이 없으면,
uv는 이 프로젝트를 어떻게 빌드/설치해야 하는지 알 수 없다.

---

## Solution

`pyproject.toml`에 다음을 추가했다:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]
```

그 후:

```
uv sync --dev
uv run python -c "import lakehouse_mlops_aiops_lab; print('ok')"
```

정상적으로 `ok`가 출력되었다.

---

## What I Learned

- 의존성 설치 ≠ 프로젝트 설치
- src-layout을 사용할 경우 build-system 설정이 반드시 필요하다
- 패키징은 단순 설정이 아니라, import 안정성과 CI 안정성을 보장하는 핵심 요소다
- “왜 import가 안 되는가?”는 거의 항상 패키징/경로 문제다