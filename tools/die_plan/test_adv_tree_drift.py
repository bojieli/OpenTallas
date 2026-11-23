"""ADV-TREE-DRIFT: a bound tree's view / flow copies against main (fixture modeled on S81 J8 j8_cut_tree, 11-23).

Real positive: j8_cut_tree (forked 11-22 from d8j7_1117_work, main pin 3c913dbdfb) carries the pre-shadow
physical/ref_tile/s81coll_cfifo_crs4/views/dsfd_cfifo_crs4/ (main 31c7ccbd1b, 11-21, via-shadow OBS: the u_cf fix of
UCF-VIEW-FIX) and the QC / KV trees carry physical/common_flow/grt183_make.sh from before main f60d28bf6d (GRT-DPL-DIAMOND-1122).
The fixture builds a tiny git history with the same paths and subjects."""
import json
import os
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_tree_drift as A  # noqa: E402

VIEW = "physical/ref_tile/s81coll_cfifo_crs4/views/dsfd_cfifo_crs4"
LEF = f"{VIEW}/dsfd_cfifo_crs4.lef"
ABS = f"{VIEW}/abstract.json"
GRT = "physical/common_flow/grt183_make.sh"
NEWTCL = "physical/common_flow/grt_dpl_diamond.tcl"
BIND = "tools/die_plan/bind.py"
SVC = "rtl/dsrom_sys/s81_glue/ot_s81_rly.sv"


def _git(repo, *a):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True, env=env).stdout.strip()


def _write(root, rel, text):
    p = os.path.join(str(root), rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


def _commit(repo, files, msg):
    for rel, text in files.items():
        _write(repo, rel, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture()
def world(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, {LEF: "MACRO dsfd_cfifo_crs4\n OBS LAYER M4 ;\nEND\n", ABS: '{"obs": 1}\n', GRT: "#!/bin/bash\ngrt v1\n",
                   BIND: "# bind v1\n", SVC: "module ot_s81_rly; endmodule\n",
                   "tools/die_plan/porous_views_data/map.json": "{}\n"}, "S81 J7 base")
    pin = _commit(repo, {BIND: "# bind v2\n"}, "bind: v2 (the tree pin)")
    fix_view = _commit(repo, {LEF: "MACRO dsfd_cfifo_crs4\n OBS LAYER M4 SHADOW 4607 ;\nEND\n", ABS: '{"obs": 4607}\n'},
                       "Views: via shadow keeps 0.30 um inside the macro outline; dsfd_cfifo_crs4 view refinalized")
    fix_grt = _commit(repo, {GRT: "#!/bin/bash\ngrt v1\ndiamond dpl\n", NEWTCL: "# diamond\n"},
                      "GRT-DPL-DIAMOND-1122: GRT post-repair detailed_placement honours the kit diamond legalizer")
    _commit(repo, {BIND: "# bind v3\n"}, "bind: v3")
    # the event tree = main at the pin, plus an event-private edit of bind.py
    tree = tmp_path / "j8_cut_tree"
    for rel in (LEF, ABS, GRT, BIND, SVC, "tools/die_plan/porous_views_data/map.json"):
        _write(tree, rel, _git(repo, "show", f"{pin}:{rel}") + "\n")
    _write(tree, BIND, "# bind v2 + event-private change\n")
    (tree / "physical" / "die_plan" / "s81").mkdir(parents=True)
    (tree / ".fork.json").write_text(json.dumps({"src_main_sha": pin}))
    raw = {"die": "s81", "partition_types": {"s81_col_h10_x": {"hard_cores": [
        {"inst": "u_cf", "lef": LEF, "lib": f"{VIEW}/dsfd_cfifo_crs4_tt.lib", "pins_file": "inputs/core_pins/dsfd_cfifo_crs4.json"}],
        "sources": [SVC]}}}
    plan = tree / "physical" / "die_plan" / "s81" / "plan.json"
    plan.write_text(json.dumps(raw))
    return dict(repo=str(repo), tree=str(tree), raw=raw, plan=str(plan), fix_view=fix_view[:10], fix_grt=fix_grt[:10], pin=pin)


def _run(w, **kw):
    return A.findings(w["raw"], w["plan"], tree=w["tree"], main_repo=w["repo"], main_ref="main", **kw)


def test_positive_view_and_flow_lag(world):
    out = _run(world)
    assert all(x.startswith("WARN ADV-TREE-DRIFT ") for x in out)
    view = [x for x in out if x.startswith(f"WARN ADV-TREE-DRIFT view {VIEW}: LAG 2 file(s)")]
    assert view and world["fix_view"] in view[0] and "via shadow keeps 0.30 um" in view[0]
    flow = [x for x in out if x.startswith(f"WARN ADV-TREE-DRIFT flow {GRT}: LAG 1")]
    assert flow and world["fix_grt"] in flow[0] and "GRT-DPL-DIAMOND-1122" in flow[0]
    assert any("MISSING 1 view/porous/flow" in x and NEWTCL in x for x in out)
    s = out[-1]
    assert " summary: " in s and "LAG 3 (view 2, flow 1)" in s and "LOCAL 1 (tool 1)" in s     # bind.py: private edit
    assert world["fix_view"] + " x2" in s and "pin " + world["pin"][:10] in s
    # priority: view before flow before the MISSING line
    assert out.index(view[0]) < out.index(flow[0])


def test_no_pin_still_lag(world):
    os.remove(os.path.join(world["tree"], ".fork.json"))
    out = _run(world)
    assert any(x.startswith(f"WARN ADV-TREE-DRIFT view {VIEW}: LAG 2") for x in out)
    assert "pin -" in out[-1]


def test_synced_tree_is_clean(world):
    for rel in (LEF, ABS, GRT, NEWTCL, BIND):
        _write(world["tree"], rel, _git(world["repo"], "show", f"main:{rel}") + "\n")
    out = _run(world)
    assert len(out) == 1 and "LAG 0 (none)" in out[0] and "LOCAL 0," in out[0] and "MISSING 0 " in out[0]


def test_local_view_edit_is_counted_not_listed(world):
    _write(world["tree"], LEF, "MACRO dsfd_cfifo_crs4\n OBS private ;\nEND\n")
    out = _run(world)
    assert not any(x.startswith(f"WARN ADV-TREE-DRIFT view {VIEW}: LAG 2") for x in out)
    assert any(x.startswith(f"WARN ADV-TREE-DRIFT view {VIEW}: LAG 1") for x in out)      # abstract.json still lags
    assert "LOCAL 2 (view 1, tool 1)" in out[-1]


def test_never_raises(world, tmp_path):
    assert A.findings(None, "/nonexistent/plan.json", tree=str(tmp_path / "none")) == []
    out = A.findings(world["raw"], world["plan"], tree=world["tree"], main_repo=str(tmp_path / "norepo"), main_ref="nosuchref")
    assert all(x.startswith("WARN ADV-TREE-DRIFT") for x in out)


@pytest.mark.skipif(shutil.which("git") is None, reason="git")
def test_tree_inferred_from_plan_path(world):
    out = A.findings(world["raw"], world["plan"], main_repo=world["repo"], main_ref="main")
    assert any(f"view {VIEW}: LAG 2" in x for x in out)
