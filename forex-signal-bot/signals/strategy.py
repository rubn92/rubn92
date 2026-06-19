from dataclasses import dataclass
from typing import Optional
import pandas as pd
from .indicators import add_indicators
import config as cfg


@dataclass
class Signal:
    pair: str
    direction: str        # BUY / SELL
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    rr_ratio: float
    timeframe: str
    reason: str


def _check_ema_crossover(df: pd.DataFrame) -> Optional[str]:
    """Detecta cruce de EMA50 sobre EMA200."""
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    if prev["ema_fast"] <= prev["ema_slow"] and curr["ema_fast"] > curr["ema_slow"]:
        return "BUY"
    if prev["ema_fast"] >= prev["ema_slow"] and curr["ema_fast"] < curr["ema_slow"]:
        return "SELL"
    return None


def _check_rsi_trend(df: pd.DataFrame, direction: str) -> bool:
    """Confirma RSI en zona favorable para la dirección."""
    rsi_val = df.iloc[-1]["rsi"]
    if direction == "BUY" and rsi_val < cfg.RSI_OVERBOUGHT:
        return True
    if direction == "SELL" and rsi_val > cfg.RSI_OVERSOLD:
        return True
    return False


def _check_bb_entry(df: pd.DataFrame, direction: str) -> bool:
    """Precio cerca de banda de Bollinger en dirección correcta."""
    row = df.iloc[-1]
    close = row["Close"]
    band_range = row["bb_upper"] - row["bb_lower"]
    if band_range == 0:
        return False
    position = (close - row["bb_lower"]) / band_range  # 0=lower, 1=upper
    if direction == "BUY" and position < 0.35:
        return True
    if direction == "SELL" and position > 0.65:
        return True
    return False


def generate_signal(pair: str, df: pd.DataFrame, timeframe: str) -> Optional[Signal]:
    if len(df) < cfg.EMA_SLOW + 10:
        return None

    df = add_indicators(df, cfg)
    last = df.iloc[-1]

    # Señal primaria: cruce de EMAs
    direction = _check_ema_crossover(df)
    if direction is None:
        return None

    # Confirmación 1: RSI no en zona extrema contraria
    if not _check_rsi_trend(df, direction):
        return None

    # Confirmación 2: posición en Bollinger Bands
    reason_parts = [f"Cruce EMA{cfg.EMA_FAST}/EMA{cfg.EMA_SLOW}"]
    if _check_bb_entry(df, direction):
        reason_parts.append("precio en banda Bollinger favorable")

    entry = round(last["Close"], 5)
    atr_val = last["atr"]

    if direction == "BUY":
        stop_loss = round(entry - cfg.ATR_MULTIPLIER_SL * atr_val, 5)
        tp1 = round(entry + cfg.ATR_MULTIPLIER_TP * atr_val * 0.6, 5)
        tp2 = round(entry + cfg.ATR_MULTIPLIER_TP * atr_val, 5)
    else:
        stop_loss = round(entry + cfg.ATR_MULTIPLIER_SL * atr_val, 5)
        tp1 = round(entry - cfg.ATR_MULTIPLIER_TP * atr_val * 0.6, 5)
        tp2 = round(entry - cfg.ATR_MULTIPLIER_TP * atr_val, 5)

    sl_distance = abs(entry - stop_loss)
    tp_distance = abs(tp2 - entry)
    rr = round(tp_distance / sl_distance, 2) if sl_distance > 0 else 0

    if rr < cfg.RR_RATIO:
        return None

    return Signal(
        pair=pair,
        direction=direction,
        entry=entry,
        stop_loss=stop_loss,
        tp1=tp1,
        tp2=tp2,
        rr_ratio=rr,
        timeframe=timeframe,
        reason=" + ".join(reason_parts),
    )
