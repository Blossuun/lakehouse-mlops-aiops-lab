# 0008 - Iceberg 운영 기능: 스냅샷 / 타임 트래블 / 스키마 진화

## 배경
Iceberg를 쓴다는 것은 단순 적재가 아니라,
스냅샷 기반으로 테이블 변경 이력을 운영하는 것이다.

## 이번 PR에서 한 일
- snapshots/history 조회(파이썬 spark-submit job)
- snapshot-id 기반 time travel 조회
- ALTER TABLE로 컬럼 추가 후 호환성 확인
- smoke 스크립트로 재현 가능한 검증 루프 제공

## 이번에 겪은 문제와 해결(중요)

### 문제: spark-sql 실행 시 Hive/Derby metastore_db 생성 실패
증상:
- jdbc:derby ... metastore_db 생성 실패
- /opt/lab/metastore_db 디렉터리 생성 불가(컨테이너 경로/권한/마운트 특성)

원인:
- spark-sql CLI가 HiveExternalCatalog를 초기화하면서
  내장 Derby 기반 metastore를 로컬 디렉터리에 만들려고 시도
- 컨테이너 환경에서 해당 경로가 writable이 아닐 수 있음

해결:
- spark-sql 기반 inspect를 제거하고, spark-submit 기반 Python inspect job으로 대체
- spark.sql.catalogImplementation=in-memory로 Hive metastore 경로 의존 제거
- spark.sql.warehouse.dir=/tmp/spark-warehouse로 writable 경로 고정

교훈:
- 컨테이너 기반 로컬 Spark에서는 “spark-sql + Derby metastore” 조합이 자주 깨진다.
- 운영/자동화(scripts)는 spark-submit 기반으로 통제하는 편이 안정적이다.
