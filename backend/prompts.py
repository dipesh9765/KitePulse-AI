"""
Root re-export shim for GenPrompts - KitePulse AI.
Allows seamless access to AI prompt templates from root-level modules and analyzers.
"""

from app.core.prompts import (
    INTRADAY_MARKET_SETUP_PROMPT,
    MARKET_SENTIMENT_ANALYSIS_PROMPT,
    VERBAL_PITCH_PROMPT,
    render_prompt,
    GenPrompts
)

__all__ = [
    "INTRADAY_MARKET_SETUP_PROMPT",
    "MARKET_SENTIMENT_ANALYSIS_PROMPT",
    "VERBAL_PITCH_PROMPT",
    "render_prompt",
    "GenPrompts"
]
