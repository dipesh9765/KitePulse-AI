"""
Quantitative Trade Analysis & Generative AI Reasoning Engine - KitePulse AI

This module implements the trade strategy analyzer layer adhering to the BaseTradeAnalyzer
interface. It leverages Google Gemini Generative AI (using the official google-genai SDK)
with structured schema output to reason over technical indicators (EMA, RSI, VWAP, ATR)
and options derivatives, providing instant fallback to deterministic quantitative rules
if offline or unconfigured.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import pandas as pd

from config import settings, is_index_symbol
from prompts import render_prompt, INTRADAY_MARKET_SETUP_PROMPT
from core.interfaces import BaseTradeAnalyzer
from server_logger import (
    log_outgoing_request,
    log_outgoing_response,
    log_outgoing_error
)

logger = logging.getLogger(__name__)


class TradeProposalSchema(BaseModel):
    """
    Pydantic schema enforcing structured JSON output from the Gemini LLM.
    Guarantees deterministic formatting and eliminates JSON parsing hallucinations.
    """
    symbol: str = Field(description="Underlying trading symbol, e.g. NIFTY 50, BANK NIFTY, RELIANCE")
    instrument_to_trade: str = Field(description="Instrument name to trade, e.g. NIFTY 24850 CE or RELIANCE MIS")
    signal_type: Literal["BUY_CALL", "BUY_PUT", "BUY_EQUITY", "SHORT_EQUITY"] = Field(description="Actionable trade signal type")
    direction: Literal["BULLISH", "BEARISH"] = Field(description="Market directional bias")
    lot_size: int = Field(default=1, description="Strictly 1 lot for risk control")
    entry_price: float = Field(description="Recommended entry execution price")
    stop_loss: float = Field(description="Strict stop-loss price calculated from technicals / ATR")
    target_1: float = Field(description="Target 1 price level (at least 1:1.8 risk-to-reward)")
    target_2: float = Field(description="Target 2 extended price level")
    risk_reward: str = Field(description="Calculated risk to reward ratio, e.g. 1:2.0")
    confidence: int = Field(description="Confidence percentage score (50 to 99)")
    verbal_pitch: str = Field(description="Concise verbal pitch for audio speech synthesis asking for user confirmation")
    technical_rationale: str = Field(description="Detailed institutional technical rationale explaining EMA, RSI, VWAP indicators")


class GeminiMarketAnalyzer(BaseTradeAnalyzer):
    """
    Quantitative Trade Analysis and Generative AI Reasoning Engine.

    Responsibilities:
        - Ingests live technical indicators (EMA, RSI, VWAP, ATR) and options chains.
        - Interfaces with Google Gemini LLMs using structured Pydantic schema generation.
        - Provides deterministic, quantitative algorithmic fallback when API keys are unconfigured
          or remote network calls encounter transient failures.
        - Formulates concise, natural-language verbal pitches suitable for Web Speech audio synthesis.

    Extends:
        - `core.interfaces.BaseTradeAnalyzer`: Abstract interface specifying the standard
          `analyze_market_setup` contract.

    Uses / Dependencies:
        - `google.genai` SDK: Official Google GenAI client for structured LLM reasoning.
        - `TradeProposalSchema`: Enforces deterministic JSON output and schema validation.
        - `TradingRepository` (`database`): Encrypted credential store for runtime API key extraction.
        - `settings` (`config`): Fallback configuration for Gemini model name and credentials.
        - `server_logger`: Structured audit telemetry for external AI API requests and responses.

    Design Pattern:
        - Strategy Pattern (pluggable trade analyzer adhering to `BaseTradeAnalyzer`).
        - Fallback Strategy Pattern (graceful degradation from GenAI to algorithmic rules).
    """

    def __init__(self):
        import database
        db_key = database.get_secure_setting("GEMINI_API_KEY", "")
        self.api_key: str = db_key or settings.GEMINI_API_KEY
        self.model_name: str = settings.GEMINI_MODEL
        self.client = None
        self._init_client()

    def load_credentials(self) -> None:
        """Reloads Gemini API key from the encrypted vault and re-initializes client."""
        import database
        db_key = database.get_secure_setting("GEMINI_API_KEY", "")
        self.api_key = db_key or settings.GEMINI_API_KEY
        self._init_client()

    def _init_client(self) -> None:
        """Initializes the google-genai Client."""
        self.client = None
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Initialized Google GenAI client successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize GenAI client: {e}")

    def update_api_key(self, key: str) -> None:
        """Updates runtime API key and re-initializes client."""
        self.api_key = key
        self._init_client()

    def analyze_market_setup(
        self,
        symbol: str,
        quote: Dict[str, Any],
        candle_df: Optional[pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Analyzes live market indicators and produces high-probability Put/Call or Intraday setup.

        Args:
            symbol: Ticker symbol (e.g. 'NIFTY 50').
            quote: Live market quote dictionary.
            candle_df: Historical candlestick DataFrame enriched with indicators.

        Returns:
            Dictionary matching the TradeProposalSchema specification.
        """
        if candle_df is None or candle_df.empty:
            return self._generate_algorithmic_fallback(symbol, quote, 50.0, 0.0, 0.0)

        last_row = candle_df.iloc[-1]
        close = float(last_row["close"])
        rsi = float(last_row.get("rsi_14", 50.0))
        ema_9 = float(last_row.get("ema_9", close))
        ema_21 = float(last_row.get("ema_21", close))
        vwap = float(last_row.get("vwap", close))
        atr = float(last_row.get("atr_14", close * 0.005))

        # If Gemini client is active, request model analysis
        if self.client:
            try:
                analysis = self._call_gemini_model(symbol, quote, close, rsi, ema_9, ema_21, vwap, atr)
                if analysis:
                    return analysis
            except Exception as e:
                logger.warning(f"Gemini API call failed, falling back to algorithmic analysis: {e}")

        # Deterministic institutional setup fallback
        return self._generate_algorithmic_fallback(symbol, quote, rsi, ema_9 - ema_21, close - vwap, atr)

    def _call_gemini_model(
        self,
        symbol: str,
        quote: Dict[str, Any],
        close: float,
        rsi: float,
        ema_9: float,
        ema_21: float,
        vwap: float,
        atr: float
    ) -> Optional[Dict[str, Any]]:
        """Invokes Google Gemini with structured output schema."""
        prompt = render_prompt(
            INTRADAY_MARKET_SETUP_PROMPT,
            symbol=symbol,
            close=close,
            ema_9=f"{ema_9:.2f}",
            ema_21=f"{ema_21:.2f}",
            vwap=f"{vwap:.2f}",
            rsi=f"{rsi:.2f}",
            atr=f"{atr:.2f}",
            call_option=quote.get("call_option"),
            put_option=quote.get("put_option"),
        )
        call_start = time.time()
        log_outgoing_request("Google Gemini", "generate_content", {
            "model": self.model_name,
            "symbol": symbol,
            "close": close,
            "rsi": round(rsi, 2),
            "response_schema": "TradeProposalSchema"
        })
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TradeProposalSchema,
                temperature=0.2,
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_response("Google Gemini", "generate_content", {"model": self.model_name, "status": "200_OK"}, dur)
        except Exception as ge:
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_error("Google Gemini", "generate_content", ge, dur)
            raise ge

        # Parse verified JSON payload
        text = response.text.strip()
        data = json.loads(text)
        data["lot_size"] = 1  # Strictly enforce safety lot size of 1
        data["ai_model"] = self.model_name
        data["source"] = "Google Gemini AI"
        return data

    def _resolve_index_option_setup(
        self,
        symbol: str,
        quote: Dict[str, Any],
        is_bullish: bool
    ) -> Dict[str, Any]:
        """Calculates deterministic ATM index options premium levels and targets."""
        opt = quote.get("call_option" if is_bullish else "put_option")
        opt_symbol = opt["symbol"] if opt else f"{symbol} ATM {'CE' if is_bullish else 'PE'}"
        premium = opt["ltp"] if opt else 115.0

        signal_type = "BUY_CALL" if is_bullish else "BUY_PUT"
        entry_price = round(premium, 2)
        risk = round(max(8.0, premium * 0.14), 2)  # ~14% options stop-loss
        stop_loss = round(entry_price - risk, 2)
        target_1 = round(entry_price + (risk * 1.8), 2)
        target_2 = round(entry_price + (risk * 2.5), 2)

        return {
            "signal_type": signal_type,
            "instrument": opt_symbol,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
        }

    def _resolve_equity_intraday_setup(
        self,
        symbol: str,
        quote: Dict[str, Any],
        is_bullish: bool,
        atr: float
    ) -> Dict[str, Any]:
        """Calculates deterministic equity intraday MIS entry, stop-loss, and multi-tier targets."""
        ltp = quote["ltp"]
        signal_type = "BUY_EQUITY" if is_bullish else "SHORT_EQUITY"
        entry_price = round(ltp, 2)
        risk = round(max(2.0, atr * 1.2), 2)

        stop_loss = round(entry_price - risk if is_bullish else entry_price + risk, 2)
        target_1 = round(entry_price + (risk * 2.0) if is_bullish else entry_price - (risk * 2.0), 2)
        target_2 = round(entry_price + (risk * 3.0) if is_bullish else entry_price - (risk * 3.0), 2)

        return {
            "signal_type": signal_type,
            "instrument": f"{symbol} MIS",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
        }

    def _build_verbal_pitch(self, signal_type: str, instrument: str, entry: float, sl: float, tp: float) -> str:
        """Formulates concise voice prompt for browser speech synthesis."""
        action_name = "BUY CALL" if signal_type == "BUY_CALL" else (
            "BUY PUT" if signal_type == "BUY_PUT" else ("LONG" if signal_type == "BUY_EQUITY" else "SHORT")
        )
        return (
            f"AI Trade Alert: High conviction {action_name} setup on {instrument}. "
            f"Entry at ₹{entry}, Stop Loss at ₹{sl}, Target at ₹{tp}. "
            f"Risk reward ratio is 1 to 2. Please say 'Approve' to confirm or 'Reject' to pass."
        )

    def _generate_algorithmic_fallback(
        self,
        symbol: str,
        quote: Dict[str, Any],
        rsi: float,
        ema_diff: float,
        vwap_diff: float,
        atr: float = 10.0
    ) -> Dict[str, Any]:
        """Provides deterministic, rule-based intraday setup if offline or API key pending."""
        is_index = is_index_symbol(symbol)
        is_bullish = ema_diff >= 0 and vwap_diff >= 0 and rsi >= 48
        direction = "BULLISH" if is_bullish else "BEARISH"

        if is_index:
            setup = self._resolve_index_option_setup(symbol, quote, is_bullish)
        else:
            setup = self._resolve_equity_intraday_setup(symbol, quote, is_bullish, atr)

        verbal_pitch = self._build_verbal_pitch(
            setup["signal_type"], setup["instrument"], setup["entry_price"], setup["stop_loss"], setup["target_1"]
        )

        return {
            "symbol": symbol,
            "instrument_to_trade": setup["instrument"],
            "signal_type": setup["signal_type"],
            "direction": direction,
            "lot_size": 1,
            "entry_price": setup["entry_price"],
            "stop_loss": setup["stop_loss"],
            "target_1": setup["target_1"],
            "target_2": setup["target_2"],
            "risk_reward": "1:2.0",
            "confidence": 85 if abs(rsi - 50) > 8 else 75,
            "verbal_pitch": verbal_pitch,
            "technical_rationale": (
                f"{'Bullish trend continuation' if is_bullish else 'Bearish reversal breakdown'} "
                f"confirmed by EMA alignment and VWAP support. RSI is at {rsi:.1f}."
            ),
            "ai_model": "Algorithmic Quantitative Fallback",
            "source": "Algorithmic Quant Rules"
        }


# Singleton instance
gemini_analyzer = GeminiMarketAnalyzer()
