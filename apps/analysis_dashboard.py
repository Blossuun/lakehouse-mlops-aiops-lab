from __future__ import annotations

import os

import pandas as pd
import streamlit as st
from trino.dbapi import connect


def get_trino_connection():
    return connect(
        host=os.getenv("TRINO_HOST", "localhost"),
        port=int(os.getenv("TRINO_PORT", "8080")),
        user=os.getenv("TRINO_USER", "trino"),
        catalog=os.getenv("TRINO_CATALOG", "iceberg"),
        schema=os.getenv("TRINO_SCHEMA", "gold"),
    )


@st.cache_data(ttl=30, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    conn = get_trino_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        return pd.DataFrame(rows, columns=columns)
    finally:
        cur.close()
        conn.close()


def fetch_available_dates() -> list[str]:
    sql = """
    SELECT dt
    FROM iceberg.gold.daily_event_metrics
    ORDER BY dt DESC
    """
    df = run_query(sql)
    if df.empty:
        return []
    return [str(v) for v in df["dt"].dropna().tolist()]


def fetch_daily_business_overview(selected_date: str) -> pd.DataFrame:
    sql = f"""
    SELECT
        e.dt,
        e.total_events,
        e.purchase_events,
        e.refund_events,
        r.gross_revenue,
        r.refund_amount,
        r.net_revenue
    FROM iceberg.gold.daily_event_metrics e
    JOIN iceberg.gold.daily_revenue_metrics r
        ON e.dt = r.dt
    WHERE e.dt = '{selected_date}'
    ORDER BY e.dt
    """
    return run_query(sql)


def fetch_conversion_funnel(selected_date: str) -> pd.DataFrame:
    sql = f"""
    SELECT
        dt,
        view_events,
        add_to_cart_events,
        purchase_events,
        view_to_cart_rate,
        cart_to_purchase_rate,
        view_to_purchase_rate
    FROM iceberg.gold.daily_conversion_metrics
    WHERE dt = '{selected_date}'
    ORDER BY dt
    """
    return run_query(sql)


def fetch_top_products(selected_date: str) -> pd.DataFrame:
    sql = f"""
    SELECT
        product_id,
        COUNT(*) AS purchase_count,
        SUM(total_amount) AS revenue
    FROM iceberg.lakehouse.silver_events
    WHERE event_type = 'purchase'
      AND dt = '{selected_date}'
      AND product_id IS NOT NULL
      AND TRIM(product_id) <> ''
    GROUP BY product_id
    ORDER BY revenue DESC
    LIMIT 10
    """
    return run_query(sql)


def render_connection_sidebar() -> None:
    st.sidebar.header("Connection")
    st.sidebar.write(f"Host: {os.getenv('TRINO_HOST', 'localhost')}")
    st.sidebar.write(f"Port: {os.getenv('TRINO_PORT', '8080')}")
    st.sidebar.write(f"Catalog: {os.getenv('TRINO_CATALOG', 'iceberg')}")
    st.sidebar.write(f"Schema: {os.getenv('TRINO_SCHEMA', 'gold')}")

    if st.sidebar.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()


def main():
    st.set_page_config(page_title="Lakehouse Analysis Dashboard", layout="wide")
    st.title("Lakehouse Analysis Dashboard")
    st.caption("Read-only Trino dashboard for Gold/Silver consumption")

    render_connection_sidebar()

    try:
        available_dates = fetch_available_dates()
    except Exception as e:
        st.error(f"Failed to load dates from Trino: {e}")
        st.stop()

    if not available_dates:
        st.warning("No available dates found in Gold metrics tables.")
        st.stop()

    selected_date = st.sidebar.selectbox("Business date", available_dates, index=0)

    try:
        overview_df = fetch_daily_business_overview(selected_date)
        funnel_df = fetch_conversion_funnel(selected_date)
        products_df = fetch_top_products(selected_date)
    except Exception as e:
        st.error(f"Failed to load dashboard data: {e}")
        st.stop()

    st.subheader("Daily Business Overview")
    if overview_df.empty:
        st.warning("No overview data found.")
    else:
        row = overview_df.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Events", int(row["total_events"]))
        c2.metric("Purchase Events", int(row["purchase_events"]))
        c3.metric("Refund Events", int(row["refund_events"]))
        c4.metric("Net Revenue", f"{float(row['net_revenue']):,.2f}")
        st.dataframe(overview_df, use_container_width=True)

    st.subheader("Conversion Funnel")
    st.dataframe(funnel_df, use_container_width=True)

    st.subheader("Top Products")
    st.dataframe(products_df, use_container_width=True)


if __name__ == "__main__":
    main()