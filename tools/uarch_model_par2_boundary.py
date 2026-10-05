#!/usr/bin/env python3
"""Opt-in PAR2 intra-rank die-to-die boundary term for the unified model's V4.1 ROM array.

Importing this module does not mutate tools/uarch_model.py, its presets or any pinned record.  The baseline
cons_v41_rom is unchanged; `cons_v41_rom_par2(..., par2=None)` is exactly the baseline call, and only an
explicit `par2` configuration wraps _cons_adjust for the duration of the call (restored on exit).

The candidate DS4096-TP4-S58-PAR2-NP2048 splits each TP rank's ROM field over two dies by RETURN REGION (output
rows, R128 -> 2 x R64; results/uarch/dsrom_reticle_fixed_debit_reconciliation_20261002/model-r4.json
single_parallel_successor: source_reduction_region_cut_count 0, row_cross_shard_K_reductions 0).  No reduction
subtree is cut, so no partial sum crosses the boundary: a weight call whose rows sit on both shards needs its
activation on the remote shard and the remote rows' results back at the ordered consumer.  The per-call census
is results/uarch/dsrom_parallel_owner_binding_20261002/r1/native_shard_choices.jsonl.gz (1,149 calls per rank).

Modes (dataflow levels 1-5 only; no algebraic reordering, no spatial vector redistribution):
  owner        as designed: one hub (VM/SU) per rank on shard 0; a crossing field step pays activation out +
               remote rows back = 2 x L1.
  owner_edge   proposed remote shared-edge root; retain the actual routed endpoint floor until a replacement
               route is measured (no credit for an inferred shorter tree).
  owner_board  owner, with the two shards in different packages (TP pair kept in package): L1 over the board.
  mirror_hub   the replicated hubs both run the (bit-identical) serial chain; field halves are all-gathered
               over UCIe: +L1 a crossing step; attention/indexer stay on shard 0 (KV home), so wo_a pays 2 x L1.
  mirror_full  mirror_hub plus attention/indexer mirrored (KV written to both shards' HBM): +L1 every step.
  split="experts" (with owner / owner_board): whole routed experts on shard 1, all dense matrices on shard 0
               (dense = 2.4% of bytes), so only the expert step crosses: +L1 into experts_gu, +L1 out of down.
  layer_split  no row split: the two dies of a "rank" hold consecutive packed layer bytes (S' = 2S groups);
               every other stage hop is in-package UCIe.  No field step crosses.
Packaging: the PAR2 pair (or the layer-split stage pair) shares a 2-die package (UCIe), so a TP-4 collective
spans four packages; `board` picks the four-package board topology (the model's 'mesh', or 'fc4', the
existing ArrayFabric's fully connected quad).  owner_board keeps the TP pair in package (collectives unchanged).
"""
import contextlib
import copy
import gzip
import json
import math
import re
from pathlib import Path

import uarch_model as baseline

MODEL_EXTENSION = "par2-boundary"
ROOT = Path(__file__).resolve().parents[1]
CHOICES = ROOT / "results/uarch/dsrom_parallel_owner_binding_20261002/r1/native_shard_choices.jsonl.gz"
TECH = ROOT / "configs/hardware/technology.json"

# Physical constants, each with its source.
VM_TO_UCIE_STAGES = 34      # W18b measured (uarch_model DIE_SHRUNK_INTERIM note): VM/collective -> UCIe PHY 34 stages
                            # at 504 um (shrunk interim die, the die the S58 pricing uses for every other crossing)
VM_TO_SERDES_STAGES = 45    # same record: collective -> SerDes 45 stages
DIE_INTERIM_MM = (28.82, 23.22)   # same record: shrunk interim die outline
UCIE_ONDIE_ROUTING_S = 1.5e-9     # technology.json links.rom_package_ucie.hop_latency_s note: on-die routing part
RETURN_PORT_BITS_PER_CYCLE = 4416  # model-r4.json boundary.unbackpressured_remote_result_port_width_bits_per_stream_cycle
ACT_PACKET_BITS = 1681            # dsrom_PAR2_wire_deadline_plan_20261002 activation.conservative_full_packet_bits
RESULT_BITS_PER_ROW = 69          # model-r4.json boundary.bits_per_source_root_result

