"""die_trial --core-branch local (DIE-HEAD-6, COORD 10-28 02:23 ruling (a)): each partition's early core taps hang as a
local branch under that partition's own die leaf.  Checks on the synthetic spine_fishbone die of test_spine_fishbone:
the die tree over the partition taps is unchanged (same nodes, levels, leaves; local LCAs kept), every core tap leaf
hangs from its own partition's leaf, the plan-computed pads deliver each core tap early_ps before the partition tap
within half a pad stage (model), and the default (no --core-branch) kit is byte-identical to a run without the flag."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as T  # noqa: E402
import gen_phys  # noqa: E402

CORE = [("clk_c0", -177.0, -186.0, 5.24), ("clk_c1", 177.0, -186.0, 5.24), ("clk_c2", -177.0, 186.0, 5.24),
        ("clk_c3", 177.0, 186.0, 5.24), ("clk_c4", 7.0, 526.0, 0.0)]


def _plan():
    parts = {f"sp{k}": dict(type="spn", origin_um=[900.0, 1000.0 + 2000.0 * k]) for k in range(3)}
    types = {"spn": dict(outline_um=[200.0, 2000.0]), "tile": dict(outline_um=[700.0, 1000.0])}
    taps = []
    for k in range(3):
        y = 2000.0 + 2000.0 * k
        taps.append((f"sp{k}", "clk", 1000.0, y))
        for j in range(4):
            for side in (-1, 1):
                for row, dy in (("o", 350.0), ("b", -680.0)):
                    n = f"t{'EW'[side < 0]}{k}{row}{j}"
                    parts[n] = dict(type="tile", origin_um=[0.0, 0.0])
                    x0, y0 = 1000.0 + side * (700.0 * (j + 1)), y + dy
                    taps.append((n, "clk", x0, y0))
                    taps += [(n, c, x0 + dx, y0 + dy2) for c, dx, dy2, _ in CORE]
    P = SimpleNamespace(clock={"spine": {"root_um": [1000.0, 4000.0]}}, parts=parts, types=types, W=4000.0, H=8000.0)
    return P, taps


def _patch(monkeypatch, taps, with_core=True):
    keep = taps if with_core else [t for t in taps if not t[1].startswith("clk_c")]
    monkeypatch.setattr(T, "clock_taps", lambda P: list(keep))
    monkeypatch.setattr(gen_phys, "core_tap_pins", lambda P, tn: [(c, 0.0, 0.0) for c, *_ in CORE] if tn == "tile" else [])
    monkeypatch.setattr(gen_phys, "core_tap_rows", lambda P, tn, corner="TT", pending=None:
                        [(c, "u_core", "clk", e, 250.0 + e) for c, _, _, e in CORE] if tn == "tile" else [])


def _kit(tmp, P, **kw):
    T.clock_kit(P, tmp, 600.0, 250.0, tree_form="spine_fishbone", **kw)
    return json.loads((Path(tmp) / "tree.json").read_text()), (Path(tmp) / "ctree.v").read_text()


def test_main_tree_unchanged_and_core_leaves_local(monkeypatch, tmp_path):
    P, taps = _plan()
    _patch(monkeypatch, taps, with_core=False)
    ref, _ = _kit(tmp_path / "ref", P)
    _patch(monkeypatch, taps)
    got, v = _kit(tmp_path / "cb", P, core_branch="local")
    main = {i: n for i, n in got["nodes"].items() if "core_branch" not in n}
    assert set(main) == set(ref["nodes"])
    for i, n in ref["nodes"].items():
        g = dict(main[i])
        g["kids"] = [k for k in g["kids"] if "core_branch" not in got["nodes"][str(k)]]
        assert g == n, i
    cb = got["meta"]["core_branch"]
    assert cb["parts"] == 48 and cb["core_taps"] == 240 and got["meta"]["levels"] == ref["meta"]["levels"] + 1
    node_of = {(t["part"], t["tap"]): t["node"] for t in got["taps"]}
    for (part, tap), i in node_of.items():
        if tap.startswith("clk_c"):
            nd = got["nodes"][str(i)]
            assert nd["core_branch"] == part and nd["parent"] == node_of[(part, "clk")]
    rows = json.loads((tmp_path / "cb" / "core_branch.json").read_text())["rows"]
    res = [r["residual_ps"] for r in rows if "residual_ps" in r]
    assert res and max(abs(r) for r in res) <= T.CORE_BRANCH_PAD_PS / 2 + 1e-6
    assert all(r["pads"] >= 1 for r in rows if r["tap"] == "own")   # the partition tap waits for its far cores
    assert cb["pad_cells"] == sum(r["pads"] for r in rows) and v.count("assign t_tE0o0__clk_c") == 5


def test_default_byte_identical(monkeypatch, tmp_path):
    P, taps = _plan()
    _patch(monkeypatch, taps)
    a = _kit(tmp_path / "a", P)
    b = _kit(tmp_path / "b", P, core_branch=None)
    assert a == b and "core_branch" not in a[0]["meta"] and not (tmp_path / "a" / "core_branch.json").exists()
    assert a[0]["meta"]["taps"] == len(taps)
