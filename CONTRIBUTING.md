# Contributing Guide

## Branch Strategy

- main은 보호 브랜치
- 기능 개발은 feature branch에서 진행

예:
```
feat/bootstrap-ci
```

---

## Commit Convention

Conventional Commits 사용:

- feat: 기능 추가
- fix: 버그 수정
- chore: 설정/환경 변경
- docs: 문서 변경
- test: 테스트 추가/수정
- ci: CI 관련 변경

예:

```
chore: configure build system for src layout
docs: add onboarding guide
ci: add GitHub Actions workflow
```

---

## PR Rule

PR에는 반드시 포함:

- What changed
- Why
- How to test
- Risk

---

## CI Rule

CI가 실패하면 merge하지 않습니다.