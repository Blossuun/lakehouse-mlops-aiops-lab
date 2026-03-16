select
    event_date,
    count(distinct case when event_type = 'view' then session_id end) as view_sessions,
    count(distinct case when event_type = 'purchase' then session_id end) as purchase_sessions,
    case
        when count(distinct case when event_type = 'view' then session_id end) = 0 then 0.0
        else cast(count(distinct case when event_type = 'purchase' then session_id end) as double)
             / count(distinct case when event_type = 'view' then session_id end)
    end as conversion_rate
from {{ ref('stg_silver_events') }}
group by 1