# Source alias -> unified-model field node key (node desc strings in the priced graph).
ALIAS_KEY = {"wq_a": "a_proj", "wkv": "a_proj", "indexer.weights_proj": "a_proj", "compressor.wkv": "a_proj",
             "compressor.wgate": "a_proj", "wq_b": "wq_b", "indexer.wq_b": "wq_b", "indexer.wk": "cmp.wk",
             "wo_a.group0": "wo_a", "wo_a.group1": "wo_a", "wo_b": "wo_b", "gate": "router",
             "shared.w1": "shared_gu", "shared.w3": "shared_gu", "exp.w1": "experts_gu", "exp.w3": "experts_gu",
             "exp.w2": "down", "shared.w2": "down", "engram.wkv": "wkv"}
ATTENTION_FED = ("wo_a",)   # field steps whose input is the attention output (KV home = shard 0)

MODES = ("owner", "owner_edge", "owner_board", "mirror_hub", "mirror_full", "layer_split")


def tech_links():
    t = json.loads(TECH.read_text())["links"]
    return dict(ucie_hop_s=t["rom_package_ucie"]["hop_latency_s"]["value"],
                ucie_bytes_s=t["rom_package_ucie"]["bytes_s"]["value"])


def call_census():
    """Per-call PAR2 crossing census of the source program (one rank, one token, all 40 layers)."""
    rows = [json.loads(x) for x in gzip.open(CHOICES, "rt")]
    per_alias, per_key = {}, {}
    for r in rows:
        pc = r["phase_choices"]
        alias = re.sub(r"^exp\d+", "exp", pc[0]["alias"])
        if {re.sub(r"^exp\d+", "exp", q["alias"]) for q in pc} != {alias}:
            raise ValueError("mixed-alias call " + r["node"])
        remote = max(q["remote_rows"] for q in pc)
        if min(q["remote_rows"] for q in pc) != remote:
            raise ValueError("choice-dependent remote rows " + r["node"])
        crosses = remote > 0
        if crosses and any(q["required_shards"] != [0, 1] for q in pc):
            raise ValueError("admission mask")
        in_words = r["input_VM"][1] - r["input_VM"][0]
        a = per_alias.setdefault(alias, dict(alias=alias, model_key=ALIAS_KEY[alias], calls=0, layers=set(),
                                             crosses=crosses, remote_rows=remote, input_VM_words=in_words,
                                             selected_choice=r["selector_slot"] is not None))
        a["calls"] += 1
        a["layers"].add(r["node"].split(".")[0])
        k = per_key.setdefault(ALIAS_KEY[alias], dict(calls=0, crossing_calls=0, crosses=False))
        k["calls"] += 1
        k["crossing_calls"] += int(crosses)
        k["crosses"] = k["crosses"] or crosses
    out = []
    for a in per_alias.values():
        a["layers"] = len(a["layers"])
        a["calls_per_layer"] = a["calls"] / a["layers"]
        a["remote_result_bits_per_call"] = RESULT_BITS_PER_ROW * a["remote_rows"]
        a["activation_bits_per_call_vm_word_bound"] = 32 * a["input_VM_words"] if a["crosses"] else 0
        out.append(a)
    out.sort(key=lambda a: (-a["calls"], a["alias"]))
    return dict(calls=len(rows), crossing_calls=sum(a["calls"] for a in out if a["crosses"]),
                local_calls=sum(a["calls"] for a in out if not a["crosses"]), per_alias=out, per_model_key=per_key,
                source=str(CHOICES.relative_to(ROOT)))


def crossing_keys():
    return {k for k, v in call_census()["per_model_key"].items() if v["crosses"]}


