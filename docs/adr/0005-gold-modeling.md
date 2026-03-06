# ADR 0005 - Gold 레이어 모델링 도입

## 배경

현재 프로젝트는 다음 레이어를 갖는다.

- Raw(JSONL)
- Silver(Parquet / Iceberg)
- Data Quality Gate

이제 다음 단계로, Silver 테이블을 바탕으로
비즈니스에서 바로 사용할 수 있는 Gold 레이어를 만든다.

## 왜 Gold가 필요한가

Silver는 기술적으로 정제된 사실 데이터다.
하지만 분석/리포트/대시보드/ML 입력에 바로 쓰기에는
비즈니스 의미가 충분히 정리되어 있지 않다.

Gold는:
- 일별 매출
- 전환율
- 이벤트 집계
처럼 바로 사용할 수 있는 지표 테이블을 제공한다.

## 왜 Silver를 거쳐 Gold로 가는가

- 정제 책임과 비즈니스 집계 책임을 분리하기 위해
- 같은 Silver를 여러 Gold 모델이 재사용할 수 있게 하기 위해
- 품질 검증 위치를 명확히 하기 위해

## 이번 PR의 범위

- Silver Iceberg 테이블을 기반으로 Gold metrics 테이블 생성
- Spark job으로 집계 수행
- smoke script로 결과 검증

## 이번 PR에서 하지 않는 것

- dbt 도입
- dashboard 연결
- BI tool integration