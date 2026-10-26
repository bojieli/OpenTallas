"""IO-HOLD option A (COORD ruling 2026-10-25 10:23; opt-in clock.io_hold = sender_min / env OT_IO_HOLD): per-port
min input delay = the driving partition's guaranteed output-min, fallback contract on die-edge / channel / undriven
inputs; legacy kits byte-identical; hold_gate / sign-off overlays re-apply the per-port values; parent check."""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import io_hold_parent  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402
import signoff  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())


def _plan(io_hold=None):
    raw = copy.deepcopy(PAIR)
    if io_hold:
        raw.setdefault("clock", {})["io_hold"] = io_hold
    return schema.Plan(raw)


def test_legacy_default_unchanged(monkeypatch):
    monkeypatch.delenv("OT_IO_HOLD", raising=False)
    P = _plan()
    assert gen_phys.io_hold_mode(P) == "legacy"
    assert gen_phys.input_hold_min(P, "fa") == {} and gen_phys.io_hold_tcl(P, "fa") is None
    s = gen_phys.sdc(P, "fa", gen_phys.type_pins(P, "fa"))
    assert "IO-HOLD A" not in s and s.count("set_input_delay -min") == 1
    assert "hold_in_min_ports_ps" not in sdc_lint.kit_context(P, "fa")


def test_sender_min_per_port():
    P = _plan("sender_min")
    g = (1 - gen_phys.UNC_SPLIT) * gen_phys.UNC_HOLD_PS - gen_phys.hold_out_min_ps(P)
    assert g == 12.5
    fa, fb = gen_phys.input_hold_min(P, "fa"), gen_phys.input_hold_min(P, "fb")
    # fa: din / fz_i come from the die edge (fallback), r_i from pfb
    assert set(fa) == {"r_i"} and fa["r_i"]["in_min_ps"] == g and fa["r_i"]["senders"] == ["fb"]
    assert set(fb) == {"z_i", "x_i"} and all(d["in_min_ps"] == g for d in fb.values())
    s = gen_phys.sdc(P, "fb", gen_phys.type_pins(P, "fb"))
    fallback = f"set_input_delay -min {gen_phys.hold_in_min_ps(P):.4f} -clock vclk $non_clk_in"
    per_port = f"set_input_delay -min {g:.4f} -clock vclk [get_ports {{x_i[*] z_i[*]}}]"
    assert fallback in s and per_port in s and s.index(fallback) < s.index(per_port)   # later command wins
    ctx = sdc_lint.kit_context(P, "fb")
    assert ctx["hold_in_min_ports_ps"] == {"x_i": g, "z_i": g}
    assert sdc_lint.lint(s, **ctx) == []
    tcl = gen_phys.io_hold_tcl(P, "fb")
    assert "proc ot_io_hold_apply {vclk}" in tcl and "[get_ports {x_i[*] z_i[*]}]" in tcl


def test_env_opt_in(monkeypatch):
    monkeypatch.setenv("OT_IO_HOLD", "sender_min")
    assert gen_phys.io_hold_mode(_plan()) == "sender_min"
    monkeypatch.setenv("OT_IO_HOLD", "bogus")
    with pytest.raises(ValueError):
        gen_phys.io_hold_mode(_plan())
    assert gen_phys.io_hold_mode(_plan("legacy")) == "legacy"            # plan key wins over env


def test_signed_view_guarantee_and_channel_fallback():
    raw = copy.deepcopy(PAIR)
    raw.setdefault("clock", {})["io_hold"] = "sender_min"
    raw["partition_types"]["fa"].setdefault("clock", {})["out_hold_guarantee_ps"] = 48.0
    P = schema.Plan(raw)
    fb = gen_phys.input_hold_min(P, "fb")
    assert fb["x_i"]["in_min_ps"] == 48.0 and fb["x_i"]["basis"] == "signed view fa"
    raw["die"]["channels"] = [dict(id="c0", between=["pfa", "pfb"], ports=["x"])]
    P = schema.Plan(raw)
    assert set(gen_phys.input_hold_min(P, "fb")) == {"z_i"}             # x through a die channel -> fallback


def test_lint_per_port_limit():
    P = _plan("sender_min")
    s = gen_phys.sdc(P, "fb", gen_phys.type_pins(P, "fb"))
    ctx = sdc_lint.kit_context(P, "fb")
    relaxed = s.replace("set_input_delay -min 12.5000 -clock vclk [get_ports {x_i[*] z_i[*]}]",
                        "set_input_delay -min 30.0000 -clock vclk [get_ports {x_i[*] z_i[*]}]")
    assert any("x_i min input delay 30" in e for e in sdc_lint.lint(relaxed, **ctx))
    legacy_ctx = {k: v for k, v in ctx.items() if k != "hold_in_min_ports_ps"}
    assert any("relaxed" in e for e in sdc_lint.lint(s, **legacy_ctx))   # a legacy context refuses A's SDC
    bad = dict(ctx, hold_in_min_ports_ps={"nope": 12.5})
    assert any("not an input port" in e for e in sdc_lint.lint(s, **bad))


