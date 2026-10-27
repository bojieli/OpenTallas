"""GEOM-24 PASS-COND on the HEAD mesh (head_mesh_r3 R17 symmetric tree): (a) sibling legs carry the same repeater
count at the same positions, (b) no doubled M9 straps, (c) a VIA89 at every M8 x M9 strap crossing."""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
import head_mesh_r3 as R  # noqa: E402

TREE = ROOT / "results" / "s81_head_r17" / "tree"


def nodes():
    return json.loads((TREE / "tree_nodes.json").read_text())


def test_r17_tree_siblings_equal_by_construction():
    N = nodes()
    assert R.sibling_rep_findings(N) == []
    by = {n["tag"]: n for n in N}
    reps = [s for s in R.sites_of(N) if s[0] == "rep"]
    # same positions: distance of every repeater from its parent, per family, is the same multiset on every sibling
    dist = {}
    for _, tag, xy in reps:
        n = by[tag]; p = by[n["parent"]]["xy"]
        dist.setdefault(n["parent"], {}).setdefault(tag, []).append(round(abs(xy[0] - p[0]) + abs(xy[1] - p[1]), 3))
    for fam in dist.values():
        assert len({tuple(sorted(v)) for v in fam.values()}) == 1
    assert len(reps) == json.loads((TREE / "head_mesh_r3.json").read_text())["tree"]["repeaters"]


def test_sibling_check_fails_closed():
    N = nodes()
    fam = next(n for n in N if len(n["kids"]) == 2)
    a = copy.deepcopy(N)
    k = next(n for n in a if n["tag"] == fam["kids"][0])
    k["nseg"] += 1                                   # one sibling with an extra repeater
    assert any("sibling (leg, nseg) differ" in f for f in R.sibling_rep_findings(a))
    b = copy.deepcopy(N)
    k = next(n for n in b if n["tag"] == fam["kids"][1])
    k["xy"] = [k["xy"][0] + 7.0, k["xy"][1] + 7.0]  # a dog-leg
    assert R.sibling_rep_findings(b)


def test_r17_mesh_no_doubled_m9_and_gates_recorded():
    J = json.loads((TREE / "head_mesh_r3.json").read_text())
    assert J["tree"]["sibling_reps"]["verdict"] == "PASS"
    assert J["mesh"]["m9_spacing"]["verdict"] == "PASS"
    x = sorted(s[1] for s in json.loads((TREE / "straps.json").read_text()) if s[0] == "M9")
    assert min(b - a for a, b in zip(x, x[1:])) >= 177.12 - 8.64


def test_r17_mesh_export_via89_every_crossing():
    M = json.loads((TREE / "mesh.json").read_text())
    S = json.loads((TREE / "straps.json").read_text())
    H = [s for s in S if s[0] == "M8"]; V = [s for s in S if s[0] == "M9"]
    cross = {(v[1], h[1]) for h in H for v in V
             if h[2] - 1e-6 <= v[1] <= h[3] + 1e-6 and v[2] - 1e-6 <= h[1] <= v[3] + 1e-6}
    assert cross and {tuple(p) for p in M["vias89"]} == cross
    assert M["meta"]["mesh_vias"] == {"None": len(cross)}
    assert len(M["strap_spans"]) == len(S)


def test_export_script_runs(tmp_path):
    for f in ("tree_nodes.json", "straps.json", "stubs.json"):
        (tmp_path / f).write_text((TREE / f).read_text())
    out = subprocess.run([sys.executable, str(ROOT / "tools/s81_head/head_mesh_export.py"), str(tmp_path),
                          "--pitch-from-straps"], capture_output=True, text=True, check=True).stdout
    assert "VIA89" in out
    assert json.loads((tmp_path / "mesh.json").read_text())["vias89"] == json.loads((TREE / "mesh.json").read_text())["vias89"]
