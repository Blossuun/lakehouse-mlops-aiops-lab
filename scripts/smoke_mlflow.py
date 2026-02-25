import os
import time
import mlflow


def wait_for_mlflow(uri: str, timeout_s: int = 60) -> None:
    start = time.time()
    while True:
        try:
            mlflow.set_tracking_uri(uri)
            mlflow.search_experiments()
            return
        except Exception:
            if time.time() - start > timeout_s:
                raise
            time.sleep(2)


def main() -> int:
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
    wait_for_mlflow(tracking_uri)

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("smoke-local-mlflow")

    with mlflow.start_run(run_name="smoke-run") as run:
        mlflow.log_param("env", "local")
        mlflow.log_metric("accuracy", 0.123)

        # log an artifact
        os.makedirs("tmp", exist_ok=True)
        path = os.path.join("tmp", "note.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("hello mlflow\n")
        mlflow.log_artifact(path)

        print(f"OK: MLflow smoke run logged. run_id={run.info.run_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
