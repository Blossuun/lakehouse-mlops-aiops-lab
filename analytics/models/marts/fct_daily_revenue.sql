select
    event_date,
    count_if(event_type = 'purchase') as order_events,
    count(distinct case when event_type = 'purchase' then user_id end) as paying_users,
    coalesce(sum(case when event_type = 'purchase' then total_amount else 0 end), 0) as gross_revenue,
    coalesce(sum(case when event_type = 'refund' then refund_amount else 0 end), 0) as refund_amount,
    coalesce(
        sum(case when event_type = 'purchase' then total_amount else 0 end),
        0
    ) - coalesce(
        sum(case when event_type = 'refund' then refund_amount else 0 end),
        0
    ) as net_revenue
from {{ ref('stg_silver_events') }}
group by 1