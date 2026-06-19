import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# Pares a monitorizar
PAIRS = ["EURUSD=X", "USDJPY=X", "EURGBP=X", "USDCHF=X", "EURJPY=X"]

PAIR_NAMES = {
    "EURUSD=X": "EUR/USD",
    "USDJPY=X": "USD/JPY",
    "EURGBP=X": "EUR/GBP",
    "USDCHF=X": "USD/CHF",
    "EURJPY=X": "EUR/JPY",
}

# Timeframes a usar (yfinance format)
TIMEFRAMES = {
    "H1": "1h",
    "H4": "4h",
}

# Parámetros de estrategia
EMA_FAST = 50
EMA_SLOW = 200
RSI_PERIOD = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65
BB_PERIOD = 20
BB_STD = 2.0

# Gestión de riesgo
RISK_PERCENT = 1.0        # % cuenta por operación recomendado
RR_RATIO = 2.0            # ratio riesgo/beneficio mínimo
ATR_MULTIPLIER_SL = 1.5   # ATR x este valor = stop loss
ATR_MULTIPLIER_TP = 3.0   # ATR x este valor = take profit

# Intervalo de chequeo en segundos
CHECK_INTERVAL = 3600  # 1 hora
