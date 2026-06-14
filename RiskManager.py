from ib_insync import IB, Stock, util
import talib


class RiskManager:

    def __init__(self, ib: IB, capital: float, mode: str = 'swing'):
        self.ib      = ib
        self.capital = capital  # capital total de la cuenta en USD
        self.mode    = mode

    # ──────────────────────────────────────────────────────────────────────────
    # PÚBLICO
    # ──────────────────────────────────────────────────────────────────────────

    def calculate_order(self, signal: dict) -> dict:
        """
        Recibe una señal del SignalEngine y calcula:
          - Tamaño de posición (cantidad de acciones)
          - Stop Loss
          - Take Profit
        """
        price  = signal['price']
        atr    = signal['atr']
        action = signal['action']

        sl_distance = atr * 1.0   # 1× ATR
        tp_distance = atr * 2.0   # 2× ATR  → ratio 1:2

        if action == 'BUY':
            stop_loss   = price - sl_distance
            take_profit = price + tp_distance
        else:  # SELL
            stop_loss   = price + sl_distance
            take_profit = price - tp_distance

        quantity = self._calculate_quantity(price, sl_distance)

        order = {
            'company'    : signal['company'],
            'action'     : action,
            'quantity'   : quantity,
            'price'      : price,
            'stop_loss'  : round(stop_loss,   2),
            'take_profit': round(take_profit, 2),
            'atr'        : atr,
        }

        print(f"📋 {signal['company']} | {action} {quantity} acciones @ ${price:.2f} | SL: ${order['stop_loss']} | TP: ${order['take_profit']}")
        return order

    def should_exit(self, company: str, action: str, entry_price: float) -> tuple[bool, str]:
        """
        Evalúa si hay que cerrar una posición abierta por señal técnica.
        Retorna (True, motivo) si hay que salir, (False, '') si no.

        Se llama en cada ciclo del bot para monitorear posiciones abiertas.
        """
        bars = self._get_bars(company)
        if bars is None:
            return False, ''

        hist   = util.df(bars)
        close  = hist["close"].values.astype(float)
        high   = hist["high"].values.astype(float)
        low    = hist["low"].values.astype(float)

        ema20 = talib.EMA(close, timeperiod=20)
        ema50 = talib.EMA(close, timeperiod=50)
        rsi   = talib.RSI(close, timeperiod=14)

        price   = close[-1]
        rsi_now = rsi[-1]

        if action == 'BUY':
            # Salida técnica para un LONG
            if rsi_now > 70:
                return True, f"RSI sobrecomprado: {rsi_now:.1f}"
            if ema20[-1] < ema50[-1] and ema20[-2] >= ema50[-2]:
                return True, "EMA20 cruzó EMA50 a la baja"
            if price < ema50[-1]:
                return True, f"Precio cayó bajo EMA50: ${price:.2f}"

        #elif action == 'SELL':
        #    # Salida técnica para un SHORT
        #    if rsi_now < 30:
        #        return True, f"RSI sobrevendido: {rsi_now:.1f}"
        #    if ema20[-1] > ema50[-1] and ema20[-2] <= ema50[-2]:
        #        return True, "EMA20 cruzó EMA50 al alza"
        #    if price > ema50[-1]:
        #        return True, f"Precio subió sobre EMA50: ${price:.2f}"

        return False, ''

    # ──────────────────────────────────────────────────────────────────────────
    # PRIVADO
    # ──────────────────────────────────────────────────────────────────────────

    def _calculate_quantity(self, price: float, sl_distance: float) -> int:
        """
        Fórmula:
          riesgo_usd = capital × 1%
          cantidad   = riesgo_usd / sl_distance

        Ejemplo:
          capital = $10,000 → riesgo = $100
          sl_distance = $1.50
          cantidad = 100 / 1.50 = 66 acciones
        """
        if self.mode == 'swing':
            riesgo_pct = 0.01   # 1% del capital por trade
        elif self.mode == 'daytrade':
            riesgo_pct = 0.005  # 0.5% del capital por trade (más operaciones al día)
        else:
            raise ValueError(f"Modo no válido: {self.mode}")

        riesgo_usd = self.capital * riesgo_pct
        cantidad   = int(riesgo_usd / sl_distance)

        # Nunca invertir más del 20% del capital en una sola posición
        max_cantidad = int((self.capital * 0.20) / price)
        cantidad     = min(cantidad, max_cantidad)

        return max(cantidad, 1)  # mínimo 1 acción

    def _get_bars(self, company: str):
        try:
            contract = Stock(company, 'SMART', 'USD')
            self.ib.qualifyContracts(contract)

            duracion = '30 D' if self.mode == 'swing' else '5 D'

            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr=duracion,
                barSizeSetting='30 mins',
                whatToShow='TRADES',
                useRTH=True
            )
            return bars if bars else None
        except Exception as e:
            print(f"Error obteniendo barras de {company}: {e}")
            return None
