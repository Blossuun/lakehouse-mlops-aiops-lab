from fastapi import FastAPI
from trino.dbapi import connect
import pandas as pd

app = FastAPI()


def run_query(sql, params=None):
    conn = connect(
        host="localhost",
        port=8080,
        user="trino",
    )
    cur = conn.cursor()
    cur.execute(sql, params or [])
    rows = cur.fetchall()
    cols = [c[0] for c in cur.description]
    return pd.DataFrame(rows, columns=cols)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics/overview")
def overview(date: str):
    sql = """
    SELECT
        e.dt,
        e.total_events,
        e.purchase_events,
        r.net_revenue
    FROM iceberg.gold.daily_event_metrics e
    JOIN iceberg.gold.daily_revenue_metrics r
        ON e.dt = r.dt
    WHERE e.dt = ?
    """
    df = run_query(sql, [date])
    return df.to_dict(orient="records")