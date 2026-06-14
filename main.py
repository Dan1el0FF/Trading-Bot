from ib_insync import IB
from FundamentalFilter import FundamentalFilter
from SignalEngine import SignalEngine
from RiskManager import RiskManager
from IBKRBroker import IBKRBroker

from datetime import datetime, timedelta
import pytz
import time


def es_horario_mercado() -> bool:
    ET = pytz.timezone('America/New_York')
    ahora = datetime.now(ET)

    # Fin de semana
    if ahora.weekday() >= 5:
        return False

    apertura = ahora.replace(hour=9, minute=30, second=0, microsecond=0)
    cierre   = ahora.replace(hour=16, minute=0, second=0, microsecond=0)

    return apertura <= ahora <= cierre


def tiempo_para_apertura():
    ET = pytz.timezone('America/New_York')
    ahora = datetime.now(ET)

    apertura = ahora.replace(hour=9, minute=30, second=0, microsecond=0)

    # Sábado o domingo
    if ahora.weekday() >= 5:
        dias_faltantes = 7 - ahora.weekday()
        proxima_apertura = apertura + timedelta(days=dias_faltantes)

    # Después del cierre
    elif ahora.hour >= 16:
        proxima_apertura = apertura + timedelta(days=1)

    # Antes de abrir
    else:
        proxima_apertura = apertura

    # Saltar fin de semana
    while proxima_apertura.weekday() >= 5:
        proxima_apertura += timedelta(days=1)

    diferencia = proxima_apertura - ahora

    horas, resto = divmod(int(diferencia.total_seconds()), 3600)
    minutos, _ = divmod(resto, 60)

    return horas, minutos


def main():

    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=1)

    MODE = 'swing'

    broker  = IBKRBroker(ib=ib)
    CAPITAL = broker.get_account_value()

    print(f"💰 Capital disponible: ${CAPITAL:,.2f}")
    print(f"📊 Modo: {MODE}")

    ff = FundamentalFilter(mode=MODE)
    se = SignalEngine(ib=ib, mode=MODE)
    rm = RiskManager(ib=ib, capital=CAPITAL, mode=MODE)

    # ── Filtro fundamental ─────────────────────────
    print("\n🔍 Ejecutando filtro fundamental...")
    ff.start_filtering()

    print(f"Watchlist lista: {len(ff.watchlist)} empresas")

    posiciones_abiertas = {}

    while True:

        ET = pytz.timezone('America/New_York')
        ahora = datetime.now(ET)

        # ── Mercado cerrado ─────────────────────────
        if not es_horario_mercado():

            horas, minutos = tiempo_para_apertura()

            print(
                f"\n⏰ Mercado cerrado — "
                f"{ahora.strftime('%A %d/%m %H:%M ET')}"
            )

            print(
                f"Faltan {horas}h {minutos}m para abrir"
            )

            print("💤 Esperando 15 minutos...\n")

            time.sleep(15 * 60)
            continue

        # ── Mercado abierto ─────────────────────────
        print(f"\n{'=' * 50}")
        print(
            f"Ciclo {ahora.strftime('%H:%M ET')} "
            f"— posiciones abiertas: {len(posiciones_abiertas)}"
        )

        # ── Revisar posiciones abiertas ─────────────
        for company, order in list(posiciones_abiertas.items()):

            salir, motivo = rm.should_exit(
                company,
                order['action'],
                order['price']
            )

            if salir:

                broker.close_position(
                    company,
                    order['quantity']
                )

                broker.cancel_all_orders(company)

                del posiciones_abiertas[company]

                print(f"🚪 {company} cerrado — {motivo}")

        # ── Buscar nuevas señales ───────────────────
        if len(posiciones_abiertas) < 3:

            signals = se.evaluate_watchlist(ff.watchlist)

            for signal in signals:

                company = signal['company']

                if company not in posiciones_abiertas:

                    order = rm.calculate_order(signal)

                    broker.open_position(order)

                    posiciones_abiertas[company] = order

        print("\n⏳ Esperando 15 minutos...")
        time.sleep(15 * 60)


if __name__ == '__main__':

    try:
        main()

    except KeyboardInterrupt:
        print("\nBot detenido manualmente")

    except Exception as e:
        print(f"\nError fatal: {e}")

    finally:
        print("Desconectando de IBKR...")