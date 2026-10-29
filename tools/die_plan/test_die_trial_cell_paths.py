"""DIE-S81-15 --cell-paths: physical cell paths without pads, so leg repeaters are tree-path nodes (start-tree retime at
the existing repeaters); netlist/placement unchanged, default byte-identical."""
import copy
import json
from types import SimpleNamespace
import die_trial as D
import trial_tap_arrivals as E


def nodes():
    # root at (10,10), one child 1000 um away (2 repeaters at rep 450), tap on the child
    return {0: dict(x=10., y=10., parent=None, level=0, kids=[1], region_root="A", taps=[]),
            1: dict(x=1010., y=10., parent=0, level=1, kids=[], taps=[("part", "ck", 1020., 20.)])}


def kit(tmp_path, monkeypatch, name, **kw):
    monkeypatch.setattr(D, "clock_taps", lambda p: [])
    monkeypatch.setattr(D, "build_htree", lambda *a, **k: copy.deepcopy(nodes()))
    out = tmp_path / name
    D.clock_kit(SimpleNamespace(W=2000., H=100.), out, 100., 450., **kw)
    return out


def test_default_unchanged_and_netlist_identical(tmp_path, monkeypatch):
    a = kit(tmp_path, monkeypatch, "a")
    b = kit(tmp_path, monkeypatch, "b", cell_paths=True)
    assert (a / "ctree.v").read_text() == (b / "ctree.v").read_text()
    ta, tb = json.loads((a / "tree.json").read_text()), json.loads((b / "tree.json").read_text())
    assert "driver" not in ta["taps"][0] and "node_stages" not in ta
    assert ta["sites"] == tb["sites"] and ta["parent_of"] == tb["parent_of"] and ta["nodes"] == tb["nodes"]
    t = tb["taps"][0]
    assert t["driver"] == "b1" and t["path"] == ["b0", "r1_0", "r1_1", "b1"] and t["stages_from_root"] == 4


def test_repeaters_become_tree_path_nodes(tmp_path, monkeypatch):
    out = kit(tmp_path, monkeypatch, "c", cell_paths=True)
    t = json.loads((out / "tree.json").read_text())
    arr = tmp_path / "arr.txt"
    arr.write_text("\n".join([f"N {c} {10 * (i + 1)} {9 * (i + 1)}" for i, c in enumerate(["b0", "r1_0", "r1_1", "b1"])] +
                             ["T t_part__ck 50 45 20"]) + "\n")
    res, miss = E.export(out / "tree.json", arr, "TT")
    assert miss == 0
    tp = res["taps"][0]["tree_path"]
    assert len(tp) == 4 and tp[0] == "h"
    # every prefix = one physical cell: root, repeater 0, repeater 1, child node
    assert [res["node_late_ps"][tp[:n]] for n in range(1, 5)] == [10, 20, 30, 40]
    # geometric (default) export has the root and the child node only
    g = kit(tmp_path, monkeypatch, "g")
    rg, _ = E.export(g / "tree.json", arr, "TT")
    assert sorted(rg["node_late_ps"].values()) == [10, 10, 40]   # root path + region key A + child


def test_cli_flag(tmp_path, monkeypatch):
    got = {}
    def write(*a, **k):
        got.update(k)
        return dict.fromkeys(("die", "parts", "types", "closed_views", "hard_cores", "clock_tree", "grt", "psm", "sta"))
    monkeypatch.setattr(D, "write_kit", write)
    D.main(["kit", "p.json", "--out", str(tmp_path / "k")])
    assert "cell_paths" not in got
    D.main(["kit", "p.json", "--out", str(tmp_path / "k"), "--cell-paths"])
    assert got["cell_paths"] is True


def test_node_cell_names_are_metadata_only(tmp_path, monkeypatch):
    out = kit(tmp_path, monkeypatch, "named", cell_paths=True)
    arr = tmp_path / 'arr_named.txt'
    arr.write_text('\n'.join([f'N {c} {10*(i+1)} {9*(i+1)}' for i,c in enumerate(['b0','r1_0','r1_1','b1'])] +
                             ['T t_part__ck 50 45 20'])+'\n')
    plain, missing = E.export(out/'tree.json', arr, 'TT')
    named, named_missing = E.export(out/'tree.json', arr, 'TT', node_cells=True)
    assert missing == named_missing == 0
    inventory = named.pop('node_cell')
    assert named == plain
    assert inventory == {'h':'b0','h0':'r1_0','h00':'r1_1','h000':'b1','A':'b0'}
