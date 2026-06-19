import pandas as pd
import numpy as np


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0):
    mid = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    return mid + std * sigma, mid, mid - std * sigma


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def add_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    df = df.copy()
    close = df["Close"]
    df["ema_fast"] = ema(close, cfg.EMA_FAST)
    df["ema_slow"] = ema(close, cfg.EMA_SLOW)
    df["rsi"] = rsi(close, cfg.RSI_PERIOD)
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = bollinger_bands(close, cfg.BB_PERIOD, cfg.BB_STD)
    df["atr"] = atr(df["High"], df["Low"], df["Close"])
    return df
