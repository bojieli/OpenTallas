"""CORES-HBM-1 11-12: views_b2r2 recipe lookup matches gen_core_kit_hbm (recipes_b2.json first, top fallback)."""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _plan(tmp, module):
    pins = tmp / "cores" / f"{module}.json"
    pins.parent.mkdir(parents=True, exist_ok=True)
    pins.write_text(json.dumps([{"name": "a", "layer": "M4", "x": 0.0, "y": 1.0}]))
    plan = tmp / "die_plan.json"
    plan.write_text(json.dumps({"partitions": [{"type": "t0"}], "partition_types": {"t0": {"hard_cores": [
        {"inst": "u0", "module": module, "outline_um": [10, 10], "pins_file": f"cores/{module}.json"}]}}}))
    return plan


def _view(tmp, module):
    out = tmp / "views.json"
    subprocess.run([sys.executable, str(HERE / "views_b2r2.py"), "--plan", str(_plan(tmp, module)), "--out", str(out)],
                   check=True, capture_output=True)
    return json.loads(out.read_text())["view_list"][0]


def test_recipes_b2_module_has_no_no_recipe(tmp_path):
    b2 = json.loads((HERE / "recipes_b2.json").read_text())
    assert "ot_svgr_top" in b2
    v = _view(tmp_path, "ot_svgr_top")
    assert "NO_RECIPE" not in v["blockers"]
    assert "ot_svgr_top" in v["recipe_keys"]


def test_unknown_module_still_no_recipe(tmp_path):
    v = _view(tmp_path, "ot_no_such_module_xyz")
    assert v["blockers"] == ["NO_RECIPE"]
    assert v["recipe_keys"] == []


def test_by_top_fallback_like_generator(tmp_path):
    # ot_hbm_idx_tail_native has no recipe keyed by its name; its split-piece recipes share one build content
    v = _view(tmp_path, "ot_hbm_idx_tail_native")
    assert "NO_RECIPE" not in v["blockers"]
    assert v["recipe_keys"] and v["recipe_keys"][0].startswith("ot_hbm_idx_score_quarter_static__tail")
