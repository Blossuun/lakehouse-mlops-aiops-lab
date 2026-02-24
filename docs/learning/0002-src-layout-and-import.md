# 0002 - src-layout and Import Behavior

## Problem

프로젝트를 다음과 같이 구성했다:

```
src/lakehouse_mlops_aiops_lab/
tests/
```

테스트 파일에서:

```
import lakehouse_mlops_aiops_lab
```

를 실행했을 때 import 에러가 발생했다.

---

## Root Cause

src-layout은 루트에 모듈이 있는 구조와 다르다.

루트 구조:
```
lakehouse_mlops_aiops_lab/
```

이 경우 PYTHONPATH에 따라 우연히 import가 될 수 있다.

그러나 src-layout은:

```
src/lakehouse_mlops_aiops_lab/
```

이기 때문에,
프로젝트가 “설치”되지 않으면 import가 되지 않는다.

즉, src-layout은 더 엄격한 구조이며,
패키지 설치가 전제 조건이다.

---

## Solution

- build-system 설정을 추가했다
- uv sync를 통해 프로젝트를 설치했다
- import 스모크 테스트를 추가했다

```
uv run python -c "import lakehouse_mlops_aiops_lab; print('ok')"
```

---

## What I Learned

- src-layout은 실무에서 널리 쓰인다
- 그러나 반드시 패키징 개념을 이해해야 한다
- 우연히 import 되는 구조는 장기적으로 위험하다
- 스모크 테스트는 구조 검증용이다