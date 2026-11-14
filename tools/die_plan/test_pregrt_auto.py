"""FIX-HOLDSTALL 11-14: die_gen_env OT_PREGRT_FF_HOLD_AUTO turns the pre-GRT hold build on for plan-silent types; the kit tcl
runs it only with >= N register-to-register hold violators (internal debt), else exits 0 without touching 4_cts.odb."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pregrt_ff_hold as P


def _env(v):
    if v is None:
        os.environ.pop("OT_PREGRT_FF_HOLD_AUTO", None)
    else:
        os.environ["OT_PREGRT_FF_HOLD_AUTO"] = v


def test_auto_default_off():
    _env(None)
    assert P.auto_min() is None and not P.enabled({}) and P.config_lines({}) == []


def test_auto_on_plan_silent_only():
    try:
        _env("1")
        assert P.auto_min() == 100 and P.enabled({})
        assert not P.enabled({"clock": {"pregrt_ff_hold": False}})
        assert P.enabled({"clock": {"pregrt_ff_hold": True}})
        _env("250")
        assert P.auto_min() == 250
        _env("0")
        assert P.auto_min() is None
    finally:
        _env(None)


def test_tcl_bakes_threshold(tmp_path):
    try:
        _env("40")
        kd = tmp_path
        hg = P.MARK.join(["# head\n" + P.READ, "tail\n"])
        (kd / "hold_gate.tcl").write_text(hg)
        assert P.install({}, kd)
        txt = (kd / "pregrt_ff_hold.tcl").read_text()
        assert "set pg_auto 40\n" in txt and "@PG_AUTO_MIN@" not in txt and "AUTO skip" in txt
        _env(None)
        assert "set pg_auto -1\n" in P.tcl_text(hg)
    finally:
        _env(None)
