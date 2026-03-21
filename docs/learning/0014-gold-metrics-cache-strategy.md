# 0014. Gold Metrics Cache Strategy (Local vs Spill Tradeoff)

## 왜 이 문서를 남기는가

`build_gold_metrics.py`는 동일한 Silver DataFrame을 여러 집계에 재사용한다.

현재 구조:

- 전체 row count 확인
- daily_event_metrics 집계
- daily_revenue_metrics 집계
- daily_conversion_metrics 집계

이 구조만 보면 `cache()`를 사용하는 것이 자연스럽다.

하지만 로컬 Docker / WSL 환경에서는
cache가 항상 성능 향상으로 이어지지 않는다.

이번 단계에서는
**로컬 개발 환경에서의 안정성**을 기준으로
Gold 단계의 cache 전략을 다시 정리한다.

---

## 기존 접근

기존 코드는 다음과 같았다.

- Silver 테이블을 읽은 뒤 `cache()`
- 이후 count + 여러 groupBy 집계를 같은 DataFrame에서 재사용

의도는 단순했다.

- 반복 읽기 방지
- 여러 집계 계산 시 재사용 최적화

---

## 문제

로컬 환경에서는 다음이 발생할 수 있다.

- cache가 메모리에 완전히 유지되지 못함
- 일부 또는 대부분이 disk spill로 전환됨
- 디스크 I/O 압박 증가
- 결과적으로 local rerun 안정성 저하

즉:

`cache()`는 cluster 환경이나 충분한 메모리 환경에서는 유리할 수 있지만,
현재 프로젝트의 local Docker / WSL 환경에서는
오히려 불안정성을 키울 수 있다.

---

## 선택지 비교

### 선택지 A. cache 유지

장점:

- 메모리에 유지되면 반복 집계에 유리
- source 재읽기 감소 가능

단점:

- 메모리 부족 시 spill 유발 가능
- local disk pressure 증가 가능
- host 전체 응답성 저하 가능

### 선택지 B. cache 제거

장점:

- spill 리스크 감소
- 로컬 안정성 개선 가능
- 실행 방식이 더 예측 가능해짐

단점:

- 같은 source를 여러 번 다시 읽게 됨
- 절대 실행 시간이 더 빨라진다고 보장할 수는 없음

---

## 이번 결정

현재 프로젝트의 로컬 기본 원칙은 다음과 같다.

- 최대 처리량보다 재실행 안정성 우선
- host 전체를 불안정하게 만드는 최적화는 피함
- local baseline을 먼저 안정화한 뒤 필요하면 다시 공격적으로 튜닝

따라서 이번 단계에서는:

- `build_gold_metrics.py`에서 `cache()`를 제거한다

---

## 이 결정이 의미하는 것

이 결정은 다음을 의미하지 않는다.

- cache가 항상 나쁘다
- production에서도 cache를 쓰면 안 된다
- Spark 재사용 최적화가 필요 없다는 뜻이다

이 결정은 오직 다음 문맥에 대한 것이다.

- local Docker / WSL
- single-node smoke / lab workflow
- 안정성 우선

즉, 이건 **로컬 개발 환경에 대한 전략**이다.

---

## 현재 기준의 해석

현재 Gold 단계는 다음과 같이 이해하는 것이 맞다.

- 반복 읽기가 조금 늘어날 수 있다
- 하지만 로컬 디스크 spill 리스크를 줄이는 편이 더 중요하다
- 따라서 local baseline에서는 cache 없이 유지한다

---

## 향후 재검토 기준

다음 경우에는 다시 검토할 수 있다.

- 데이터 크기가 지금보다 크게 증가
- cluster 환경으로 옮겨감
- local memory 여유가 커짐
- task gold가 다시 주요 병목으로 확인됨
- selective cache / persist 전략을 시험할 필요가 생김

---

## 결론

현재 프로젝트의 로컬 환경 기준에서는:

- `cache()` 유지보다
- spill 리스크를 줄이는 방향이 더 적절하다

따라서 Gold 단계에서는
**local stability > cache reuse** 원칙을 유지한다.