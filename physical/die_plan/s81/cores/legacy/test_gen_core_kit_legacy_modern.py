"""KITS-SPARE/S81C 10-25: gen_core_kit_legacy.py modern flow (default) vs --legacy-flow (opt-out, old kit).
    python3 -m pytest -q physical/die_plan/s81/cores/legacy/test_gen_core_kit_legacy_modern.py"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_core_kit_legacy.py"
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402

MOD = "dsdv_bksel_c"   # no macros, no hard children, plan pins from the S81 plan


def _gen(out, *extra):
    r = subprocess.run([sys.executable, str(GEN), "--module", MOD, "--out", str(out), *extra],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"])


def test_run_kit_templates():
    leg, mod = G.run_kit(False), G.run_kit(True)
    assert "@" not in leg.split("bash -lc", 1)[1].split('> "$K/run_$GOAL.log"', 1)[0]
    assert "rtl_lint" not in leg and "reg_fanout" not in leg and "OT_VCLK_CORNER" not in leg
    assert "  python3 -I /work/sdc_lint.py" in leg          # old unguarded first step, old indentation
    i_lint, i_sdc = mod.index("rtl_lint.py"), mod.index("sdc_lint.py /work")
    i_fg, i_rf, i_ff, i_goal = (mod.index("face_guard_core.py \\$N"), mod.index("reg_fanout_gate.py"),
                                mod.index("OT_VCLK_CORNER=ff"), mod.index("\\$M $GOAL"))
    assert i_lint < i_sdc < i_fg < i_rf < i_ff < i_goal


@pytest.mark.skipif(not (G.S81 / "die_plan.json").is_file(), reason="sparse checkout without the S81 plan")
def test_modern_vs_legacy_kit(tmp_path):
    leg = _gen(tmp_path / "leg", "--legacy-flow")
    mod = _gen(tmp_path / "mod", "--regional-taps", "4x2")
    lc, mc = (leg / "config.mk").read_text(), (mod / "config.mk").read_text()
    # legacy: fixed plan vclk, stock RC, tap balance + MCMM CTS repair, no new gates
    assert "LAYER_PARASITICS_FILE" not in lc and "OT_VCLK_FF" not in lc and "regional_taps" not in lc
    assert "insertion_ff_ps" not in json.loads((leg / "sdc_lint.json").read_text())
    assert not (leg / "reg_fanout_gate.py").exists() and (leg / "tap_balance.tcl").exists()
    # modern: RCX RC, per-corner binding, FF-only GRT hold, lint + reg_fanout, regional taps replace tap_balance
    for k in ("export LAYER_PARASITICS_FILE = /work/setRC_rcx.tcl", "export OT_VCLK_TT = 250.0000",
              "export OT_VCLK_FF = 202.5000", "override export POST_GLOBAL_ROUTE_TCL = /work/grt_post_core.tcl",
              "export PRE_CTS_TCL = /work/regional_taps.tcl", "export OT_RT_PROTECT_SPINE = 1", "export OT_RT_SETUP_ONLY = 1"):
        assert k in mc, k
    assert mc.rindex("export CTS_ARGS = -sink_clustering_enable -obstruction_aware") > mc.index("export CTS_ARGS")
    assert json.loads((mod / "sdc_lint.json").read_text())["insertion_ff_ps"] == 202.5
    assert json.loads((mod / "clock_binding.json").read_text())["insertion_ps"] == {"tt": 250.0, "ff": 202.5}
    for f in ("rtl_lint.py", "reg_fanout_gate.py", "setRC_rcx.tcl", "vclk_corner.tcl", "regional_taps.tcl",
              "regional_taps_balance.tcl", "clock_spine_guard.tcl"):
        assert (mod / f).is_file(), f
    assert not (mod / "tap_balance.tcl").exists() and not (mod / "hold_budget.tcl").exists()
    assert "post_grt_drv.tcl" in (mod / "grt_post_core.tcl").read_text()
    subprocess.run(["bash", "-n", str(mod / "run_kit.sh")], check=True)
    # modern without regional taps: tap balance stays, CTS repair is setup-only (hold only in the FF frame)
    m2 = _gen(tmp_path / "m2")
    assert "repair_timing_helper -setup" in (m2 / "cts_post.tcl").read_text()
    assert "repair_timing_helper -setup" not in (leg / "cts_post.tcl").read_text()


@pytest.mark.skipif(not (G.S81 / "die_plan.json").is_file(), reason="sparse checkout without the S81 plan")
def test_hard_child_master_kit(tmp_path):
    """KITS-SPARE-2/HB: the 16 hist_bank children of dsdv_bksel_q = one master kit (child_of + child view LEF)."""
    r = subprocess.run([sys.executable, str(GEN), "--module", "ot_s81ph_native_sel_hist_bank", "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    k = Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"])
    fz = json.loads((k / "freeze.json").read_text())
    assert fz["child_of"] == "dsdv_bksel_q" and fz["child_count"] == 16 and fz["plan_type"] == "bk_sel__t2"
    assert fz["pins"] == 359 + 16 + 60 and fz["pin_expand"] == {"clr": 17, "gsel": 64} and fz["outline_um"] == [64.8, 54.0] and fz["insertion_ff_ps"] == 202.5
    assert "gold_hist256" not in (k / "config.mk").read_text()
    # the parent itself stays refused until the child view is signed off
    r = subprocess.run([sys.executable, str(GEN), "--module", "dsdv_bksel_q", "--out", str(tmp_path / "p")],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "must be SIGNED first" in r.stderr


def test_pin_gate_refusal_message():
    """ROOT-MERGE-23: a core_pin_sites_gate FAIL must refuse with the message, not a NameError"""
    pg = dict(pins=3, counts=dict(stacked=2, off_face=1), stacked_pins=2, verdict="FAIL",
              examples=dict(stacked=["a", "b"], off_face=["c"]))
    msg = G.pin_gate_refusal("dsdv_x", pg)
    assert msg.startswith("dsdv_x: plan pin table fails core_pin_sites_gate {'stacked': 2, 'off_face': 1} (2 stacked pins")
    assert "['c']" in msg and msg.endswith("fix the plan pin assignment, not the kit")


def test_planned_tree_cts_hooks(tmp_path):
    # S81-CORE-LAT-R12: only a kit with a plan core tree gets the CTS-open-only TritonCTS + report-only post-CTS
    hold, post = "source /work/face_capture_release.tcl\n", "source /work/tap_balance.tcl\nsource /work/leaf_affinity.tcl\n"
    (tmp_path / "hold_budget.tcl").write_text(hold)
    (tmp_path / "cts_post.tcl").write_text(post)
    cfg = ["export SKIP_CTS_REPAIR_TIMING = 1", "export POST_CTS_TCL = /work/cts_post.tcl",
           "export PRE_CTS_TCL = /work/hold_budget.tcl"]
    cfg0 = list(cfg)
    assert G.planned_tree_cts(tmp_path, cfg) is False          # no core_infra_plan.json: byte-identical
    (tmp_path / "core_infra_plan.json").write_text(json.dumps({"core_tree": None}))
    assert G.planned_tree_cts(tmp_path, cfg) is False
    assert (tmp_path / "hold_budget.tcl").read_text() == hold and (tmp_path / "cts_post.tcl").read_text() == post
    (tmp_path / "core_infra_plan.json").write_text(json.dumps({"core_tree": {"cts_open": []}}))
    with pytest.raises(SystemExit, match="core_infra_cts.tcl"):
        G.planned_tree_cts(tmp_path, cfg)
    (tmp_path / "core_infra_cts.tcl").write_text("set ::ot_ci_cts_plan_open 0\n")
    assert G.planned_tree_cts(tmp_path, cfg) is True
    h = (tmp_path / "hold_budget.tcl").read_text()
    assert h.startswith(hold) and h.rstrip().endswith("source /work/core_infra_cts.tcl")
    c = (tmp_path / "cts_post.tcl").read_text()
    assert c.endswith(post) and "set ::env(OT_TAP_REPORT_ONLY) 1" in c and "set ::env(OT_LEAF_AFF_REPORT_ONLY) 1" in c
    # CTS-HOOK-PORT-1: same bytes as the R12 in-generator form; config.mk lines unchanged (hooks edited in place)
    assert h == hold + "# S81-CORE-LAT-R12: plan-built tree -> TritonCTS only on CTS-open nets\nsource /work/core_infra_cts.tcl\n"
    assert c == ("# S81-CORE-LAT-R12: plan-built tree -> tap balance + leaf affinity measure/report only\n"
                 "set ::env(OT_TAP_REPORT_ONLY) 1\nset ::env(OT_LEAF_AFF_REPORT_ONLY) 1\n" + post)
    assert cfg == cfg0


def test_explicit_slice_interior_clock_exact_rectangle():
    q=dict(name="clk",layer="M5",x=129.612,y=21.6)
    shape={"clk":("M5",.048,.48,129.588,21.36,129.636,21.84)}
    contract=("M5",129.612,21.6,(.048,.48))
    assert G.planned_pin_geometry(q,shape,259.2,43.2,interior_clock=contract)==(q,.048,.48,0)
    with pytest.raises(SystemExit,match="explicit on-track"):
        G.planned_pin_geometry(dict(q,x=129.6),shape,259.2,43.2,interior_clock=contract)
    with pytest.raises(SystemExit,match="off its declared"):
        G.planned_pin_geometry(dict(q,name="data"),{},259.2,43.2)
    with pytest.raises(SystemExit,match="full-sized"):
        G.planned_pin_geometry(q,{"clk":("M5",.024,.084,129.6,21.558,129.624,21.642)},259.2,43.2,interior_clock=contract)


def test_natural_core_publishes_latency_contract(tmp_path):
    """A natural core must retain the FF frame used by its hold repair."""
    r = subprocess.run([sys.executable, str(GEN), "--module", "ot_s81_cfg7_seq_bfp",
                        "--out", str(tmp_path), "--trial"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    kit = Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"])
    sys.path.insert(0, str(G.TOOL))
    import signoff
    cc = signoff.hard_core_latency_contract({"kit": str(kit)})
    assert cc is not None and cc["kind"] == "hard_core_latency"
    assert json.loads((kit / "sdc_lint.json").read_text())["insertion_ff_ps"] == 202.5
