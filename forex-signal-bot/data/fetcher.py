import pandas as pd
from typing import Optional
import config as cfg

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False


def fetch_ohlc(pair: str, timeframe: str, bars: int = 500) -> Optional[pd.DataFrame]:
    """
    Intenta descargar datos de Yahoo Finance.
    Si falla (sin red / fuera de allowlist), usa datos sintéticos.
    pair: símbolo yfinance (ej. EURUSD=X)
    timeframe: "1h" o "4h"
    """
    if _YF_AVAILABLE:
        period_map = {"1h": "60d", "4h": "180d"}
        period = period_map.get(timeframe, "60d")
        try:
            ticker = yf.Ticker(pair)
            df = ticker.history(period=period, interval=timeframe)
            if not df.empty:
                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                df.dropna(inplace=True)
                return df.tail(bars)
        except Exception:
            pass

    # Fallback a datos sintéticos (demo / sin red)
    from data.synthetic import generate_ohlcv
    tf_hours = 1 if timeframe == "1h" else 4
    print(f"[fetcher] Usando datos sintéticos para {pair} ({timeframe})")
    return generate_ohlcv(pair, bars=bars, timeframe_hours=tf_hours)


def fetch_all_pairs(timeframe: str) -> dict:
    result = {}
    for pair in cfg.PAIRS:
        df = fetch_ohlc(pair, timeframe)
        if df is not None and len(df) > 0:
            result[pair] = df
    return result
