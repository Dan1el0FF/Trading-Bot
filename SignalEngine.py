from ib_insync import IB, Stock, util
import pandas as pd
import numpy as np
import talib


class SignalEngine:

    def __init__(self, ib: IB, mode: str = 'swing'):
        self.ib   = ib
        self.mode = mode

    def evaluate_watchlist(self, watchlist: list) -> list:
        signals = []

        for company in watchlist:
            try:
                signal = self._evaluate(company)
                if signal['action'] != 'HOLD':
                    signals.append(signal)
                    print(f"{company} → {signal['action']} | precio: {signal['price']:.2f} | RSI: {signal['rsi']:.1f} | ATR%: {signal['atr_pct']:.2f}%")
                else:
                    print(f"⏸ {company} HOLD — {signal.get('reason', '')}")
            except Exception as e:
                print(f"{company} error: {e}")

        print(f"\nSeñales encontradas: {len(signals)}")
        return signals

    def _evaluate(self, company: str) -> dict:

        if self.mode == 'swing':
            duracion          = '30 D'
            ema_rapida        = 20
            ema_lenta         = 50
            ema_macro         = 200
            rsi_long_min      = 35
            rsi_long_max      = 50
            rsi_short_min     = 50
            rsi_short_max     = 65
        elif self.mode == 'daytrade':
            duracion          = '5 D'
            ema_rapida        = 9
            ema_lenta         = 21
            ema_macro         = 50
            rsi_long_min      = 30
            rsi_long_max      = 45
            rsi_short_min     = 55
            rsi_short_max     = 70
        else:
            raise ValueError(f"Modo no válido: {self.mode}. Usa 'swing' o 'daytrade'")

        # ── Datos históricos vía IBKR ─────────────────────────
        contract = Stock(company, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)

        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=duracion,
            barSizeSetting='30 mins',
            whatToShow='TRADES',
            useRTH=True
        )

        if not bars or len(bars) < ema_macro:
            return self._no_signal(company, f"Datos insuficientes ({len(bars) if bars else 0} velas, necesita {ema_macro})")

        hist   = util.df(bars)
        close  = hist["close"].values.astype(float)
        high   = hist["high"].values.astype(float)
        low    = hist["low"].values.astype(float)
        volume = hist["volume"].values.astype(float)

        # ── Indicadores con TA-Lib ────────────────────────────
        ema_r  = talib.EMA(close, timeperiod=ema_rapida)
        ema_l  = talib.EMA(close, timeperiod=ema_lenta)
        ema_m  = talib.EMA(close, timeperiod=ema_macro)
        rsi    = talib.RSI(close, timeperiod=14)
        atr    = talib.ATR(high, low, close, timeperiod=14)
        vol_ma = talib.SMA(volume, timeperiod=20)

        price   = close[-1]
        rsi_now = rsi[-1]
        atr_pct = (atr[-1] / price) * 100

        # ── Condiciones LONG ──────────────────────────────────
        long = (
            price      > ema_m[-1]  and
            ema_r[-1]  > ema_l[-1]  and
            rsi_long_min <= rsi_now <= rsi_long_max and
            volume[-1] > vol_ma[-1]
        )

        # ── Condiciones SHORT ─────────────────────────────────
        short = (
            price      < ema_m[-1]  and
            ema_r[-1]  < ema_l[-1]  and
            rsi_short_min <= rsi_now <= rsi_short_max and
            volume[-1] > vol_ma[-1]
        )

        if long:
            return {
                'company': company,
                'action' : 'BUY',
                'price'  : price,
                'rsi'    : rsi_now,
                'atr_pct': atr_pct,
                'atr'    : atr[-1],
            }

        #if short:
        #    return {
        #        'company': company,
        #       'action' : 'SELL',
        #        'price'  : price,
        #        'rsi'    : rsi_now,
        #        'atr_pct': atr_pct,
        #        'atr'    : atr[-1],
        #    }

        return self._no_signal(company, f"RSI: {rsi_now:.1f}")

    def _no_signal(self, company: str, reason: str) -> dict:
        return {
            'company': company,
            'action' : 'HOLD',
            'reason' : reason,
            'price'  : 0,
            'rsi'    : 0,
            'atr_pct': 0,
            'atr'    : 0,
        }