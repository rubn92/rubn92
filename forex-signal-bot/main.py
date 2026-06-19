"""
Forex Signal Bot — bucle principal.
Escanea todos los pares cada hora, genera señales y las envía a Telegram.
"""
import time
import logging
import sys
from data.fetcher import fetch_all_pairs
from signals.strategy import generate_signal
from telegram.bot import send_signal, send_no_signals_update
import config as cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def scan_cycle():
    log.info("Iniciando escaneo de señales...")
    found = 0

    for tf_label, tf_code in cfg.TIMEFRAMES.items():
        log.info(f"Timeframe: {tf_label}")
        data = fetch_all_pairs(tf_code)

        for pair, df in data.items():
            name = cfg.PAIR_NAMES.get(pair, pair)
            signal = generate_signal(pair, df, tf_label)
            if signal:
                log.info(f"  ✅ Señal {signal.direction} en {name} ({tf_label})")
                send_signal(signal)
                found += 1
            else:
                log.info(f"  —  Sin señal en {name} ({tf_label})")

    if found == 0:
        log.info("Sin señales en este ciclo.")
    else:
        log.info(f"Ciclo completado. {found} señal(es) enviada(s).")

    return found


def run():
    log.info("Bot de señales Forex iniciado.")
    log.info(f"Pares: {', '.join(cfg.PAIR_NAMES.values())}")
    log.info(f"Intervalo: {cfg.CHECK_INTERVAL // 60} minutos")

    while True:
        try:
            scan_cycle()
        except KeyboardInterrupt:
            log.info("Bot detenido.")
            break
        except Exception as e:
            log.error(f"Error en ciclo: {e}")

        log.info(f"Próximo escaneo en {cfg.CHECK_INTERVAL // 60} minutos...")
        time.sleep(cfg.CHECK_INTERVAL)


if __name__ == "__main__":
    run()