def default_cfg(mode, **kw):
    if mode not in MODES:
        raise ValueError(mode)
    lk = tech_links()
    cfg = dict(mode=mode, board="fc4", vm_ucie_stages=VM_TO_UCIE_STAGES, vm_serdes_stages=VM_TO_SERDES_STAGES,
               link_core_s=lk["ucie_hop_s"] - UCIE_ONDIE_ROUTING_S, ucie_bytes_s=lk["ucie_bytes_s"],
               board_hop_s=baseline.A.BASELINE["board_hop_s"], edge_root_extra_stages=None, field_term=True,
               split="rows", credit_overlap=False)
    cfg.update(kw)
    if cfg["vm_ucie_stages"] < VM_TO_UCIE_STAGES or cfg["vm_serdes_stages"] < VM_TO_SERDES_STAGES:
        raise ValueError("cannot remove source-bound hub-to-edge stages")
    if cfg["edge_root_extra_stages"] is None:   # shared long edge: the remote tree reaches half the short side
        cfg["edge_root_extra_stages"] = math.ceil(min(DIE_INTERIM_MM) / 2 * 1e3 / baseline.SS_REACH_UM[1.2e9])
    return cfg


def one_way_s(cfg, clock):
    """One-way boundary crossing (streaming 1.2 GHz domain both sides; the slow<->fast CDC at the VM port is the
    one the local path already pays): on-die wire stages + UCIe PHY/adapter + mesochronous die-to-die sync."""
    m = cfg["mode"]
    if m == "owner_board":
        return 2 * cfg["vm_serdes_stages"] / clock + cfg["board_hop_s"]
    if m == "owner_edge":
        return (cfg["vm_ucie_stages"] + max(cfg["vm_ucie_stages"], cfg["edge_root_extra_stages"])) / clock + cfg["link_core_s"]
    return 2 * cfg["vm_ucie_stages"] / clock + cfg["link_core_s"]


def _fabrics(cfg):
    D = baseline.A.D
    links = baseline.A.links_for(baseline.A.BASELINE)
    base = D.ArrayFabric(links, 2, "mesh", 4)          # arch_budget_v41's fabric for the priced graph
    if cfg["mode"] == "owner_board":
        return base, base
    new = D.ArrayFabric(links, 2, cfg["board"], 4)     # the package's 2-die SerDes budget ...
    if new.refused:
        raise ValueError(new.refused)
    new = copy.copy(new)
    new.dp = 1                                         # ... but each TP rank in its own package
    return base, new


