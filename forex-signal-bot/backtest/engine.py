import pandas as pd
import numpy as np
from signals.indicators import add_indicators
import config as cfg


def backtest(df: pd.DataFrame, pair: str = "") -> dict:
    """
    Simula la estrategia sobre datos históricos.
    Devuelve métricas de rendimiento.
    """
    df = add_indicators(df.copy(), cfg)
    df.dropna(inplace=True)

    trades = []

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]

        # Detectar cruce EMA
        bull_cross = prev["ema_fast"] <= prev["ema_slow"] and curr["ema_fast"] > curr["ema_slow"]
        bear_cross = prev["ema_fast"] >= prev["ema_slow"] and curr["ema_fast"] < curr["ema_slow"]

        if not bull_cross and not bear_cross:
            continue

        direction = "BUY" if bull_cross else "SELL"
        rsi_val = curr["rsi"]

        # Filtro RSI
        if direction == "BUY" and rsi_val >= cfg.RSI_OVERBOUGHT:
            continue
        if direction == "SELL" and rsi_val <= cfg.RSI_OVERSOLD:
            continue

        entry = curr["Close"]
        atr_val = curr["atr"]
        if pd.isna(atr_val) or atr_val == 0:
            continue

        if direction == "BUY":
            sl = entry - cfg.ATR_MULTIPLIER_SL * atr_val
            tp = entry + cfg.ATR_MULTIPLIER_TP * atr_val
        else:
            sl = entry + cfg.ATR_MULTIPLIER_SL * atr_val
            tp = entry - cfg.ATR_MULTIPLIER_TP * atr_val

        sl_dist = abs(entry - sl)
        tp_dist = abs(tp - entry)
        rr = tp_dist / sl_dist if sl_dist > 0 else 0
        if rr < cfg.RR_RATIO:
            continue

        # Simular resultado mirando velas siguientes (máx 50)
        outcome = None
        future = df.iloc[i + 1: i + 51]
        for _, bar in future.iterrows():
            if direction == "BUY":
                if bar["Low"] <= sl:
                    outcome = "LOSS"
                    break
                if bar["High"] >= tp:
                    outcome = "WIN"
                    break
            else:
                if bar["High"] >= sl:
                    outcome = "LOSS"
                    break
                if bar["Low"] <= tp:
                    outcome = "WIN"
                    break

        if outcome is None:
            outcome = "OPEN"

        trades.append({
            "date": curr.name,
            "pair": pair,
            "direction": direction,
            "entry": round(entry, 5),
            "sl": round(sl, 5),
            "tp": round(tp, 5),
            "rr": round(rr, 2),
            "outcome": outcome,
        })

    return _summarize(trades)


def _summarize(trades: list) -> dict:
    if not trades:
        return {"total": 0, "message": "Sin operaciones suficientes"}

    df = pd.DataFrame(trades)
    closed = df[df["outcome"] != "OPEN"]
    wins = (closed["outcome"] == "WIN").sum()
    losses = (closed["outcome"] == "LOSS").sum()
    total_closed = len(closed)
    win_rate = round(wins / total_closed * 100, 1) if total_closed > 0 else 0

    # PnL simulado con riesgo fijo 1% por operación
    pnl = []
    for _, row in closed.iterrows():
        if row["outcome"] == "WIN":
            pnl.append(cfg.RISK_PERCENT * row["rr"])
        else:
            pnl.append(-cfg.RISK_PERCENT)

    total_pnl = round(sum(pnl), 2)
    avg_win = round(np.mean([p for p in pnl if p > 0]), 2) if any(p > 0 for p in pnl) else 0
    avg_loss = round(np.mean([p for p in pnl if p < 0]), 2) if any(p < 0 for p in pnl) else 0

    return {
        "total_signals": len(trades),
        "closed": total_closed,
        "wins": int(wins),
        "losses": int(losses),
        "win_rate": win_rate,
        "total_pnl_pct": total_pnl,
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "trades": trades,
    }


def print_report(results: dict, pair: str = "", timeframe: str = ""):
    print(f"\n{'═' * 45}")
    print(f"  BACKTEST: {pair}  {timeframe}")
    print(f"{'═' * 45}")
    if "message" in results:
        print(f"  {results['message']}")
        return
    print(f"  Señales generadas:  {results['total_signals']}")
    print(f"  Operaciones cerradas: {results['closed']}")
    print(f"  Ganadoras:          {results['wins']}")
    print(f"  Perdedoras:         {results['losses']}")
    print(f"  Win rate:           {results['win_rate']}%")
    print(f"  PnL total (1% riesgo): {results['total_pnl_pct']}%")
    print(f"  Ganancia media:     {results['avg_win_pct']}%")
    print(f"  Pérdida media:      {results['avg_loss_pct']}%")
    print(f"{'═' * 45}")
