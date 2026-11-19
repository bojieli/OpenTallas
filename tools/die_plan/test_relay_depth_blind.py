"""RELAY-DEPTH-BLIND 11-19 (FABLE-FIX-S81-LEAF): cbc_pass ran relay_depth on the branch-applied plan in its work dir without
--repo / --plan-dir, so it measured 0 core-to-core paths on every type of every die and printed "0 relay rows" (S81 D8g:
395 types; 36 leaf types had a 203..980 um vsw -> vs link with no station).
    python3 -m pytest -q tools/die_plan/test_relay_depth_blind.py"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cbc_pass as CP  # noqa: E402
import relay_depth as RD  # noqa: E402

HC = [{"inst": "u_a", "pins_file": "a.json"}, {"inst": "u_b", "pins_file": "b.json"}]


def test_blind_types():
    plan = {"partition_types": {"seen": {"hard_cores": HC}, "norepo": {"hard_cores": HC}, "nopins": {"hard_cores": HC},
                                "one": {"hard_cores": HC[:1]}, "nolinks": {"hard_cores": HC}, "err": {"hard_cores": HC}}}
    reports = [dict(type="seen", paths_measured=37, paths_traced=120, skipped_no_pins=0),
               dict(type="norepo", paths_measured=0, paths_traced=0, skipped_no_pins=0),       # trace found nothing at all
               dict(type="nopins", paths_measured=0, paths_traced=120, skipped_no_pins=37),    # pin files not found
               dict(type="one", paths_measured=0, paths_traced=0, skipped_no_pins=0),          # one core: nothing to measure
               dict(type="nolinks", paths_measured=0, paths_traced=9, skipped_no_pins=0),      # traced, no core-to-core link
               dict(type="err", error="no bound module x")]
    assert RD.blind_types(plan, reports) == ["norepo", "nopins"]


def test_cbc_pass_gives_relay_depth_the_tree_and_plan_dir(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(CP, "run_tool", lambda args, log: calls.append([str(a) for a in args]) or 0)
    plan = tmp_path / "src" / "physical" / "die_plan" / "x" / "plan.json"
    plan.parent.mkdir(parents=True)
    plan.write_text("{}")
    CP.relay_rows(str(plan), ".", str(tmp_path / "bound"), str(tmp_path / "work"), 405.0)
    depth = [c for c in calls if c[0].endswith("relay_depth.py")][0]
    assert depth[depth.index("--plan-dir") + 1] == str(plan.parent) and depth[depth.index("--repo") + 1] == str(tmp_path / "src")
    calls.clear()
    lone = tmp_path / "plan.json"                                           # a plan outside any source tree: no --repo, still a plan dir
    lone.write_text("{}")
    CP.relay_rows(str(lone), ".", str(tmp_path / "bound"), str(tmp_path / "work"), 405.0)
    depth = [c for c in calls if c[0].endswith("relay_depth.py")][0]
    assert "--repo" not in depth and depth[depth.index("--plan-dir") + 1] == str(tmp_path)


def test_schema_imports_its_siblings_in_isolated_mode():
    r = subprocess.run([sys.executable, "-I", "-c", "import runpy, sys; sys.argv = ['schema.py']; "
                        f"runpy.run_path({str(HERE / 'schema.py')!r}); import parent_id_straps"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
