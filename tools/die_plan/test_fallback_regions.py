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
