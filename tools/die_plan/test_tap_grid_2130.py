"""TAP-GRID-2130: canonical post-hook CTS read (cts_read.py, consumers) and the opt-in tap grid (clock.tap_grid)."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D)); sys.path.insert(0, str(D.parent / "autopilot"))
import cts_read as CR  # noqa: E402
import gen_phys as G  # noqa: E402

POST = "OT_CTS_POST_TIMING setup_ws -18.60 setup_tns -310.5 hold_ws -91.21 hold_tns -4000.0 (after POST_CTS hooks; 4_cts_final.rpt is pre-hook)\n"


def kit(tmp_path, log=POST, ws=-161.16, marker=False):
    b = tmp_path / "run/logs/asap7/dp_x/base"; b.mkdir(parents=True)
    (b / "4_1_cts.json").write_text(json.dumps({"cts__timing__setup__ws": ws, "cts__timing__hold__ws": 664.61}))
    (b / "4_1_cts.log").write_text("Report metrics stage 4, cts final...\n" + log + ("OT_CTS_FINAL_POSTHOOK rewritten\n" if marker else ""))
    return b


def test_log_line_wins_over_prehook_json(tmp_path):
    b = kit(tmp_path)
    for p in (tmp_path, b, b / "4_1_cts.json", b / "4_1_cts.log"):
        d = CR.cts_timing(str(p))
        assert d["source"] == "posthook" and d["setup_ws"] == -18.60 and d["hold_ws"] == -91.21, p


def test_old_kit_without_post_line_is_prehook_never_a_verdict(tmp_path):
    b = kit(tmp_path, log="")
    d = CR.cts_timing(str(tmp_path))
    assert d["source"] == "prehook" and d["setup_ws"] == -161.16
    assert CR.cts_timing(str(tmp_path / "none")) is None


def test_rewritten_json_is_posthook(tmp_path):
    kit(tmp_path, log="", ws=-19.0, marker=True)
    d = CR.cts_timing(str(tmp_path))
    assert d["source"] == "posthook" and d["setup_ws"] == -19.0


def test_canonical_report(tmp_path):
    (tmp_path / "4_cts_final.rpt").write_text("worst slack max -161\n")
    assert CR.canonical_report(str(tmp_path)) is None
    (tmp_path / "4_cts_post_hook.rpt").write_text("setup_ws -18\n")
    assert CR.canonical_report(str(tmp_path)).endswith("4_cts_post_hook.rpt")
    (tmp_path / "4_cts_final.rpt").write_text("worst slack max -18\nOT_CTS_FINAL_POSTHOOK x\n")
    assert CR.canonical_report(str(tmp_path)).endswith("4_cts_final.rpt")


def test_noprog_unsignable_reads_posthook(tmp_path):
    import noprog_watchdog as nw
    b = kit(tmp_path)
    os.utime(b / "4_1_cts.json", (1e9, 1e9))
    assert nw.measured_setup([str(tmp_path)], 1e9 - 10)[0] == -18.60      # not the pre-hook -161.16


def test_cts_post_report_rewrites_final_report():
    t = (D / "cts_post_report.tcl").read_text()
    assert "::report_metrics 4 \"cts final\"" in t and "4_cts_final_prehook.rpt" in t and "OT_CTS_FINAL_POSTHOOK" in t
    for cmd in ("insert_buffer", "repair_", "make_inst", "connect_pin", "detailed_placement"):
        assert cmd not in t


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
@pytest.mark.parametrize("f", ["tap_balance.tcl", "cts_post_report.tcl"])
def test_tcl_complete(f):
    r = subprocess.run(["tclsh"], input="set f [open %s]; puts [info complete [read $f]]" % (D / f), capture_output=True, text=True)
    assert r.stdout.strip() == "1"


def test_tap_balance_converge_is_opt_in():
    t = (D / "tap_balance.tcl").read_text()
    assert 'set tb_conv [expr {[info exists ::env(OT_TAP_CONVERGE)] && $::env(OT_TAP_CONVERGE) eq "1"}]' in t
    assert "($tb_conv ? 8 : 4)" in t and "($tb_conv ? $tb_iters : 3)" in t          # old bounds when off
    assert "OT_TAP_CONVERGE [expr" in t                                                  # verification line


def test_tap_grid_off_by_default():
    t = {"clock": {"tap_max_sinks": 1000}}
    assert G.tap_grid_exports(t) == [] and G.tap_grid_cfg(t) is None
    assert G.tap_pair_affinity_exports(t) == []


def test_tap_grid_exports(monkeypatch):
    monkeypatch.delenv("OT_TAP_SPAN_UM", raising=False)
    t = {"clock": {"tap_grid": {}, "tap_radius_um": 200.0, "tap_max_sinks": 1000}}
    e = G.tap_grid_exports(t)
    assert "export OT_TAP_CONVERGE = 1" in e and "export OT_TAP_SPAN_UM = 300" in e and "export OT_TAP_CONVERGE_ITERS = 8" in e
    assert "export OT_TAP_PAIR_UM = 200" in G.tap_pair_affinity_exports(t)
    t2 = {"clock": {"tap_grid": {"pair_um": 120, "raise_ps": 60}, "tap_pair_affinity": {"pair_um": 60}, "tap_span_um": 250}}
    e2 = G.tap_grid_exports(t2)
    assert "export OT_TAP_CONVERGE_RAISE_PS = 60" in e2 and not any("OT_TAP_SPAN_UM" in x for x in e2)
    assert "export OT_TAP_PAIR_UM = 120" in G.tap_pair_affinity_exports(t2)
    with pytest.raises(ValueError):
        G.tap_grid_cfg({"clock": {"tap_grid": {"pitch_um": 400}}})


def test_tap_grid_density_only_on_tables():
    raw = {"partition_types": {"a": {"clock": {"tap_mode": "grid+explicit", "tap_grid": {"regs": "r.json"}}},
                               "b": {"clock": {"tap_grid": {"regs": "r.json"}}},
                               "c": {"clock": {"tap_mode": "explicit", "tap_grid": {"regs": "r.json"}, "tap_density": {"regs": "own.json"}}}}}
    assert G.tap_grid_density(raw, None) == ["a"]
    assert raw["partition_types"]["a"]["clock"]["tap_density"] == {"regs": "r.json", "span_um": 300.0, "target": 1000}
    assert raw["partition_types"]["c"]["clock"]["tap_density"] == {"regs": "own.json"}


def test_tap_pitch_caps_grid_types_only():
    import schema as S
    class P:  # minimal plan-like object
        budgets = {"tap_pitch_um": 400.0}
        types = {"g": {"clock": {"tap_grid": {}}}, "e": {"clock": {"tap_grid": {}, "tap_mode": "grid+explicit"}}, "o": {"clock": {}}}
    assert S.tap_pitch(P, "g") == 300.0 and S.tap_pitch(P, "e") == 400.0 and S.tap_pitch(P, "o") == 400.0
