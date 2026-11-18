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
    assert F.family_margin("qwen_compute", {"hold_ff_margin_ps": 30}) == 30.0
    assert F.family_margin("qwen_compute", {"hold_ff_margin_ps": 30}, {"hold_ff_margin_ps": 20}) == 20.0
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
    assert "_fam = None if _hm else" in src                    # the per-item env knob wins over the family value


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
