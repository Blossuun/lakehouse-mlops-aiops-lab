# 0006 - Silver 변환: Raw(JSONL) → Parquet(PyArrow, 스트리밍/청크)

## 배경

Raw(JSONL)는 원본 보존과 유연성을 위해 적합하지만,
다음과 같은 한계가 있다.

- 컬럼형 최적화가 없어 스캔/필터/집계가 느림
- 스키마가 가변적이라 downstream 처리가 복잡해짐
- 대용량에서는 JSON 파싱 비용과 메모리 사용이 커짐

따라서 Silver 레이어에서 다음을 목표로 한다.

- 스키마 고정(컬럼화)
- 최소 정제(dedup/타입 정규화/시간 파싱)
- 컬럼 포맷(Parquet)으로 저장

---

## 이번에 했던 선택과 이유

### 1) 왜 PyArrow인가?

- Parquet/Arrow 생태계 표준 도구
- Silver의 목적(포맷 변환 + 스키마 고정)에 직접 적합
- 이후 Spark/Iceberg 도입과 연결이 자연스럽다

### 2) 왜 반복문이 많은 구현이 걱정되었나?

초기 구현은 파이썬 루프 + 전체 메모리 적재 방식이 될 수 있다.
데이터가 커지면 다음 문제가 생긴다.

- S3 객체를 통째로 읽으면 메모리 사용량이 급증
- JSON 파싱이 CPU 병목
- rows → table 변환에서 반복이 누적

### 3) 왜 스트리밍(iter_lines) + 청크(part files)로 리팩터링했나?

현업에서는 “전체를 한 번에 메모리에 올려 처리”하지 않는다.
이번 PR에서는 최소한의 개선으로 다음을 확보했다.

- S3에서 JSONL을 스트리밍으로 읽는다(파일 전체를 메모리에 올리지 않음)
- 일정 row 단위로 Parquet part를 만든다(메모리 상한이 생김)
- part-*.parquet 형태의 출력은 병렬 처리/확장에 유리하다

### 4) Silver에서 dedup을 하는 이유

Raw에는 at-least-once 전달을 흉내낸 중복이 존재할 수 있다.
Silver에서 event_id 기준 dedup을 수행해 downstream 안정성을 확보한다.

(단, 어떤 dedup 정책을 쓸지는 업무 요구에 따라 달라질 수 있음)

### 5) Copilot 리뷰로 보완한 운영 관점 포인트

- **JSON 파싱 오류 관측:** 더티 Raw를 허용하더라도 “얼마나 버렸는지”를 알아야 한다.  
  그래서 `json_parse_errors` 카운터를 추가해 런 요약에 포함했다.
- **재현성:** S3 list 결과 순서에 의존하면 “first seen dedup” 결과가 매번 달라질 수 있다.  
  그래서 raw object key 목록을 정렬하여 결과를 안정화했다.
- **재실행 안전성:** 같은 날짜 파티션에 다시 실행하면 `part-*.parquet`가 섞일 수 있다.  
  그래서 변환 시작 시 기존 parquet part를 삭제하고 새로 쓴다.
- **Smoke 신뢰성:** smoke에서 bucket/prefix를 바꿀 수 있다면 transform 호출도 같은 값을 사용해야 한다.  
  그래서 env 값을 CLI 인자로 전달하도록 수정했다.

### 6) 스케일 한계(현재 설계의 제약)

- `event_id` dedup을 위해 파티션 내 모든 `event_id`를 in-memory set으로 유지한다.  
  파티션의 unique event 수가 커지면 메모리 병목이 될 수 있다.
- 이 문제는 다음 단계에서 **Spark/Iceberg**로 넘어가며 분산/외부 정렬 기반으로 해결하는 것이 자연스럽다.

---

## Silver에서 수행한 최소 정제

- `event_id` 기준 중복 제거
- `event_time`, `ingest_time` 파싱(UTC timestamp)
- 숫자 필드 타입 정규화(예: "price": "12900" → 12900)
- payload 핵심 필드를 컬럼으로 승격 + payload_json 보존

---

## 내가 배운 점

- “빠르게 보이는 구현”이 반드시 확장 가능한 구현은 아니다.
- 스트리밍과 청크는 대용량 처리의 최소 안전장치다.
- 레이어를 나누면( Raw → Silver ) 이후 Spark/Iceberg로 확장할 때 설계가 깔끔해진다.
