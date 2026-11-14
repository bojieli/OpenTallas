"""HARD-S81-SVC-1 11-13: the S81 svc memory closure runs in BOTH kit_rtl modes.

Class: the closure (generated MEM v2 macros for the svc native memories) was a line of the script-mode kit_rtl.sh.
The S81 wave moved to kit_rtl mode "bind" on 11-12 21:46 and lost it: 16 svc items failed GEN_LINT memory_bits.
"""
import json
import os
import re
import subprocess
from pathlib import Path

import kit_wave as KW

ROOT = Path(__file__).resolve().parents[2]
POST = ROOT / "tools/autopilot/kit_rtl_post.d/s81_svc_memory.sh"
WRAP = ROOT / "physical/die_plan/s81/kit_wave/kit_rtl_post.sh"
SCRIPT = ROOT / "physical/die_plan/s81/kit_wave/kit_rtl.sh"


def test_bind_mode_command_inlines_the_runtime_steps():
    c = KW.kit_rtl_post_cmd("svc_hi_dsdv_svc_rs__t1", "/w/a b", "/p/plan.json")
    # the step TEXT comes from the running kit_wave.py, not from a path in the wave source
    assert "for P in physical/die_plan" not in c
    assert "s81_svc_memory_closure.py --form v2 --kit-rtl" in c
    assert "TYPE=svc_hi_dsdv_svc_rs__t1 " in c and "OUT='/w/a b/rtl' " in c and "PLAN=/p/plan.json " in c
    src = (ROOT / "tools/autopilot/kit_wave.py").read_text()
    assert len(re.findall(r'--kit \{q\(W\)\}/rtl" \+ kit_rtl_post_cmd\(T, W, plan\)', src)) == 1


