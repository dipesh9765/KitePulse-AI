"""
Technical Indicators & Quantitative Signal Metrics - KitePulse AI

This module implements institutional-grade intraday technical indicators used
for momentum, trend, volatility, and mean-reversion analysis on equity & derivative
time-series data.

Implemented Indicators:
1. Exponential Moving Average (EMA 9, 21, 50) - Trend tracking and dynamic support/resistance.
2. Relative Strength Index (RSI 14) - Oscillator for overbought (>70) and oversold (<30) momentum.
3. Volume Weighted Average Price (VWAP) - Benchmark for institutional intraday execution.
4. Average True Range (ATR 14) - Volatility measure for dynamic stop-loss and target placement.
5. Bollinger Bands (20, 2.0) - Volatility bands for mean-reversion breakouts.
6. Classic Floor Pivot Points - Intraday support (S1, S2) and resistance (R1, R2) levels.
"""

from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calculates the Exponential Moving Average (EMA) for a price series.

    Formula:
        EMA_t = (Price_t * alpha) + (EMA_{t-1} * (1 - alpha))
        where alpha = 2 / (period + 1)

    Args:
        series: Pandas Series of prices (typically close prices).
        period: Smoothing period window (e.g., 9, 21, 50).

    Returns:
        Pandas Series containing the computed EMA values.
    """
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculates the Relative Strength Index (RSI) momentum oscillator.

    Formula:
        RSI = 100 - [100 / (1 + RS)]
        where RS = Average Gain / Average Loss over the specified period.

    Args:
        series: Pandas Series of closing prices.
        period: Lookback window length (standard: 14 periods).

    Returns:
        Pandas Series containing RSI values bounded between 0 and 100.
        Missing initial values default to a neutral 50.0.
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()

    rs = gain / loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculates the Volume Weighted Average Price (VWAP) for intraday candle data.

    Formula:
        Typical Price (TP) = (High + Low + Close) / 3
        VWAP = Cumulative Sum(TP * Volume) / Cumulative Sum(Volume)

    Args:
        df: Pandas DataFrame containing 'high', 'low', 'close', and 'volume' columns.

    Returns:
        Pandas Series containing cumulative intraday VWAP values.
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3.0
    cum_vol = df["volume"].cumsum()
    cum_pv = (typical_price * df["volume"]).cumsum()
    vwap = cum_pv / cum_vol.replace(0, np.nan)
    return vwap.bfill().ffill()


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculates the Average True Range (ATR) volatility metric.

    Formula:
        True Range (TR) = max(
            High - Low,
            abs(High - Previous Close),
            abs(Low - Previous Close)
        )
        ATR = Simple/Exponential Moving Average of TR over period.

    Args:
        df: Pandas DataFrame containing 'high', 'low', and 'close' columns.
        period: Lookback window for smoothing (default: 14).

    Returns:
        Pandas Series containing ATR volatility values.
    """
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)

    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.bfill()


def calculate_bollinger_bands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculates Bollinger Bands (Upper Band, Middle Band / SMA, Lower Band).

    Formula:
        Middle Band = SMA(series, period)
        Upper Band = Middle Band + (num_std * Standard Deviation)
        Lower Band = Middle Band - (num_std * Standard Deviation)

    Args:
        series: Pandas Series of closing prices.
        period: Moving average lookback period (default: 20).
        num_std: Standard deviation multiplier (default: 2.0).

    Returns:
        Tuple of (upper_band, middle_band, lower_band).
    """
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower


def calculate_pivot_points(high: float, low: float, close: float) -> Dict[str, float]:
    """
    Calculates Classic Floor Pivot Points and support/resistance levels.

    Formulas:
        Pivot Point (PP) = (High + Low + Close) / 3
        Resistance 1 (R1) = (2 * PP) - Low
        Support 1 (S1) = (2 * PP) - High
        Resistance 2 (R2) = PP + (High - Low)
        Support 2 (S2) = PP - (High - Low)

    Args:
        high: Previous period high price.
        low: Previous period low price.
        close: Previous period close price.

    Returns:
        Dictionary mapping level names ('pivot', 'r1', 's1', 'r2', 's2') to prices.
    """
    pp = (high + low + close) / 3.0
    r1 = 2.0 * pp - low
    s1 = 2.0 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    return {
        "pivot": round(pp, 2),
        "r1": round(r1, 2),
        "s1": round(s1, 2),
        "r2": round(r2, 2),
        "s2": round(s2, 2)
    }


def enrich_candle_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriches raw OHLCV candle records with complete intraday quantitative indicators.

    Calculates EMA (9, 21, 50), RSI 14, cumulative VWAP, ATR 14, and Bollinger Bands.

    Args:
        df: Pandas DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].

    Returns:
        Enriched DataFrame with newly computed indicator feature columns.
    """
    df = df.copy()
    if len(df) == 0:
        return df

    df["ema_9"] = calculate_ema(df["close"], 9)
    df["ema_21"] = calculate_ema(df["close"], 21)
    df["ema_50"] = calculate_ema(df["close"], 50)
    df["rsi_14"] = calculate_rsi(df["close"], 14)
    df["vwap"] = calculate_vwap(df)
    df["atr_14"] = calculate_atr(df, 14)

    bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(df["close"])
    df["bb_upper"] = bb_upper
    df["bb_middle"] = bb_mid
    df["bb_lower"] = bb_lower

    return df
