"""Measured collective exposure (gate C7 / O2) for the decode critical-path DAG.

Standalone (json + pathlib only) so any checkout's decode_critical_path graph can take it: the V4.1 design point
lives on another line (v41-rack-gates) whose model is driven from here by tools/v41_collective_exposure.py.

tools/decode_critical_path.Graph.solve prices a STREAMING node as
    finish = max(start_producer + ctrl + bytes, producer_finish) + depth,
so a collective's bytes cross the link during its producer's pipeline depth, before any output exists.  The RTL
stage bench (tools/rtl_v41_stage_collective_campaign.py) measures what is exposed after the producer's LAST output
on the real one-shot engine with credit queues and the validated links.  expose_collectives() re-prices every
streaming collective and stage hop as store-and-forward from its producer's last output:
    issue = max(0, bytes x bytes_scale - window) + residual,     depth unchanged (hop + fold),
window = the producer's emission window (its issue, or the class's measured span for select / HBM-gather producers
whose outputs appear at the end); residual = measured tail - that formula at the bench's design point.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/arch/v41_collective_exposure.json"


def exposure_class(name, nd):
    """The measured pattern a collective or hop node is priced by."""
    if nd["kind"] == "hop":
        return "hop" if nd.get("hop_kind") in ("stage", "substage", "head") else None
    if name.endswith("rows_allgather"):
        return "all_gather_rows"
    if name.endswith(("topk_merge", "cand.merge")):
        return "all_gather_select"
    if nd.get("op") == "all_gather":
        return "all_gather_small"
    return "all_reduce"                                   # all_reduce, wo_a_group_reduce, combine_a2a


def load_terms(path=None):
    """{class: dict(window, window_s, residual_s)} from the committed exposure record."""
    return json.loads(Path(path or REC).read_text())["terms"]


def expose_collectives(g, terms):
    """Re-price every streaming collective / stage hop of graph g (a decode_critical_path.Graph) with the measured
    terms.  Idempotent; nodes already store-and-forward (overlap not assumed) are left alone."""
    for name, nd in g.nodes.items():
        if nd["kind"] not in ("collective", "hop") or not nd.get("stream") or nd.get("_exposed"):
            continue
        cls = exposure_class(name, nd)
        if cls == "hop" and getattr(g, "positions", 1) > 1 and "hop_mtp" in terms:
            cls = "hop_mtp"            # the MTP verify pass's hop: its own bench-measured multi-position tail
        t = terms.get(cls) if cls else None
        if not t:
            continue
        if t["window"] == "producer":
            window = max((g.nodes[d]["issue"] for d in nd["deps"]), default=0.0)
        else:
            window = t["window_s"]
        nd["_stream_issue_s"] = nd["issue"]
        # bytes_scale: the share of the modelled per-link bytes a link still carries (0.5 under the receive-side
        # relay, rtl/rom/ot_rom_oneshot_px.sv); the residual was measured against the same scaled formula
        nd["issue"] = max(0.0, max(0.0, nd["issue"] * t.get("bytes_scale", 1.0) - window) + t["residual_s"])
        nd["stream"] = False
        nd["ctrl"] = 0.0
        nd["_exposed"] = cls
    return g


def mutation(terms):
    """The same as a lever mutation f(g, spec) for tools/arch_latency_ladder_v41 / arch_utilization_v41 muts; it
    must run AFTER any mutation that re-prices collective bytes (arch_lanes_v41.m_lanes)."""
    def m_exposed(g, sp):
        expose_collectives(g, terms)
    return m_exposed


# -- consumer early start (gate C7 / O2 levers, tools/rtl_v41_collective_levers_campaign.py) ---------------------------
def stream_consumers(g):
    """hc_post after an all-reduce is elementwise in index order, and the one-shot emits the reduced words in index
    order, so it can start on the first word that lands: price it as STREAMING (its issue overlaps the arrivals;
    it still ends no earlier than its last input's finish + its depth).  Idempotent."""
    for name, nd in g.nodes.items():
        if not name.endswith(".hc_post") or nd["stream"] or nd.get("_early"):
            continue
        if any(g.nodes[d]["kind"] == "collective" and g.nodes[d].get("op") != "all_gather" for d in nd["deps"]):
            nd["stream"] = True
            nd["_early"] = "hc_post"
    return g


def stream_top6(g):
    """SENSITIVITY (no RTL): a streaming top-6 that ingests router scores as they land, so its issue overlaps the
    router all-gather; its depth (and top6_order's) still follows the last score."""
    for name, nd in g.nodes.items():
        if name.endswith(".ffn.top6") and not nd["stream"] and not nd.get("_early"):
            nd["stream"] = True
            nd["_early"] = "top6"
    return g


def consumer_mutation(which=("hc_post",)):
    fns = dict(hc_post=stream_consumers, top6=stream_top6)

    def m_consumers(g, sp):
        for w in which:
            fns[w](g)
    return m_consumers
