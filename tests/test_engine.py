import time

from copytrader.api.clob import DryRunExecutor
from copytrader.config import Settings
from copytrader.engine import CopyEngine
from copytrader.journal import TradeJournal
from copytrader.models import CopyStatus

TARGET = "0x" + "1" * 40


class FakeDataApi:
    def __init__(self):
        self.activity = []

    def get_activity(self, user, limit=100, offset=0, activity_type=None):
        return list(self.activity)


class FailingExecutor:
    dry_run = False

    def place(self, order):
        raise RuntimeError("not enough balance")


def make_engine(tmp_path, executor=None):
    settings = Settings(target_wallet=TARGET, copy_ratio_percent=10, journal_path=tmp_path / "journal.csv")
    api = FakeDataApi()
    engine = CopyEngine(settings, api, executor or DryRunExecutor(), TradeJournal(settings.journal_path))
    return engine, api


def test_existing_trades_are_not_copied_on_start(tmp_path, trade_factory):
    engine, api = make_engine(tmp_path)
    api.activity = [trade_factory(tx="0xold")]
    assert engine.poll() == []
    assert engine.poll() == []


def test_new_trades_are_copied_once_in_chronological_order(tmp_path, trade_factory):
    engine, api = make_engine(tmp_path)
    api.activity = [trade_factory(tx="0xold")]
    engine.poll()

    now = time.time()
    api.activity = [trade_factory(tx="0xnew2", ts=now), trade_factory(tx="0xnew1", ts=now - 1)] + api.activity
    results = engine.poll()
    assert [r.source.transaction_hash for r in results] == ["0xnew1", "0xnew2"]
    assert all(r.status is CopyStatus.SIMULATED for r in results)
    assert engine.poll() == []
    assert len(TradeJournal(tmp_path / "journal.csv").read_rows()) == 2


def test_non_trade_activity_is_ignored(tmp_path, trade_factory):
    engine, api = make_engine(tmp_path)
    engine.poll()
    api.activity = [trade_factory(tx="0xredeem", type_="REDEEM")]
    assert engine.poll() == []


def test_stale_trades_are_ignored(tmp_path, trade_factory):
    engine, api = make_engine(tmp_path)
    engine.poll()
    api.activity = [trade_factory(tx="0xlate", ts=time.time() - 3600)]
    assert engine.poll() == []


def test_execution_errors_are_reported_not_raised(tmp_path, trade_factory):
    engine, api = make_engine(tmp_path, FailingExecutor())
    engine.poll()
    api.activity = [trade_factory(tx="0xnew")]
    [result] = engine.poll()
    assert result.status is CopyStatus.FAILED
    assert "not enough balance" in result.message
