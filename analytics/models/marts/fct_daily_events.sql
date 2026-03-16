select
    event_date,
    count(*) as event_count,
    count(distinct user_id) as unique_users,
    count(distinct session_id) as unique_sessions
from {{ ref('stg_silver_events') }}
group by 1