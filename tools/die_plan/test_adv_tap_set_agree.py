"""pytest: ADV-TAP-SET-AGREE on the hd_ctl 63 vs 64 pattern (stale tap_window clk_t64, W6 view with 64 taps)."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_tap_set_agree as A  # noqa: E402

N = 63


def _ports(n):
    return ["clk"] + [f"clk_t{i}" for i in range(1, n + 1)]


def _rtl(mod, n, extra=""):
    body = ",\n".join(f"    input  wire {p},  // tap" for p in _ports(n))
    return f"module {mod} (\n{body},\n    input wire fclk_in_a_i{extra}\n);\nendmodule\n"


def _plan(win_n, off_n):
    return {"partition_types": {"hd_ctl": {"module": "ot_s81hd_ctl"}},
            "clock": {"tap_window": {"per_port_ps": {"hd_ctl": {p: 1 for p in _ports(win_n)}}},
                      "tap_offset": {"per_port_ps": {"hd_ctl": {p: {"TT": 0} for p in _ports(off_n)}}}}}


def _setup(tmp_path, win_n, off_n, rtl_n):
    pub = tmp_path / "published"
    pub.mkdir()
    (pub / "ot_s81hd_ctl.sv").write_text(_rtl("ot_s81hd_ctl", rtl_n))
    pl = tmp_path / "source_plan.json"
    pl.write_text("{}")
    return _plan(win_n, off_n), str(pl)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("OT_PRE_TAPSET", "OT_PRE_TAPSET_RTL", "OT_PRE_TAPSET_VIEWS", "OT_PRE_TAPSET_TOP"):
        monkeypatch.delenv(k, raising=False)


def test_default_off(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_PRE_TAPSET", raising=False)
    raw, pl = _setup(tmp_path, 64, 63, 63)
    assert A.findings(raw, pl) == []


def test_env_enables(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_PRE_TAPSET", "1")
    raw, pl = _setup(tmp_path, 64, 63, 63)
    assert any("clk_t64" in x for x in A.findings(raw, pl))


def test_hd_ctl_63_vs_64(tmp_path):
    raw, pl = _setup(tmp_path, 64, 63, 63)
    out = A.findings(raw, pl, enabled=True)
    assert len(out) == 2
    assert "hd_ctl: tap sets disagree" in out[0] and "tap_window only ['clk_t64']" in out[0]
    assert "tap_window only ['clk_t64']" in out[0] and "tap_window names ['clk_t64'] absent from the RTL" in out[0]
    assert "1 of 1 types" in out[1]


def test_agreeing_is_clean(tmp_path):
    raw, pl = _setup(tmp_path, 63, 63, 63)
    out = A.findings(raw, pl, enabled=True)
    assert len(out) == 1 and "0 of 1 types" in out[0]


def test_rtl_missing_is_not_checked_but_tables_compared(tmp_path):
    raw, pl = _setup(tmp_path, 64, 63, 63)
    (tmp_path / "published" / "ot_s81hd_ctl.sv").unlink()
    out = A.findings(raw, pl, enabled=True)
    assert "tap_window only ['clk_t64']" in out[0] and "1 types have no RTL module" in out[-1]


def test_view_and_top_legs(tmp_path):
    raw, pl = _setup(tmp_path, 63, 63, 63)
    v = tmp_path / "views" / "ot_s81hd_ctl"
    v.mkdir(parents=True)
    (v / "ilm.json").write_text(json.dumps({"clock_ports": _ports(64) + ["fclk_in_a_i", "fclk_in_lepk_i0"]}))
    top = tmp_path / "top.sv"
    conn = ", ".join(f".{p}(w_{p})" for p in _ports(63))
    top.write_text("module top;\n  ot_s81hd_ctl ctl (\n    " + conn + ",\n    .fclk_in_a_i(x)\n  );\nendmodule\n")
    out = A.findings(raw, pl, enabled=True, views=str(tmp_path / "views"), top_sv=str(top))
    assert any("view has tap port(s) ['clk_t64']" in x for x in out)
    assert any("not connected in the die top" in x and "fclk_in_lepk_i0" in x for x in out)
    assert any("clk_t64" in x for x in out if "die top" in x)


def test_never_raises():
    assert A.findings(None, "p") == []
    assert A.findings(None, "p", enabled=True)[0].startswith("WARN ADV-TAP-SET-AGREE not checked")


def test_rtl_only_taps_are_counted_not_flagged(tmp_path):
    raw, pl = _setup(tmp_path, 40, 40, 63)
    out = A.findings(raw, pl, enabled=True)
    assert len(out) == 1 and "0 of 1 types" in out[0] and "1 types have RTL taps without a table row" in out[0]


def test_empty_connection_is_open_and_offset_only_direction(tmp_path):
    assert A.instance_ports("m u (.a(x), .b(), .c( ));", "m") == [("u", {"a"})]
    raw, pl = _setup(tmp_path, 63, 64, 64)
    raw["clock"]["tap_window"]["per_port_ps"]["hd_ctl"].pop("clk_t63")
    (tmp_path / "published" / "ot_s81hd_ctl.sv").write_text(_rtl("ot_s81hd_ctl", 64))
    out = A.findings(raw, pl, enabled=True)
    assert "tap_offset only" in out[0] and "add the missing row" in out[0]
