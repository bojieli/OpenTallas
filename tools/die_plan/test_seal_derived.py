"""STATION-MOVE-HELPER 11-24 (COORD flow review 78d6e61 fix 5): seal_derived.py, report only + --regen."""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen  # noqa: E402
import latpkg_check as LP  # noqa: E402
import seal_derived as SD  # noqa: E402

TINY = HERE / "examples" / "tiny_plan.json"


def setup(tmp_path):
    raw = json.loads(TINY.read_text())
    tree = tmp_path / "tree"
    dd = tree / "physical" / "die_plan" / "tiny"
    old = copy.deepcopy(raw); old["note"] = "11-16 plan"
    gen.write_latency(old, dd / "lat")                       # the c8 form: packages copied forward into the seal tree
    gen.write_latency(old, dd / "prep" / "x" / "lat")        # a prep snapshot: history, never touched
    plan = tmp_path / "bound.json"; plan.write_text(json.dumps(raw))
    return raw, tree, dd, plan


def test_latpkg_reported_then_regenerated(tmp_path):
    raw, tree, dd, plan = setup(tmp_path)
    lines, cnt = SD.run(tree, plan, do_schema=False, do_contract=False)
    assert cnt["latpkg"] == 2 and cnt["latpkg_stale"] == 2 and cnt["latpkg_regen"] == 0
    assert sum(x.startswith("WARN SEAL-LATPKG") for x in lines) == 2
    snap = (dd / "prep/x/lat/tiny_latency.json").read_text()
    lines, cnt = SD.run(tree, plan, regen=True, do_schema=False, do_contract=False)
    assert cnt["latpkg_regen"] == 2 and not [x for x in lines if x.startswith("WARN")]
    for n in ("tiny_latency.json", "tiny_lat_pkg.sv"):
        assert LP.read_package(dd / "lat" / n)["digest"] == gen.plan_digest(raw)
    assert (dd / "prep/x/lat/tiny_latency.json").read_text() == snap
    assert SD.run(tree, plan, regen=True, do_schema=False, do_contract=False)[1]["latpkg_stale"] == 0    # idempotent


def test_r8_folded_package_listed_not_rewritten(tmp_path):
    raw, tree, dd, plan = setup(tmp_path)
    js = dd / "lat" / "tiny_latency.json"
    j = json.loads(js.read_text()); j["r8"] = {"fold": {"folded": True}}; js.write_text(json.dumps(j))
    lines, cnt = SD.run(tree, plan, regen=True, do_schema=False, do_contract=False)
    assert cnt["latpkg_regen"] == 0 and any("R8-folded" in x for x in lines)


def test_tree_schema_older_than_plan(tmp_path):
    raw, tree, dd, plan = setup(tmp_path)
    td = tree / "tools" / "die_plan"; td.mkdir(parents=True)
    (td / "schema.py").write_text("def validate(raw):\n    return ['partition_types.mid.clock: unknown key tap_reset_split_rounds']\n")
    lines, cnt = SD.run(tree, plan, do_contract=False)
    assert cnt["schema_errors"] == 1 and any("SEAL-SCHEMA" in x and "tap_reset_split_rounds" in x for x in lines)
    (td / "schema.py").write_text("def validate(raw):\n    return []\n")
    assert SD.run(tree, plan, do_contract=False)[1]["schema_errors"] == 0


def test_contract_refusal_named(tmp_path, monkeypatch):
    import core_clock_contract as CC
    import gen_phys as GP
    raw, tree, dd, plan = setup(tmp_path)
    raw["partition_types"]["mid"]["hard_cores"] = [{"inst": "u_lane0", "module": "lane"}]
    raw["partition_types"]["mid"].setdefault("clock", {})["taps"] = [{"name": "t0", "kind": "core", "budget_owner": "SIGNED r251"}]
    monkeypatch.setattr(GP, "core_mean_contract_options", lambda P, tn, trial=False: dict(mean_contract=True, require_signed=True))

    def lt(P, tn, root=None, require_signed=True):
        raise CC.ContractError("lane_tt.lib: no SIGNED mean clock contract; ETM max_clock_tree_path is not a mean")
    monkeypatch.setattr(CC, "latency_table", lt)
    lines, bad, n = SD.contracts(raw, plan)
    assert (bad, n) == (1, 1) and "SEAL-CONTRACT mid" in lines[0] and "no SIGNED mean" in lines[0] and "t0" in lines[0]


def test_r8_recipe_dir_not_regenerated_plain(tmp_path):
    raw, tree, dd, plan = setup(tmp_path)
    (dd / "lat" / "run_lat_r8.sh").write_text("python3 tools/die_plan/gen.py latency ... --fold-r8\n")   # the S81 lat/ form
    lines, cnt = SD.run(tree, plan, regen=True, do_schema=False, do_contract=False)
    assert cnt["latpkg_regen"] == 0 and cnt["latpkg_stale"] == 2 and all("R8-folded" in x for x in lines if x.startswith("WARN"))
