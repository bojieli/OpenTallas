"""HOLD-MARGIN-FAMILY 11-17: reg-to-reg hold repair target per die family, and that it reaches config.mk / the pre-route tcl / the GRT guard."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_margin_family as F  # noqa: E402


def test_family_table():
    assert F.family_margin("qwen_compute") == F.family_margin("qwen_kvsys") == F.family_margin("s81_head") == 40.0
    assert F.family_margin("s81") is None and F.family_margin("hbm") is None
    assert F.core_margin() == 15.0


def test_plan_keys_override_and_are_range_checked():
    assert F.family_margin("qwen_compute", {"hold_ff_margin_ps": 30}) == 40.0       # die key is a floor next to the table: the larger wins
    assert F.family_margin("qwen_compute", {"hold_ff_margin_ps": 55}) == 55.0
    assert F.family_margin("qwen_compute", {"hold_ff_margin_ps": 30}, {"hold_ff_margin_ps": 20}) == 40.0
    assert F.family_margin("s81", {"hold_ff_margin_ps": 12}) == 12.0          # a die can opt in
    try:
        F.family_margin("s81", {"hold_ff_margin_ps": 400})
        raise AssertionError("must refuse")
    except ValueError:
        pass


def test_off_switch_gives_the_old_flow():
    env = {"OT_HOLD_FAMILY_MARGIN": "0"}
    assert F.family_margin("qwen_compute", env=env) is None and F.core_margin(env) is None
    assert F.grt_margin(10.0, "qwen_compute", env=env) == 10.0 and F.config_lines(None) == []


def test_grt_margin_only_raises_never_lowers_and_keeps_none():
    assert F.grt_margin(10.0, "qwen_kvsys") == 40.0
    assert F.grt_margin(55.0, "qwen_kvsys") == 55.0
    assert F.grt_margin(None, "qwen_kvsys") is None             # two-mode kit: unchanged
    assert F.grt_margin(10.0, core=True) == 15.0 and F.grt_margin(20.0, core=True) == 20.0
    assert F.grt_margin(10.0, "s81") == 10.0


def test_config_lines():
    ls = F.config_lines(40.0)
    assert ls == ["export OT_HOLD_FAMILY_MARGIN_PS = 40", "export OT_PREGRT_HOLD_R2R_MARGIN = 40", "export OT_HOLD_SETUP_GUARD_PS = 0"]
    assert "OT_PREGRT_HOLD_R2R_MARGIN" not in "".join(F.config_lines(15.0, pregrt=False))


def test_check_kit_reads_config_mk_back(tmp_path):
    (tmp_path / "config.mk").write_text("export OT_HOLD_FF_MARGIN = 40\nexport OT_HOLD_FAMILY_MARGIN_PS = 40\n")
    assert F.check_kit(tmp_path, "qwen_compute") == []
    (tmp_path / "config.mk").write_text("export OT_HOLD_FF_MARGIN = 10\n")
    bad = F.check_kit(tmp_path, "qwen_compute")
    assert len(bad) == 2 and "predates" in bad[1]
    assert F.check_kit(tmp_path, "s81") == []                    # no family value: nothing expected
    (tmp_path / "config.mk").write_text("export SOMETHING = 1\n")
    assert any("no OT_HOLD_FF_MARGIN" in b for b in F.check_kit(tmp_path, "qwen_kvsys"))


def test_core_flow_apply_carries_the_core_margin(tmp_path):
    import core_flow
    cfg = core_flow.apply(tmp_path, {"tt": 100.0, "ff": 80.0, "tol": 5.0, "basis": "t"}, "unit_core", hold_ff_margin=core_flow.HOLD_FF_MARGIN_DEFAULT)
    assert "export OT_HOLD_FF_MARGIN = 15" in cfg and "export OT_HOLD_FAMILY_MARGIN_PS = 15" in cfg and "export OT_HOLD_SETUP_GUARD_PS = 0" in cfg
    assert "OT_PREGRT_HOLD_R2R_MARGIN" not in "\n".join(cfg)
    cfg2 = core_flow.apply(tmp_path, {"tt": 100.0, "ff": 80.0, "tol": 5.0, "basis": "t"}, "unit_core", hold_ff_margin=25.0)
    assert "export OT_HOLD_FF_MARGIN = 25" in cfg2


def test_core_flow_apply_off_switch(tmp_path, monkeypatch):
    import core_flow
    monkeypatch.setenv("OT_HOLD_FAMILY_MARGIN", "0")
    cfg = core_flow.apply(tmp_path, {"tt": 100.0, "ff": 80.0, "tol": 5.0, "basis": "t"}, "unit_core")
    assert f"export OT_HOLD_FF_MARGIN = {core_flow.HOLD_FF_MARGIN_DEFAULT:g}" in cfg and "OT_HOLD_FAMILY_MARGIN_PS" not in "\n".join(cfg)


def test_gen_phys_reads_the_family_before_building_config():
    src = (HERE / "gen_phys.py").read_text()
    assert "_HMF.family_margin(P.name" in src and "_HMF.config_lines(_fam" in src
    assert src.index("_HMF.family_margin(P.name") < src.index("export OT_HOLD_FF_MARGIN = {hold_ff_margin:g}")


def test_pregrt_tcl_has_the_reg_to_reg_pass_with_ports_excepted_and_restored():
    import pregrt_ff_hold as P
    t = P.TAIL
    assert "OT_PREGRT_HOLD_R2R_MARGIN" in t and "foreach pg_tag {all rr xt}" in t
    rr = t[t.index('if {$pg_tag eq "rr"} {'):]
    assert "set_false_path -hold -from $pg_in" in rr and "set pg_mrg $pg_rm" in rr
    assert "unset_path_exceptions -hold -from $pg_in" in t[t.index('if {$pg_tag eq "rr"} {', t.index("repair_timing -hold")):]
    assert "repair_timing -hold -hold_margin $pg_mrg" in t and "repair_timing -hold -hold_margin $pg_pm" not in t


def test_grt_hold_guard_has_the_setup_floor():
    s = (HERE / "hold_guard_grt.tcl").read_text()
    assert "OT_HOLD_SETUP_GUARD_PS" in s and "OT_HOLD_SETUP_GUARD stop" in s and "min($sg0, $sg)" in s
    assert s.index("OT_HOLD_SETUP_GUARD stop") < s.index("if {[lindex $cur 0] >= $hm} { break }")


def test_gen_hold_ff_margin_0_is_raised_to_the_family_floor_but_a_plan_key_is_the_value():
    assert F.grt_margin(0.0, "qwen_compute") == 40.0               # gen.py --hold-ff-margin 0 does not override the family
    assert F.grt_margin(5.0, "qwen_kvsys", None, None) == 40.0
    assert F.grt_margin(0.0, "qwen_compute", {"hold_ff_margin_ps": 20}) == 40.0      # a die key below the table does not lower it
    assert F.grt_margin(0.0, "s81", {"hold_ff_margin_ps": 25}) == 25.0               # die key = floor on a die without a table value
    assert F.grt_margin(10.0, "s81", {"hold_ff_margin_ps": 25}) == 25.0              # an item value of 10 does not beat the die's 25 (COORD)
    assert F.grt_margin(30.0, "s81", {"hold_ff_margin_ps": 25}) == 30.0              # an item may raise it
    assert F.grt_margin(60.0, "qwen_compute") == 60.0              # the floor never lowers a higher caller value
    assert F.grt_margin(0.0, "qwen_compute", env={"OT_HOLD_FAMILY_MARGIN": "0"}) == 0.0
    assert F.explicit({"hold_ff_margin_ps": 0}) is True and F.explicit({}) is False


def test_hold_after_tt_keep_decision():
    import hold_after_tt_keep as K
    assert K.decide((-25.0, -10.0), (2.0, -9.8))[0] is True
    assert K.decide((-25.0, -10.0), (2.0, -12.0))[0] is False        # TT setup fell more than the 0.5 ps guard
    assert K.decide((-25.0, -10.0), (-25.0, -10.0))[0] is False      # no hold gain
    assert K.decide(None, (0.0, 0.0))[0] is False


def test_hold_after_tt_is_wired_after_the_grt_tt_repair_and_before_the_gate():
    g = (HERE / "gen_phys.py").read_text()
    a = g.index("tt_setup_keep.py /work/tt_setup_repair_grt.log")
    b = g.index("bash /work/hold_after_tt.sh")
    c = g.index("O5=\\$(ls /work/run/results/asap7/*/base/5_1_grt.odb")
    assert a < b < c
    assert "grep -q '^export OT_HOLD_AFTER_TT = 1' /work/config.mk" in g and 'os.environ.get("OT_HOLD_AFTER_TT"' in g
    s = (HERE / "hold_after_tt.sh").read_text()
    assert s.index('measure "$G" before') < s.index("OT_VCLK_CORNER=ff $MF grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=$HM") < s.index("python3 -I /work/hold_after_tt_keep.py")
    assert s.count("restore restore") >= 3 and s.rstrip().endswith("exit 0")


def test_item_env_hold_margin_is_max_not_replace():
    g = (HERE / "gen_phys.py").read_text()
    assert "_fam = None if _hm else" not in g and "_fam = _HMF.family_margin(P.name" in g
    # the item value is read first (hold_ff_margin = float(_hm)), then raised to the floor by grt_margin
    assert g.index("hold_ff_margin = float(_hm)") < g.index("hold_ff_margin = _HMF.grt_margin(hold_ff_margin")


def _tcl_procs(*names):
    src = (HERE.parent / "orfs_hold_mm.tcl").read_text()
    out = []
    for n in names:
        i = src.index("proc %s " % n)
        out.append(src[i:src.index("\n}\n", i) + 3])      # a top-level proc ends at the first line that is a lone closing brace
    return "\n".join(out)


def _tclsh(script):
    import shutil
    import subprocess
    t = shutil.which("tclsh")
    if not t:
        import pytest
        pytest.skip("tclsh required")
    return subprocess.run([t], input=script, capture_output=True, text=True, timeout=60).stdout.split()


def test_area_guard_never_goes_below_the_level_needed_for_hold_met():
    procs = _tcl_procs("ot_hm_decide")
    # hm 30, 20k endpoints in margin (flood), worst real violation -9: 19 (violation + floor); a deep violation -25 raises it to 30 (never above asked)
    out = _tclsh(procs + "\nputs [lindex [ot_hm_decide 30 -9.0 20000 100 1000.0 0.08 10000 8.0 10.0] 0]"
                 "\nputs [lindex [ot_hm_decide 30 -25.0 20000 100 1000.0 0.08 10000 8.0 10.0] 0]"
                 "\nputs [lindex [ot_hm_decide 30 -9.0 20 100 1000.0 0.08 10000 8.0 10.0] 0]"
                 "\nset ::env(OT_HM_GUARD_MIN_CUSHION_PS) 25\nputs [lindex [ot_hm_decide 30 -9.0 20000 100 1000.0 0.08 10000 8.0 5.0] 0]")
    assert out == ["19.0", "30", "30", "30"]
    assert float(out[0]) >= 9.0 + 1.0                    # violation + cushion, strictly met


def test_hold_retry_runs_at_the_asked_margin_with_the_guard_off_and_is_bounded():
    t = (HERE.parent / "orfs_hold_mm.tcl").read_text()
    assert "proc ot_hold_final_retry" in t and "OT_HOLD_REPAIR_RETRIES" in t and "OT_HOLD_MARGINS asked" in t
    assert "ot_hold_final_retry $rt_args0 $hm_asked $hm }" in t                      # after the chunk loop, with the unreduced args
    r = t[t.index("proc ot_hold_final_retry"):t.index("proc ot_repair_hold_guarded")]
    assert "ot_hm_guard" not in r and "lreplace $args" in r and "$gain < 0.5" in r  # asked margin, no area guard, stops on no gain
    assert "OT_HOLD_MARGINS guard applied" in t and "OT_HOLD_MARGINS met-first pass applied margin 0" in t
    # simulate: ws -10.6 after the first pass, retry brings it to +1
    procs = _tcl_procs("ot_env_num", "ot_hold_final_retry")
    script = ("set ::n 0\nproc ot_hold_stats {} {global n; return [list [expr {$n ? 1.0 : -10.6}] 0 0]}\n"
              "proc log_cmd {args} {global n; incr n; puts \"CMD $args\"}\n" + procs +
              "\not_hold_final_retry {-hold_margin 19 -max_buffer_percent 20} 30 19\n")
    out = " ".join(_tclsh(script))
    assert "CMD repair_timing -hold_margin 30 -max_buffer_percent 20 -hold" in out and "applied 19,30" in out and "met" in out
