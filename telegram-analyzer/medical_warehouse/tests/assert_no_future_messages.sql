-- Custom data test: assert_no_future_messages
-- Business rule: a message can never have a date in the future relative to
-- when this test is run. If any rows come back, that's a real data problem
-- (e.g. timezone bug, bad parsing, clock skew) - dbt fails this test
-- whenever the query below returns 1 or more rows.

select
    f.message_id,
    d.full_date
from {{ ref('fct_messages') }} as f
inner join {{ ref('dim_dates') }} as d
    on f.date_key = d.date_key
where d.full_date > current_date
