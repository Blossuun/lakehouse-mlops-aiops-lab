# 0004 - Local Infra: MinIO + Postgres + MLflow

## Background

PR #2에서는 로컬에서 다음을 구성했다:

- MinIO (S3 compatible storage)
- Postgres (MLflow backend store)
- MLflow Tracking Server

단순히 Docker를 띄우는 것이 목적이 아니라,
실제 Lakehouse/MLOps 구조를 흉내 내는 것이 목표였다.

---

## Questions I Had

### 1. 왜 .env 파일을 코드에서 직접 읽지 않는가?

### 2. 왜 os.environ 기반으로 설계하는가?

### 3. 왜 스모크 스크립트는 exit code를 반환하는 구조인가?

### 4. 왜 `if __name__ == "__main__"` 패턴을 사용하는가?

---

## Question 1 - Why not read .env directly?

### Observation

`scripts/smoke_minio.py`는 `.env` 파일을 직접 읽지 않고,
OS 환경변수를 통해 설정을 받는다.

### Analysis

`.env`는 "개발 편의용 설정 파일"이다.

실행 환경은 다양하다:

- 로컬 개발 환경
- Docker container
- GitHub Actions
- Kubernetes
- ECS

이 환경들에서 공통 분모는 "환경변수"이다.

`.env`를 직접 읽는 코드는 실행 환경과 강하게 결합된다.

### Conclusion

코드는 환경에 의존하지 않고,
환경이 코드를 설정하도록 해야 한다.

This is a separation-of-concerns decision.

---

## Question 2 - Why use os.environ?

### Observation

모든 설정은 다음과 같이 가져온다:

```python
os.environ.get("AWS_ACCESS_KEY_ID")
```

### Reasoning

이 패턴은:

- 로컬 → PowerShell에서 주입 가능
- Docker → compose environment로 주입 가능
- CI → GitHub Secrets로 주입 가능
- Kubernetes → ConfigMap/Secret로 주입 가능

코드는 단 한 줄도 수정할 필요가 없다.

### Conclusion

환경 변수 기반 설계는
확장성과 배포 가능성을 동시에 확보한다.

---

## Question 3 - Why return exit codes?

### Observation

main()은 정수를 반환하고,
`raise SystemExit(main())`로 종료한다.

### Why not just print error?

CI, Docker, Kubernetes는
"출력"이 아니라 "exit code"를 본다.

- 0 → success
- non-zero → failure

### Conclusion

Exit code는 자동화 환경에서의 신호 체계다.

스모크 스크립트는 사람이 읽는 로그가 아니라,
자동화 시스템이 판단할 수 있는 구조로 설계되어야 한다.

---

## Question 4 - Why `if __name__ == "__main__"`?

### Observation

스크립트는 main()을 정의하고,
직접 실행될 때만 호출된다.

### Reasoning

이 파일은:

- CLI로 실행 가능
- 테스트에서 import 가능
- 다른 코드에서 재사용 가능

이 패턴은 실행과 라이브러리 역할을 분리한다.

### Conclusion

이 구조는 재사용성과 테스트 가능성을 높인다.

---

## Architectural Insight

이번 PR에서 구성한 구조는 단순 로컬 세팅이 아니다.

MLflow artifact store를 S3로 두는 것은,
향후 다음 확장을 의미한다:

- Spark/Iceberg 연결
- 대용량 모델 artifact 저장
- 분산 학습 결과 저장

MinIO는 단순 스토리지가 아니라,
Lakehouse로 확장 가능한 기반이다.

---

## What I Learned

- 환경과 코드는 분리해야 한다.
- exit code는 자동화 세계의 언어다.
- src-layout과 패키징은 초기부터 설계해야 한다.
- 로컬 Docker 환경은 클라우드의 축소판이다.
- 인프라 설계는 확장성을 고려한 추상화다.
