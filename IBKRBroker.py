from ib_insync import IB, Stock, MarketOrder, StopOrder, LimitOrder, BracketOrder, util


class IBKRBroker:

    def __init__(self, ib: IB):
        self.ib = ib

    # ──────────────────────────────────────────────────────────────────────────
    # PÚBLICO
    # ──────────────────────────────────────────────────────────────────────────

    def open_position(self, order: dict):
        """
        Abre una posición con bracket order:
          - Orden de compra al precio actual
          - Take Profit automático
          - Stop Loss automático

        IBKR maneja el TP y SL por ti — si uno se ejecuta, el otro se cancela.
        """
        company     = order['company']
        quantity    = order['quantity']
        take_profit = order['take_profit']
        stop_loss   = order['stop_loss']

        contract = Stock(company, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)

        # Bracket order = entrada + TP + SL en una sola instrucción
        bracket = self.ib.bracketOrder(
            action          = 'BUY',
            quantity        = quantity,
            limitPrice      = round(order['price'] * 1.001, 2),  # 0.1% de slippage
            takeProfitPrice = take_profit,
            stopLossPrice   = stop_loss,
        )

        trades = []
        for o in bracket:
            trade = self.ib.placeOrder(contract, o)
            trades.append(trade)
            print(f"Orden enviada: {company} | {o.action} | qty={quantity} | tipo={o.orderType}")

        return trades

    def close_position(self, company: str, quantity: int):
        """
        Cierra una posición abierta con una orden de venta a mercado.
        Se llama cuando should_exit() retorna True.
        """
        contract = Stock(company, 'SMART', 'USD')
        self.ib.qualifyContracts(contract)

        orden = MarketOrder('SELL', quantity)
        trade = self.ib.placeOrder(contract, orden)

        print(f"Posición cerrada: {company} | SELL {quantity} acciones a mercado")
        return trade

    def cancel_all_orders(self, company: str):
        """
        Cancela todas las órdenes pendientes de una empresa.
        Útil cuando cerramos la posición manualmente antes de que toque TP o SL.
        """
        open_orders = self.ib.openOrders()
        canceladas  = 0

        for order in open_orders:
            if hasattr(order, 'contract') and order.contract.symbol == company:
                self.ib.cancelOrder(order)
                canceladas += 1

        print(f"{canceladas} órdenes canceladas para {company}")

    def get_open_positions(self) -> dict:
        """
        Retorna las posiciones abiertas actualmente en la cuenta.
        Formato: {ticker: cantidad}
        """
        positions = {}
        for pos in self.ib.positions():
            if pos.position != 0:
                positions[pos.contract.symbol] = {
                    'quantity' : pos.position,
                    'avg_cost' : pos.avgCost,
                }
        return positions

    def get_account_value(self) -> float:
        """
        Retorna el valor neto de la cuenta en USD.
        Se usa para recalcular el tamaño de posición en cada ciclo.
        """
        for av in self.ib.accountValues():
            if av.tag == 'NetLiquidation' and av.currency == 'USD':
                return float(av.value)
        return 0.0