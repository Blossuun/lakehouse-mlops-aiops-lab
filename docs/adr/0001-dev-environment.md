# ADR 0001 - Development Environment & Packaging Decision

## Context

이 프로젝트는 데이터 엔지니어링 → MLOps → AI 엔지니어링까지
점진적으로 확장될 예정입니다.

초기 단계에서 개발 루프, 패키징, CI 구조를 명확히 정의해야 합니다.

---

## Decision

1. Python 3.12 사용
2. uv로 의존성 관리
3. ruff로 포맷/린트 통합
4. pytest 사용
5. src-layout 채택
6. setuptools 기반 build-system 명시

---

## Rationale

### Python 3.12
- 생태계 안정성 확보
- 최신 기능 사용 가능

### uv
- 빠른 dependency resolution
- 표준 pyproject 기반 관리

### ruff
- black/isort/flake8 대체 가능
- 단일 도구로 품질 관리 단순화

### src-layout
- import 안정성
- 실무 표준 구조
- 테스트 환경 일관성 확보

### build-system 명시
- 프로젝트를 설치 가능한 패키지로 정의
- 의존성 설치와 프로젝트 설치 분리

---

## Consequences

### 장점
- 확장성 확보
- CI 일관성 유지
- 실무형 구조

### 단점
- 초기 설정이 단순 스크립트보다 복잡
- 패키징 이해 필요