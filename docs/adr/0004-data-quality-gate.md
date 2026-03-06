# ADR 0004 - Iceberg Silver 데이터 품질 게이트 도입

## 배경

현재 프로젝트는 다음 구조를 갖습니다.

- Raw(JSONL)
- Silver(Parquet)
- Iceberg table (`local.lakehouse.silver_events`)

이제 테이블이 존재하므로, 다음 단계에서는 단순 적재가 아니라
**데이터를 신뢰할 수 있는지 검증하는 과정**이 필요합니다.

실무에서는 ML/분석/서빙 이전에
데이터 품질 검증을 자동화하는 것이 일반적입니다.

## 결정

PR #7에서는 다음을 구현합니다.

1. Spark 기반 품질 검증 job
2. 규칙별 pass/fail 계산
3. 결과를 object storage에 JSON report로 저장
4. smoke script로 품질 게이트 실행

## 왜 지금 하는가

- Iceberg 테이블이 이미 존재하므로 검증 대상이 명확함
- 이후 Gold 모델링, dbt, ML feature engineering 전에 필요한 단계
- “데이터가 존재함”과 “데이터를 써도 됨”은 다르기 때문

## 왜 외부 품질 프레임워크를 바로 쓰지 않는가

Great Expectations, Soda 같은 도구는 유용하지만,
지금 단계에서는 Spark/SQL로 직접 품질 규칙을 구현해보는 것이 더 중요합니다.

그 이유는:
- 규칙 설계 자체를 이해해야 하고
- Iceberg/Spark/S3 구조를 먼저 명확히 이해해야 하며
- 외부 프레임워크를 도입하면 학습 포인트가 분산되기 때문입니다.

## 범위

이번 PR에서 검증하는 범위:
- Silver table: `local.lakehouse.silver_events`
- 특정 `dt` 파티션 단위 검증
- JSON 리포트 저장
- smoke script 실행

이번 PR에서 하지 않는 것:
- audit Iceberg table 구축
- Great Expectations/Soda 도입
- 스케줄러 연동