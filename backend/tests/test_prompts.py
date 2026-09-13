"""
Unit test suite for centralized prompts and dynamic '%VALUE%' placeholder substitution.
"""

from prompts import (
    INTRADAY_MARKET_SETUP_PROMPT,
    MARKET_SENTIMENT_ANALYSIS_PROMPT,
    VERBAL_PITCH_PROMPT,
    render_prompt,
    GenPrompts
)


def test_intraday_market_setup_prompt_placeholders():
    """Verifies that all '%KEY%' tokens in the intraday setup prompt are substituted at runtime."""
    rendered = render_prompt(
        INTRADAY_MARKET_SETUP_PROMPT,
        symbol="NIFTY 50",
        close=24850.50,
        ema_9=24820.10,
        ema_21=24790.00,
        vwap=24800.00,
        rsi=58.5,
        atr=45.2,
        call_option="NIFTY 24850 CE",
        put_option="NIFTY 24850 PE"
    )

    # Check that placeholders were replaced
    assert "%SYMBOL%" not in rendered
    assert "%CLOSE%" not in rendered
    assert "%EMA_9%" not in rendered
    assert "%EMA_21%" not in rendered
    assert "%VWAP%" not in rendered
    assert "%RSI%" not in rendered
    assert "%ATR%" not in rendered
    assert "%CALL_OPTION%" not in rendered
    assert "%PUT_OPTION%" not in rendered

    # Check that actual values appear
    assert "NIFTY 50" in rendered
    assert "24850.5" in rendered
    assert "24820.1" in rendered
    assert "NIFTY 24850 CE" in rendered
    assert "NIFTY 24850 PE" in rendered


def test_verbal_pitch_prompt_placeholders():
    """Verifies verbal pitch placeholder replacement."""
    rendered = GenPrompts.render(
        GenPrompts.VERBAL_PITCH,
        instrument="BANK NIFTY 52000 CE",
        action="BUY",
        entry_price=350.0,
        stop_loss=300.0,
        target=440.0,
        confidence=88
    )

    assert "%INSTRUMENT%" not in rendered
    assert "%ACTION%" not in rendered
    assert "%ENTRY_PRICE%" not in rendered
    assert "%STOP_LOSS%" not in rendered
    assert "%TARGET%" not in rendered
    assert "%CONFIDENCE%" not in rendered

    assert "BANK NIFTY 52000 CE" in rendered
    assert "₹350" in rendered
    assert "88%" in rendered
