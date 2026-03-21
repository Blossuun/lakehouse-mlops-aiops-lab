# 0015. Single-Pass Gold Aggregation (Local Stability without Cache)

## 왜 이 문서를 남기는가

이전 단계에서 `build_gold_metrics.py`의 `cache()`를 제거했다.

이 결정은 local Docker / WSL 환경에서 disk spill 리스크를 줄이는 데 초점이 있었다.

하지만 cache를 제거한 뒤에도 다음 문제가 남아 있었다.

- 같은 `df`를 여러 번 집계함
- event / revenue / conversion metrics 계산을 위해 반복적인 스캔이 발생함
- local 환경에서는 이 반복 스캔도 I/O 부담으로 이어질 수 있음

즉, 다음 단계의 목표는 다음과 같았다.

- cache는 유지하지 않음
- 대신 반복 집계를 single-pass aggregate 로 줄임

## 기존 구조

기존 Gold 계산 구조는 개념적으로 다음과 같았다.

    df
     ├─ count()
     ├─ groupBy(dt) -> event metrics
     ├─ groupBy(dt) -> revenue metrics
     └─ groupBy(dt) -> conversion metrics

이 방식의 문제:

- 같은 source를 여러 번 읽음
- local 환경에서 반복 스캔 부담이 큼
- cache를 제거한 이후에는 이 비용이 더 직접적으로 드러남

## 이번 변경

핵심 아이디어:

- reusable aggregate 를 한 번에 계산
- 그 결과로 세 개의 Gold table 을 파생

즉 구조를 다음처럼 바꿨다.

    df
     └─ single agg -> base_metrics (1 row)
          ├─ event_metrics
          ├─ revenue_metrics
          └─ conversion_metrics

이 방식의 장점:

- source scan 횟수 감소
- local disk / I/O 부담 완화
- cache 없이도 더 예측 가능한 실행

## 왜 이 방식이 맞는가

현재 Gold metrics 는 날짜 단위(`dt`)로만 생성한다.

그리고 `task gold`의 기본 사용 방식도 특정 `dt` 파티션 기준이다.

따라서 local baseline에서는 다음이 더 자연스럽다.

- 먼저 해당 날짜 파티션을 읽음
- reusable aggregate 를 한 번 계산
- 이를 1-row DataFrame 으로 유지
- 각 Gold table 을 여기서 파생

즉, 이 단계에서는 full generic distributed aggregation 보다
single-date local rerun stability가 더 중요하다.

## 추가로 같이 정리한 것

이번 변경에서는 write path도 같이 정리했다.

이전에는 Gold table 이 없을 때:

- `create()`
- 직후 다시 `overwritePartitions()`

패턴이 반복될 수 있었다.

이번에는 helper를 통해:

- 없으면 create
- 있으면 overwrite

로 나누어, 첫 생성 시 불필요한 추가 write를 피하도록 정리했다.

## 현재 기준의 선택

현재 local baseline 원칙은 다음과 같다.

- cache 사용하지 않음
- 반복 집계 줄임
- create path / rerun path 분리
- local rerun stability 우선

즉 이번 단계의 핵심은:

    cache 제거 + single-pass aggregate + first-create write 정리

이다.

## 이 변경이 의미하지 않는 것

이 변경은 다음을 의미하지 않는다.

- distributed Spark optimization 이 끝났다는 뜻은 아님
- cluster 환경에서도 이 방식이 무조건 최적이라는 뜻은 아님
- 더 큰 데이터에서도 현재 형태를 그대로 유지해야 한다는 뜻은 아님

이건 현재 프로젝트의 local baseline에 대한 결정이다.

## 향후 재검토 가능성

다음 경우에는 다시 설계를 볼 수 있다.

- dt 범위를 여러 날짜로 넓힐 때
- Gold table 종류가 더 많아질 때
- cluster 환경으로 옮길 때
- benchmark 결과가 다른 전략을 더 지지할 때

## 결론

현재 단계에서는:

- cache에 기대기보다
- single-pass aggregate 로 반복 스캔을 줄이고
- write path도 create / rerun 으로 정리하는 것이

local Docker / WSL 환경에서 더 현실적이다.