from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import re
from collections import Counter

from database import get_db
import schemas

app = FastAPI(
    title="Medical Telegram Warehouse API",
    description="Analytical API exposing insights from the medical Telegram data warehouse.",
    version="1.0.0",
)


# A small list of common words to exclude from "top products" - these
# appear constantly in any text but aren't meaningful product/term mentions.
STOPWORDS = {
    "the", "and", "for", "are", "you", "with", "this", "that", "from",
    "your", "have", "has", "will", "all", "our", "can", "not", "more",
    "new", "get", "out", "use", "now", "any", "per", "via",
}


@app.get(
    "/api/reports/top-products",
    response_model=List[schemas.TopProductItem],
    tags=["Reports"],
    summary="Most frequently mentioned terms across all channels",
    description=(
        "Returns the most frequently occurring words found in message text "
        "across all scraped channels, excluding common stopwords. This is a "
        "simple word-frequency analysis, not true product-name extraction."
    ),
)
def get_top_products(
    limit: int = Query(10, ge=1, le=100, description="Number of top terms to return"),
    db: Session = Depends(get_db),
):
    # Pull all message text from the warehouse's fact table.
    result = db.execute(text("SELECT message_text FROM marts.fct_messages WHERE message_text IS NOT NULL"))
    rows = result.fetchall()

    # Tally word frequency across every message, in Python rather than SQL -
    # tokenizing/stopword filtering is easier expressed this way than in raw SQL.
    word_counter = Counter()
    for row in rows:
        text_value = row[0]
        # Extract lowercase word-like tokens (letters only, 3+ characters)
        words = re.findall(r"[a-zA-Z]{3,}", text_value.lower())
        for word in words:
            if word not in STOPWORDS:
                word_counter[word] += 1

    top_terms = word_counter.most_common(limit)

    return [
        schemas.TopProductItem(term=term, mention_count=count)
        for term, count in top_terms
    ]


@app.get(
    "/api/channels/{channel_name}/activity",
    response_model=schemas.ChannelActivityResponse,
    tags=["Channels"],
    summary="Posting activity and trends for a specific channel",
    description="Returns aggregated posting statistics for a single channel, sourced from dim_channels.",
)
def get_channel_activity(
    channel_name: str,
    db: Session = Depends(get_db),
):
    query = text("""
        SELECT
            channel_name,
            channel_type,
            total_posts,
            avg_views,
            first_post_date,
            last_post_date
        FROM marts.dim_channels
        WHERE channel_name = :channel_name
    """)

    result = db.execute(query, {"channel_name": channel_name})
    row = result.fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Channel '{channel_name}' not found.",
        )

    return schemas.ChannelActivityResponse(
        channel_name=row.channel_name,
        channel_type=row.channel_type,
        total_posts=row.total_posts,
        avg_views=float(row.avg_views),
        first_post_date=row.first_post_date,
        last_post_date=row.last_post_date,
    )


@app.get(
    "/api/search/messages",
    response_model=List[schemas.MessageSearchResult],
    tags=["Search"],
    summary="Search for messages containing a keyword",
    description="Performs a case-insensitive search for messages whose text contains the given query string.",
)
def search_messages(
    query: str = Query(..., min_length=1, description="Keyword to search for in message text"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results to return"),
    db: Session = Depends(get_db),
):
    sql = text("""
        SELECT
            fm.message_id,
            dc.channel_name,
            dd.full_date AS message_date,
            fm.message_text,
            fm.view_count
        FROM marts.fct_messages fm
        JOIN marts.dim_channels dc ON fm.channel_key = dc.channel_key
        JOIN marts.dim_dates dd ON fm.date_key = dd.date_key
        WHERE fm.message_text ILIKE :search_pattern
        ORDER BY dd.full_date DESC
        LIMIT :limit
    """)

    # ILIKE = case-insensitive LIKE in Postgres. Wrapping the search term
    # in % wildcards means "contains this text anywhere", not "starts with"
    # or "exact match".
    search_pattern = f"%{query}%"

    result = db.execute(sql, {"search_pattern": search_pattern, "limit": limit})
    rows = result.fetchall()

    return [
        schemas.MessageSearchResult(
            message_id=row.message_id,
            channel_name=row.channel_name,
            message_date=row.message_date,
            message_text=row.message_text,
            view_count=row.view_count,
        )
        for row in rows
    ]


@app.get(
    "/api/reports/visual-content",
    response_model=List[schemas.VisualContentStat],
    tags=["Reports"],
    summary="Image usage statistics across channels",
    description="Returns, per channel, how many messages include an image and what proportion of total posts that represents.",
)
def get_visual_content_stats(db: Session = Depends(get_db)):
    sql = text("""
        SELECT
            dc.channel_name,
            COUNT(fm.message_id) AS total_messages,
            COUNT(fm.message_id) FILTER (WHERE fm.has_image) AS messages_with_images
        FROM marts.fct_messages fm
        JOIN marts.dim_channels dc ON fm.channel_key = dc.channel_key
        GROUP BY dc.channel_name
        ORDER BY dc.channel_name
    """)

    result = db.execute(sql)
    rows = result.fetchall()

    stats = []
    for row in rows:
        # Guard against dividing by zero, even though every channel here
        # has at least one message.
        rate = (row.messages_with_images / row.total_messages) if row.total_messages > 0 else 0.0

        stats.append(
            schemas.VisualContentStat(
                channel_name=row.channel_name,
                total_messages=row.total_messages,
                messages_with_images=row.messages_with_images,
                image_usage_rate=round(rate, 4),
            )
        )

    return stats