def test_frozen_source_without_the_step_still_runs_it(tmp_path):
    # SVC-BAND-3 class: a wave source that predates the step (no kit_rtl_post.sh, as S81 7073a6b4a5) must still run it.
    # cwd = an empty "source": the svc kit reaches the step, which fails closed (no closure tool), never passes silently.
    out = tmp_path / "w" / "rtl"
    out.mkdir(parents=True)
    (out / "kit_rtl.json").write_text(json.dumps({"bound_module": "s81p_svc_lo_dsdv_svc_rs__t2_bound"}))
    (out / "s81p_svc_lo_dsdv_svc_rs__t2_bound.sv").write_text(
        "    ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b0), .TROWS(640)) u (\n);\n")
    src = tmp_path / "src"
    src.mkdir()
    c = "true" + KW.kit_rtl_post_cmd("svc_lo_dsdv_svc_rs__t2", str(tmp_path / "w"), "x")
    r = subprocess.run(["bash", "-c", c], cwd=src, capture_output=True, text=True)
    assert r.returncode != 0
    # and a non-svc kit in the same empty source passes untouched
    (out / "kit_rtl.json").write_text(json.dumps({"bound_module": "s81p_ot_s81sl_leaf__t1_bound"}))
    r = subprocess.run(["bash", "-c", c], cwd=src, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_missing_step_dir_fails_the_stage(tmp_path):
    c = "true" + KW.kit_rtl_post_cmd("svc_hi_dsdv_svc_rs__t1", "/w", "x", steps_dir=tmp_path / "none")
    r = subprocess.run(["bash", "-c", c], capture_output=True, text=True)
    assert r.returncode != 0 and "KIT_RTL_POST" in r.stderr


def test_script_mode_uses_the_same_step():
    s = SCRIPT.read_text()
    assert 'bash "$HERE/kit_rtl_post.sh"' in s
    assert "s81_svc_memory_closure.py --form" not in s   # one copy of the recipe, in kit_rtl_post.sh
    assert "s81_svc_memory_closure.py --form v2 --kit-rtl" in POST.read_text()
    assert "kit_rtl_post.d/s81_svc_memory.sh" in WRAP.read_text()
    assert os.access(POST, os.X_OK) and os.access(WRAP, os.X_OK)


def run_post(out, typ, cwd):
    return subprocess.run(["bash", str(WRAP)], cwd=cwd, env=dict(os.environ, TYPE=typ, OUT=str(out), PLAN="x"),
                          capture_output=True, text=True)


def test_other_kits_are_untouched(tmp_path):
    (tmp_path / "kit_rtl.json").write_text(json.dumps({"bound_module": "s81p_ot_s81sl_leaf__t1_bound"}))
    before = sorted(p.name for p in tmp_path.iterdir())
    r = run_post(tmp_path, "ot_s81sl_leaf__t1", tmp_path)       # cwd without tools/: the closure must not be reached
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_missing_kit_rtl_json_fails(tmp_path):
    r = run_post(tmp_path, "svc_hi_dsdv_svc_rs__t1", tmp_path)
    assert r.returncode == 1 and "S81_KIT_RTL_POST" in r.stderr


def test_svc_kit_reaches_the_closure_and_fails_closed(tmp_path):
    # a svc bound with a behavioural staging memory and no closure tool in cwd: the step must FAIL, never pass through
    (tmp_path / "kit_rtl.json").write_text(json.dumps({"bound_module": "s81p_svc_hi_dsdv_svc_rs__t1_bound"}))
    (tmp_path / "s81p_svc_hi_dsdv_svc_rs__t1_bound.sv").write_text(
        "    ot_hdc_v41x_attn_staging #(.D(32), .NL(4), .SRAM_MACRO(1'b0), .TROWS(640)) u (\n);\n")
    r = run_post(tmp_path, "svc_hi_dsdv_svc_rs__t1", tmp_path)
    assert r.returncode != 0


def test_svc_bound_without_native_helpers_passes(tmp_path):
    # cwd = repo root (real closure tool): a bound that has no native helper set is NOT_APPLICABLE and stays as it is
    (tmp_path / "kit_rtl.json").write_text(json.dumps({"bound_module": "s81p_svc_hi_dsdv_svc_rs__t1_bound", "files": []}))
    b = tmp_path / "s81p_svc_hi_dsdv_svc_rs__t1_bound.sv"
    b.write_text("module s81p_svc_hi_dsdv_svc_rs__t1_bound; endmodule\n")
    r = run_post(tmp_path, "svc_hi_dsdv_svc_rs__t1", ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "S81_KIT_RTL_POST PASS" in r.stdout and "NOT_APPLICABLE" in r.stdout
    assert b.read_text() == "module s81p_svc_hi_dsdv_svc_rs__t1_bound; endmodule\n"


IRG = ROOT / "tools/autopilot/kit_rtl_post.d/s81_svc_pr_irg.sh"


def _irg_kit(tmp_path, pr, files=True):
    bm = "s81p_svc_lo_dsdv_svc_rs__t2_bound"
    (tmp_path / "kit_rtl.json").write_text(json.dumps({"bound_module": bm, "defines": ["OT_SVC_ALLQ"]}))
    (tmp_path / (bm + ".sv")).write_text(
        "    dsdv_idx_rg3_fit #(.DQR(24), .EL(140), .PR(%d), .SRAM_MACRO(1'b1)) u_u_irg_02 (\n);\n" % pr)
    (tmp_path / "kit_rtl.f").write_text(
        "a/dsdv_idx_rg2.sv\nb/ot_s81_svc_idx_hslice_fp.sv\nc/ot_hdc_v41x_idx_hslice_fp.sv\n" if files else "a/x.sv\n")


def _run_irg(tmp_path):
    return subprocess.run(["bash", str(IRG)], cwd=tmp_path, env=dict(os.environ, TYPE="t", OUT=str(tmp_path), PLAN="x"),
                          capture_output=True, text=True)


def test_irg_pr_adds_the_fastpad_defines(tmp_path):
    _irg_kit(tmp_path, 1)
    r = _run_irg(tmp_path)
    assert r.returncode == 0, r.stderr
    d = json.loads((tmp_path / "kit_rtl.json").read_text())["defines"]
    assert d == ["OT_SVC_ALLQ", "OT_IDX_HSLICE_FASTPAD", "OT_IDX_HSLICE_FP_CS"]
    r = _run_irg(tmp_path)                                   # idempotent
    assert json.loads((tmp_path / "kit_rtl.json").read_text())["defines"] == d


def test_irg_pr0_and_other_kits_untouched(tmp_path):
    _irg_kit(tmp_path, 0)
    before = (tmp_path / "kit_rtl.json").read_text()
    assert _run_irg(tmp_path).returncode == 0
    assert (tmp_path / "kit_rtl.json").read_text() == before


def test_irg_pr_without_fastpad_sources_fails(tmp_path):
    _irg_kit(tmp_path, 1, files=False)
    assert _run_irg(tmp_path).returncode != 0


def test_irg_step_runs_after_the_memory_closure():
    names = [p.name for p in sorted((ROOT / "tools/autopilot/kit_rtl_post.d").glob("*.sh"))]
    assert names.index("s81_svc_memory.sh") < names.index("s81_svc_pr_irg.sh")
