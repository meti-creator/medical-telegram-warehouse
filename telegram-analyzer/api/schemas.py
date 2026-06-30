from pydantic import BaseModel, Field
from datetime import date
from typing import Optional


# ---- Endpoint 1: Top Products ----

class TopProductItem(BaseModel):
    """One row in the top-products report: a frequently mentioned term and its count."""
    term: str = Field(..., description="The word/term that appeared frequently in messages")
    mention_count: int = Field(..., description="Number of messages containing this term")

    class Config:
        from_attributes = True  # allows Pydantic to read this from SQLAlchemy result rows


# ---- Endpoint 2: Channel Activity ----

class ChannelActivityResponse(BaseModel):
    """Summary of a single channel's posting activity."""
    channel_name: str = Field(..., description="The Telegram channel's username")
    channel_type: str = Field(..., description="Business category: Pharmaceutical, Cosmetics, or Medical")
    total_posts: int = Field(..., description="Total number of messages scraped from this channel")
    avg_views: float = Field(..., description="Average view count across all messages")
    first_post_date: Optional[date] = Field(None, description="Date of the earliest scraped message")
    last_post_date: Optional[date] = Field(None, description="Date of the most recent scraped message")

    class Config:
        from_attributes = True


# ---- Endpoint 3: Message Search ----

class MessageSearchResult(BaseModel):
    """One matching message from a keyword search."""
    message_id: int = Field(..., description="Telegram's internal message ID")
    channel_name: str = Field(..., description="Channel the message belongs to")
    message_date: date = Field(..., description="Date the message was posted")
    message_text: str = Field(..., description="The message's text content")
    view_count: int = Field(..., description="Number of views the message received")

    class Config:
        from_attributes = True


# ---- Endpoint 4: Visual Content Stats ----

class VisualContentStat(BaseModel):
    """Image usage statistics for a single channel."""
    channel_name: str = Field(..., description="The Telegram channel's username")
    total_messages: int = Field(..., description="Total messages from this channel")
    messages_with_images: int = Field(..., description="Number of messages that included an image")
    image_usage_rate: float = Field(..., description="Proportion of messages that include an image (0-1)")

    class Config:
        from_attributes = True
