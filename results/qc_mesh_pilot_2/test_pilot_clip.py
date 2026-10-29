"""QC-MESH-PILOT-2 clip tests on the committed QC-MESH-PILOT-1 trial tA3 (pilot.json + GRT tree).
run: python3 -m pytest -q results/qc_mesh_pilot_2/test_pilot_clip.py"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pilot_clip as PC   # noqa: E402

TRIAL = HERE.parent / "qc_mesh_pilot_1" / "trials" / "tA3"


def _build(tmp):
    for c in PC.CLIPS:
        PC.build(str(TRIAL), c, str(tmp / c), 0.4)
    return {c: json.load(open(tmp / c / "clip.json")) for c in PC.CLIPS}


def test_every_tree_net_in_exactly_one_clip_and_cells_inside(tmp_path):
    J = json.load(open(TRIAL / "pilot.json"))
    S = _build(tmp_path)
    tree = sorted(n for n, v in J["nets"].items() if v["kind"] == "tree")
    got = sorted(n for s in S.values() for n in s["nets"] if n != "n_in")
    assert got == tree
    for s in S.values():
        x0, y0, x1, y1 = s["rect"]
        assert all(abs(v / PC.G - round(v / PC.G)) < 1e-6 for v in s["rect"])      # 8.64-um grid: tracks/sites align
        for c in s["cells"]:
            cc = J["cells"][c]
            assert x0 <= cc["x"] and cc["x"] + PC.WID[cc["master"]] <= x1 and y0 <= cc["y"] <= y1
        d = (tmp_path / s["clip"] / "clip.def").read_text()
        assert "NONDEFAULTRULE CK4W" in d and "+ FIXED M9" in d       # mesh strap = fixed wiring, DRT routes the pin stacks
    assert all(len(S[f"c{i}"]["mesh_drivers"]) == 8 for i in range(4))


def test_compose_reproduces_full_tree(tmp_path):
    """clip trees cut from the full GRT tree (entry-relative offsets) must compose back to it exactly."""
    S = _build(tmp_path)
    F = PC.read_tree(TRIAL / "tree_grt_TT.txt")
    for c, s in S.items():
        with open(tmp_path / c / "tree_grt_TT.txt", "w") as fh:
            sh = 0.0 if c == "mid" else 100.0          # clip-local time origin differs; compose must remove it
            for n in s["cells"]:
                for p, (a, b, sl) in F.get(n, {}).items():
                    fh.write(f"{p} {n} {a - (F[s['entry']]['A'][0] - sh if s['entry'] else 0)} "
                             f"{b - (F[s['entry']]['A'][1] - sh if s['entry'] else 0)} {sl}\n")
    T = tmp_path / "trial"
    T.mkdir()
    shutil.copy(TRIAL / "pilot.json", T)
    shutil.copy(TRIAL / "tree_grt_TT.txt", T)
    PC.compose(str(T), str(tmp_path), "grt", "TT", str(tmp_path / "out.txt"))
    O = PC.read_tree(tmp_path / "out.txt")
    for n, v in O.items():
        for p, (a, b, _) in v.items():
            if abs(F[n][p][0]) == float("inf"):      # mesh driver Y: timing disabled (the mesh is timed by the MC)
                continue
            assert abs(a - F[n][p][0]) < 1e-3 and abs(b - F[n][p][1]) < 1e-3, (n, p)
    J = json.load(open(TRIAL / "pilot.json"))
    assert all(d in O for d in J["geom"]["drivers"])
