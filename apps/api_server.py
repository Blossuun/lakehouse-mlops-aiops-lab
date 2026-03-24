from __future__ import annotations

import datetime as dt
import os

import pandas as pd
from fastapi import FastAPI
from trino.dbapi import connect

app = FastAPI()


def get_trino_connection():
    return connect(
        host=os.getenv("TRINO_HOST", "localhost"),
        port=int(os.getenv("TRINO_PORT", "8080")),
        user=os.getenv("TRINO_USER", "trino"),
    )


def run_query(sql: str, params: list | tuple | None = None) -> pd.DataFrame:
    conn = None
    cur = None
    try:
        conn = get_trino_connection()
        cur = conn.cursor()
        cur.execute(sql, params or [])
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description] if cur.description else []
        return pd.DataFrame(rows, columns=cols)
    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics/overview")
def overview(date: dt.date):
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
    df = run_query(sql, [date.isoformat()])
    return df.to_dict(orient="records")
