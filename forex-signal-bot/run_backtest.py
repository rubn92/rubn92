"""
Ejecuta backtesting sobre todos los pares y timeframes configurados.
Uso: python run_backtest.py
"""
from data.fetcher import fetch_ohlc
from backtest.engine import backtest, print_report
import config as cfg


def main():
    print("\n🔁  BACKTESTING — Forex Signal Bot")
    print(f"Estrategia: EMA{cfg.EMA_FAST}/EMA{cfg.EMA_SLOW} + RSI + Bollinger Bands")
    print(f"Riesgo por operación: {cfg.RISK_PERCENT}%  |  R/R mínimo: 1:{cfg.RR_RATIO}")

    for tf_label, tf_code in cfg.TIMEFRAMES.items():
        for pair in cfg.PAIRS:
            name = cfg.PAIR_NAMES.get(pair, pair)
            df = fetch_ohlc(pair, tf_code, bars=1000)
            if df is None or len(df) < cfg.EMA_SLOW + 50:
                print(f"\n  ⚠️  Datos insuficientes para {name} {tf_label}")
                continue
            results = backtest(df, pair=name)
            print_report(results, pair=name, timeframe=tf_label)


if __name__ == "__main__":
    main()
