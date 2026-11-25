"""CABIND-1125: plan_gate_pre.check_cabind (sidecar count_aligned.parts / ports vs the plan, the bind's own rules)."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_gate_pre as G  # noqa: E402


def _plan():
    mk = lambda n, t: {"name": n, "type": t}
    return {"partitions": [mk("o1", "TO"), mk("r1", "TR"), mk("r2", "TR"), mk("o2", "TO")],
            "partition_types": {"TO": {"landing_relay_tx_stages": 2}, "TR": {"landing_relay_rx_stages": 1}},
            "ports": [{"id": "p1", "dst": {"part": "r1", "bus": "b"}}],
            "clock": {"landing_network": {"data_cycles_per_crossing": "count_aligned", "count_aligned_cycles": {"p1": 5},
                                          "count_aligned_bind": {"root": "st:h", "pad": 0}}}}


def _side(stages=5):
    return {"count_aligned": {"root": "st:h", "pad": 0, "regions": {"x": {"origin_part": "o1"}, "y": {"origin_part": "o2"}},
                              "ports": {"p1": {"sched_lat": 5}},
                              "parts": {"st:h": {"region": "z", "role": "origin", "src": None, "stages": 0},
                                        "o1": {"region": "x", "role": "origin", "src": None, "stages": 0},
                                        "r1": {"region": "x", "role": "relay", "src": "o1", "stages": stages},
                                        "r2": {"region": "x", "role": "relay", "src": "o1", "stages": 5},
                                        "o2": {"region": "y", "role": "origin", "src": None, "stages": 0}}}}



def _run(plan, side):
    import tempfile, json
    with tempfile.TemporaryDirectory() as d:
        pp, sp = Path(d) / "p.json", Path(d) / "s.json"
        pp.write_text(json.dumps(plan))
        sp.write_text(json.dumps(side))
        return G.check_cabind(str(pp), str(sp))


def test_consistent_is_clean():
    out = _run(_plan(), _side())
    assert not [l for l in out if l.startswith("FAIL")]
    assert "mismatching 0" in out[-1]


def test_every_stale_part_listed():
    side = _side(stages=2)          # 2 + tx 2 + rx 1 = 5 expected for r1; r2 stays 5 (ok)
    out = _run(_plan(), side)
    fails = [l for l in out if l.startswith("FAIL CABIND")]
    assert len(fails) == 1 and "r1: stages 2 != 2 + tx[TO]=2 + rx[TR]=1 = 5" in fails[0]
    side["count_aligned"]["parts"]["r2"]["stages"] = 2
    out = _run(_plan(), side)
    assert len([l for l in out if l.startswith("FAIL CABIND")]) == 2
    assert sum("MISMATCH" in l for l in out) == 2 and "mismatching 2" in out[-1]


def test_other_equalities():
    side = _side()
    side["count_aligned"]["ports"]["p1"]["sched_lat"] = 6
    side["count_aligned"]["pad"] = 1
    out = _run(_plan(), side)
    msg = "\n".join(l for l in out if l.startswith("FAIL"))
    assert "count_aligned_cycles != sidecar sched_lat" in msg and "count_aligned_bind pad" in msg


def test_no_sidecar_count_aligned_no_lines():
    assert _run(_plan(), {}) == []


def test_wired_in_classes():
    assert "CABIND" in G.CLASSES
