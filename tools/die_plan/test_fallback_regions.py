import json
import subprocess
import sys
from pathlib import Path

import fallback_regions as FR

HERE = Path(__file__).resolve().parent


def _plan():
    core = dict(outline_um=[10, 10], clock=dict(taps=[dict(kind="core", insertion_ps=644.9)]))
    std = dict(outline_um=[10, 10], clock={})
    hard = dict(outline_um=[10, 10], clock={}, hard=True)
    parts = [dict(name="a", type="core", origin_um=[0, 0]), dict(name="b", type="core", origin_um=[10, 0]),
             dict(name="c", type="std", origin_um=[20, 0]), dict(name="d", type="std", origin_um=[30, 0]),
             dict(name="h", type="hard", origin_um=[40, 0])]
    ports = [dict(id="ab", src=dict(part="a", bus="o"), dst=dict(part="b", bus="i"), width=8),
             dict(id="bc", src=dict(part="b", bus="o"), dst=dict(part="c", bus="i"), width=4),
             dict(id="cd", src=dict(part="c", bus="o"), dst=dict(part="d", bus="i"), width=2),
             dict(id="dh", src=dict(part="d", bus="o"), dst=dict(part="h", bus="i"), width=2)]
    lanes = [dict(id="L1", ports=["ab", "bc", "cd"]), dict(id="L2", ports=["dh"])]
    return dict(partition_types=dict(core=core, std=std, hard=hard), partitions=parts, ports=ports, lanes=lanes)


def test_classes_and_hard_merge():
    P = _plan()
    reg, _, cls = FR.regions(P, 99, "class")
    assert cls["a"] == "core640" and cls["c"] == "std"
    assert reg["a"] == reg["b"] and reg["b"] != reg["c"]
    # the hard partition absorbs the WHOLE region of its neighbour d (c-d are one connected std region)
    assert reg["h"] == reg["d"] == reg["c"] == "hard_h" and reg["a"] != reg["h"]
    reg, _, _ = FR.regions(P, 0, "partition")
    assert len({reg[n] for n in "abc"}) == 3 and reg["h"] == reg["d"]


def test_input_only_hard_merge_does_not_drag_regions(monkeypatch):
    P = _plan()
    # d drives the hard input; c shares d's old region but does not drive h.
    # A hard output landing belongs at its ordinary receiver a, not in h.
    P["ports"].append(dict(id="ha", src=dict(part="h"), dst=dict(part="a"), width=8))
    monkeypatch.setattr(FR, "HARD_MERGE", "inputs")
    reg = FR.merge_hard(P, dict(a="a", b="b", c="cd", d="cd", h="h"))
    assert reg["h"] == reg["d"] == "hard_h"
    assert reg["c"] == "cd" and reg["a"] == "a"


def test_input_only_hard_merge_shared_driver(monkeypatch):
    P = _plan()
    P["partitions"].append(dict(name="h2", type="hard", origin_um=[50, 0]))
    P["ports"].append(dict(id="dh2", src=dict(part="d"), dst=dict(part="h2"), width=8))
    monkeypatch.setattr(FR, "HARD_MERGE", "inputs")
    reg = FR.merge_hard(P, {q["name"]:q["name"] for q in P["partitions"]})
    assert reg["h"] == reg["d"] == reg["h2"]
    assert reg["c"] != reg["h"]


def test_cli_prices_face_and_fwd(tmp_path):
    P = _plan()
    lat = dict(lanes=dict(L1=dict(cycles=10, natural=10), L2=dict(cycles=4, natural=4)))
    (tmp_path / "p.json").write_text(json.dumps(P))
    (tmp_path / "l.json").write_text(json.dumps(lat))
    subprocess.run([sys.executable, str(HERE / "fallback_regions.py"), "plan", str(tmp_path / "p.json"), "--lat",
                    str(tmp_path / "l.json"), "--out", str(tmp_path / "o"), "--mode", "partition"], check=True,
                   capture_output=True)
    t = json.loads((tmp_path / "o" / "landed_crossings.json").read_text())
    assert {r["port"] for r in t["ports"]} == {"ab", "bc", "cd"}
    face = json.loads((tmp_path / "o" / "lat_face.json").read_text())["lanes"]
    fwd = json.loads((tmp_path / "o" / "lat_fwd.json").read_text())["lanes"]
    assert face["L1"]["cycles"] == 19 and fwd["L1"]["cycles"] == 13 and face["L2"]["cycles"] == 4


def test_core_land_collapses_classes_and_prices_core_ports(tmp_path):
    P = _plan()
    lat = dict(lanes=dict(L1=dict(cycles=10, natural=10, src=dict(part="a"), dst=dict(part="d")),
                          L2=dict(cycles=4, natural=4, src=dict(part="d"), dst=dict(part="h"))))
    (tmp_path / "p.json").write_text(json.dumps(P))
    (tmp_path / "l.json").write_text(json.dumps(lat))
    for mode, l1 in (("land", 13), ("rebuild", 10)):
        o = tmp_path / mode
        subprocess.run([sys.executable, str(HERE / "fallback_regions.py"), "plan", str(tmp_path / "p.json"), "--lat",
                        str(tmp_path / "l.json"), "--out", str(o), "--mode", "class", "--block", "99", "--core", mode],
                       check=True, capture_output=True)
        reg = json.loads((o / "regions.json").read_text())
        assert set(reg["part_class"].values()) == {"std"}
        # one std class: a-b-c-d connected, h merges -> no landed region port at all
        assert json.loads((o / "landed_crossings.json").read_text())["crossings"] == 0
        face = json.loads((o / "lat_face.json").read_text())["lanes"]
        assert face["L1"]["cycles"] == l1 and face["L2"]["cycles"] == 4
