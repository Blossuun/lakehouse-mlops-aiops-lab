# 0010 - Gold 레이어 모델링

## 배경

현재 데이터 파이프라인은 다음 단계까지 구축되었다.

```
Raw → Silver → Iceberg → Quality Gate
```

하지만 Silver 테이블은 **정제된 이벤트 데이터**일 뿐,
비즈니스에서 바로 사용할 수 있는 형태는 아니다.

따라서 Gold 레이어를 도입했다.

---

# Silver vs Gold

## Silver

정제된 사실 데이터.

예:

- 이벤트 로그
- 주문 기록
- 사용자 행동

특징:

- 중복 제거
- 타입 정규화
- 스키마 고정
- 품질 검증

즉

```
기술적으로 신뢰 가능한 데이터
```

---

## Gold

비즈니스 지표 중심 데이터.

예:

- 일별 매출
- 전환율
- 이벤트 집계

즉

```
업무 의사결정에 바로 사용할 데이터
```

---

# 왜 Silver가 필요한가

Silver를 거치지 않으면:

- 정제 로직과 집계 로직이 섞인다
- 문제 원인 추적이 어렵다
- 여러 지표 모델이 중복 구현된다

Silver는

```
여러 Gold 모델이 공유하는 데이터 기반
```

이다.

---

# 이번 PR에서 구현한 것

Gold 테이블:

```
gold.daily_event_metrics
gold.daily_revenue_metrics
gold.daily_conversion_metrics
```

생성 방식:

```
Spark aggregation
→ Iceberg table write
```

---

# 구현에서 고려한 점

### rerun-safe

동일 날짜 실행 시:

```
overwritePartitions()
```

사용

---

### snapshot 유지

Iceberg snapshot 히스토리를 유지하도록 설계.

---

# 이번 단계의 의미

이제 데이터 플랫폼은 다음 구조를 갖는다.

```
Raw ingestion
Silver cleaning
Iceberg table
Quality gate
Gold metrics
```

이 구조는 실제 데이터 플랫폼에서도 가장 흔한 형태이다.