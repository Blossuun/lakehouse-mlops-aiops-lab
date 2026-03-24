# ADR-0010: API Layer (Programmatic Data Access)

## Status
Accepted

## Context

현재 프로젝트는:

- data pipeline
- query layer
- dashboard

까지 포함한다.

하지만 프로그램이 데이터를 접근할 수 있는 인터페이스가 없다.

즉:

- 외부 서비스
- ML pipeline
- BI tool

이 접근할 표준 인터페이스가 없다.

## Decision

FastAPI 기반 read-only API layer를 추가한다.

원칙:

- Trino를 통해 데이터 조회
- read-only
- Gold 중심
- 단순 endpoint 구조

## Consequences

장점:
- programmatic access 가능
- 서비스 형태로 확장 가능

단점:
- 서버 레이어 추가
- 운영 고려 필요

## Non-Goals

- auth
- rate limiting
- production deployment