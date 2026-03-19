# Gold Metrics 계약서

이 문서는 Spark가 생성하는 Gold 레이어의 주요 지표 테이블을 정의한다.

Gold 레이어는 현재 프로젝트에서 **platform-owned aggregate layer** 로 취급한다.

즉, 이 레이어의 목적은 다음과 같다.

- Spark 배치 파이프라인의 집계 산출물 제공
- 프로그램적으로 소비 가능한 운영 집계 테이블 제공
- downstream batch / pipeline / feature preparation 후보 데이터 제공
- 반복 실행 가능한 aggregate artifact 유지

원본:

- `local.lakehouse.silver_events`

생성 대상:

- `local.gold.daily_event_metrics`
- `local.gold.daily_revenue_metrics`
- `local.gold.daily_conversion_metrics`

---

## 이 레이어의 소비자

이 레이어는 주로 다음 소비자를 대상으로 한다.

- Spark / batch 기반 후속 작업
- 데이터 플랫폼 내부 집계 산출물 소비자
- 프로그램적 aggregate input 이 필요한 downstream 작업
- 운영 파이프라인 관점의 정제된 지표 테이블이 필요한 경우

---

## analytics marts 와의 관계

이 프로젝트에는 Gold 레이어 외에도 Trino + dbt 기반 analytics marts 가 존재한다.

중요한 점:

- Gold 는 Spark가 생성하는 platform aggregate layer 이다
- dbt marts 는 analyst / BI / ad hoc query 를 위한 analytics semantic layer 이다
- 현재 dbt marts 는 `local.gold.*` 를 source 로 사용하지 않고,
  `iceberg.lakehouse.silver_events` 를 source 로 사용한다

즉, Gold 와 dbt marts 는 현재 구조에서 서로 다른 ownership 을 가진 별도 레이어이다.

비슷한 일별 지표가 존재할 수 있지만, 이는 현재 프로젝트에서 허용되는 구조적 중복이다.

---

## Non-Goals

이 문서는 다음을 정의하지 않는다.

- BI / dashboard 용 최종 semantic presentation 모델
- dbt marts 의 컬럼 naming 규칙
- analyst 친화적 lineage / test / semantic modeling 규칙
- 모든 소비자에게 단 하나의 절대적 지표 레이어

이 문서는 **Spark Gold aggregate tables 의 계약**만 정의한다.

---

## 1. daily_event_metrics

일별 이벤트 집계 테이블

### 컬럼

- `dt` : 날짜
- `total_events` : 전체 이벤트 수
- `view_events` : view 이벤트 수
- `search_events` : search 이벤트 수
- `add_to_cart_events` : add_to_cart 이벤트 수
- `purchase_events` : purchase 이벤트 수
- `refund_events` : refund 이벤트 수

### 용도

- 일별 이벤트 볼륨 집계
- batch / platform 관점의 이벤트 수준 aggregate
- downstream programmatic use 후보

---

## 2. daily_revenue_metrics

일별 매출 집계 테이블

### 컬럼

- `dt` : 날짜
- `gross_revenue` : 총 매출 합계
- `refund_amount` : 총 환불 금액 합계
- `net_revenue` : 순매출 (`gross_revenue - refund_amount`)

### 용도

- 일별 매출 수준 aggregate
- 프로그램적 매출 지표 입력
- pipeline-owned revenue summary

---

## 3. daily_conversion_metrics

일별 전환 관련 지표 테이블

### 컬럼

- `dt` : 날짜
- `view_events` : view 이벤트 수
- `add_to_cart_events` : add_to_cart 이벤트 수
- `purchase_events` : purchase 이벤트 수
- `view_to_cart_rate` : add_to_cart / view
- `cart_to_purchase_rate` : purchase / add_to_cart
- `view_to_purchase_rate` : purchase / view

### 용도

- 전환 퍼널 수준 aggregate
- downstream batch / feature / programmatic analysis 후보
- platform 관점의 conversion summary

---

## 운영 특성

현재 Gold 레이어의 운영 특성은 다음과 같다.

- `dt` 파티션 기반 집계
- rerun-safe overwrite 방식
- Spark 기반 생성
- Iceberg 테이블 형태로 관리

즉, Gold 는 현재 프로젝트에서
“분석 보기용 최종 테이블”이라기보다
**Spark 파이프라인이 소유하는 운영 집계 레이어**로 이해하는 것이 맞다.