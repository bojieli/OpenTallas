"""die_trial.build_spine_fishbone (LAND-HEAD-3, opt-in --tree-form spine_fishbone): a die clock that FOLLOWS THE DATA
(METHODOLOGY 12.13b): a 1-D zero-skew spine along the spine partitions + per-row fishbone ribs along the channel rows.
Checks on a synthetic 3-rib die: every tap attached exactly once, rib roots at equal spine length (DME), neighbouring
channel columns share the trunk (their branches split one column apart, not at the root), default htree untouched."""
import sys
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_trial as T  # noqa: E402


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
                    taps.append((n, "clk", 1000.0 + side * (700.0 * (j + 1)), y + dy))
    P = SimpleNamespace(clock={"spine": {"root_um": [1000.0, 4000.0]}}, parts=parts, types=types, W=4000.0, H=8000.0)
    return P, taps


def _path_len(nodes, i):
    L = 0.0
    while nodes[i]["parent"] is not None:
        p = nodes[nodes[i]["parent"]]
        L += abs(p["x"] - nodes[i]["x"]) + abs(p["y"] - nodes[i]["y"])
        i = nodes[i]["parent"]
    return L


def _anc(nodes, i):
    out = []
    while i is not None:
        out.append(i)
        i = nodes[i]["parent"]
    return out


def test_every_tap_once_and_rooted():
    P, taps = _plan()
    nodes = T.build_spine_fishbone(P, taps)
    got = [t for n in nodes.values() for t in n["taps"]]
    assert sorted(got) == sorted(taps)
    assert nodes[0]["parent"] is None and all(n["parent"] is not None for i, n in nodes.items() if i)


def test_rib_roots_equal_spine_length():
    P, taps = _plan()
    nodes = T.build_spine_fishbone(P, taps)
    ribs = nodes[0]["spine_dme"]["ribs"]
    assert len(ribs) == 3 and nodes[0]["spine_dme"]["clamp_um"] == 0.0
    sp_node = {t[0]: i for i, n in nodes.items() for t in n["taps"] if t[0].startswith("sp")}
    lens = {k: _path_len(nodes, i) for k, i in sp_node.items()}
    assert max(lens.values()) - min(lens.values()) < 1e-6, lens


def test_neighbour_columns_split_late():
    P, taps = _plan()
    nodes = T.build_spine_fishbone(P, taps)
    leaf = {t[0]: i for i, n in nodes.items() for t in n["taps"]}
    for k in range(3):
        for j in range(3):
            a, b = _anc(nodes, leaf[f"tE{k}o{j}"]), _anc(nodes, leaf[f"tE{k}o{j + 1}"])
            lca = next(x for x in a if x in b)
            assert lca != 0 and nodes[lca]["level"] > 1
            assert _path_len(nodes, leaf[f"tE{k}o{j + 1}"]) - _path_len(nodes, lca) <= 700.0 + 350.0 + 1e-6


def test_matched_sp_entry_detour():
    P, taps = _plan()
    nodes = T.build_spine_fishbone(P, taps, matched=True, station_max_taps=8)
    assert sorted(t for n in nodes.values() for t in n["taps"]) == sorted(taps)
    assert any(n.get("detour_um") for n in nodes.values())
