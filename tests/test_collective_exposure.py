"""tools/collective_exposure.py: a streaming collective is re-priced from its producer's last output."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import collective_exposure as CX  # noqa: E402
import decode_critical_path as D  # noqa: E402

TERMS = {"all_reduce": dict(window="producer", window_s=0.0, residual_s=5.0),
         "hop": dict(window="producer", window_s=0.0, residual_s=1.0)}


def graph():
    g = D.Graph()
    g.add("mv", [], layer=0, issue=40.0, depth=50.0, kind="matvec")
    g.add("ar", ["mv"], layer=0, issue=130.0, depth=150.0, kind="collective", op="all_reduce", payload=1, span=4,
          stream=True, ctrl=2.0)
    g.add("post", ["ar"], layer=0, issue=1.0, depth=1.0)
    return g


def test_stream_pricing_hides_bytes_under_producer_depth():
    g = graph()
    fin = g.solve()
    # start 0 + ctrl 2 + 130 bytes > producer finish 90: the bytes ran from the producer's START
    assert fin["ar"] == 132.0 + 150.0


def test_exposed_pricing_starts_at_the_last_output():
    g = CX.expose_collectives(graph(), TERMS)
    nd = g.nodes["ar"]
    assert not nd["stream"] and nd["_exposed"] == "all_reduce"
    assert nd["issue"] == (130.0 - 40.0) + 5.0
    fin = g.solve()
    assert fin["ar"] == 90.0 + 95.0 + 150.0
    CX.expose_collectives(g, TERMS)                     # idempotent
    assert g.nodes["ar"]["issue"] == 95.0


def test_committed_records():
    import json
    camp = json.loads((ROOT / "results/rtl/v41_stage_collective_campaign.json").read_text())
    assert camp["summary"]["all_pass"] and camp["summary"]["bit_exact"]
    rec = json.loads((ROOT / "results/arch/v41_collective_exposure.json").read_text())
    # the measured tail is never below the overlap-assumed model on any pattern
    for row in rec["per_pattern"].values():
        assert row["measured_tail_cycles"] >= row["model_exposed_cycles"]
    for r in rec["design_point_rates"].values():
        assert r["measured_exposure"]["ar"] < r["overlap_assumed"]["ar"]
    assert set(CX.load_terms()) == {"all_reduce", "all_gather_small", "all_gather_select", "all_gather_rows", "hop"}


def test_classes():
    assert CX.exposure_class("L2.attn.rows_allgather", dict(kind="collective", op="all_gather")) == "all_gather_rows"
    assert CX.exposure_class("L2.attn.idx.topk_merge", dict(kind="collective", op="all_gather")) == "all_gather_select"
    assert CX.exposure_class("L0.ffn.router_allgather", dict(kind="collective", op="all_gather")) == "all_gather_small"
    assert CX.exposure_class("L0.ffn.combine_allreduce", dict(kind="collective", op="all_reduce")) == "all_reduce"
    assert CX.exposure_class("token.return", dict(kind="hop", hop_kind="return")) is None
    assert CX.exposure_class("L1.substage_hop0", dict(kind="hop", hop_kind="substage")) == "hop"
