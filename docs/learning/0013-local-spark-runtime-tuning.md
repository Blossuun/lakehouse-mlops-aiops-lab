# 0013. Local Spark Runtime Tuning (Docker / WSL)

## 왜 이 문서를 남기는가

이 프로젝트는 로컬 Docker / WSL 환경에서 다음과 같은 Spark 기반 작업을 반복 실행한다.

- Silver → Iceberg load
- Iceberg ops
- Silver quality gate
- Gold metrics build

실행 중 실제로 관찰된 문제:

- 디스크 사용률 급등
- 작업이 극단적으로 느려짐
- 시스템 응답성이 크게 저하됨 (거의 멈춘 것처럼 보이는 구간 발생)

즉, 기본 Spark 설정은 범용 환경에는 적절할 수 있지만,
현재와 같은 **단일 컨테이너 + 제한된 리소스 + 반복 실행 환경**에서는 과한 경우가 있다.

---

## 문제 정의

로컬 환경에서의 핵심 문제는 다음과 같다.

- Spark 작업 중 디스크 I/O 급증
- 반복적인 스캔 / 셔플로 인한 local spill 증가
- 여러 컨테이너 동시 실행으로 인한 메모리 경쟁
- 결과적으로 host 전체의 안정성 저하

중요한 점:

이 단계의 목표는 "최대 성능"이 아니라  
**로컬 개발 환경에서 안정적으로 반복 실행 가능한 상태**를 만드는 것이다.

---

## 이번 변경 (spark-defaults.conf)

다음 설정을 추가했다.
```spark-defaults.conf
spark.sql.shuffle.partitions 4
spark.sql.adaptive.enabled true
spark.sql.adaptive.coalescePartitions.enabled true
spark.driver.memory 1536m
spark.executor.memory 1536m
```

---

## 왜 이렇게 설정했는가

### 1. shuffle partitions = 4

기본 셔플 파티션 수는 로컬 환경 기준으로 과하다.

문제:

- 작은 데이터도 과도하게 분할됨
- 많은 작은 task / 작은 파일 생성
- 디스크 I/O 증가

의도:

- 파티션 수를 줄여 local I/O 부담 완화
- 불필요한 fan-out 방지

---

### 2. Adaptive Query Execution 활성화

고정값만 두는 것보다 Spark가 런타임에 파티션을 조정하도록 허용한다.

의도:

- 작은 데이터셋에서 불필요한 셔플 축소
- 로컬 환경에서 더 유연한 실행

---

### 3. 메모리 1536m / 1536m

이 값은 최적값이 아니라 **보수적 시작값**이다.

환경 특성:

- Spark 외에도 여러 컨테이너 동시 실행
  - MinIO
  - Postgres
  - MLflow
  - Hive Metastore
  - Trino

따라서:

- 2g 이상 → 다른 컨테이너와 경쟁 심화 가능
- 1g → spill이 너무 쉽게 발생할 수 있음

결론:

- 중간값으로 1.5g 근처에서 시작
- 목표는 성능 극대화가 아니라 **안정적인 재실행**

---

## 측정 방법

이번 변경은 시간 최적화가 아니라 **리소스 안정성 개선**이 목적이다.

따라서 다음을 기록했다.

### 컨테이너 지표

- CPU %
- Memory usage
- BlockIO
- PIDs

### 호스트 지표

- CPU %
- Available memory
- DiskTime (%)
- DiskQueue

---

## 측정 시 주의사항

### 1. BlockIO는 누적값이다

BlockIO는 총합이므로 절대값 비교가 아니라:

- 증가량
- 증가 패턴

을 봐야 한다.

---

### 2. DiskTime만으로 병목을 단정할 수 없다

DiskTime이 높다고 해서 반드시 문제라고 단정할 수 없다.

중요한 것은:

- 지속적으로 높은 상태인지
- queue가 길게 유지되는지
- 시스템이 멈추는지

이다.

---

### 3. 목표는 성능이 아니라 안정성이다

이번 단계의 판단 기준:

- 디스크 100% 포화가 줄었는가
- 시스템 응답성이 유지되는가
- 작업이 끝까지 정상 실행되는가

---

## 관찰 결과 요약

### 확실하게 말할 수 있는 것

- 호스트 메모리 고갈은 완화됨
- Spark 메모리 사용은 더 예측 가능해짐
- 이전처럼 시스템이 거의 멈추는 현상은 감소

### 조심해서 말해야 하는 것

- I/O 총량이 크게 줄었다고 단정할 수 없음
- BlockIO 절대값 비교는 의미 없음
- I/O 패턴 변화는 추가 측정 없이는 확정 불가

---

## 해석

이번 변경은 다음과 같이 이해하는 것이 정확하다.

- 리소스 사용량 자체를 줄인 것이 아니라
- **리소스 사용 패턴을 덜 극단적으로 만든 것**

즉:

Before:
- burst + disk saturation + 시스템 멈춤

After:
- 높은 부하는 유지되지만
- 시스템이 견딜 수 있는 형태로 분산됨

---

## 이번 단계에서 하지 않은 것

다음은 의도적으로 제외했다.

- Gold metrics `cache()` 제거
- Spark job 로직 변경
- production 수준 tuning
- benchmark 자동화

이들은 별도 PR에서 다룬다.

---

## 다음 단계

다음 PR 후보:

### 1. Gold metrics 리소스 최적화
- `task gold` 기준 측정
- cache 유지 vs 제거 비교

### 2. 측정 도구 정식 도입 여부
- scripts/monitor 도입
- benchmark runbook 작성

---

## 결론

이번 설정은 다음을 달성했다.

- 로컬 Spark 실행 안정성 개선
- 디스크 포화로 인한 시스템 멈춤 완화
- 반복 실행 가능한 개발 환경 확보

하지만:

- 최적값이 확정된 것은 아니다
- 이후 Gold 단계에서 추가 튜닝이 필요할 수 있다

현재 설정은 **로컬 개발을 위한 합리적인 baseline**이다.