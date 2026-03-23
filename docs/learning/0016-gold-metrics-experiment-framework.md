# 0016. Gold Metrics Execution Strategy (Measured Comparison)

## 왜 이 문서를 남기는가

이전 단계에서 Gold metrics를 다음 구조로 정리했다.

- cache 제거
- single-pass aggregate 구조 도입
- create / rerun write 경로 정리

하지만 이 구조가 실제로 더 나은 선택인지에 대해서는
"설계 의도"가 아니라 "측정 결과"로 판단할 필요가 있다.

따라서 이번 단계에서는 Gold 실행 전략을 비교하고,
그 결과를 기반으로 현재 기준을 확정한다.

---

## 비교 대상

다음 3가지 실행 모드를 동일 조건에서 비교했다.

1. single-pass
   - single aggregation → materialized row → 3개 table 파생

2. with-cache
   - df.cache() 후 기존 multi-aggregation 구조

3. multi-pass
   - cache 없이 groupBy를 여러 번 수행

---

## 실험 방법

- 동일한 dt 파티션 (`2026-02-27`)
- 동일한 local Docker / WSL 환경
- 각 모드별로 Gold 테이블 초기화 후 실행
- 실행 시간과 row count 기록

기록 형식:

mode, date, elapsed_sec, total_count

---

## 실험 결과

single-pass, 2026-02-27, 18.32, 4000  
with-cache, 2026-02-27, 17.70, 4000  
multi-pass, 2026-02-27, 17.65, 4000  

---

## 결과 해석

### 1. 세 방식의 실행 시간 차이는 크지 않다

- single-pass: 18.32s  
- with-cache: 17.70s  
- multi-pass: 17.65s  

차이는 약 0.6~0.7초 수준이다.

즉 현재 데이터 크기에서는:

- repeated scan 비용
- cache reuse 효과

둘 다 크게 드러나지 않는다.

---

### 2. cache는 기대만큼 유리하지 않다

with-cache는 가장 빠르지 않다.

- multi-pass가 더 빠르다
- single-pass는 오히려 가장 느리다

즉 local 환경에서는:

- cache 유지 비용
- materialization 비용

이 생각보다 크지 않거나,
오히려 약간의 오버헤드로 작용할 수 있다.

---

### 3. single-pass는 "성능"이 아니라 "구조"의 선택이다

single-pass의 목적은:

- 반복 스캔 제거
- 실행 구조 단순화
- 향후 확장성 확보

이지,

- 현재 데이터에서 더 빠르게 만드는 것

은 아니다.

실험 결과도 이를 뒷받침한다.

---

### 4. 현재 데이터 크기에서는 I/O 병목이 지배적이지 않다

quality 단계에서 관찰된 디스크 포화 문제와 달리,

Gold 단계에서는:

- 데이터 크기가 상대적으로 작고
- groupBy 결과가 단일 row로 축소되기 때문에

I/O 병목이 크게 드러나지 않는다.

---

## 현재 기준에서의 결론

현재 프로젝트의 local baseline에서는:

- 성능 기준으로는 세 방식의 차이가 거의 없다
- 안정성 기준에서는 cache가 리스크를 가질 수 있다

따라서 다음 원칙을 채택한다.

    local baseline:
        cache 제거
        single-pass 구조 유지

이유:

- 구조가 더 명확하다
- 반복 스캔 제거라는 설계 의도가 유지된다
- cache로 인한 spill 리스크를 피할 수 있다
- 성능 손해가 거의 없다

---

## 중요한 해석

이번 실험에서 가장 중요한 포인트는 이것이다.

    "single-pass가 더 빠르다"가 아니라
    "single-pass로 바꿔도 손해가 없다"

즉 이 변경은 성능 최적화가 아니라:

- 구조 단순화
- 리스크 제거
- 실행 안정성 확보

를 위한 선택이다.

---

## 이번 단계에서 하지 않은 것

- larger dataset 기준 비교
- multi-date aggregation
- cluster 환경 비교
- Spark physical plan 분석

이들은 다음 단계에서 다룰 수 있다.

---

## 향후 재검토 조건

다음 조건이 생기면 다시 판단한다.

- 데이터 크기가 크게 증가
- groupBy 결과가 1-row가 아닌 경우
- cluster 환경으로 이동
- Gold 단계가 실제 병목으로 확인된 경우

---

## 결론

현재 상태에서 가장 합리적인 선택은 다음이다.

    cache 제거 + single-pass 유지

이 선택은:

- 성능을 희생하지 않으면서
- 구조를 단순하게 만들고
- local 환경 안정성을 확보한다

즉, 이번 단계에서는

    "빠른 것"보다
    "안정적으로 반복 가능한 것"

을 선택한다.