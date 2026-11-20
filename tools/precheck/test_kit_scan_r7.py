"""CBC rule 7 live check in kit_scan (CBC-ALL-0200)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_scan as KS  # noqa: E402


def _kit(tmp_path, cts, pg=None, cfg=""):
    w = tmp_path / "work"
    w.mkdir()
    (w / "config.mk").write_text(cfg)
    c = tmp_path / "4_1_cts.log"
    c.write_text(cts)
    if pg is not None:
        (w / "pregrt_ff_hold.log").write_text(pg)
    return tmp_path, c


def test_r7_on(tmp_path):
    k, c = _kit(tmp_path, "OT_TAP_INSERTION tap=clk sinks=5\nOT_STB done: 12 delay buffers\n",
                "OT_PREGRT_FF_HOLD pass xt 45 margin 5 + cross-tap 40 wns 1\n")
    r = KS.r7_scan(k, c)
    assert (r["stb"], r["guard"]) == ("ON", "ON")


def test_r7_old_tools(tmp_path):
    k, c = _kit(tmp_path, "OT_TAP_INSERTION tap=clk sinks=5\n",
                "OT_PREGRT_FF_HOLD cross-tap guard not applied (no tap window lines in the kit SDC)\n")
    r = KS.r7_scan(k, c)
    assert r["stb"] == "MISSING" and r["guard"] == "OFF" and "7755352068" in r["guard_why"]


def test_r7_opt_out_and_pending(tmp_path):
    k, c = _kit(tmp_path, "OT_TAP_INSERTION tap=clk\n", None, cfg="export OT_CTS_STB = 0\n")
    r = KS.r7_scan(k, c)
    assert r["stb"] == "OFF" and r["guard"] == "pending"
