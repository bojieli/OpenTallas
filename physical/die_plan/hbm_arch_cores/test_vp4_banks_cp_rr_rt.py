#!/usr/bin/env python3
"""Regression (CORES-HBM-1 11-12, COORD ruling on vp4_banks_cp): the hard DMA-back core is kitted at the bound RR_RT.

ot_hgi_dma_back_static_vp4_banks_cp is a hard view; a parent #(.RR_RT(80)) override cannot reach a hardened macro, so the
recipe params ARE the core's behaviour.  The recipe used to carry params {} (RR_RT 7 = the standalone default) while every
bound instance passes RR_RT 80 (= tools/hbm_die_v16/d4g_bank_latency.DMA_RR_RT_BUDGET, the compiler's
dma_min_drain_lag basis).  Checks: (1) every recipe of the module sets RR_RT = DMA_RR_RT_BUDGET; (2) every bound
instantiation in the repo's bind inputs uses that same value; (3) the face shell carries recipe params onto the core
instance (the kit top has no parameters of its own).
"""
import importlib.util, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODULE = "ot_hgi_dma_back_static_vp4_banks_cp"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def budget():
    return _load("d4g_bank_latency", ROOT / "tools/hbm_die_v16/d4g_bank_latency.py").DMA_RR_RT_BUDGET


def recipes():
    out = []
    for f in ("recipes_split.json", "recipes_other.json", "recipes.json"):
        p = ROOT / "physical/die_plan/hbm/cores/harden" / f
        if p.is_file():
            for k, r in json.loads(p.read_text()).items():
                if isinstance(r, dict) and r.get("top") == MODULE:
                    out.append((f, k, r))
    b2 = HERE / "recipes_b2.json"
    if b2.is_file():
        for k, r in json.loads(b2.read_text()).items():
            if isinstance(r, dict) and (k == MODULE or r.get("top") == MODULE):
                out.append(("recipes_b2.json", k, r))
    return out


def test_recipe_rr_rt_is_bound_budget():
    rr = budget()
    found = recipes()
    assert found, f"no recipe for {MODULE}"
    for f, k, r in found:
        assert int((r.get("params") or {}).get("RR_RT", 7)) == rr, (f, k, r.get("params"))


def test_bound_instances_match_recipe():
    rr = budget()
    pat = re.compile(MODULE + r"\s*#\(\s*\.RR_RT\((\d+)\)\s*\)")
    seen = 0
    for p in (ROOT / "physical/die_plan/hbm/bind").glob("*/inputs/*.sv"):
        for m in pat.finditer(p.read_text(errors="replace")):
            seen += 1
            assert int(m.group(1)) == rr, (str(p), m.group(0))
    assert seen, "no bound instantiation found (bind inputs moved?)"


def test_face_shell_carries_params():
    fs = _load("face_shell", HERE / "face_shell.py")
    widths = {"clk": 1, "x": 8, "y": 8}
    dirs = {"clk": "input", "x": "input", "y": "output"}
    keep, dropped, _ = fs.drop_plan(widths, dirs, {}, {"clk"})
    txt = fs.emit_shell(MODULE, MODULE + "__fcore", {"RR_RT": budget()}, widths, dirs, keep, {"clk"}, "clk")
    assert f"{MODULE}__fcore #(.RR_RT({budget()})) u_fcore" in txt, txt


if __name__ == "__main__":
    for n, f in sorted(globals().items()):
        if n.startswith("test_") and callable(f):
            f()
    print("PASS test_vp4_banks_cp_rr_rt")
