"""DIE-QC-36 A0 opt-in core_infra delta (COORD ruling [DIE-QC-35-PARK] (2)):
 (i)   stage_basis total + per-leaf cts_stages for CTS-open FF gated domains of very different size (514/781/2849);
 (ii)  planned-domain macro gates (form C) on a shallower node, leaf.early_tap_ps from the macro's signed/real view;
 (iii) core_tree.install_stage pre_cts: tree built at PRE_CTS on the placed design (incremental DPL of planned cells);
 (iv)  every new field absent -> emit_tcl / install / kit_cts_hook byte-identical to the pre-delta tool (BASE_REF).
    python3 -m pytest -q tools/die_plan/test_core_infra_a0_optin.py"""
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import core_infra as CI
from test_core_infra import sample, icg_tree, icg_planned_tree
from test_core_infra_stage_basis import macro_chain_tree

HERE = Path(__file__).resolve().parent
# The A0 delta was cut from 49d8a0c889b and proven byte-identical there (ROOT-MERGE-U 10-29). Later DEFAULT-ON
# class fixes changed the default output on purpose: 2adc27c06 (M5 feedthrough ports snapped to the kit track grid,
# plan_xy_um recorded) and a9498693c5a (typed clock FT ports get the 0.048x0.48 clock via-access pin shape).
# FLOW-17 (10-31) re-based on main 400bc86b1d4, which carries both; (iv) now guards the default output from there.
BASE_REF = "400bc86b1d4"
B = {"TT": 36.154, "FF": 27.549, "source": "tools/die_plan/clk_aocv_table_g021.json class B mu_stage_ps"}
ROMLEAF = {"TT": {"min": 245.1, "max": 324.1}, "FF": {"min": 190.4, "max": 256.8}}
LSL = {"TT": {"min": 234.9, "max": 289.0}, "FF": {"min": 182.1, "max": 221.3}}


def a0_tree(install_stage=None):
    """A0-shaped tile: 3 register hop ICGs (CTS-open domains 514/781/2849, all 3 CTS stages) at depth 4, an equal
    total-stage root-register leaf at depth 7, and a macro hop ICG (form C) on the root node with an early-tap leaf."""
    s = sample()
    s["pg_obstructions_um"] = {}
    nodes = [dict(name="R", master="BUFx24_ASAP7_75t_R", xy_um=[432, 432], parent="port:ck"),
             dict(name="t2", master="BUFx24_ASAP7_75t_R", xy_um=[432, 440], parent="R"),
             dict(name="t3", master="BUFx24_ASAP7_75t_R", xy_um=[432, 448], parent="t2"),
             dict(name="r4", master="BUFx12f_ASAP7_75t_R", xy_um=[300, 448], parent="t3"),
             dict(name="r5", master="BUFx12f_ASAP7_75t_R", xy_um=[300, 400], parent="r4"),
             dict(name="r6", master="BUFx8_ASAP7_75t_R", xy_um=[300, 350], parent="r5"),
             dict(name="r7", master="BUFx8_ASAP7_75t_R", xy_um=[300, 300], parent="r6"),
             dict(name="m3", master="BUFx8_ASAP7_75t_R", xy_um=[600, 600], parent="u_rp0.u_icg")]
    gates = [dict(inst=f"u_hop_{d}.u_icg", master="ICGx2_ASAP7_75t_R", parent="t3", xy_um=[420 + k, 450])
             for k, d in enumerate(("rs", "tx0", "ck"))]
    gates.append(dict(inst="u_rp0.u_icg", master="ICGx2_ASAP7_75t_R", parent="R", xy_um=[440, 430], domain="planned"))
    leaves = [dict(node=f"u_hop_{d}.u_icg", load_class="gated_domain", domain_sinks=n, cts_stages=3)
              for d, n in (("rs", 514), ("tx0", 781), ("ck", 2849))]
    leaves += [dict(node="r7", sinks=["f0/CLK", "f1/CLK"]),
               dict(node="m3", sinks=["u_rom0/CLK"], load_class="macro", early_tap_ps={
                   "TT": {"min": 140.0, "max": 150.0}, "FF": {"min": 100.0, "max": 120.0}},
                   early_tap_view="macros/romleaf.lib sha256:feed")]
    s["core_tree"] = {"clock_port": "ck", "stage_basis": "total", "early_tap_stage_ps": dict(B),
                      "nodes": nodes, "gates": gates, "leaves": leaves}
    if install_stage:
        s["core_tree"]["install_stage"] = install_stage
    return s


# ------------------------------------------------------------------------------------------------ (i) cts_stages
def test_i_total_basis_declares_equal_cts_stages_for_unequal_domains():
    s = a0_tree()
    p = CI.compile_slice(s)["core_tree"]
    assert p["depth"] == 7
    assert p["cts_open"] == ["u_hop_ck.u_icg", "u_hop_rs.u_icg", "u_hop_tx0.u_icg"]


