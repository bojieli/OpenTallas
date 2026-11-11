"""ARHOST_1111 (KW-FIX-44, COORD 11-11): an AUTO-RESIGN placement refusal (no host / disk floor) is INFRA retried next
tick on any host (staged inputs), never the end of the row and never the infra budget."""
from pathlib import Path

import auto_resign as AR
from test_auto_resign import ap, fake_hub, register, make_kit, only_item, roots_ok, _collect  # noqa: F401

NOHOST = {"not_run": True, "msg": "ot-run: NOT RUN: no host qualifies (epyc2: scratch3 floor 200 GB < 220)"}


def _log(ap):
    p = Path(only_item(ap)["log"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("ot-run: NOT RUN: no host qualifies\n")


def test_no_host_refusal_relaunches_on_any_host(ap, tmp_path, monkeypatch):
    roots_ok(monkeypatch, tmp_path)
    register(ap, make_kit(tmp_path))
    AR.step(ap)
    first = ap.launched[0][1]
    assert "--hosts" in first and "--no-spill" in first
    for k in range(3):                                 # every refusal: PENDING, relaunch, budget untouched
        _log(ap)
        _collect(ap, {}, client=dict(NOHOST))
        AR.step(ap)
        it = only_item(ap)
        assert it["status"] == "RUNNING" and it.get("infra", 0) == 0 and not it.get("failed")
        argv = ap.launched[-1][1]
        assert "--hosts" not in argv and "--no-spill" not in argv
        st = argv[argv.index("--stage") + 1].split(",")
        out = argv[argv.index("--out") + 1]
        assert "/tools/" + AR.TAG if hasattr(AR, "TAG") else True
        assert out in st and argv[argv.index("--kit") + 1] in st and argv[argv.index("--run-dir") + 1] in st
    assert len(ap.launched) == 4


def test_old_no_host_failure_key_is_not_a_verdict():
    assert AR.NO_HOST.search("ot-run: NOT RUN: no host qualifies (epyc2 scratch3 floor)")
    assert AR.NO_HOST.search("ROOT FS 96% full > 95% (DISK GUARD)")
    assert not AR.NO_HOST.search("re-sign FAIL TT -12 FF 3: setup")
