-- Custom data test: assert_positive_views
-- Business rule: view counts can never be negative. Telegram wouldn't
-- naturally produce a negative number, so a negative value here would
-- indicate a parsing/casting bug somewhere upstream. This test fails
-- if the query below returns any rows at all.

select
    message_id,
    view_count
from {{ ref('fct_messages') }}
where view_count < 0
