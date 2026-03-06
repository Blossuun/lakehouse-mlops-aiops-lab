# 0009 - Iceberg Silver Data Quality Gate

## 배경

현재 데이터 파이프라인 구조는 다음과 같다.

```
Raw(JSONL)
  ↓
Silver(Parquet)
  ↓
Iceberg Table
```

하지만 테이블이 존재한다고 해서 데이터가 **신뢰 가능한 상태**라는 보장은 없다.

실무에서는 다음 질문이 항상 따라온다.

- 이 데이터를 분석에 사용해도 되는가?
- 이 데이터를 모델 학습에 사용해도 되는가?

이를 해결하기 위해 **데이터 품질 게이트(Data Quality Gate)**를 도입했다.

---

## 데이터 품질 게이트란 무엇인가

데이터 품질 게이트는:

> 데이터가 downstream 단계로 넘어가기 전에  
> 일정한 품질 기준을 만족하는지 검증하는 단계

이다.

즉,

```
데이터 존재 여부 ≠ 데이터 사용 가능
```

이다.

---

## 이번 PR에서 구현한 것

Spark 기반 품질 검증 job:

```
jobs/spark/check_silver_quality.py
```

이 job은 다음을 수행한다.

1. Iceberg 테이블 조회
2. 특정 dt 파티션 데이터 로드
3. 품질 규칙 계산
4. JSON 리포트 생성
5. 실패 시 non-zero exit

---

## 검증 대상

테이블:

```
local.lakehouse.silver_events
```

검증 단위:

```
dt = YYYY-MM-DD
```

---

## 구현한 품질 규칙

대표적인 규칙:

### 1️⃣ event_id 중복 없음

```
count(event_id) == count(distinct event_id)
```

---

### 2️⃣ event_type 허용 값

허용 값:

```
view
search
add_to_cart
purchase
refund
```

---

### 3️⃣ 시간 무결성

```
event_time <= ingest_time
```

---

### 4️⃣ 금액 컬럼 음수 금지

대상 컬럼:

```
price
total_amount
refund_amount
```

---

### 5️⃣ 이벤트 타입별 필수 컬럼

예:

```
purchase → order_id 필수
search → search_query 필수
refund → refund_amount 필수
```

---

## 품질 검증 범위를 dt 파티션으로 제한한 이유

전체 테이블 검증은 비용이 크다.

따라서 실무에서는 보통 다음 단위로 검증한다.

- 신규 파티션
- 증분 데이터
- 특정 기간 데이터

이번 구현에서는:

```
dt = YYYY-MM-DD
```

단위로 검증한다.

---

## smoke script를 별도로 만든 이유

PowerShell script:

```
scripts/smoke_silver_quality.ps1
```

역할:

- Spark job 실행
- Ivy cache 준비
- 결과 코드 확인
- 품질 게이트 성공/실패 판단

이렇게 하면 개발자가 다음 명령으로 바로 검증할 수 있다.

```
powershell scripts/smoke_silver_quality.ps1 -Date 2026-02-27
```

---

## 이번 구현에서 배운 점

### 1️⃣ 데이터 품질 검증은 “데이터 파이프라인의 일부”다

품질 검증은 분석 도구가 아니라 **엔지니어링 파이프라인의 단계**다.

---

### 2️⃣ fail-fast 전략

이번 구현은:

```
규칙 하나라도 FAIL → pipeline 중단
```

전략을 사용했다.

---

### 3️⃣ bad data는 아직 격리하지 않는다

현재 구현은:

- 데이터 수정 없음
- quarantine 없음

즉,

```
검증 → 실패 → pipeline 중단
```

까지만 수행한다.

---

## 다음 개선 아이디어

- WARN / FAIL 규칙 분리
- quarantine dataset
- audit Iceberg table
- 품질 metric 시계열 저장

---

## 이번 단계의 의미

이제 파이프라인은 다음 구조를 갖는다.

```
Raw ingestion
→ Silver transform
→ Iceberg table
→ Iceberg operations
→ Data Quality Gate
```

즉,

데이터는 이제 **존재하는 것뿐 아니라 신뢰 가능한 상태인지 검증되는 단계**에 도달했다.