import pytest

from app.data_providers.base import Bar, MarketDataProvider, ProviderError, Quote
from app.data_providers.demo_provider import DemoProvider
from app.data_providers.symbols import is_valid_symbol, normalize_symbol
from app.data_providers.yfinance_provider import YFinanceProvider


def test_both_providers_satisfy_interface():
    assert isinstance(DemoProvider(), MarketDataProvider)
    assert isinstance(YFinanceProvider(), MarketDataProvider)


def test_symbol_validation():
    assert is_valid_symbol("reliance")            # case-insensitive
    assert is_valid_symbol("RELIANCE")
    assert not is_valid_symbol("NOTAREALSYMBOL")
    assert normalize_symbol("  infy ") == "INFY"


def test_yfinance_ticker_suffix_mapping():
    p = YFinanceProvider()
    assert p._ticker("RELIANCE", "NSE") == "RELIANCE.NS"
    assert p._ticker("reliance", "bse") == "RELIANCE.BO"


def test_yfinance_unknown_exchange_raises():
    p = YFinanceProvider()
    with pytest.raises(ProviderError):
        p._ticker("RELIANCE", "LSE")


@pytest.mark.asyncio
async def test_demo_is_deterministic_across_instances():
    a = await DemoProvider().get_daily_bars("TCS", "NSE", 30)
    b = await DemoProvider().get_daily_bars("TCS", "NSE", 30)
    assert [bar.close for bar in a] == [bar.close for bar in b]
    assert len(a) == 30


@pytest.mark.asyncio
async def test_demo_quote_and_benchmark_shapes():
    q = await DemoProvider().get_quote("INFY", "NSE")
    assert isinstance(q, Quote)
    assert q.symbol == "INFY" and q.price > 0 and q.previous_close > 0

    bench = await DemoProvider().get_benchmark(20)
    assert len(bench) == 20 and all(isinstance(x, Bar) for x in bench)


@pytest.mark.asyncio
async def test_swap_is_a_no_touch_change():
    """The same exercise code runs against either provider unchanged —
    this is the whole point of the boundary."""

    async def exercise(provider: MarketDataProvider) -> Quote:
        return await provider.get_quote("HDFCBANK", "NSE")

    q_demo = await exercise(DemoProvider())
    assert q_demo.symbol == "HDFCBANK"
    # (YFinanceProvider would run through the identical `exercise` — proven by the
    # shared type, exercised for real in scripts/check_providers.py.)