def test_i_default_basis_refuses_the_a0_census():
    s = a0_tree()
    del s["core_tree"]["stage_basis"]
    for lf in s["core_tree"]["leaves"]:
        lf.pop("early_tap_ps", None)
    with pytest.raises(CI.InfraError, match="unequal"):
        CI.compile_slice(s)


# --------------------------------------------------------------------------------------------- (ii) early taps
def test_ii_early_tap_stage_count_from_the_macro_view():
    t = {"early_tap_stage_ps": dict(B)}
    k, res = CI._early_tap(t, dict(load_class="macro", early_tap_ps=ROMLEAF, early_tap_view="v"), "m", "total")
    assert k == 8 and abs(res["FF"] - (223.6 - 8 * 27.549)) < 1e-3
    assert CI._early_tap(t, dict(load_class="macro", early_tap_ps=LSL, early_tap_view="v"), "m", "total")[0] == 7


def test_ii_planned_macro_gate_on_shallower_node_joins_equal_total():
    p = CI.compile_slice(a0_tree())["core_tree"]
    assert p["under_gate"] == {"m3": "u_rp0.u_icg"}
    (e,) = p["early_taps"]
    assert e["node"] == "m3" and e["stages"] == 4 and e["view"].startswith("macros/romleaf.lib")
    tcl = CI.emit_tcl(a0_tree())
    assert "ot_ci_tree_gate_planned {u_rp0.u_icg}" in tcl and "ot_ci_tree_sink {m3} {u_rom0/CLK}" in tcl


def _leaf(s, node):
    return next(lf for lf in s["core_tree"]["leaves"] if lf["node"] == node)


@pytest.mark.parametrize("mut,frag", [
    (lambda s: _leaf(s, "m3")["early_tap_ps"]["FF"].update(min=150.0, max=170.0), "agree at TT/FF"),
    (lambda s: _leaf(s, "m3")["early_tap_ps"]["TT"].update(min=200.0, max=230.0), "agree at TT/FF"),
    (lambda s: _leaf(s, "m3").update(early_tap_ps=ROMLEAF), "unequal stage counts"),
    (lambda s: _leaf(s, "m3").pop("early_tap_view"), "early_tap_view"),
    (lambda s: _leaf(s, "m3").update(load_class="register"), "macro-leaf field"),
    (lambda s: _leaf(s, "m3")["early_tap_ps"].pop("TT"), "TT and FF"),
    (lambda s: s["core_tree"].pop("early_tap_stage_ps"), "early_tap_stage_ps"),
    (lambda s: s["core_tree"]["early_tap_stage_ps"].pop("source"), "early_tap_stage_ps"),
    (lambda s: s["core_tree"].update(stage_basis="node_depth"), "stage_basis total"),
    (lambda s: _leaf(s, "u_hop_rs.u_icg").update(early_tap_ps=ROMLEAF), "planned macro leaf"),
])
def test_ii_early_tap_refusals(mut, frag):
    s = a0_tree()
    mut(s)
    with pytest.raises(CI.InfraError, match=frag):
        CI.compile_slice(s)


def test_ii_stage_model_without_early_leaf_refused():
    s = macro_chain_tree()
    s["core_tree"]["early_tap_stage_ps"] = dict(B)
    with pytest.raises(CI.InfraError, match="without any early_tap_ps"):
        CI.compile_slice(s)


# ------------------------------------------------------------------------------------------- (iii) PRE_CTS install
def test_iii_pre_cts_install_moves_the_tree_out_of_the_pre_gpl_hook(tmp_path):
    s = a0_tree("pre_cts")
    assert CI.install(tmp_path, s)
    pre = (tmp_path / "master_core_infra.tcl").read_text()
    late = (tmp_path / CI.LATE_HOOK).read_text()
    assert "ot_ci_tree" not in pre and "ot_ci_cell {R}" not in pre and "ot_ci_cell {mp_isl0_ck0}" in pre
    assert (tmp_path / CI.LATE_IMPL).read_text() == (HERE / CI.LATE_IMPL).read_text()
    for frag in ("source /work/core_infra_impl.tcl", f"source /work/{CI.LATE_IMPL}", "ot_ci_late_cell {R} BUFx24",
                 "ot_ci_late_gate {u_hop_ck.u_icg} ICGx2_ASAP7_75t_R {t3}", "ot_ci_tree_gate_planned {u_rp0.u_icg}",
                 "ot_ci_tree_domain {u_hop_ck.u_icg} 2849", "ot_ci_tree_finish", "ot_ci_late_legalize 20"):
        assert frag in late, frag
    assert "ot_ci_tree_gate " not in late and "ot_ci_late_cell {mp_isl0" not in late
    impl = (tmp_path / CI.LATE_IMPL).read_text()
    assert "-no_insertion_delay" in impl and "lsearch -exact $args -repair_clock_nets" in impl
    order = [late.index(x) for x in ("ot_ci_begin", "ot_ci_late_cell {R}", "ot_ci_tree_begin", "ot_ci_tree_finish",
                                     "ot_ci_late_legalize", "ot_ci_finish")]
    assert order == sorted(order)
    plan = json.loads((tmp_path / "core_infra_plan.json").read_text())
    assert plan["core_tree"]["install_stage"] == "pre_cts"
    assert "set ::ot_ci_cts_plan_open 3" in (tmp_path / CI.CTS_HOOK).read_text()


