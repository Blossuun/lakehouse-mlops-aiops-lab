# 0003 - uv init and Project Installation

## Problem

`uv init`을 실행했지만,
`pyproject.toml`에 build-system이 자동으로 생성되지 않았다.

“uv가 자동으로 build-system을 만들어주지 않는가?”라는 의문이 생겼다.

---

## Root Cause

uv는 기본적으로 “의존성 관리 도구”이다.

`uv init`은 중립적인 프로젝트를 생성한다.

즉:

- 스크립트 프로젝트일 수도 있고
- 패키지 프로젝트일 수도 있다

패키지로 사용할 경우에만 build-system이 필요하다.

기본 `uv init`은 build-system을 강제하지 않는다.

---

## Solution

패키지 프로젝트로 사용하기 위해
명시적으로 build-system을 추가했다.

이로써:

- 프로젝트가 설치 가능해졌고
- src-layout import 문제가 해결되었다

---

## What I Learned

- uv는 pip의 빠른 대체제이자 의존성 관리자이다
- 의존성 관리와 패키징은 별개의 개념이다
- build-system은 프로젝트를 “설치 가능”하게 만드는 선언이다
- 도구가 자동으로 해주지 않는 부분은 명시적으로 이해하고 설정해야 한다