"""
Generador de datos OHLCV sintéticos para demo/testing.
Simula movimiento de precios tipo forex con tendencias y ruido realista.
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


SEED_PRICES = {
    "EURUSD=X": 1.0850,
    "USDJPY=X": 149.50,
    "EURGBP=X": 0.8560,
    "USDCHF=X": 0.8980,
    "EURJPY=X": 162.20,
}

VOLATILITY = {
    "EURUSD=X": 0.0006,
    "USDJPY=X": 0.060,
    "EURGBP=X": 0.0004,
    "USDCHF=X": 0.0005,
    "EURJPY=X": 0.075,
}


def generate_ohlcv(pair: str, bars: int = 1000, timeframe_hours: int = 1) -> pd.DataFrame:
    np.random.seed(42 + abs(hash(pair)) % 100)

    price = SEED_PRICES.get(pair, 1.0)
    vol = VOLATILITY.get(pair, 0.0005)

    closes = [price]
    # Simula drift + tendencias con cambios de régimen
    regime = 1
    for i in range(1, bars):
        if i % 80 == 0:
            regime = np.random.choice([-1, 1])
        drift = regime * vol * 0.15
        shock = np.random.normal(0, vol)
        closes.append(max(closes[-1] + drift + shock, price * 0.7))

    closes = np.array(closes)

    # Construir OHLC desde closes con ruido intra-barra
    highs = closes + np.abs(np.random.normal(0, vol * 0.6, bars))
    lows = closes - np.abs(np.random.normal(0, vol * 0.6, bars))
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    volumes = np.random.randint(1000, 5000, bars)

    end = datetime.now().replace(minute=0, second=0, microsecond=0)
    index = [end - timedelta(hours=timeframe_hours * (bars - i)) for i in range(bars)]

    return pd.DataFrame({
        "Open": np.round(opens, 5),
        "High": np.round(highs, 5),
        "Low": np.round(lows, 5),
        "Close": np.round(closes, 5),
        "Volume": volumes,
    }, index=index)
