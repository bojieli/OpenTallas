"""Tests for tools/die_plan/obs_sync.py (OBS-SYNC-1): plan blockage ceiling and size against the real LEF."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import obs_sync as osy  # noqa: E402
import route_supply as rs  # noqa: E402


def lef(path, name, w, h, obs, pin_layers=("M5",)):
    """obs = {layer: area fraction}; one full-width strip per layer."""
    o = "".join(f"    LAYER {L} ;\n      RECT 0 0 {w} {h * f} ;\n" for L, f in obs.items())
    pins = "".join(f"  PIN p{i}\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER {L} ;\n        RECT 1 1 1.1 1.1 ;\n"
                   f"    END\n  END p{i}\n" for i, L in enumerate(pin_layers))
    obs_blk = f"  OBS\n{o}  END\n" if obs else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"MACRO {name}\n  CLASS BLOCK ;\n  SIZE {w} BY {h} ;\n{pins}{obs_blk}END {name}\nEND LIBRARY\n")


def test_facts_split_pin_and_obs_shapes(tmp_path):
    lef(tmp_path / "a.lef", "a", 100, 100, {"M1": 1, "M2": 1, "M5": 0.6, "M6": 0.03}, pin_layers=("M5", "M6"))
    f = osy.lef_facts(tmp_path / "a.lef")
    assert f["size"] == [100.0, 100.0]
    assert f["obs_top"] == "M5"          # wall: > 50%
    assert f["obs_ceil"] == "M5"         # M6 at 3% is a sliver, not a ceiling
    assert f["obs_any_top"] == "M6"
    assert f["pin_layers"] == {"M5": 1, "M6": 1}
    assert f["obs"]["M6"] == 0.03        # the pin rects were not counted as blockage


def test_lef_without_obs_block(tmp_path):
    lef(tmp_path / "n.lef", "n", 100, 100, {})
    f = osy.lef_facts(tmp_path / "n.lef")
    assert f["obs"] == {} and f["obs_top"] is None


def test_classify_classes(tmp_path):
    f6 = osy.lef_facts(_mk(tmp_path, "f6", {"M1": 1, "M5": 1, "M6": 1}))
    f5 = osy.lef_facts(_mk(tmp_path, "f5", {"M1": 1, "M5": 1}))
    fp = osy.lef_facts(_mk(tmp_path, "fp", {"M1": 1, "M2": 1, "M3": 0.6, "M5": 0.3}))
    fn = osy.lef_facts(_mk(tmp_path, "fn", {}))
    h = {"module": "x", "obs_max": "M5", "outline_um": [100, 100]}
    assert osy.classify(h, "signed", f6) == ["under-modelled"]
    assert osy.classify(h, "signed", f5) == []
    assert osy.classify(dict(h, obs_max="M6"), "signed", f5) == ["over-modelled"]
    assert osy.classify(h, "signed", fp) == ["porous"]
    assert osy.classify(h, "signed", fn) == ["LEF-missing-OBS"]
    assert osy.classify(dict(h, obs_max=None), "signed", f6) == ["under-modelled"]      # default ceiling M5
    assert "size-mismatch" in osy.classify(dict(h, outline_um=[100, 150]), "signed", f5)
    assert osy.classify(dict(h, outline_um=[100, 100.01]), "signed", f5) == []
    assert osy.classify(h, "no-lef", None) == ["no-lef"]
    assert osy.classify(h, "template-only", f6) == ["template-only"]


def _mk(tmp, name, obs):
    lef(tmp / f"{name}.lef", name, 100, 100, obs)
    return tmp / f"{name}.lef"


def _repo(tmp, core_obs, plan_obs_max="M5", plan_lef=None):
    """repo with one die 'tst': core 'c' (LEF at physical/ref_tile/c/c.lef), optional plan lef."""
    lef(tmp / "physical/ref_tile/c/c.lef", "c", 40, 40, core_obs)
    hc = {"inst": "u_c", "module": "c", "origin_um": [0, 0], "outline_um": [40, 40], "obs_max": plan_obs_max}
    if plan_lef:
        hc["lef"] = plan_lef
    (tmp / "physical/die_plan/tst").mkdir(parents=True)
    P = {"die": {"name": "tst"}, "partition_types": {"t": {"outline_um": [100, 100], "hard_cores": [hc]}}}
    (tmp / "physical/die_plan/tst/die_plan.json").write_text(json.dumps(P))
    return P


def test_repo_lef_found_by_module_name_when_plan_has_no_lef(tmp_path):
    P = _repo(tmp_path, {"M1": 1, "M2": 1, "M3": 1, "M4": 1, "M5": 1, "M6": 1})
    h = P["partition_types"]["t"]["hard_cores"][0]
    assert osy.lef_ceiling_for(h, "tst", tmp_path) == "M6"
    Q = osy.apply_lef_ceilings(P, "tst", tmp_path)
    assert Q["partition_types"]["t"]["hard_cores"][0]["obs_max"] == "M6"
    assert P["partition_types"]["t"]["hard_cores"][0]["obs_max"] == "M5"      # input untouched


def test_template_lef_is_not_truth(tmp_path):
    P = _repo(tmp_path, {f"M{k}": 1 for k in range(1, 8)})      # whole-block M1-M7 = template
    h = P["partition_types"]["t"]["hard_cores"][0]
    assert osy.lef_ceiling_for(h, "tst", tmp_path) is None


def test_sync_rewrites_plan_and_leaves_lefless_alone(tmp_path):
    _repo(tmp_path, {"M1": 1, "M5": 1, "M6": 1})
    osy.PLAN_OF_RECORD["tst"] = "physical/die_plan/tst/die_plan.json"
    try:
        assert osy.write_sync("tst", tmp_path, False) == [("t", "u_c", "M5", "M6")]
        assert json.loads((tmp_path / "physical/die_plan/tst/die_plan.json").read_text())["partition_types"]["t"][
            "hard_cores"][0]["obs_max"] == "M5"                                  # dry run
        osy.write_sync("tst", tmp_path, True)
        assert json.loads((tmp_path / "physical/die_plan/tst/die_plan.json").read_text())["partition_types"]["t"][
            "hard_cores"][0]["obs_max"] == "M6"
        assert osy.write_sync("tst", tmp_path, True) == []                       # idempotent
    finally:
        osy.PLAN_OF_RECORD.pop("tst")


def test_route_supply_macro_view_uses_repo_lef_not_plan_ceiling(tmp_path):
    P = _repo(tmp_path, {"M1": 1, "M2": 1, "M3": 0.6, "M4": 0.4, "M5": 0.3})
    h = P["partition_types"]["t"]["hard_cores"][0]
    rs.REF_DIRS[:] = []
    cfg = dict(rs.DEFAULTS, template_cap_obs_max=True, views={}, kit_views={}, signed_modules=None)
    die_dir = tmp_path / "physical/die_plan/tst"
    obs, kind, src, prov = rs.macro_view(h, die_dir, tmp_path, cfg)
    assert src == "repo-lef" and obs["M3"] == 0.6 and obs["M5"] == 0.3 and "M6" not in obs
    obs, kind, src, prov = rs.macro_view(h, die_dir, tmp_path, dict(cfg, lef_by_module=False))
    assert src == "plan-obs_max" and obs["M3"] == 1.0                           # old model: the ceiling


def test_route_supply_under_modelled_m6_wall(tmp_path):
    """S81 coll_lane case: plan obs_max M5, the LEF blocks M6 too -> M6 is not free over the core."""
    P = _repo(tmp_path, {f"M{k}": 0.99 for k in range(1, 7)})
    h = P["partition_types"]["t"]["hard_cores"][0]
    rs.REF_DIRS[:] = []
    cfg = dict(rs.DEFAULTS, template_cap_obs_max=True, views={}, kit_views={}, signed_modules=None)
    obs, kind, src, _ = rs.macro_view(h, tmp_path / "physical/die_plan/tst", tmp_path, cfg)
    assert obs["M6"] > 0.9 and kind == "core"


def test_route_supply_pin_only_contract_lef_is_not_a_free_core(tmp_path):
    """norm_finish case: the plan lef has no OBS block; the model must not treat M2-M7 as free over the core."""
    P = _repo(tmp_path, {}, plan_lef="physical/ref_tile/c/c.lef")
    h = P["partition_types"]["t"]["hard_cores"][0]
    rs.REF_DIRS[:] = []
    cfg = dict(rs.DEFAULTS, template_cap_obs_max=True, views={}, kit_views={}, signed_modules=None)
    die_dir = tmp_path / "physical/die_plan/tst"
    obs, kind, src, _ = rs.macro_view(h, die_dir, tmp_path, cfg)
    assert src == "plan-obs_max" and obs["M5"] == 1.0 and kind == "core"
    obs, kind, src, _ = rs.macro_view(h, die_dir, tmp_path, dict(cfg, lef_by_module=False))
    assert src == "plan-lef" and obs == {}                                      # old model: nothing blocked


def test_sync_lowers_only_on_request(tmp_path):
    _repo(tmp_path, {"M1": 1, "M5": 1}, plan_obs_max="M7")
    osy.PLAN_OF_RECORD["tst"] = "physical/die_plan/tst/die_plan.json"
    try:
        assert osy.write_sync("tst", tmp_path, True) == []                         # LEF M5 < plan M7: left alone
        assert osy.write_sync("tst", tmp_path, True, lower=True) == [("t", "u_c", "M7", "M5")]
    finally:
        osy.PLAN_OF_RECORD.pop("tst")