def test_iii_kit_cts_hook_sources_the_late_tree_before_cts(tmp_path):
    CI.install(tmp_path, a0_tree("pre_cts"))
    (tmp_path / "fc_dt_lift_cts.tcl").write_text("# lift\n")
    cfg = ["export PRE_CTS_TCL = /work/fc_dt_lift_cts.tcl"]
    assert CI.kit_cts_hook(tmp_path, cfg)
    txt = (tmp_path / "fc_dt_lift_cts.tcl").read_text()
    assert txt.index("# lift") < txt.index(f"source /work/{CI.LATE_HOOK}") < txt.index("source /work/core_infra_cts.tcl")
    (tmp_path / CI.LATE_IMPL).unlink()
    with pytest.raises(SystemExit, match="install_stage pre_cts"):
        CI.kit_cts_hook(tmp_path, list(cfg))


@pytest.mark.parametrize("mut,frag", [
    (lambda t: t.update(install_stage="post_route"), "install_stage"),
    (lambda t: t.update(late_dpl_max_um=0), "late_dpl_max_um"),
])
def test_iii_pre_cts_refusals(mut, frag):
    s = a0_tree("pre_cts")
    mut(s["core_tree"])
    with pytest.raises(CI.InfraError, match=frag):
        CI.compile_slice(s)


def test_iii_pre_cts_refuses_gate_copies_and_rebind():
    s = icg_planned_tree()
    s["core_tree"]["install_stage"] = "pre_cts"
    with pytest.raises(CI.InfraError, match="gate copies"):
        CI.compile_slice(s)


def test_iii_late_emitter_needs_the_opt_in():
    with pytest.raises(CI.InfraError, match="pre_cts"):
        CI.emit_late_tcl(CI.compile_slice(a0_tree()))


# ------------------------------------------------------------------------------- (iv) default output byte-identical
def _base_module(tmp_path):
    try:
        src = subprocess.run(["git", "-C", str(HERE), "show", f"{BASE_REF}:tools/die_plan/core_infra.py"],
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(f"git history with {BASE_REF} unavailable")
    d = tmp_path / "base"
    d.mkdir()
    (d / "core_infra.py").write_text(src)
    spec = importlib.util.spec_from_file_location("core_infra_base", d / "core_infra.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["core_infra_base"] = m
    spec.loader.exec_module(m)
    m.HERE = HERE                      # same core_infra.tcl / core_infra_cts.tcl / rebind sources as the new tool
    return m


def _repo_slices():
    try:
        names = subprocess.run(["git", "-C", str(HERE), "grep", "-l", '"pushdown"', BASE_REF, "--", ":(top)*.json"],
                               capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return []
    out = []
    for n in names:
        try:
            sl = json.loads(subprocess.run(["git", "-C", str(HERE), "show", n], capture_output=True, text=True,
                                           check=True).stdout)
        except (ValueError, subprocess.CalledProcessError):
            continue
        if isinstance(sl, dict) and sl.get("kind") in ("core", "partition") and sl.get("pushdown"):
            out.append((n, sl))
    return out


def _fixtures():
    import test_core_infra as T
    import test_core_infra_stage_basis as S
    fx = [("sample", sample()), ("icg_tree", icg_tree()), ("icg_planned_tree", icg_planned_tree()),
          ("macro_chain", macro_chain_tree())]
    for name in ("icg_copy_tree",):
        if hasattr(T, name):
            fx.append((name, getattr(T, name)()))
    return fx


def _outputs(mod, sl, kd):
    res = {}
    kd.mkdir(parents=True)
    try:
        res["emit_tcl"] = mod.emit_tcl(copy.deepcopy(sl))
        res["plan"] = json.dumps(mod.compile_slice(copy.deepcopy(sl)), indent=2, sort_keys=True)
        mod.install(kd, copy.deepcopy(sl))
        cfg = ["export PRE_CTS_TCL = /work/pre.tcl", "export POST_CTS_TCL = /work/post.tcl"]
        (kd / "pre.tcl").write_text("# pre\n")
        (kd / "post.tcl").write_text("# post\n")
        res["hook"] = repr(mod.kit_cts_hook(kd, cfg))
        res["cfg"] = "\n".join(cfg)
    except (Exception, SystemExit) as e:   # a refusal must be the identical refusal
        res["error"] = f"{type(e).__name__}: {e}".replace(str(kd), "<kd>")
    for p in sorted(kd.iterdir()):
        res["file:" + p.name] = p.read_bytes()
    return res


def test_iv_default_outputs_byte_identical_to_base(tmp_path):
    base = _base_module(tmp_path)
    cases = _fixtures() + _repo_slices()
    assert len(cases) >= 4
    for k, (name, sl) in enumerate(cases):
        a = _outputs(base, sl, tmp_path / "b" / str(k))
        b = _outputs(CI, sl, tmp_path / "n" / str(k))
        assert a == b, name
