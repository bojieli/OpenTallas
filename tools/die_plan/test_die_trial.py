"""die_trial.py: build smoke on the tiny plan (no OpenROAD) + hop-table helpers."""
import gzip
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as D  # noqa: E402


def test_build_tiny(tmp_path):
    D.main(["build", str(HERE / "examples" / "tiny_plan.json"), "--out", str(tmp_path)])
    b = json.loads((tmp_path / "build.json").read_text())
    assert b["parts"] == 4 and b["data"]["nets"] > 0
    assert b["clock"]["taps"] == len(json.loads((tmp_path / "clock_tree.json").read_text())["taps"])
    rows = gzip.open(tmp_path / "nets.tsv.gz", "rt").read().splitlines()[1:]
    ft = [r.split("\t") for r in rows if r.split("\t")[1] == "ft"]
    # every ft hop has exactly one launch register and >= 1 capture register
    assert ft and all(r[4] and ";" not in r[4] and r[5] for r in ft)
    lef = next((tmp_path / "abstracts").glob("tq_*mid*.lef")).read_text()
    assert "fx_s0_d[0]" in lef and "fx_s0_q[0]" in lef


def test_interp_and_reach():
    rows = [(0, 700.0, 10.0, 60.0), (1000, 100.0, 50.0, 600.0), (2000, -500.0, 90.0, 1200.0)]
    assert D.interp(rows, 500, 1) == 400.0
    assert D.interp(rows, 3000, 1) == -1100.0
    assert abs(D.reach_of(rows) - 1166.7) < 0.1


def test_seam_tree_keeps_related_seam_deep():
    # two 2-tile clusters side by side; the heavy related seam runs between the stacked tiles of each cluster: no cut
    # may separate a heavy pair before the leaves (their common node is deep), and the root cut costs nothing
    taps = []
    for cx in range(2):
        for ty in range(2):
            for i in range(2):
                for j in range(4):
                    taps.append((f"c{cx}_t{ty}", f"k{i}{j}", cx * 1000 + 250 + 500 * i, ty * 2000 + 250 + 500 * j))
    idx = {(t[0], t[1]): k for k, t in enumerate(taps)}
    w = {}
    for cx in range(2):
        for i in range(2):
            a, b = idx[(f"c{cx}_t0", f"k{i}3")], idx[(f"c{cx}_t1", f"k{i}0")]
            w[(min(a, b), max(a, b))] = 1000
    nodes, leaf_of, cuts = D.seam_tree_geom(taps, w, window=0.5)
    assert cuts[0]["weight"] == 0
    assert sorted(leaf_of) == list(range(len(taps)))

    def anc(n):
        out = []
        while n is not None:
            out.append(n)
            n = nodes[n][1]
        return out
    for (a, b) in w:
        common = next(n for n in anc(leaf_of[a]) if n in set(anc(leaf_of[b])))
        assert nodes[common][4] >= 2


def test_branch_pads_telescope():
    import clock_pad_probe as CP
    d = dict(parent={"r": None, "a": "r", "b": "r", "t1": "a", "t2": "a", "t3": "b"},
             taps=[dict(inst="t1"), dict(inst="t2"), dict(inst="t3")])
    arr = {"t1/CLK": 100.0, "t2/CLK": 60.0, "t3/CLK": 20.0}
    pads = CP.branch_pads(d, arr, 100.0, 20.0)
    assert pads == {("a", "t2"): 2, ("r", "b"): 4}