def test_signoff_overlay_per_port():
    base = signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind")
    assert base == signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind", hold_in_min_ports={})
    t = signoff.session_tcl("ff", [], "x.spef", ff_vclk="rebind", hold_in_min_ports={"x_i": 12.5, "z_i": 12.5})
    i0 = t.index("set_input_delay -min [expr {-40}] ")
    i1 = t.index("set_input_delay -min 12.5 -clock [lindex $so_vclk 0] [get_ports {x_i[*] z_i[*]}]")
    assert i0 < i1 and "@IN_MIN_PORTS@" not in t


def test_kit_files_and_hold_gate_hook():
    hg = (HERE / "hold_gate.tcl").read_text()
    assert hg.index("set_input_delay -min $hg_in") < hg.index("ot_io_hold_apply")
    P = _plan("sender_min")
    with tempfile.TemporaryDirectory() as d:
        gen_phys.write_type_kit(P, "fb", d, [])
        kd = Path(d) / "fb"
        assert (kd / "io_hold.tcl").exists()
        assert json.loads((kd / "sdc_lint.json").read_text())["hold_in_min_ports_ps"] == {"x_i": 12.5, "z_i": 12.5}
        assert sdc_lint.lint_kit_files(kd) == []
    with tempfile.TemporaryDirectory() as d:
        gen_phys.write_type_kit(_plan(), "fb", d, [])
        assert not (Path(d) / "fb" / "io_hold.tcl").exists()


# ------------------------------------------------------------------------------------------- parent related-pair check
def _sta(hold_ff, pairs_ff=30.0, neg=0, nopath=False):
    seam = dict(paths=10, worst=hold_ff, neg=neg, tns=min(0.0, hold_ff), launch="10", capture="20",
                start="u_a/q", end="u_b/d")
    corners = {}
    for c in ("TT", "FF"):
        seams = {"pfa->pfb/x_i": {"max": dict(seam, worst=100.0, neg=0, tns=0.0), "min": None if nopath else seam},
                 "pfa->pfb/z_i": {"max": dict(seam, worst=100.0, neg=0, tns=0.0), "min": dict(seam, worst=20.0, neg=0, tns=0)},
                 "pfb->pfa/r_i": {"max": dict(seam, worst=100.0, neg=0, tns=0.0), "min": dict(seam, worst=20.0, neg=0, tns=0)}}
        ps = {g: dict(n=4, max=pairs_ff, min=-5.0, max_pair=["a", "b"], min_pair=["a", "b"], p99=pairs_ff, over=0,
                      crpr_hold=2.0, crpr_setup=1.0, max_cppr=pairs_ff - 2.0, min_cppr=-4.0) for g in seams}
        corners[c] = dict(exit=0, seams=seams, pairskew=ps)
    return dict(mode="flat", corners=corners, period_ps=833,unc_setup_ps=60,unc_hold_ps=25,spine="tree",instances={"pfa":PAIR["partition_types"]["fa"]["module"],"pfb":PAIR["partition_types"]["fb"]["module"]},
                view_evidence={t["module"]:dict(kind="real",spef_present=True,netlist_sha256="fixture",spef_sha256="fixture")
                               for t in PAIR["partition_types"].values()})


def test_parent_check_pass_fail_and_coverage():
    P = _plan("sender_min")
    r = io_hold_parent.check(P, _sta(5.0))
    assert r["verdict"] == "PASS" and r["counts"]["a_ports"] == 3 and r["counts"]["fail"] == 0
    r = io_hold_parent.check(P, _sta(-3.0, neg=7))
    assert r["verdict"] == "FAIL" and r["counts"]["fail"] == 1
    row = next(x for x in r["ports"] if x["port"] == "x")
    assert row["hold_ff_ps"] == -3.0 and row["neg"] == 7 and row["status"] == "FAIL"
    r = io_hold_parent.check(P, _sta(5.0, pairs_ff=120.0))
    assert r["verdict"] == "FAIL"                                            # related pair skew (CPPR) > 80
    r = io_hold_parent.check(P, _sta(5.0, nopath=True))
    assert r["verdict"] == "INCOMPLETE" and r["counts"]["not_timed"] == 1    # A port not timed: kit does not count


def test_parent_check_cli(tmp_path):
    (tmp_path / "plan.json").write_text(json.dumps(dict(PAIR, clock=dict(PAIR.get("clock", {}), io_hold="sender_min"))))
    (tmp_path / "die_sta.json").write_text(json.dumps(_sta(5.0)))
    p = subprocess.run([sys.executable, str(HERE / "io_hold_parent.py"), str(tmp_path / "plan.json"),
                        str(tmp_path / "die_sta.json"), "--out", str(tmp_path / "r.json")], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    assert json.loads((tmp_path / "r.json").read_text())["verdict"] == "PASS"


def test_parent_check_all_seams_without_plan():
    r = io_hold_parent.check(None, _sta(5.0), all_seams=True)
    assert r["verdict"] == "PASS" and r["counts"]["a_ports"] == 3
    with pytest.raises(ValueError):
        io_hold_parent.check(None, dict(_sta(5.0), mode="etm"), all_seams=True)


def test_parent_check_requires_pair_skew():
    sta = _sta(5.0)
    for c in sta["corners"].values():
        c.pop("pairskew")
    r = io_hold_parent.check(None, sta, all_seams=True)
    assert r["verdict"] == "INCOMPLETE" and r["counts"]["not_timed"] == 3
