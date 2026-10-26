"""OWNER 10-25 option B: strap gates wired into the KV core generator and the die constant-cell step."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import sdc_lint  # noqa: E402
import straps  # noqa: E402

GEN = REPO / "physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py"
TCL = REPO / "physical/common_flow/die_constant_cells.tcl"


def _gen():
    spec = importlib.util.spec_from_file_location("gen_core_kit_kv", GEN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CJ = {"port_decl": {"ck": ["input", 1], "strap_hid": ["input", 2], "strap_bsel": ["input", 2], "d": ["input", 8],
                    "q": ["output", 8]},
      "report": {"straps": [{"port": "strap_bsel", "kind": "id_strap"}, {"port": "cfg", "kind": "other"}]}}
HC = {"inst": "u_h", "straps": [{"port": "strap_hid", "width": 2, "value": "2'b01"}]}


def _lint(g, st):
    txt = g.sdc(833.0, 250.0, 40.0, ["ck"], [], "t", st)
    ins = ["strap_hid", "strap_bsel", "d"]
    return txt, sdc_lint.lint(txt, period_ps=833.0, insertion_ps=250.0, insertion_tol_ps=40.0, clock_ports=["ck"],
                              inputs=ins, outputs=["q"], unc_setup_ps=sdc_lint.POLICY_SETUP_PS,
                              unc_hold_ps=sdc_lint.POLICY_HOLD_PS, time_unit_ps=1.0,
                              io_floor_ps={p: g.IO_BUDGET * 833.0 for p in ins + ["q"]}, port_latency_ps={},
                              straps=st)


def test_kv_kit_straps_from_plan_and_core_json():
    g = _gen()
    assert g.kit_id_straps(HC, CJ) == ["strap_hid", "strap_bsel"]
    assert g.kit_id_straps({"inst": "u"}, {"port_decl": {}, "report": {}}) == []


def test_kv_kit_strap_must_be_input():
    g = _gen()
    cj = {"port_decl": {"strap_hid": ["output", 2]}, "report": {}}
    with pytest.raises(ValueError):
        g.kit_id_straps(HC, cj)


def test_kv_sdc_carries_false_path_and_lints_with_straps():
    g = _gen()
    st = g.kit_id_straps(HC, CJ)
    txt, err = _lint(g, st)
    assert "set_false_path -from [get_ports {strap_hid strap_bsel}]" in txt
    assert err == []
    txt0, err0 = _lint(g, [])          # no straps declared: no exception emitted, still clean
    assert "set_false_path" not in txt0 and err0 == []


def test_kv_sdc_without_false_path_fails_lint_when_straps_declared():
    g = _gen()
    txt = g.sdc(833.0, 250.0, 40.0, ["ck"], [], "t")
    err = sdc_lint.lint(txt, period_ps=833.0, insertion_ps=250.0, insertion_tol_ps=40.0, clock_ports=["ck"],
                        inputs=["strap_hid", "d"], outputs=["q"], io_floor_ps={}, port_latency_ps={},
                        straps=["strap_hid"])
    assert any("no set_false_path" in e for e in err)


def _hook_script(tmp, check=None, manifest=False, env=None):
    src = TCL.read_text()
    hook = src[src.index("proc ot_die_strap_ties"):]
    if check is not None:
        (tmp / "strap_ties_check.tcl").write_text(check)
    if manifest:
        (tmp / "bind_parent_id_straps.json").write_text("{}\n")
    (tmp / "t.tcl").write_text("proc wrap {} { source " + str(tmp / "hook.tcl") + " }\nwrap\n")
    (tmp / "hook.tcl").write_text(hook)
    return subprocess.run(["tclsh", str(tmp / "t.tcl")], cwd=tmp, capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", **(env or {})})


tcl_only = pytest.mark.skipif(subprocess.run(["which", "tclsh"], capture_output=True).returncode, reason="no tclsh")


@tcl_only
def test_hook_none_without_straps(tmp_path):
    r = _hook_script(tmp_path)
    assert r.returncode == 0 and "OT_STRAP_TIE NONE" in r.stdout


@tcl_only
def test_hook_fails_closed_when_manifest_without_check(tmp_path):
    r = _hook_script(tmp_path, manifest=True)
    assert r.returncode != 0 and "strap_ties_check.tcl is missing" in r.stderr


@tcl_only
def test_hook_sources_check_at_global_scope_inside_proc(tmp_path):
    ok = "set ot_strap_fail 0\nputs \"OT_STRAP_TIE PASS 2 bits 0 failed\"\n"
    r = _hook_script(tmp_path, check=ok)
    assert r.returncode == 0 and "OT_STRAP_TIE PASS" in r.stdout, r.stderr
    bad = "set ot_strap_fail 1\n"
    r = _hook_script(tmp_path, check=bad)
    assert r.returncode != 0 and "OT_STRAP_TIE FAIL" in r.stderr


@tcl_only
def test_hook_env_path_must_exist(tmp_path):
    r = _hook_script(tmp_path, env={"OT_STRAP_TIES_TCL": str(tmp_path / "nope.tcl")})
    assert r.returncode != 0 and "does not exist" in r.stderr


def test_generated_check_reports_through_hook_variable():
    t = straps.tie_check_tcl([("u_p", "strap_u_h__strap_hid", "2'b01")])
    assert "set ot_strap_fail 0" in t and "incr ot_strap_fail" in t