def apply(g, P, clock, cfg, keys, S=None):
    """Add the PAR2 boundary to a priced, re-timed graph (one pass of P positions).  Returns a ledger."""
    m = cfg["mode"]
    L1 = one_way_s(cfg, clock)
    ledger = dict(one_way_s=L1, field=0, collectives=0, hops=0)
    if m != "layer_split" and cfg.get("field_term", True):
        for name, nd in g.nodes.items():
            u = nd.get("_uarch")
            if not u or nd["layer"] is None or nd["layer"] < 0 or u["key"] not in keys:
                continue
            if name.endswith("lm_head"):
                continue                               # head dies are not PAR2
            if cfg.get("split", "rows") == "experts":
                # whole routed experts on shard 1, every dense/attention matrix on shard 0: x + selected ids +
                # route weights cross once into experts_gu (one packet), expert outputs cross once out of down
                mult = {"experts_gu": 1, "down": 1}.get(u["key"], 0)
                if not mult:
                    continue
            else:
                mult = 2 if m.startswith("owner") or (m == "mirror_hub" and u["key"] in ATTENTION_FED) else 1
            nd["depth"] += mult * L1
            nd["_par2_s"] = mult * L1
            ledger["field"] += 1
    if m == "owner_board":
        return ledger
    base, new = _fabrics(cfg)
    for name, nd in g.nodes.items():
        if nd["kind"] == "collective":
            if nd["op"] == "combine_a2a":
                continue
            a = base.collective(nd["op"], nd["payload"] * P, nd["span"])
            b = new.collective(nd["op"], nd["payload"] * P, nd["span"])
            # conservative unless credit_overlap: the extra bytes of the four-package collective are NOT credited to the overlap
            d = (b["latency_s"] - a["latency_s"]) + (0.0 if cfg.get("credit_overlap") else
                                                       max(0.0, b["bytes_s"] - a["bytes_s"]))
            nd["depth"] += d
            nd["_par2_s"] = d
            ledger["collectives"] += 1
        elif nd["kind"] == "hop" and nd.get("hop_kind") in ("stage", "substage", "head") and nd.get("stage") is not None:
            pay = nd["payload"]
            a = base.hop(nd["hop_kind"], pay, nd["stage"])
            # _cons_adjust has already paid the ordinary mapping's endpoint
            # wires. Replace that FULL path; do not leave it under PAR2's L1.
            a = dict(a, latency_s=a["latency_s"] + nd["_hub_edge_s"])
            if m == "layer_split" and nd["hop_kind"] != "head" and nd["stage"] % 2 == 1:
                # in-package hop between the two dies of a layer-split pair: VM -> UCIe PHY -> next die's VM
                b = dict(latency_s=one_way_s(dict(cfg, mode="owner"), clock), bytes_s=pay / cfg["ucie_bytes_s"])
            else:
                b = new.hop(nd["hop_kind"], pay, nd["stage"])
                b = dict(b, latency_s=b["latency_s"] + baseline.hub_edge_hop_wire_s(
                    b, clock, nd["_hub_edge_die"],
                    "UCIe fan-out" in b["link"] and new.dp > 1))
                if m.startswith("mirror"):    # both dies of the next rank need the vector: UCIe forward or split
                    b = dict(b, latency_s=b["latency_s"] + L1)
            nd["depth"] += b["latency_s"] - a["latency_s"]
            nd["issue"] += b["bytes_s"] - a["bytes_s"]
            nd["_par2_s"] = (b["latency_s"] - a["latency_s"]) + (b["bytes_s"] - a["bytes_s"])
            ledger["hops"] += 1
    return ledger


def bandwidth_check(cfg, clock):
    """The remote result port streams at most RETURN_PORT_BITS_PER_CYCLE; the activation packet ACT_PACKET_BITS a
    cycle.  The link must carry both without serialising behind the field's own return rate."""
    need = (RETURN_PORT_BITS_PER_CYCLE + ACT_PACKET_BITS) * clock / 8
    return dict(need_bytes_s=need, ucie_bytes_s=cfg["ucie_bytes_s"], headroom=cfg["ucie_bytes_s"] / need,
                serialisation_exposed_s=0.0 if cfg["ucie_bytes_s"] >= need else None)


@contextlib.contextmanager
def _wrapped(cfg, S, ledgers):
    orig = baseline._cons_adjust
    keys = crossing_keys()

    def adj(g, P, clock, *a, **k):
        orig(g, P, clock, *a, **k)
        ledgers.append(dict(P=P, **apply(g, P, clock, cfg, keys, S)))
        fin = g.solve(True)
        sink = [n for n in g.nodes if n.endswith("token.return")][0]
        path = g.path(sink)
        ledgers[-1]["on_path"] = dict(
            field=sum(1 for n in path if g.nodes[n].get("_uarch") and "_par2_s" in g.nodes[n]),
            collectives=sum(1 for n in path if g.nodes[n]["kind"] == "collective" and "_par2_s" in g.nodes[n]),
            hops=sum(1 for n in path if g.nodes[n]["kind"] == "hop" and "_par2_s" in g.nodes[n]),
            added_s_on_path=sum(g.nodes[n].get("_par2_s", 0.0) for n in path))
        return fin[sink]
    baseline._cons_adjust = adj
    try:
        yield
    finally:
        baseline._cons_adjust = orig


def cons_v41_rom_par2(S, *args, par2=None, **kw):
    """cons_v41_rom with the opt-in PAR2 boundary.  par2=None is the unchanged baseline call."""
    if par2 is None:
        return baseline.cons_v41_rom(S, *args, **kw)
    ledgers = []
    with _wrapped(par2, S, ledgers):
        r = baseline.cons_v41_rom(S, *args, **kw)
    r["par2"] = dict(cfg=par2, passes=ledgers)
    return r
