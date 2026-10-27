"""SIGNOFF-MODES-2 2026-10-27: one timing mode per corner (kit_modes.py, core_flow FF_GRT_STEP, signoff timing_modes).

TT setup is timed with vclk = OT_VCLK_TT (250), FF hold with vclk = OT_VCLK_FF (202.5).  A single-mode two-corner
session gives both corners one vclk latency, so: CTS single-mode tc+bc hold repair = advisory; GRT / ECO sessions
and the sign-off FF bound fail closed."""
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import core_flow  # noqa: E402
import kit_modes  # noqa: E402
import signoff  # noqa: E402


def kit(tmp_path, tt=250.0, ff=202.5, sdc_tt=None, lint_ff=202.5, corners="tc bc", cts_skip=True, post_cts=None,
        extra=""):
    kd = tmp_path / "kit"
    kd.mkdir()
    cfg = [f"export CORNERS = {corners}", "export TC_LIB_FILES = a.lib", "export BC_LIB_FILES = b.lib",
           f"export OT_VCLK_TT = {tt:.4f}", f"export OT_VCLK_FF = {ff:.4f}", "export OT_HOLD_FF_MARGIN = 5"]
    if cts_skip:
        cfg.append("export SKIP_CTS_REPAIR_TIMING = 1")
    if post_cts:
        cfg.append("export POST_CTS_TCL = /work/cts_post.tcl")
        (kd / "cts_post.tcl").write_text(post_cts)
    (kd / "config.mk").write_text("\n".join(cfg) + "\n" + extra)
    (kd / "constraint.sdc").write_text("create_clock -name vclk -period 833\n"
                                       f"set_clock_latency -source {sdc_tt if sdc_tt is not None else tt:g} "
                                       "[get_clocks vclk]\n")
    lint = dict(time_unit_ps=1.0, insertion_ps=tt)
    if lint_ff is not None:
        lint["insertion_ff_ps"] = lint_ff
    (kd / "sdc_lint.json").write_text(json.dumps(lint))
    return kd


def test_binding_consistent_kit_passes_every_legal_session(tmp_path):
    kd = kit(tmp_path)
    assert kit_modes.check(kd, "cts")["hold_repair"] is False
    r = kit_modes.check(kd, "grt", session="bc", vclk_corner="ff", hold_repair=True)
    assert (r["tt"], r["ff"], r["session"]) == (250.0, 202.5, ["bc"])
    assert kit_modes.check(kd, "grt", session="tc", vclk_corner="", hold_repair=False)["session"] == ["tc"]
    assert kit_modes.main(["check", str(kd), "--step", "grt", "--session", "bc", "--vclk-corner", "ff",
                           "--hold-repair"]) == 0


@pytest.mark.parametrize("kw,msg", [
    (dict(sdc_tt=240.0), "constraint.sdc vclk"),
    (dict(lint_ff=210.0), "FF binding"),
    (dict(lint_ff=None), "insertion_ff_ps"),
    (dict(tt=250.0, ff=260.0, lint_ff=260.0), "not in (0, TT"),
])
def test_binding_mismatch_fails_closed(tmp_path, kw, msg):
    kd = kit(tmp_path, **kw)
    with pytest.raises(kit_modes.Fail, match=re.escape(msg)):
        kit_modes.check(kd, "grt", session="bc", vclk_corner="ff", hold_repair=True)
    assert kit_modes.main(["check", str(kd), "--step", "grt", "--session", "bc", "--vclk-corner", "ff",
                           "--hold-repair"]) == 2


def test_illegal_sessions_fail_closed(tmp_path):
    kd = kit(tmp_path)
    # FF-only hold repair against the TT vclk
    with pytest.raises(kit_modes.Fail, match="FF-only hold repair without OT_VCLK_CORNER=ff"):
        kit_modes.check(kd, "grt", session="bc", vclk_corner="", hold_repair=True)
    # KV run_kit_kv.sh MCMM GRT form: tc+bc single mode with the FF vclk -> TT setup timed against 202.5
    with pytest.raises(kit_modes.Fail, match="TT timed against the FF vclk"):
        kit_modes.check(kd, "grt", session="tc bc", vclk_corner="ff", hold_repair=True)
    # single-mode tc+bc hold repair (KV mk_eco m / mk_fd4 form)
    with pytest.raises(kit_modes.Fail, match="FF hold timed against the TT vclk"):
        kit_modes.check(kd, "eco", session="tc bc", vclk_corner="", hold_repair=True)
    with pytest.raises(kit_modes.Fail, match="TT-only session"):
        kit_modes.check(kd, "grt", session="tc", vclk_corner="ff")


def test_cts_hold_repair_detection_follows_hooks(tmp_path):
    # QC legacy cts_post.tcl form: repair_timing_helper without -setup in a single-mode tc+bc CTS
    kd = kit(tmp_path, post_cts="source /work/tap_balance.tcl\nrepair_timing_helper\n")
    with pytest.raises(kit_modes.Fail, match="single-mode tc\\+bc hold repair"):
        kit_modes.check(kd, "cts")
    # S81 modern form: setup-only CTS repair is one mode (TT vclk) per its corner
    (kd / "cts_post.tcl").write_text("repair_timing_helper -setup\n")
    assert kit_modes.check(kd, "cts")["hold_repair"] is False
    # ORFS CTS repair not skipped (KV core kits) -> hold repaired over tc+bc
    (tmp_path / "b").mkdir()
    kd2 = kit(tmp_path / "b", cts_skip=False)
    with pytest.raises(kit_modes.Fail):
        kit_modes.check(kd2, "cts")
    # a sourced hook file that repairs hold is followed
    (kd / "cts_post.tcl").write_text("source /work/inner.tcl\n")
    (kd / "inner.tcl").write_text("  repair_timing -hold -hold_margin 5\n")
    with pytest.raises(kit_modes.Fail):
        kit_modes.check(kd, "cts")


