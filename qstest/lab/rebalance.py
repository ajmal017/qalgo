import calendar
import datetime
import sys

##sys.path.insert(0, '/home/jun/proj/qalgo/qstest/qstrader/')
sys.path.insert(0, '/home/jun/proj/qalgo/qstest/')

#from qstrader import settings
from qstrader.config import Config
from qstrader.strategy.base import AbstractStrategy
from qstrader.position_sizer.rebalance import LiquidateRebalancePositionSizer
from qstrader.event import SignalEvent, EventType
#from qstrader.compat import queue
import queue
import pickle
from qstrader.trading_session import TradingSession


class MonthlyLiquidateRebalanceStrategy(AbstractStrategy):
    """
    A generic strategy that allows monthly rebalancing of a
    set of tickers, via full liquidation and dollar-weighting
    of new positions.

    Must be used in conjunction with the
    LiquidateRebalancePositionSizer object to work correctly.
    """
    def __init__(self, tickers, events_queue):
        self.tickers = tickers
        self.events_queue = events_queue
        self.tickers_invested = self._create_invested_list()

    def _end_of_month(self, cur_time):
        """
        Determine if the current day is at the end of the month.
        """
        cur_day = cur_time.day
        end_day = calendar.monthrange(cur_time.year, cur_time.month)[1]
        return cur_day == end_day

    def _create_invested_list(self):
        """
        Create a dictionary with each ticker as a key, with
        a boolean value depending upon whether the ticker has
        been "invested" yet. This is necessary to avoid sending
        a liquidation signal on the first allocation.
        """
        tickers_invested = {ticker: False for ticker in self.tickers}
        return tickers_invested

    def calculate_signals(self, event):
        """
        For a particular received BarEvent, determine whether
        it is the end of the month (for that bar) and generate
        a liquidation signal, as well as a purchase signal,
        for each ticker.
        """
        is_new = False
        if (event.type in [EventType.BAR, EventType.TICK] and
            self._end_of_month(event.time) ):
            ticker = event.ticker
            if self.tickers_invested[ticker]:
                liquidate_signal = SignalEvent(ticker, "EXIT")
                self.events_queue.put(liquidate_signal)
            long_signal = SignalEvent(ticker, "BOT")
            self.events_queue.put(long_signal)
            self.tickers_invested[ticker] = True
            newEvent = True
        return is_new


def run(config, testing, tickers, filename):
    # Backtest information
    title = ['Monthly Liquidate/Rebalance on Portfolio']
    initial_equity = 100000.0
    start_date = datetime.datetime(2015, 1, 1)
    end_date = datetime.datetime(2020, 1, 1)

    # Use the Monthly Liquidate And Rebalance strategy
    events_queue = queue.Queue()
    strategy = MonthlyLiquidateRebalanceStrategy(tickers, events_queue)

    # Use the liquidate and rebalance position sizer
    # with prespecified ticker weights
    ticker_weights = {"AAPL": 0.4, "ADI": 0.4 , "SPY": 0.2}
    position_sizer = LiquidateRebalancePositionSizer(ticker_weights)

    # Set up the backtest
    backtest = TradingSession(
        config, strategy, tickers,
        initial_equity, start_date, end_date,
        events_queue, position_sizer=position_sizer,
        name = "rebalance",
        title=title, benchmark=tickers[-1],)
    results = backtest.start_trading(testing=testing)
    return results


if __name__ == "__main__":
    # Configuration data
    testing = False
    #config = settings.from_file(settings.DEFAULT_CONFIG_FILENAME, testing)
    conf = Config()
    filename = None
    tickers = ["AAPL", "ADI", "SPY"]
    results = run(conf, testing, tickers, filename)
    #print(type(results))

