"""ISTCYC-1122 (FLOW-OPS-R2, COORD): a lane whose end-bus station count changed must re-price fixed_cycles; plan_gate_pre
refuses in seconds naming the lane and the required cycles, `reprice` fixes exactly those lanes."""
import copy
import json
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402


def base():
    st = lambda bus, n: {"conn": "bus:" + bus, "regs_um": [[i, 0] for i in range(n)]}  # noqa: E731
    return {"partitions": [{"name": "a0", "type": "A"}, {"name": "b0", "type": "B"}, {"name": "c0", "type": "C"}],
            "ports": [{"id": "p1", "src": {"part": "a0", "bus": "o1"}, "dst": {"part": "b0", "bus": "i1"}},
                      {"id": "p2", "src": {"part": "c0", "bus": "o2"}, "dst": {"part": "b0", "bus": "i2"}},
                      {"id": "p3", "src": {"part": "c0", "bus": "o3"}, "dst": {"part": "a0", "bus": "i3"}}],
            "lanes": [{"id": "L1", "ports": ["p1"], "fixed_cycles": 3}, {"id": "L2", "ports": ["p2"], "fixed_cycles": 5},
                      {"id": "L3", "ports": ["p3"], "fixed_cycles": 0}],
            "latency": {"lanes": {"L1": {"fixed": 3, "cycles": 9, "natural": 9}, "L2": {"fixed": 5, "cycles": 8},
                                  "L3": {"fixed": 0, "cycles": 2}}},
            "partition_types": {"A": {"internal_stations": [st("o1", 2)]}, "B": {"internal_stations": [st("i1", 1)]},
                                "C": {"internal_stations": [st("o2", 1)]}}}


def write(tmp_path, b, n):
    pb, pn = tmp_path / "base.json", tmp_path / "new.json"
    pb.write_text(json.dumps(b)); pn.write_text(json.dumps(n))
    return str(pn), str(pb)


def test_added_station_without_reprice_refused_and_fixed(tmp_path):
    b = base(); n = copy.deepcopy(b)
    n["partition_types"]["A"]["internal_stations"][0]["regs_um"].append([9, 9])     # L1 source 2 -> 3
    n["partition_types"]["C"]["internal_stations"][0]["regs_um"].append([9, 9])     # L2 (fixed 5 != 1+0: not on the rule)
    pn, pb = write(tmp_path, b, n)
    f = G.check_istcyc(pn, pb)
    assert f[0] == "FAIL ISTCYC lane L1: stations A.o1 -> B.i1 source+destination 3 -> 4, fixed_cycles 3 (base 3), required 4"
    assert len(f) == 2 and "reprice --plan" in f[1] and "L2" not in " ".join(f) and "L3" not in " ".join(f)
    out = tmp_path / "fixed.json"
    assert G.reprice(pn, pb, str(out)) == {"L1": (3, 4)}
    d = json.loads(out.read_text())
    assert d["lanes"][0]["fixed_cycles"] == 4 and d["latency"]["lanes"]["L1"] == {"fixed": 4, "cycles": 10, "natural": 10}
    assert d["lanes"][1]["fixed_cycles"] == 5
    assert G.check_istcyc(str(out), pb) == []


def test_repriced_or_untouched_passes(tmp_path):
    b = base(); n = copy.deepcopy(b)
    n["partition_types"]["B"]["internal_stations"][0]["regs_um"].append([9, 9])
    n["lanes"][0]["fixed_cycles"] = 4
    pn, pb = write(tmp_path, b, n)
    assert G.check_istcyc(pn, pb) == []
    pn, pb = write(tmp_path, b, copy.deepcopy(b))
    assert G.check_istcyc(pn, pb) == [] and G.check_istcyc(pn, None) == []
