"""split_lane_reference_export: the reference frozen from an UNSPLIT bind is exactly what the split bind's prefill reads
(FABLE-FIX-KV-PV-CUT 11-16: a split old lane must keep its as-built payload, else native stations find no lane)."""
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import split_lane_reference_export as X
import split_source_guard as SSG
from test_split_bind_routes import Toy, cell, lane


def base_binder(tmp_path):
    """the unsplit die: cells a, b in partition A; old lanes L0 (a) and L1 (b) A -> B, a plan-cell lane LP"""
    b = SimpleNamespace(F=SimpleNamespace(cells=[cell("a"), cell("b")]), cpart={0: "A", 1: "A"},
                        parts={"A": {}, "B": {}, "C": {}}, ab={}, base=str(tmp_path), extra_lib=[])
    lanes = [lane("L1", "A", "B", 2), lane("L0", "A", "B", 2), lane("LP", "B", "C", 3)]
    lanes[1]["carried"] = {(0, "q", 0): 0, (0, "q", 1): 1}
    lanes[0]["carried"] = {(1, "q", 1): 1, (1, "q", 0): 0}          # dict order is not lane-bit order
    lanes[2].update(plan=True)
    return b, lanes


def test_exported_reference_equals_the_frozen_payload_and_prefills_the_split(tmp_path, monkeypatch):
    monkeypatch.setattr(SSG, "source_rules_fingerprint", lambda b: "rules")
    monkeypatch.setattr(SSG, "logical_graph_fingerprint", lambda b: "graph")
    b, lanes = base_binder(tmp_path)
    ref = X.build(b, lanes, {"A": ["A0", "A1"], "B": ["B0", "B1"]})
    want = Toy().reference()
    assert ref["schema"] == want["schema"] and ref["part_groups"] == want["part_groups"] and ref["cells"] == want["cells"]
    assert [r for r in ref["lanes"] if r["id"] != "LP"] == want["lanes"]
    assert [r for r in ref["lanes"] if r["id"] == "LP"] == [dict(id="LP", src="B", dst="C", drivers=[])]
    assert ref["source_rules_sha256"] == "rules" and ref["source_graph_sha256"] == "graph"
    # the split bind (pieces A0/A1, B0/B1 and their cut lanes) puts both old payloads back, in the old bit order
    ref["lanes"] = [r for r in ref["lanes"] if r["id"] != "LP"]      # the toy split has no plan-cell lane
    from split_bind_routes import payload_sha256
    ref["payload_sha256"] = payload_sha256(ref["lanes"])
    split = Toy()
    receipt = split.prefill(ref)
    assert receipt["original_lanes"] == 2 and receipt["original_bits"] == 4
    assert list(split.byid["L0"]["carried"]) == [split.key("a", i) for i in range(2)]
    assert list(split.byid["L1"]["carried"]) == [split.key("b", i) for i in range(2)]


def test_unknown_group_base_partition_fails(tmp_path, monkeypatch):
    import pytest
    b, lanes = base_binder(tmp_path)
    with pytest.raises(ValueError, match="not a partition of the base plan"):
        X.build(b, lanes, {"Z": ["Z0", "Z1"]})


def test_usage_without_separator_prints_help(capsys):
    assert X.main(["ref.json", "groups.json", "bind"]) == 2
    assert "split_lane_reference" in capsys.readouterr().out