def test_staged_two_mode_kit(tmp_path, monkeypatch):
    kd = kit(tmp_path)
    r = kit_modes.stage(kd)
    assert r["staged"] and (r["tt"], r["ff"]) == (250.0, 202.5)
    assert "set_clock_latency -source 202.5 [get_clocks vclk]" in (kd / "vclk_ff.sdc").read_text()
    v = kit_modes.mk_vars((kd / "config.mk").read_text())
    assert (v["CORNERS"], v["OT_HOLD_MM"], v["OT_MM_SETUP_CORNER"]) == ("tc BC", "1", "tc")
    # idempotent
    assert kit_modes.stage(kd)["already"]
    # two-mode session: legal hold repair over tc+bc, but never with OT_VCLK_CORNER=ff
    assert kit_modes.check(kd, "grt", session="tc bc", vclk_corner="", hold_repair=True)["mm"] is True
    with pytest.raises(kit_modes.Fail, match="two-mode session with OT_VCLK_CORNER=ff"):
        kit_modes.check(kd, "grt", session="tc bc", vclk_corner="ff", hold_repair=True)
    # a broken FF SDC fails closed
    (kd / "vclk_ff.sdc").write_text("set_clock_latency -source 250 [get_clocks vclk]\n")
    with pytest.raises(kit_modes.Fail, match="vclk_ff.sdc"):
        kit_modes.check(kd, "grt", session="tc bc", hold_repair=True)


def test_signoff_record_bound_and_advisory(tmp_path):
    kd = kit(tmp_path, post_cts="repair_timing_helper\n")
    r = kit_modes.signoff_record(kd, 202.5)
    assert r["verdict"] == "PASS" and "advisory" in r            # wrong-mode CTS repair = QoR advisory only
    r = kit_modes.signoff_record(kd, 250.0)                       # FF hold timed against the TT value
    assert r["verdict"] == "FAIL" and "FF bound 250" in r["reason"]
    assert kit_modes.signoff_record(tmp_path / "nokit")["applicable"] is False
    old = tmp_path / "old"
    old.mkdir()
    (old / "config.mk").write_text("export CORNERS = tc bc\n")    # kit predates the per-corner binding
    assert kit_modes.signoff_record(old, 202.5)["applicable"] is False
    # signoff.timing_modes_check wraps it; non-applicable -> no check
    assert signoff.timing_modes_check(str(kd), 202.5)["verdict"] == "PASS"
    assert signoff.timing_modes_check(str(kd), 250.0)["verdict"] == "FAIL"
    assert signoff.timing_modes_check(str(old), 202.5) is None
    assert signoff.timing_modes_check(None) is None


def test_signoff_bundle_and_kit_copy_carry_kit_modes(tmp_path):
    assert "kit_modes.py" in signoff.SIGNOFF_BUNDLE
    assert set(core_flow.KIT_MODE_FILES) <= {p.name for p in HERE.iterdir()}
    kd = tmp_path / "k"
    kd.mkdir()
    b = core_flow.binding(250, 202.5)
    core_flow.apply(kd, b, "dut", rc_cal=False)
    assert (kd / "kit_modes.py").is_file() and (kd / "kit_modes_eco.tcl").is_file()


def test_ff_grt_step_checks_modes_before_each_session():
    s = core_flow.FF_GRT_STEP
    # CTS check before `make cts`; advisory unless OT_KIT_MODES_STRICT
    assert s.index("--step cts") < s.index("\\$M cts")
    assert "OT_KIT_MODES_STRICT = 1" in s and "KIT_MODES ADVISORY cts" in s
    # FF-only GRT: session check (fail closed) right before the FF-only make grt with the FF vclk
    i = s.index("--step grt --session bc --vclk-corner ff --hold-repair || rc=9")
    assert i < s.index("OT_VCLK_CORNER=ff \\$M grt CORNER=BC CORNERS=bc")
    # staged two-mode kit: its own corners, no OT_VCLK_CORNER
    j = s.index("--step grt --session 'tc bc' --hold-repair || rc=9")
    seg = s[j:s.index("elif", j)]
    assert "\\$M grt HOLD_SLACK_MARGIN" in seg and "OT_VCLK_CORNER" not in seg
    assert "orfs_hold_mm.py" in s


def test_stage_from_a_kit_copy_fails_closed(tmp_path, monkeypatch):
    kd = kit(tmp_path)
    monkeypatch.setattr(kit_modes, "REPO", tmp_path / "norepo")
    with pytest.raises(kit_modes.Fail, match="repository copy"):
        kit_modes.stage(kd)
    assert "OT_HOLD_MM" not in (kd / "config.mk").read_text()
