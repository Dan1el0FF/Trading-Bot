import yfinance as yf
import pandas as pd


class FundamentalFilter:

    def __init__(self,mode = 'swing'):
        self.tickers = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                                    storage_options={"User-Agent": "Mozilla/5.0"})[0]["Symbol"].tolist()
        self.tickers.insert(0,'SPY')
        self.mode = mode
        self.watchlist = []

    def start_filtering(self):
        for company in self.tickers:
            try:
                ticker = yf.Ticker(company)
                info = ticker.info
                hist = ticker.history(period="20d")

                ok = self._passorfail(company, info, hist)
                if ok:
                    self.watchlist.append(company)
                    print(f"✅ {company} pasó")
            except Exception as e:
                print(f"⚠️ {company} error: {e}")

        print(f'Watchlist final para modo {self.mode}, {len(self.watchlist)}: {self.watchlist}')

    def _passorfail(self, company: str, info: dict, hist: pd.DataFrame) -> bool:

        peg    = info.get('trailingPegRatio')
        volume = info.get('averageVolume')
        cap    = info.get('marketCap')

        if self.mode == 'swing':
            min_volume = 2_000_000
            min_cap    = 5_000_000_000
            max_var    = 3.0
            min_atr    = 1.0
            max_atr    = 3.0
        elif self.mode == 'daytrade':
            min_volume = 10_000_000
            min_cap    = 2_000_000_000
            max_var    = 6.0
            min_atr    = 2.0
            max_atr    = 5.0
        else:
            raise ValueError(f"Modo no válido: {self.mode}. Usa 'swing' o 'daytrade'")

        if volume is None or volume < min_volume:
            print(f"❌ {company} no pasó por volumen: {volume}")
            return False

        if cap is None or cap < min_cap:
            print(f"❌ {company} no pasó por market cap: {cap}")
            return False

        # PEG solo aplica en swing
        if self.mode == "swing":
            if peg is None or peg < 0.6 or peg > 1.7:
                print(f"❌ {company} no pasó por PEG: {peg}")
                return False

        if len(hist) < 2:
            print(f"❌ {company} no pasó por historial insuficiente")
            return False

        variacion = hist["Close"].pct_change().abs().mean() * 100
        if self.mode == "swing" and variacion > max_var:
            print(f"❌ {company} no pasó por variación: {variacion:.2f}%")
            return False
        elif self.mode == "daytrade" and (variacion < 2.0 or variacion > max_var):
            print(f"❌ {company} no pasó por variación: {variacion:.2f}%")
            return False

        atr     = (hist["High"] - hist["Low"]).tail(14).mean()
        precio  = hist["Close"].iloc[-1]
        atr_pct = (atr / precio) * 100

        if atr_pct < min_atr or atr_pct > max_atr:
            print(f"❌ {company} no pasó por ATR%: {atr_pct:.2f}%")
            return False

        return True
