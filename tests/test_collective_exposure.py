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


def test_bytes_scale_prices_the_relayed_share():
    terms = {"all_reduce": dict(window="producer", window_s=0.0, residual_s=5.0, bytes_scale=0.5)}
    g = CX.expose_collectives(graph(), terms)
    assert g.nodes["ar"]["issue"] == (65.0 - 40.0) + 5.0
    # a negative residual never prices a negative issue
    g = CX.expose_collectives(graph(), {"all_reduce": dict(window="producer", window_s=0.0, residual_s=-80.0)})
    assert g.nodes["ar"]["issue"] == 10.0
    g = CX.expose_collectives(graph(), {"all_reduce": dict(window="producer", window_s=0.0, residual_s=-99.0,
                                                           bytes_scale=0.5)})
    assert g.nodes["ar"]["issue"] == 0.0


def test_hc_post_streams_behind_the_all_reduce():
    g = graph()
    g.add("L0.attn.hc_post", ["ar"], layer=0, issue=10.0, depth=33.0, kind="vector")
    CX.expose_collectives(g, TERMS)
    fin0 = dict(g.solve())
    CX.stream_consumers(g)
    assert g.nodes["L0.attn.hc_post"]["stream"] and g.nodes["L0.attn.hc_post"]["_early"] == "hc_post"
    assert g.nodes["post"].get("_early") is None
    fin1 = g.solve()
    # the consumer's issue hides under the arrivals; it still ends its depth after the collective's last word
    assert fin0["L0.attn.hc_post"] == fin0["ar"] + 10.0 + 33.0
    assert fin1["L0.attn.hc_post"] == fin0["ar"] + 33.0


def test_lever_records():
    import json
    lev = json.loads((ROOT / "results/rtl/v41_collective_levers_campaign.json").read_text())
    assert lev["summary"]["all_pass"] and lev["summary"]["bit_exact"]
    by = {c["case"]: c for c in lev["cases"]}
    # 8 data lanes with the full 512-B link cost schedule exactly as 128 lanes do
    assert by["allreduce_wo_b_relay_l8_control_d64_q64"]["exposed_tail_cycles"] == \
        by["allreduce_wo_b_relay_d64_q64"]["exposed_tail_cycles"]
    P = lev["summary"]["patterns"]
    for pat in ("allreduce_wo_b", "allreduce_down", "gather_rows", "stage_hop"):
        assert P[pat]["best_tail_cycles"] < P[pat]["before_tail_cycles"]
    rec = json.loads((ROOT / "results/arch/v41_collective_levers.json").read_text())
    base = rec["scenarios"]["measured_baseline"]["rates"]
    best = rec["scenarios"]["recommended"]["rates"]
    for ctx in base:
        assert best[ctx]["ar"] > base[ctx]["ar"] and best[ctx]["mtp"] > base[ctx]["mtp"]
    # the model's half-payload hop (its other half crossing over T1) is slower than the full payload per package
    assert rec["scenarios"]["hop_half_payload_t1"]["rates"]["1048576"]["ar"] < base["1048576"]["ar"]
    # record-bound derived figures: the recovered share of the overlap loss and the analytical queue-area total
    sh = rec["recovered_share_of_overlap_loss"]
    for ctx in base:
        ovl = rec["scenarios"]["recommended"]["overlap_assumed"][ctx]
        assert abs(sh[ctx]["ar"] - (best[ctx]["ar"] - base[ctx]["ar"]) / (ovl["ar"] - base[ctx]["ar"])) < 1e-12
        assert 0.0 < sh[ctx]["ar"] < 1.0
    q = rec["queue_area_per_die"]
    assert q["kind"].startswith("ANALYTICAL")
    assert abs(q["growth_mm2"] - sum(q["growth_by_pattern_mm2"].values())) < 1e-12
