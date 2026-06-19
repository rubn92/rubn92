import asyncio
import requests
from signals.strategy import Signal
import config as cfg


EMOJI = {"BUY": "📈", "SELL": "📉"}
FLAG = {"BUY": "🟢", "SELL": "🔴"}


def format_signal(signal: Signal) -> str:
    e = EMOJI[signal.direction]
    f = FLAG[signal.direction]
    name = cfg.PAIR_NAMES.get(signal.pair, signal.pair)

    lines = [
        f"{'─' * 28}",
        f"{e}  *{name}*  —  {signal.timeframe}",
        f"{'─' * 28}",
        f"{f}  *{signal.direction}*",
        f"",
        f"📌  Entrada:     `{signal.entry}`",
        f"🛑  Stop Loss:   `{signal.stop_loss}`",
        f"🎯  TP1:         `{signal.tp1}`",
        f"✅  TP2:         `{signal.tp2}`",
        f"",
        f"📊  R/R:  `1:{signal.rr_ratio}`",
        f"⚠️  Riesgo recomendado: `{cfg.RISK_PERCENT}% de cuenta`",
        f"",
        f"🔍  *Análisis:* {signal.reason}",
        f"{'─' * 28}",
        f"_Resultados auditados en Myfxbook._",
        f"_Las señales no garantizan beneficios._",
    ]
    return "\n".join(lines)


def send_message(text: str) -> bool:
    if not cfg.TELEGRAM_TOKEN or not cfg.TELEGRAM_CHANNEL_ID:
        print("[telegram] Token o canal no configurado.")
        print("─" * 40)
        print(text)
        print("─" * 40)
        return False

    url = f"https://api.telegram.org/bot{cfg.TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": cfg.TELEGRAM_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[telegram] Error enviando mensaje: {e}")
        return False


def send_signal(signal: Signal) -> bool:
    text = format_signal(signal)
    return send_message(text)


def send_no_signals_update():
    send_message("🔍  Escaneo completado. Sin señales nuevas en este ciclo.")
