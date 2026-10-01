#!/usr/bin/env python3
"""Microarchitecture analytical model: re-price the architecture DAG from elements, replicas, mappings,
ports, networks and wires (docs/MICROARCH_MODEL.md, AGENTS.md rule 1).

    python3 tools/uarch_model.py [--ctx 1048576] [--out results/uarch/v41_rom.json]

WHY.  tools/arch_budget_v41.py prices every node of the token DAG from die-level widths (spec.weight_macs,
spec.rom_bytes, ...): a matvec reads ROM at the WHOLE DIE's aggregate rate, activations and results cost
nothing to move, and wire delay is a separate lump (arch_lanes_v41.wire_mutation).  Composed hardware does not
work that way.  A matrix is read only as fast as the macros that hold it; its activation vector comes out of
the vector memory through a finite read port and a broadcast tree whose depth is set by the floorplan; its
results go back through a finite return network and VM write port; a stream-unit op runs at the lane count
actually built; and the index scan runs at the reader's measured sector rate.  This module keeps the
architecture's DAG, its workload and its dependency structure, and replaces each node's issue and depth with
those microarchitectural terms.  The same node therefore has an architecture price and a microarchitecture
price, and every gap between them is attributed to one named parameter.

A DESIGN is a dict of named parameters (PRESETS below): the as-built RTL (measured elements), the
architecture spec realised naively (the spec's widths but real mappings, ports and wires), and proposals.
Every constant cites its source; ASSUMED marks a number that has no measurement yet.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_budget_v41 as A  # noqa: E402

# ---------------------------------------------------------------------------------------------------------
# Physical constants (sources in-line)
# ---------------------------------------------------------------------------------------------------------
WIRE_PS_PER_UM = 0.5997       # routed express-link fit (tools/chip_assembly/floorplans.wire_delay_model)
WIRE_OVERHEAD_PS = 189.5      # same fit: flop clk-q + setup + skew
UNCERTAINTY_PS = 60.0         # adopted clock uncertainty (briefing / W5 records)
ROM_MACRO_UM2 = 125.712 * 119.340   # ot_rom_8192x274_m8 (physical/asap7_memory_macros)
ROM_DEPTH = 8192
FP8_MAC_UM2 = 78.466875       # arch_budget_v41 unit_areas (ot_hdc_blockdot / 32, closed 1195.7 MHz)
BF16_MAC_UM2 = 509.352        # arch_budget_v41 unit_areas (ot_mac_bf16_fp32_pipe)
DFF_UM2 = 0.2916              # DFFHQNx1 (W5 unit areas, results/floorplan/qwen_o4_unit_areas.json)

# weights delivered by one ROM word, by the node's format (W1 bank map: FP4 two 136-bit 32-blocks per
# 274-bit word, FP8 one 264-bit block, BF16 16 x 16 bit, FP32 8 x 32 bit)
WEIGHTS_PER_WORD = {"fp4": 64, "fp8": 32, "bf16": 16, "fp32": 8}

# K (input width) of every weight node of the V4.1 DAG, per die (tools/decode_critical_path.v41_graph;
# configs/models/candidates/deepseek-v4.1-flash.json).  Rows per die = die MACs / K.
NODE_K = {
    "a_proj": 5120, "wq_b": 1280, "wo_a": 4096, "wo_b": 2048, "router": 5120, "shared_gu": 5120,
    "experts_gu": 5120, "down": 2304, "hc.fn": 20480, "cmp.wk": 512, "wkv": 3072, "lm_head": 5120,
}
NODE_FMT = {
    "a_proj": "fp8", "wq_b": "fp8", "wo_a": "bf16", "wo_b": "fp8", "router": "bf16", "shared_gu": "fp8",
    "experts_gu": "fp4", "down": "fp4", "hc.fn": "fp32", "cmp.wk": "bf16", "wkv": "fp8", "lm_head": "bf16",
}
# floorplan region of each weight node's macros (W1 pack: results/floorplan/v41_pack_expanded_woa.json)
NODE_REGION = {
    "experts_gu": "expert", "down": "expert", "wo_a": "me", "a_proj": "dense", "wq_b": "dense",
    "wo_b": "dense", "shared_gu": "dense", "router": "dense", "cmp.wk": "dense", "wkv": "spill",
    "lm_head": "dense", "hc.fn": "hub",
}


def node_key(name: str) -> str:
    tail = name.split(".", 1)[1] if "." in name else name
    for k in sorted(NODE_K, key=len, reverse=True):
        if tail.endswith(k):
            return k
    return ""


WIRE_PS_PER_UM_LOADED = 0.76  # W3 real-technology channel runs: 0.72-0.81 ps/um under 300-1,500 routed wires
                              # (branch claude/w3-v41-die-assembly 01ef74dc, v41_corridor records)


def wire_cycles(um: float, clock_hz: float, ps_per_um: float = WIRE_PS_PER_UM) -> int:
    """One-way cycles to cross `um` of registered wire (W1 rule: registers = ceil(L/seg) - 1, +1 cycle)."""
    period_ps = 1e12 / clock_hz
    seg = (period_ps - UNCERTAINTY_PS - WIRE_OVERHEAD_PS) / ps_per_um
    regs = max(0, math.ceil(um / seg) - 1)
    return regs + 1 if regs > 0 else (1 if um > 0 else 0)


# ---------------------------------------------------------------------------------------------------------
# Designs.  Every resource is a named parameter; PRESETS differ only where stated.
# ---------------------------------------------------------------------------------------------------------
BASE = dict(
    name="base",
    # ROM weight array
    macros=13798,                 # busiest die, stage 1 rank 3 (W1 bank map, v41_die_bankmap_busiest_expanded_woa)
    mapping="contiguous",         # "contiguous": a matrix slice owns its full-depth banks (W1 map);
                                  # "striped": every matrix's rows interleaved over all macros (W8)
    expert_fill_rows=5760,        # rows of an expert matrix per bank in the contiguous map (70.3% of 8192)
    bf16_stripe_macros=None,      # striped mapping: macros that carry BF16 lanes (None = every macro); BF16
                                  # matrices (wo_a, router, cmp.wk, lm_head) stripe over only these
    mac_lanes_per_macro=None,     # None: one word per cycle per macro (lanes sized to the word); else a cap
    weight_macs_die=None,         # optional die-wide MAC cap (as-built: 512 QE block-dot lanes)
    bf16_macs_die=None,
    elem_fill=78,                 # measured: W2 QE ROM/MAC neighbourhood accept -> first result 78 cycles
                                  # (claude/w2-rommac, qe_romac_exactness.json; the formula gave 45-60)
    wire_ps_per_um=WIRE_PS_PER_UM_LOADED,
    # vector memory ports (elements of 32 bit per cycle)
    vm_read_elems=4,              # x operand path: G4 = 4 FP32 elements/cycle (V41_FLOORPLAN_CONNECTIVITY 2)
    vm_write_elems=64,            # collective/result write: 4 x 512-bit words (W1 handoff 1)
    # networks
    bcast_um={"expert": 20465.5, "dense": 9040.0, "me": 7690.0, "spill": 9590.0, "hub": 0.0},
                                  # VM -> farthest macro of each region (W1 latency_crossings, manhattan)
    return_fanin=8,               # result tree fan-in per registered level (ASSUMED)
    return_leaf_elems=None,       # None: every holding macro is a leaf of the return tree
    # stream unit / SFU
    su_lanes=16, sfu_lanes=8,     # as-built SU (V41_DIE_ENGINE_PROFILE: SUN 16 / SUM 8)
    # attention, index, select
    att_macs=32768,               # as-built attention products (NT64 x H16 x TD32)
    att_measured_job_cycles=609,  # measured H16/D512/T640 process cycles (results/rtl, e1ac020d)
    su_softmax_measured_cycles=3280,  # measured H16/T640 actual SU softmax + divide (b674827f)
    use_measured_attention=True,
    idx_reader_Bpc=60 * 32,       # measured four-stack reader: 557,056 sectors in 9,278 cycles (TASKS)
    idx_macs=1024,                # as-built indexer FP4 block-dot lanes
    collective_cycles=232,        # measured: 12 layer-0 collectives in 2,780 cycles (V41_DIE_ENGINE_PROFILE)
)

# Distributed VM (root decision 2026-09-29): the VM is lane-group-local banks inside HUB_SU_VECTOR (128 groups of 8
# lanes, element i in group i mod 128).  Register stages from the W1 hub geometry (results/floorplan/
# v41_pack_expanded_woa.json), SU lane array 11.96 mm2 as a 3,458 um square abutting the HUB_VM strip and centred on
# it, at 0.92 ns / 0.76 ps/um:
#   x gather     farthest group -> VM port (west edge centre): 3,458 + 1,729 = 5,187 um      -> 6
#   result scatter  VM port -> farthest group, the same run                                    -> 6
#   collective write  with the collective endpoint at the VM port (W10 placement, root 2026-09-29): the scatter
#                     tree alone -> 6 (11 from HUB_COLLECTIVE's W1 position)
#   SU results   reducer root at the array centre -> farthest group 3,458 um (element writes are local) -> 4
VM_DIST = dict(vm_x_gather_stages=6, vm_ret_scatter_stages=6, vm_coll_write_stages=6, su_ret_stages=4)
# the SU's broadcast tree to the farthest lane (W11 SU worker's placement derivation, root-accepted)
SU_BCAST = dict(su_bcast_stages=4)

PRESETS = {
    # the RTL as elaborated today (W1 rung 1 profile + measured component gates)
    "as_built": dict(BASE, name="as_built", weight_macs_die=512, bf16_macs_die=64, idx_macs=1024,
                     vm_read_elems=4, vm_write_elems=4),
    # the architecture spec's widths, realised with the W1 contiguous bank map and today's ports
    "spec_contiguous": dict(BASE, name="spec_contiguous", su_lanes=1024, sfu_lanes=256, att_macs=37184,
                            idx_macs=248832, use_measured_attention=False, collective_cycles=None,
                            idx_reader_Bpc=None),
    # the spec's widths with every matrix striped over every macro (W8 sizing)
    "spec_striped": dict(BASE, name="spec_striped", mapping="striped", su_lanes=1024, sfu_lanes=256,
                         att_macs=37184, idx_macs=248832, use_measured_attention=False, collective_cycles=None,
                         idx_reader_Bpc=None),
}
# proposals: striped rows plus VM ports sized so that neither x nor the result stream binds a projection
PRESETS["prop_vm64"] = dict(PRESETS["spec_striped"], name="prop_vm64", vm_read_elems=64, vm_write_elems=128)
PRESETS["prop_vm256"] = dict(PRESETS["spec_striped"], name="prop_vm256", vm_read_elems=256, vm_write_elems=512)
PRESETS["proposal"] = dict(PRESETS["spec_striped"], name="proposal", vm_read_elems=64, vm_write_elems=128,
                           bf16_stripe_macros=2048, collective_cycles=232, row_split="ksplit",
                           # W11 decisions (2026-09-29): indexer = 16 NK=4 score slices, 64 keys/cycle (beat-aligned
                           # with the reader; reader-bound); attention NL=4 tiles (32,768 products) + PWORDS=2
                           # loader; SU per the RTL layout rule (+14 cycles/layer) with its own VM ports (~6 mm2)
                           idx_macs=262144, att_macs=32768, su_layout_extra_cycles=14, su_vm_ports_mm2=6.0,
                           # ROOT DECISION 2026-09-29 (W15): collectives priced from the RTL measurement of the
                           # adopted design -- endpoint at the die centre (W3 placement, 17 wire stages to the link
                           # PHYs), direct T1 links (no relay), receive depth 1,024 (results/rtl/w15_collectives.json
                           # v41p17_r0d1024_sweep fit); collective_cycles is then unused
                           collective_w15="v41p17_r0d1024",
                           # ROOT DECISION 2026-09-29 (W11): distributed VM (lane-group banks) and SU broadcast stages
                           **VM_DIST, **SU_BCAST)
PRESETS["proposal_whole"] = dict(PRESETS["proposal"], name="proposal_whole", row_split="whole")
PRESETS["proposal_ksplit"] = dict(PRESETS["proposal"], name="proposal_ksplit", row_split="ksplit")
PRESETS["prop_vm256_measured"] = dict(PRESETS["prop_vm256"], name="prop_vm256_measured", su_lanes=16, sfu_lanes=8,
                                      att_macs=32768, use_measured_attention=True, idx_reader_Bpc=60 * 32,
                                      idx_macs=1024, collective_cycles=232)


# ---------------------------------------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------------------------------------
def _spec():
    rec = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())
    fields = {f.name for f in dataclasses.fields(A.Spec)}
    return A.Spec(**{k: v for k, v in rec["required_spec"].items() if k in fields})


_ARCH_CACHE = {}


def arch_graph(ctx: int):
    """The architecture-level priced DAG at the required spec (the model this one refines); a fresh copy."""
    if ctx not in _ARCH_CACHE:
        r = A.price(_spec(), ctx=ctx, keep=True)
        b = r.pop("_built")
        _ARCH_CACHE[ctx] = (r, b)
    r, b = _ARCH_CACHE[ctx]
    return dict(r), copy.deepcopy(b)


EXPERT_ROWS = {"experts_gu": 1152, "down": 1280}   # rows of ONE expert's slice per die (w1|w3 2 x 576; w2 1280)
FADD_PIPE = 5                                       # ot_fp32_add_rne_pipe latency (closed 0.7 ns)


def expected_max_load(balls: int, bins: int, trials: int = 4000, seed: int = 7) -> float:
    """E[max bin occupancy] of `balls` placed uniformly at random in `bins` (Monte Carlo, fixed seed)."""
    import random
    if bins <= 1:
        return float(balls)
    rng = random.Random(seed)
    tot = 0
    for _ in range(trials):
        cnt = {}
        for _b in range(balls):
            k = rng.randrange(bins)
            cnt[k] = cnt.get(k, 0) + 1
        tot += max(cnt.values())
    return tot / trials


def next_pow2(x: int) -> int:
    return 1 << max(0, math.ceil(math.log2(max(1, x))))


CHAIN_FLOOR = 8 * 5   # golden chunk sum = 8 sequential FP32 adds x adder latency 5: no stream round is shorter


def striped_read(d, key, rows, K, fmt):
    """Cycles to read `rows` x K of format `fmt` striped over the ROM field (W10-validated rules):
    whole rows cost ceil(K / weights-per-word) words in one macro; a K split of s puts power-of-two-aligned runs
    of golden chunks (next_pow2(ceil(C / s)) chunks) in each macro, exact under the golden csum padded tree;
    an expert's split is chosen so ONE expert's tile covers the whole field (no tile collisions); every stream
    round lasts at least the chunk-sum chain recurrence.  Returns (t_read, split, adder_levels, holding)."""
    n = d["macros"]
    if fmt == "bf16" and d.get("bf16_stripe_macros"):
        n = min(n, d["bf16_stripe_macros"])
    wpw = WEIGHTS_PER_WORD[fmt]
    C = math.ceil(K / 256)
    s = 1
    seg_words = math.ceil(K / wpw)
    unit_rows = EXPERT_ROWS[key] if key in EXPERT_ROWS else rows
    seg_per_row = 1
    if d.get("row_split", "whole") == "ksplit":
        while s < C and unit_rows * s < n:
            s *= 2
        s = min(s, next_pow2(C))
        if fmt == "fp4":                     # an FP4 word carries block b of two sibling chunks: segments are
            s = min(s, max(1, next_pow2(C) // 2))   # whole chunk pairs (W10 generator rule)
        if s > 1:
            c_seg = next_pow2(math.ceil(C / s))      # golden-aligned chunks per segment
            seg_words = math.ceil(min(K, c_seg * 256) / wpw)
            seg_per_row = math.ceil(C / c_seg)       # a row has ceil(C/c) segments, fewer than s when C is not
                                                     # a power of two (W10: C=20, c=2 -> 10 segments)
    segs = rows * seg_per_row
    holding = min(n, segs)
    if key in EXPERT_ROWS and EXPERT_ROWS[key] * seg_per_row < n:
        active = max(1, round(rows / EXPERT_ROWS[key]))
        tiles = max(1, n // (EXPERT_ROWS[key] * seg_per_row))
        t = expected_max_load(active, tiles) * seg_words
    else:
        t = math.ceil(segs / n) * seg_words
    if d.get("row_split") == "ksplit":
        t = max(t, CHAIN_FLOOR)
    al = math.ceil(math.log2(s)) if s > 1 else 0
    return t, s, al, holding


def price_matvec(nd, name, d, clock, c):
    key = node_key(name)
    if not key or key == "hc.fn":
        return None
    sw = nd["sweep"]
    f = A.die_fraction(name, c, 4)
    macs = sw["macs"] * f
    fmt = NODE_FMT[key]
    K = NODE_K[key]
    rows = max(1.0, macs / K)
    wpw = WEIGHTS_PER_WORD[fmt]
    words = macs / wpw
    region = NODE_REGION[key]
    ksplit = 1
    adder_levels = 0
    t_x = K / d["vm_read_elems"]
    if d["mapping"] == "striped":
        if key == "a_proj":
            # a_proj fuses FP8 (wq_a, wkv) with BF16 rows (index weights_proj when the layer scans; compressor
            # wkv/wgate on KV-source layers), which stripe over the BF16 macros and need x in BF16 lane order:
            # two sequential sub-phases and x streamed twice (W10 interim report)
            L = nd["layer"]
            mode, r = c["modes"][L], c["compress_ratios"][L]
            bf_rows = ((c["index_heads"] if mode.get("scans_index") else 0)
                       + ((2 if r == 2 else 1) * c["head_dim"] if L in c["kv_source_layer_ids"] else 0)) / 4
            parts = [(max(1.0, rows - bf_rows), "fp8")] + ([(bf_rows, "bf16")] if bf_rows else [])
            t_x *= len(parts)                # FP8/FP4 share one FP8 x stream; only BF16 needs a second (W10)
        else:
            parts = [(rows, fmt)]
        t_read, holding = 0.0, 0
        for prow, pfmt in parts:
            tr, ks, al, hd = striped_read(d, key, prow, K, pfmt)
            t_read += tr
            ksplit, adder_levels, holding = max(ksplit, ks), max(adder_levels, al), max(holding, hd)
    else:
        depth_rows = d["expert_fill_rows"] if region == "expert" else ROM_DEPTH
        holding = max(1, math.ceil(words / depth_rows))
        t_read = math.ceil(words / holding)
    lanes_cap = []
    if key in ("wo_a", "router", "cmp.wk", "lm_head"):
        if d["bf16_macs_die"]:
            lanes_cap.append(macs / d["bf16_macs_die"])
    elif d["weight_macs_die"]:
        lanes_cap.append(macs / d["weight_macs_die"])
    t_mac = max(lanes_cap) if lanes_cap else 0.0
    t_ret = rows / d["vm_write_elems"]
    issue_c = max(t_read, t_mac, t_x, t_ret)
    bind = max((("rom_read", t_read), ("mac", t_mac), ("vm_read_x", t_x), ("vm_write_ret", t_ret)),
               key=lambda kv: kv[1])[0]
    leaves = holding if d["return_leaf_elems"] is None else d["return_leaf_elems"]
    tree = math.ceil(math.log(max(2, leaves), d["return_fanin"]))
    wire = 2 * wire_cycles(d["bcast_um"][region], clock, d.get("wire_ps_per_um", WIRE_PS_PER_UM))
    # distributed VM (W11, root 2026-09-29): x is gathered from the lane-group banks to the VM port, results are
    # scattered back to them -- register stages from the hub geometry (VM_DIST below)
    wire += d.get("vm_x_gather_stages", 0) + d.get("vm_ret_scatter_stages", 0)
    depth_c = d["elem_fill"] + wire + tree + adder_levels * FADD_PIPE
    return dict(key=key, fmt=fmt, K=K, rows=rows, words=words, holding=holding, region=region,
                t_read=t_read, t_mac=t_mac, t_x=t_x, t_ret=t_ret, issue=issue_c, bind=bind,
                depth=depth_c, wire=wire, tree=tree, ksplit=ksplit, adder_levels=adder_levels)


def evaluate(d: dict, ctx: int = 1048576):
    arch, b = arch_graph(ctx)
    g = b.g
    E = A._env()
    clock, c = E["clock"], E["c"]
    cyc = 1.0 / clock
    notes = {}
    for name, nd in g.nodes.items():
        k = nd["kind"]
        if k == "matvec":
            r = price_matvec(nd, name, d, clock, c)
            if r is None:
                continue
            nd["issue"] = r["issue"] * cyc
            nd["issue_cat"] = "weight_sweep"
            nd["depth"] = r["depth"] * cyc
            nd["_uarch"] = r
        elif k in ("vector", "reduce"):
            if nd.get("resource") and nd["resource"][0] in ("su", "sfu"):
                lanes_arch = _spec().sfu_lanes if nd["resource"][0] == "sfu" else _spec().su_lanes
                n_el = nd["resource"][1] * lanes_arch
                lanes = d["sfu_lanes"] if nd["resource"][0] == "sfu" else d["su_lanes"]
                nd["issue"] = math.ceil(n_el / lanes) * cyc
        elif k == "kvscan":
            if name.endswith("idx.score") and d["idx_reader_Bpc"]:
                n_keys = int(nd["desc"].split()[2])
                by = n_keys * A.IDX_KEY_B
                macs = n_keys * c["index_heads"] * c["index_head_dim"]
                t = max(by / d["idx_reader_Bpc"], macs / d["idx_macs"])
                nd["issue"] = t * cyc
            elif name.endswith("idx.score"):
                n_keys = int(nd["desc"].split()[2])
                macs = n_keys * c["index_heads"] * c["index_head_dim"]
                nd["issue"] = max(nd["issue"], macs / d["idx_macs"] * cyc)
            elif d["use_measured_attention"] and name.endswith(".scores"):
                # PWORDS=2 loader: measured 449 cycles at T640 (claude/w11-attn c80877d8); else the PWORDS=1 job
                nd["issue"] = (449 if d.get("att_pwords") == 2 else d["att_measured_job_cycles"]) * cyc
                nd["depth"] = 0.0
            elif d["use_measured_attention"] and name.endswith(".pv"):
                nd["issue"] = 0.0      # the measured job covers scores + PV
        elif k == "collective" and d.get("collective_latency_s") is not None:
            nd["depth"] = d["collective_latency_s"] + (d["collective_cycles"] or 0) * cyc
        elif k == "collective" and d.get("collective_w15"):
            nd["depth"] = w15_collective_s(d["collective_w15"], nd["op"], nd["payload"], nd.get("span") or 4)
            nd["issue"] = 0.0          # the measured issue -> last commit latency includes the payload stream
        elif k == "collective" and d["collective_cycles"]:
            nd["depth"] = max(nd["depth"], d["collective_cycles"] * cyc)
        if k == "collective" and d.get("vm_coll_write_stages"):
            nd["depth"] += d["vm_coll_write_stages"] * cyc      # the collective DMA's write into the lane groups
    if d.get("su_layout_extra_cycles"):
        for name, nd in g.nodes.items():
            if name.endswith(".attn.exp"):
                nd["issue"] += d["su_layout_extra_cycles"] * cyc
    if d["use_measured_attention"]:
        # the measured SU softmax chain replaces exp + den + normalize issue (they are one measured process)
        for name, nd in g.nodes.items():
            if name.endswith(".attn.exp"):
                nd["issue"] = d["su_softmax_measured_cycles"] * cyc
                nd["depth"] = 0.0
            elif name.endswith((".attn.den", ".attn.normalize")):
                nd["issue"] = 0.0
    fin = g.solve(True)
    T = fin[b.sink]
    path = g.path(b.sink)
    cats = {}
    for n in path:
        for k_, v in g.contrib[n].items():
            cats[k_] = cats.get(k_, 0.0) + v
    # critical-path time by node family (layer-independent suffix)
    fam = {}
    for n in path:
        nd = g.nodes[n]
        tail = n.split(".", 1)[1] if n.startswith(("L", "E")) and "." in n else n
        t = sum(g.contrib[n].values())
        fam[tail] = fam.get(tail, 0.0) + t
    top = sorted(fam.items(), key=lambda kv: -kv[1])[:25]
    mv = {}
    for name, nd in g.nodes.items():
        u = nd.get("_uarch")
        if u and name.startswith("L20."):
            mv[name] = {k_: (round(v, 1) if isinstance(v, float) else v) for k_, v in u.items()}
    return dict(design=d["name"], ctx=ctx, clock_hz=clock, T_us=T * 1e6, tokens_s=1.0 / T,
                arch_T_us=arch["T_s"] * 1e6, arch_tokens_s=arch["tokens_s_per_user"],
                breakdown_us={k_: round(v * 1e6, 3) for k_, v in sorted(cats.items(), key=lambda kv: -kv[1])},
                critical_path_by_node_us={k_: round(v * 1e6, 3) for k_, v in top},
                layer20_matvecs=mv, _g=g)


# ---------------------------------------------------------------------------------------------------------
# Power ledger (busiest layer die): dynamic energy per token from every priced node's work, network wire energy,
# clock and leakage by area class, HBM interface idle; at the single-user rate and at pipeline saturation.
# Constants: configs/hardware/technology.json (energy.*, power.*), except WIRE_J_PER_BIT_MM (below).
# ---------------------------------------------------------------------------------------------------------
TECH = json.loads((ROOT / "configs/hardware/technology.json").read_text())
_E = TECH["energy"]
_P = TECH["power"]
E_MAC = {k: v["value"] for k, v in _E["mac_energy_j_per_op"].items()}
E_ROM_B = _E["rom_read_j_per_byte"]["value"]
E_SRAM_B = _E["sram_read_j_per_byte"]["value"]
E_HBM_B = _E["hbm_j_per_byte"]["value"]
E_DELIVER_B = _E["operand_delivery_j_per_byte"]["value"]
E_LINK_BIT = 0.5 * (_E["link_j_per_bit"]["ucie_advanced"]["value"] + _E["link_j_per_bit"]["board_serdes_112g"]["value"])
CLOCK_J_MM2 = _P["clock_energy_j_per_mm2_per_cycle"]["value"]
LEAK = {k: v["value"] for k, v in _P["static_leakage_w_per_mm2"].items()}
HBM_IDLE_W_STACK = _P["memory_interface_idle_w_per_stack"]["value"]
E_HBM_IF_B = _P["memory_interface_active_j_per_bit"]["value"] * 8   # on-die PHY/controller share of an HBM byte;
                                                                    # the rest of E_HBM_B dissipates in the stack
COOLING_LIMIT_W = 474.56      # liquid, two-die package (results/arch/v41_hbm_switched.json rom_worst_die_w)
WIRE_J_PER_BIT_MM = 0.1e-12   # ASSUMED: repeated RC global wire, C ~0.2 fF/um, 0.7 V, activity 0.5, x2 repeaters;
                              # a 45 nm survey puts repeated RC wire at ~0.4 pJ/bit/mm (sensitivity row)
SFU_OPS_PER_ELEM = 10         # ASSUMED FP32-op equivalents per exp/sigmoid/divide element
BYTES_PER_WORD = {"fp4": 34, "fp8": 33, "bf16": 32, "fp32": 32}
# ROM field power, MEASURED (W18, 2026-09-30): OpenSTA report_power on W10 p5's routed pair (6_final.odb + SPEF, TT
# 0.7 V, 1.087 GHz, input toggle density 0.5).  A pair = 2 ROM macros + their strip logic.  Busy 229.6 mW (seq 45.1,
# comb 128.0, clock tree 23.7, ROM macros 32.7); idle with the clock running 83.5 mW (clock tree 23.7, flop clock pins
# 27.0, ROM macro clock 32.7, leakage 0.22); idle with an ideal per-pair ICG that also stops the ROM macro clock
# 0.22 mW (leakage: ROM 0.20, cells 0.02).  These replace the area-based clock and leakage of the ROM field (the old
# terms under-stated its clock ~45x); the hub keeps the area-based terms, UNCALIBRATED.
PAIR_W = dict(clock_hz=1.087e9, busy=0.2296, idle_ungated=0.0835, idle_icg=0.00022, leak_rom=0.00020,
              leak_cell=0.00002, placed_pairs=7102,
              src="W18 report_power on W10 p5 routed pair (claude/w18-die-assembly, 2026-09-30); placed pairs = "
                  "results/floorplan/v41_pack_refit_w10_interim.json capacity.used_pair_rows (W10 428c3631)")


# Stage power gating (W18, 2026-09-30): a 16-pair cluster measures 14-17 mV IR; the power-switch rings that hold a
# 10 mV budget take 5% of the cluster area.  Pair outline 513.756 x 131.76 um (W18, from W10 p5's abstract).
SWITCH_RING = dict(cluster_area_frac=0.05, pair_um2=513.756 * 131.76, slots=9931,
                   src="W18 cluster PSM + switch-ring sizing (claude/w18-die-assembly, 2026-09-30); slots = "
                       "v41_pack_refit_w10_interim.json capacity.pair_row_slots")


def switch_ring_ledger():
    """Area of the stage power-switch rings in the ROM field, and whether the re-fit's spare pair slots hold it."""
    N = PAIR_W["placed_pairs"]
    mm2 = SWITCH_RING["cluster_area_frac"] * N * SWITCH_RING["pair_um2"] / 1e6
    slots_needed = N * (1 + SWITCH_RING["cluster_area_frac"])
    return dict(switch_ring_mm2=round(mm2, 2), pair_slots_needed=round(slots_needed),
                pair_slots=SWITCH_RING["slots"], fits_spare_slots=bool(slots_needed <= SWITCH_RING["slots"]),
                basis=SWITCH_RING["src"])


def pair_power(clock):
    """Per-pair ROM-field power at `clock`: leakage, the clock of an idle pair whose clock runs, and the full
    (clock + switching) power of a busy pair, each excluding leakage.  Clock and switching scale linearly with the
    clock from the 1.087 GHz measurement (ASSUMED: same 0.7 V supply)."""
    s = clock / PAIR_W["clock_hz"]
    leak = PAIR_W["idle_icg"]
    return dict(leak=leak, clock=(PAIR_W["idle_ungated"] - leak) * s, busy=(PAIR_W["busy"] - leak) * s)


def busy_pairs(nd):
    """Pairs a weight matvec keeps busy while it issues: the pairs of its holding macros (2 macros a pair)."""
    u = nd.get("_uarch")
    return min(PAIR_W["placed_pairs"], math.ceil(u["holding"] / 2)) if u else 0


def xnet_energy(u, field_mm, wire_j):
    """Energy of a weight matvec outside its pairs: x broadcast over the field, the VM read of x, the partial-sum
    return wires and the VM write of the result (the pairs' own MACs, ROM reads and x capture are in PAIR_W)."""
    xbits = u["K"] * (16 if u["fmt"] == "bf16" else 8)
    return (xbits * field_mm * wire_j + u["K"] * 4 * E_SRAM_B
            + u["rows"] * u["ksplit"] * 32 * (field_mm / FLOORPLAN["cols"] / 2 + 10.0) * wire_j + u["rows"] * 4 * E_SRAM_B)


def power_ledger(d, g, clock, tokens_s, area, wire_j=WIRE_J_PER_BIT_MM):
    """Busiest layer die.  ROM field from the measured pair (PAIR_W): every weight matvec keeps its holding pairs
    busy for its issue time; the other placed pairs idle, clocked (ungated) or stopped by the per-pair ICG.  Hub
    (dedicated units + VM ports) clock and leakage from its area (UNCALIBRATED).  Energy per token = dynamic above
    the clocked-idle floor (field busy excess, off-pair network, hub units, HBM interface, links)."""
    pp = pair_power(clock)
    N = PAIR_W["placed_pairs"]
    stack_e = {}
    per_layer, field_layer, bp_layer, occ_layer, peak_layer = {}, {}, {}, {}, {}
    field_mm = FLOORPLAN["cols"] * 25.628 + 20.0          # broadcast tree wire length (column runs + trunk)
    for name, nd in g.nodes.items():
        L = nd["layer"]
        if L is None or L < 0:
            continue
        e = 0.0
        k = nd["kind"]
        u = nd.get("_uarch")
        if u:
            bp = busy_pairs(nd) * nd["issue"]
            bp_layer[L] = bp_layer.get(L, 0.0) + bp
            field_layer[L] = field_layer.get(L, 0.0) + bp * (pp["busy"] - pp["clock"])
            peak_layer[L] = max(peak_layer.get(L, 0), busy_pairs(nd))
            e += xnet_energy(u, field_mm, wire_j)
        elif k == "matvec" and name.endswith("hc.fn"):
            e += nd["sweep"]["macs"] * E_MAC["fp32"]
        elif k in ("vector", "reduce") and nd.get("_work"):
            cls, n_el = nd["_work"]
            e += n_el * E_MAC["fp32"] * (SFU_OPS_PER_ELEM if cls == "sfu" else 1) + n_el * 4 * 2 * E_SRAM_B
        elif k == "kvscan" and nd.get("_work"):
            cls, macs = nd["_work"]
            e += macs * (E_MAC["fp4"] if cls == "idx" else E_MAC["bf16"])
            if name.endswith("idx.score"):
                hb = int(nd["desc"].split()[2]) * A.IDX_KEY_B
            elif name.endswith(".scores"):
                hb = 640 * A.WIN_ROW_B / 4
            else:
                hb = 0
            e += hb * E_HBM_IF_B
            stack_e[L] = stack_e.get(L, 0.0) + hb * (E_HBM_B - E_HBM_IF_B)
        elif k == "collective":
            e += nd.get("payload", 0) * 8 * E_LINK_BIT
        per_layer[L] = per_layer.get(L, 0.0) + e
        if k not in ("collective", "hop"):
            occ_layer[L] = occ_layer.get(L, 0.0) + nd["issue"]
    lps = 40 / 28
    stages, fstage, bstage, occ, peak = {}, {}, {}, {}, {}
    for L, e in per_layer.items():
        st = int(L / lps)
        stages[st] = stages.get(st, 0.0) + e + field_layer.get(L, 0.0)
        fstage[st] = fstage.get(st, 0.0) + field_layer.get(L, 0.0)
        bstage[st] = bstage.get(st, 0.0) + bp_layer.get(L, 0.0)
        occ[st] = occ.get(st, 0.0) + occ_layer.get(L, 0.0)
        peak[st] = max(peak.get(st, 0), peak_layer.get(L, 0))
    busiest = max(stages, key=stages.get)
    e_tok = stages[busiest]
    e_other = e_tok - fstage[busiest]
    bp_tok = bstage[busiest]                       # busy pair-seconds per token on this die
    stack_tok = sum(v for L, v in stack_e.items() if int(L / lps) == busiest)
    hub_mm2 = area["hub_logic_mm2"]
    sram_mm2 = area["vm_ports"]
    hub_clock_w = CLOCK_J_MM2 * clock * (hub_mm2 + 0.15 * sram_mm2)
    hub_leak_w = hub_mm2 * LEAK["logic"] + sram_mm2 * LEAK["sram_array"]
    field_clock_w = N * pp["clock"]
    field_leak_w = N * pp["leak"]
    idle_w = 4 * HBM_IDLE_W_STACK
    sat_rate = 1.0 / max(occ.values())
    maxp = peak[busiest]

    def mode(icg):
        static = field_leak_w + (0.0 if icg else field_clock_w) + hub_clock_w + hub_leak_w + idle_w
        e = e_tok + (bp_tok * pp["clock"] if icg else 0.0)      # with the ICG a busy pair's clock is dynamic
        p1, ps = static + e * tokens_s, static + e * sat_rate
        # peak: the widest op's pairs busy, the rest idle; the rest of the die at its saturated average
        idle_pair = pp["leak"] + (0.0 if icg else pp["clock"])
        peak_w = (maxp * (pp["busy"] + pp["leak"]) + (N - maxp) * idle_pair + hub_clock_w + hub_leak_w + idle_w
                  + e_other * sat_rate)
        fits = ps <= COOLING_LIMIT_W
        thr = sat_rate if fits else max(0.0, (COOLING_LIMIT_W - static) / e)
        return dict(static_w=round(static, 1), energy_per_token_uJ=round(e * 1e6, 2),
                    total_w_single_user=round(p1, 1), total_w_saturated=round(ps, 1),
                    peak_w_saturated=round(peak_w, 1), fits_cooling_saturated=bool(fits),
                    peak_fits_cooling=bool(peak_w <= COOLING_LIMIT_W),
                    cooling_throttled_tokens_s_per_stage=round(thr, 1))
    ung, icg = mode(False), mode(True)
    out = dict(busiest_stage=busiest, energy_per_token_uJ=round(e_tok * 1e6, 2),
               hbm_stack_energy_per_token_uJ=round(stack_tok * 1e6, 2),
               hbm_stack_w_saturated=round(stack_tok / max(occ.values()), 1),
               dynamic_w_single_user=round(e_tok * tokens_s, 1), dynamic_w_saturated=round(e_tok * sat_rate, 1),
               saturated_tokens_s_per_stage=round(sat_rate, 1),
               clock_w=round(field_clock_w + hub_clock_w, 1), leakage_w=round(field_leak_w + hub_leak_w, 1),
               hbm_idle_w=idle_w,
               total_w_single_user=ung["total_w_single_user"], total_w_saturated=ung["total_w_saturated"],
               cooling_limit_w=COOLING_LIMIT_W, fits_cooling_saturated=ung["fits_cooling_saturated"],
               field=dict(basis="MEASURED per pair (PAIR_W, W18)", placed_pairs=N,
                          pair_w=dict(leak=round(pp["leak"], 5), clock=round(pp["clock"], 5), busy=round(pp["busy"], 5)),
                          clock_w=round(field_clock_w, 1), leakage_w=round(field_leak_w, 2),
                          busy_pair_us_per_token=round(bp_tok * 1e6, 1),
                          busy_pairs_equiv_single_user=round(bp_tok * tokens_s, 1),
                          busy_pairs_equiv_saturated=round(bp_tok * sat_rate, 1),
                          peak_busy_pairs=maxp, dynamic_energy_per_token_uJ=round(fstage[busiest] * 1e6, 2)),
               hub=dict(basis="area x technology.json clock / leakage constants, UNCALIBRATED",
                        clock_w=round(hub_clock_w, 1), leakage_w=round(hub_leak_w, 1)),
               ungated=ung, per_pair_icg=icg, switch_rings=switch_ring_ledger(),
               wire_j_per_bit_mm=wire_j)
    return out

UNIT = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())["unit_areas_um2"]
SRAM_256B_MACRO = dict(um2=174.744 * 70.47, bits=262144, width=256)   # ot_sram_1r1w_1024x256_m2_r2c2
FLOORPLAN = dict(die_mm2=815.0, rom_field_strip_mm2=132.34, hub_mm2=233.7, cols=71, rows=190,
                 spine_tracks=1153, over_rom_tracks_per_100um=1128, pair_pitch_um=418.608,
                 src="results/floorplan/v41_pack_expanded_woa.json (claude/w1-v41-floorplan 3756a5bc)")


def area_ledger(d: dict):
    """Logic and memory area (mm2) the design instantiates, by resource.  ROM macros are placed in the W1
    ROM field; lanes must fit its MAC strips (132.34 mm2); dedicated units must fit the hub (233.7 mm2)."""
    n = d["macros"]
    striped = d["mapping"] == "striped"
    nb = (d.get("bf16_stripe_macros") or n) if striped else 64
    out = dict(
        rom_macros=n * ROM_MACRO_UM2,
        blockdot_lanes=(n * 2 * UNIT["blockdot_um2"]) if striped else (d.get("weight_macs_die") or 264960) / 32 * UNIT["blockdot_um2"],
        bf16_lanes=(nb * 16 * UNIT["mac_bf16_um2"]) if striped else (d.get("bf16_macs_die") or 41664) * UNIT["mac_bf16_um2"],
        capture_regs=n * 274 * DFF_UM2,
        chunk_partials=(n * 8 * 32 * DFF_UM2) if striped else 0.0,   # 8 rows x FP32 chunk partial per element
        # K-split partials meet in the return tree: about one FP32 adder per macro pair (UNIT fp32_add_um2)
        return_adders=(n / 2 * UNIT["fp32_add_um2"]) if striped and d.get("row_split") == "ksplit" else 0.0,
        # W10: a BF16 element completes 16 chunk sums a cycle: a 15-adder tree plus 128 chain registers (FP32);
        # an FP4/FP8 element: one chain adder per block-dot lane plus 8 chain registers each
        bf16_chain=(nb * (15 * UNIT["fp32_add_um2"] + 128 * 32 * DFF_UM2)) if striped else 0.0,
        blockdot_chain=(n * 2 * (UNIT["fp32_add_um2"] + 8 * 32 * DFF_UM2)) if striped else 0.0,
        indexer=d["idx_macs"] / 32 * UNIT["blockdot_um2"],
        attention=d["att_macs"] * UNIT["mac_bf16_um2"],
        su_lanes=d["su_lanes"] * UNIT["su_light_lane_um2"],
        sfu_lanes=d["sfu_lanes"] * UNIT["su_lane_um2"],
        vm_ports=(math.ceil(d["vm_read_elems"] * 32 / 256) + math.ceil(d["vm_write_elems"] * 32 / 256))
        * SRAM_256B_MACRO["um2"],
    )
    out = {k: v / 1e6 for k, v in out.items()}
    strip = out["blockdot_lanes"] + out["bf16_lanes"] + out["capture_regs"] + out["chunk_partials"] \
        + out["return_adders"] + out["bf16_chain"] + out["blockdot_chain"]
    hub = out["indexer"] + out["attention"] + out["su_lanes"] + out["sfu_lanes"] + out["vm_ports"] \
        + d.get("su_vm_ports_mm2", 0.0)
    out["rom_field_strip_used_mm2"] = strip
    out["rom_field_strip_avail_mm2"] = FLOORPLAN["rom_field_strip_mm2"]
    out["hub_logic_mm2"] = hub
    out["hub_avail_mm2"] = FLOORPLAN["hub_mm2"]
    out["fits"] = bool(strip <= FLOORPLAN["rom_field_strip_mm2"] and hub <= FLOORPLAN["hub_mm2"])
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out.items()}


def network_ledger(d: dict, clock: float):
    """Activation broadcast and result return networks of the ROM field.

    x broadcast: vm_read_elems per cycle leave the VM as FP8 (BF16 for wo_a: 16 bit) and reach every column
    pair of the field (71 columns; W1 pack).  Result return: vm_write_elems FP32 per cycle arrive at the VM.
    Wires at the VM edge must fit the spine corridor's tracks; each column's vertical run fits over the ROM
    on M6/M8.  Registers: one per register segment along every column run and along the trunk."""
    cols = FLOORPLAN["cols"]
    xb = d["vm_read_elems"] * 16
    rb = d["vm_write_elems"] * 32
    seg_um = ((1e12 / clock) - UNCERTAINTY_PS - WIRE_OVERHEAD_PS) / WIRE_PS_PER_UM
    col_len_um = 25628.0
    trunk_um = d["bcast_um"]["expert"]
    per_col_ret = max(32, rb // cols * 4)                # a column bursts at 4x its fair share of the return
    col_wires = xb + per_col_ret + 64
    col_tracks = FLOORPLAN["over_rom_tracks_per_100um"] * FLOORPLAN["pair_pitch_um"] / 100 * 0.5
    trunk_wires = xb + rb + 64
    spines = math.ceil(trunk_wires / (FLOORPLAN["spine_tracks"]))
    reg_bits = (xb + per_col_ret) * cols * math.ceil(col_len_um / seg_um) + (xb + rb) * math.ceil(trunk_um / seg_um)
    return dict(x_bits_per_cycle=xb, return_bits_per_cycle=rb, trunk_wires=trunk_wires,
                spine_corridors_needed=spines, column_wires=col_wires, column_tracks=round(col_tracks),
                column_utilisation=round(col_wires / col_tracks, 3), register_bits=reg_bits,
                register_mm2=round(reg_bits * DFF_UM2 / 1e6, 3), stages_trunk=wire_cycles(trunk_um, clock))


# ---------------------------------------------------------------------------------------------------------
# Dedicated units (W11): each unit is ONE element replicated to the count the design needs.  Same schema for
# every unit: element (RTL module + parameters), replica count (must be whole), ports per element and in total,
# storage, area per element (a hardened element when one exists, else a marked estimate), and the per-op cycles
# of the L20 (busiest scanning layer) ops at the design's context, which is what evaluate() prices.
# Shared by the V4.1 ROM and V4.1 HBM dies (the hub region of the W1 floorplan).
# ---------------------------------------------------------------------------------------------------------
HBM_PC_SECTORS_PER_CYCLE = (1e12 / 1.0339e9) / 1024.0
                                                # one 32-B burst per 1,024 ps per pseudo-channel (HBM3E 1 TB/s over
                                                # 32 PCs; rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv) at 967.2 ps/cycle
HBM_PCS_DIE = 4 * 32                            # four stacks x 32 pseudo-channels
SECTOR_B = 32
DEDICATED = dict(
    indexer=dict(
        element="ot_hdc_v41x_idx_score_slice #(NK=4, NB=4, IH=32): 4 keys x 32 heads x 128 FP4 dims per cycle "
                "(16 x ot_hdc_v41x_idx_chunk + 4 x ot_hdc_v41x_idx_tail); rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv",
        sub_element="ot_hdc_v41x_idx_chunk #(NB=4, NKT=1): 8 heads x 1 key, 32 exact FP4 32-block dots = 1,024 MACs",
        macs_per_element=4 * 32 * 128, keys_per_element=4,
        key_bits_in=4 * 544,                    # 4 keys x (512 FP4 code bits + 4 UE8M0 scales + pad) per cycle
        query_bits=17920,                       # 32 heads x (128 FP4 + 4 scales + BF16 weight), one copy per slice
        meta_fifo_bits=64 * 35,                 # score-metadata FIFO (index, mask, last), IW=30
        out_bits=4 * (16 + 30),                 # BF16 score + global index per key
        latency=48,                             # first score after the key beat (results/rtl/v41_idx_score_slice.json)
        area_est_um2=16 * 32 * UNIT["blockdot_um2"] + 4 * 17310.0,
        area_basis="ESTIMATE until hardened: 512 FP4 block dots at the closed FP8/FP4 weight lane's area "
                   "(ot_hdc_blockdot, 2,511 um2 per 32-product lane) + the per-key head-sum (idx_hsum 17,310 um2 "
                   "closed, per key of 4)",
        hardened_record="results/physical_abi3/asap7/hdc/v41x/w11/idx_chunk/physical.json",
        hardened_scale=16,                      # 16 chunks per NK=4 slice (+ 4 tails, 1% of a chunk)
    ),
    idx_reader=dict(
        element="per-pseudo-channel key reader: request generator + reorder slice of ot_hdc_v41x_idx_kctl / "
                "_kstream_range (one per HBM3E pseudo-channel), 64-key collector ot_hdc_v41x_idx_shard_quarter_collect",
        replicas_fixed=HBM_PCS_DIE,
        bytes_per_key=A.IDX_KEY_B, sector_B=SECTOR_B,
        peak_sectors_per_cycle=HBM_PCS_DIE * HBM_PC_SECTORS_PER_CYCLE,
        collector_out_bits=64 * 544,
        measured_record="results/rtl/hdc_v41x_idx_four_stack_verilator_collector_pipeline.json",
        measured_sectors_per_cycle=60.04,       # 557,056 sectors in 9,278 cycles (262,144 keys)
    ),
    attention=dict(
        element="ot_hdc_v41x_attn_tile #(H=16, TD=32): 16 heads x 32 BF16 products per cycle, stationary banks; "
                "rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv",
        products_per_element=16 * 32, H=16, D=512, TD=32,
        q_bits=512 * 16, kv_row_bits=16 * 265, p_word_bits=32 * 16, pv_out_bits_per_tile=16 * 32,
        area_est_um2=16 * 32 * UNIT["mac_bf16_um2"],
        area_basis="ESTIMATE until hardened: 512 pipelined BF16 MACs (ot_mac_bf16_fp32_pipe 509 um2)",
        hardened_record="results/physical_abi3/asap7/hdc/v41x/w11/attn_tile/physical.json",
        hardened_scale=1,
        measured_record="results/rtl/v41_full_attention_numeric/result.json",
        measured_job_cycles_pwords1=609, measured_pv_window_pwords1=(248, 559),
        # the two-word probability loader (claude/w11-attn c80877d8, results/rtl/w11_attn_ploader.json): exact on all
        # four full-geometry cases; with 2 probability words/cycle upstream (1/cycle gives back the PWORDS=1 cycles)
        measured_job_cycles_pwords2={640: 449, 128: 193}, measured_pv_window_pwords2=(240, 399),
        measured_verify6_cycles={1: 3389, 2: 2429},
    ),
    stream_unit=dict(
        element="ot_hdc_v41x_vec_lane (KIND 0 light / 1 SFU / 2 full lane 0) under ONE controller and ONE "
                "chunk8 reducer (ot_hdc_v41x_vec, ot_hdc_v41x_vec_red); rtl/hdc/v41x/ot_hdc_v41x_vec*.sv",
        read_streams=4, AW=24,
        area_est_light_um2=UNIT["su_light_lane_um2"], area_est_sfu_um2=UNIT["su_lane_um2"],
        area_basis="ESTIMATE until hardened: light lane 1.5 x (2 fp32 mul + 3 fp32 add); SFU lane = the "
                   "synthesis-only ot_hdc_v41_su_lane",
        hardened_record_light="results/physical_abi3/asap7/hdc/v41x/w11/vec_light1024r/physical.json",
        hardened_record_sfu="results/physical_abi3/asap7/hdc/v41x/w11/vec_sfu1024r/physical.json",
        measured_record="results/rtl/v41x_su_softmax.json", measured_softmax_t640_n16_m8=3280,
    ),
)


SU_OP_ACCEPT = 6          # measured: SU accept -> first emit per op (results/rtl/w11_su_spec.json, claude/w11-su)
# SU placement (W11 SU worker derivation): lane array 11.96 mm2 as a square of side 3,458 um; controller at its
# centre -> farthest lane (corner) 3,458 um Manhattan; results return to HUB_VM on the SU region's west edge,
# farthest lane -> VM edge 3,458 + 392 um
SU_FARTHEST_LANE_UM = 3458.0
SU_RETURN_UM = 3850.0
SU_BCAST_STAGES_W1 = wire_cycles(SU_FARTHEST_LANE_UM, 1e12 / 920, WIRE_PS_PER_UM_LOADED)   # = 4
SU_RET_STAGES_W1 = wire_cycles(SU_RETURN_UM, 1e12 / 920, WIRE_PS_PER_UM_LOADED)            # = 5


def _hardened_um2(rel):
    p = ROOT / rel
    if not p.exists():
        return None, None
    dsg = json.loads(p.read_text()).get("design", {})
    return dsg.get("area_um2"), dict(fmax_mhz=round((dsg.get("fmax_hz") or 0) / 1e6, 1), closed=dsg.get("closed"))


def _su_softmax_ops(N, M, heads=16, T=640, hd=512):
    """The attention softmax chain as SU ops (tools/rtl_v41x_su_softmax_campaign.fixture), laid out by the RTL's
    own layout rule (tools/rtl_hdc_v41x_vec_campaign.layout): vectors per op and emit->result depth."""
    import rtl_hdc_v41x_vec_campaign as C
    import hdc_isa_v41 as I
    base = C.op_defaults()
    common = dict(nout=heads, nin=T, abase=0, aso=T, asi=1, dst=I.DST_VM, obase=0, oso=T, osi=1)
    ops = dict(
        max=dict(base, **common, m1=I.M1_AIMM, red=I.RED_MAX, rbase=16384, rso=1),
        exp_sum=dict(base, **common, bbase=16384, bso=1, ad=I.AD_NEGB, sfu=I.SFU_EXP, red=I.RED_SUM, rbase=16400,
                     rso=1),
        sink=dict(base, nout=1, nin=heads, asrc=I.SRC_CLO, asi=1, bbase=16384, bsi=1, ad=I.AD_NEGB, sfu=I.SFU_EXP,
                  cbase=16400, csi=1, e1=I.E1_ADDC, dst=I.DST_VM, obase=16416, osi=1),
        divide=dict(base, nout=heads, nin=hd, abase=17408, aso=hd, asi=1, bbase=16416, bso=1, m1=I.M1_DIVB, rnd=1,
                    dst=I.DST_VM, obase=17408, oso=hd, osi=1))
    out = {}
    for k, f in ops.items():
        lay = C.layout(f, N, M)
        out[k] = dict(vectors_per_row_set=lay["nv"], vectors=lay["nv"], depth=lay["dR"] if f["red"] else lay["dP"], vw=lay["vw"],
                      span=bool(lay["span"]), bad=bool(lay["bad"]))
    return out


def dedicated_ledger(d: dict, ctx: int = 1048576, layer: int = 20, positions: int = 1):
    """Element, replicas, ports, area and per-op cycles of the four dedicated units of design `d`.
    positions > 1: an MTP verify pass time-multiplexed on the same lanes (m = 1): the index keys, KV rows and
    probabilities of the block are read once, every position's MACs and stream elements are issued in turn."""
    E = A._env()
    c, clock = E["c"], E["clock"]
    ops, meta = A.ops_of_layer(c, layer, ctx)
    keys = int(meta["n_scan"] / 4) if meta["n_scan"] else 0          # keys per die (tensor group 4)
    T = meta["T"]
    out, flags = {}, []
    # -- indexer
    u = DEDICATED["indexer"]
    rep = d["idx_macs"] / u["macs_per_element"]
    if abs(rep - round(rep)) > 1e-9:
        flags.append(f"indexer: idx_macs {d['idx_macs']} is {rep:.3f} NK=4 slices (not whole)")
    rep_i = math.ceil(rep)
    kpc = rep_i * u["keys_per_element"]
    a_h, q_h = _hardened_um2(u["hardened_record"])
    a_el = a_h * u["hardened_scale"] if a_h else u["area_est_um2"]
    reader_Bpc = d["idx_reader_Bpc"] or min(A.ROM_DIE_HBM_BPS / clock, 1e18)
    t_mac = positions * math.ceil(keys / kpc) if keys else 0
    t_rd = keys * A.IDX_KEY_B / reader_Bpc if keys else 0.0
    out["indexer"] = dict(
        element=u["element"], sub_element=u["sub_element"], replicas=rep_i, keys_per_cycle=kpc,
        macs_per_cycle=rep_i * u["macs_per_element"],
        ports_per_element=dict(key_in_bits=u["key_bits_in"], score_out_bits=u["out_bits"], query_bits=u["query_bits"]),
        ports_total=dict(key_in_bits=rep_i * u["key_bits_in"], score_out_bits=rep_i * u["out_bits"]),
        storage_bits=rep_i * (u["query_bits"] + u["meta_fifo_bits"]),
        area_element_um2=round(a_el), area_basis="hardened x16 chunks" if a_h else u["area_basis"],
        hardened=q_h, area_mm2=round(rep_i * a_el / 1e6, 3),
        ops={f"L{layer}.attn.idx.score": dict(keys=keys, positions=positions, t_mac=t_mac, t_reader=round(t_rd, 1),
                                               issue=round(max(t_mac, t_rd), 1), latency=u["latency"],
                                               bind="reader" if t_rd > t_mac else "mac")})
    # -- index reader
    u = DEDICATED["idx_reader"]
    need_spc = reader_Bpc / u["sector_B"]
    out["idx_reader"] = dict(
        element=u["element"], replicas=u["replicas_fixed"], target_bytes_per_cycle=round(reader_Bpc, 1),
        target_sectors_per_cycle=round(need_spc, 2), hbm_peak_sectors_per_cycle=round(u["peak_sectors_per_cycle"], 2),
        per_pc_target_sectors_per_cycle=round(need_spc / u["replicas_fixed"], 4),
        measured_sectors_per_cycle=u["measured_sectors_per_cycle"], measured_record=u["measured_record"],
        collector_out_bits=u["collector_out_bits"],
        ops={f"L{layer}.attn.idx.score(read)": dict(sectors=keys * A.IDX_KEY_B // u["sector_B"],
                                                     cycles_at_target=round(keys * A.IDX_KEY_B / reader_Bpc, 1),
                                                     cycles_measured=round(keys * A.IDX_KEY_B / u["sector_B"]
                                                                           / u["measured_sectors_per_cycle"], 1))})
    # -- attention
    u = DEDICATED["attention"]
    per_row = u["H"] * u["D"]
    NL = d["att_macs"] / per_row
    if abs(NL - round(NL)) > 1e-9:
        flags.append(f"attention: att_macs {d['att_macs']} is NL={NL:.3f} rows/cycle (not whole)")
    NL = max(1, round(NL))
    tiles = NL * u["D"] // u["TD"]
    pwords = d.get("att_pwords", 1)           # 2 = the two-word probability loader (W11)
    PB, DPT = u["H"], u["D"] // tiles                 # p words per TD-row block; p.v beats per block
    beats = math.ceil(T / NL)
    load_per_blk = math.ceil(PB / pwords)
    pv_cycles = math.ceil(T / u["TD"]) * max(DPT, load_per_blk)
    a_h, q_h = _hardened_um2(u["hardened_record"])
    a_el = a_h if a_h else u["area_est_um2"]
    lvt = int(math.log2(u["TD"] // 8))
    out["attention"] = dict(
        element=u["element"], replicas=tiles, rows_per_cycle=NL, products_per_cycle=tiles * u["products_per_element"],
        ports_total=dict(q_bits=u["q_bits"], kv_in_bits=NL * u["kv_row_bits"], p_in_bits=pwords * u["p_word_bits"],
                         pv_out_bits=tiles * u["pv_out_bits_per_tile"]),
        stationary_banks=4 if pwords == 2 else 3,
        area_element_um2=round(a_el), area_basis="hardened" if a_h else u["area_basis"], hardened=q_h,
        area_mm2=round(tiles * a_el / 1e6, 3),
        ops={f"L{layer}.attn.scores": dict(beats=beats, positions=positions, issue=positions * beats,
                                           tile_latency=27 + 3 * lvt),
             f"L{layer}.attn.pv": dict(beats=beats, p_words=math.ceil(T * u["H"] * 16 / u["p_word_bits"]),
                                       pwords_per_cycle=pwords, positions=positions, issue=positions * pv_cycles,
                                       note="p.v issue = blocks x max(beats/block, p-load cycles/block)")},
        measured_job_cycles=(u["measured_job_cycles_pwords2"].get(T) if pwords == 2
                             else (u["measured_job_cycles_pwords1"] if T == 640 else None)),
        measured=dict(record=u["measured_record"], record_pwords2="results/rtl/w11_attn_ploader.json",
                      job_cycles_pwords2=u["measured_job_cycles_pwords2"], verify6=u["measured_verify6_cycles"],
                      job_cycles_pwords1=u["measured_job_cycles_pwords1"],
                      pv_window_pwords1=u["measured_pv_window_pwords1"]))
    # -- stream unit
    u = DEDICATED["stream_unit"]
    N, M = d["su_lanes"], d["sfu_lanes"]
    sm = _su_softmax_ops(N, M, T=T)
    bst, rst = d.get("su_bcast_stages", 0), d.get("su_ret_stages", d.get("su_bcast_stages", 0))
    for v in sm.values():
        v["vectors"] *= positions
    aL, qL = _hardened_um2(u["hardened_record_light"])
    aS, qS = _hardened_um2(u["hardened_record_sfu"])
    light = aL or u["area_est_light_um2"]
    sfu = aS or u["area_est_sfu_um2"]
    ports = dict(read_bits=u["read_streams"] * N * 32, gather_bits=N * 32, write_bits=N * 32, kv_write_bits=N * 32,
                 result_bits=N // 8 * 32)
    banks = {k: math.ceil(v / 256) for k, v in ports.items()}
    out["stream_unit"] = dict(
        element=u["element"], replicas=dict(light=N - M, sfu=M - 1, full=1), lanes=N, sfu_lanes=M,
        ports_total=ports, vm_banks_256b=banks,
        area_element_um2=dict(light=round(light), sfu=round(sfu)),
        area_basis=("hardened" if aL and aS else u["area_basis"]), hardened=dict(light=qL, sfu=qS),
        area_mm2=round(((N - M) * light + M * sfu) / 1e6, 3),
        ops={f"L{layer}.attn.softmax.{k}": v for k, v in sm.items()},
        softmax_issue_vectors=sum(v["vectors"] for v in sm.values()),
        # a dependent op pays its issue, its pipeline depth, the broadcast tree to the farthest lane and the
        # result return to the VM (su_bcast_stages / su_ret_stages, from the W1 hub placement; root 2026-09-29)
        su_bcast_stages=bst, su_ret_stages=rst,
        softmax_chain_cycles=sum(v["vectors"] + v["depth"] + bst + rst + SU_OP_ACCEPT for v in sm.values()),
        measured=dict(record=u["measured_record"], t640_n16_m8=u["measured_softmax_t640_n16_m8"]))
    hub = sum(out[k]["area_mm2"] for k in ("indexer", "attention", "stream_unit"))
    return dict(design=d["name"], ctx=ctx, layer=layer, T=T, positions=positions, keys_per_die=keys, units=out,
                hub_logic_mm2=round(hub, 3), hub_avail_mm2=FLOORPLAN["hub_mm2"], discrepancies=flags)


# ---------------------------------------------------------------------------------------------------------
# Qwen3-8B ROM die (O4: two reticles, TP-2, INT8 weights, G weight-lane groups of 16 lanes per die)
# ---------------------------------------------------------------------------------------------------------
# The element is already weight-stationary: a group owns its ROM column and 16 lanes; W5 hardens a tile of
# 4 groups (22 code macros ot_rom_4096x266_m8, 4 KV-slice SRAMs).  The architecture replay
# (tools/arch_budget_qwen3.as_built -> tools/hdc_timing.simulate, calibrated 32,191 vs 32,196 RTL cycles) has
# single-cycle wires.  The microarchitecture adds, from W5's floorplan (docs/QWEN_O4_FLOORPLAN.md,
# results/floorplan/qwen_o4/floorplan.json on claude/w5-qwen-physical e93d75ef):
QWEN_WIRE = dict(
    x_stages_extra=24,        # VM -> farthest group 27.0 mm: 25 register stages vs the RTL's 1
    vm_conflict_reg=1,        # registered conflict/bank decode in the 8-bank VM (W5 VM cut: -699 ps without)
    result_write_extra=2,     # result write path (434 cycles / 217 ME ops)
    tree_extra_per_token=1728,  # split-tree compaction beyond the RTL's levels (o/down 1440 + qkv 252 + gu 36)
    ucie_wire_per_token=1898,   # farthest tile -> west UCIe and back, 13 stages each way, 146 crossings
)
# W12 floorplan (tools/qwen_rom_floorplan_w12.py, G=6144, one hardened tile replicated, VM and engine top at the
# spine centre, 0.76 ps/um): per matrix-engine op the instruction/x broadcast, the tree levels above the tile and
# the tree words' return to the spine are register stages of the RTL array (ot_qwen_me_array: BD, NWS, TWS, ORD).
# They replace W5's x + conflict + write per-op terms and its per-token tree term; the UCIe crossing stays.
QWEN_WIRE_W12 = dict(
    bd=31,                    # instruction broadcast + x network, incl. the tile input register and XVM
    xvm=1,                    # registered VM conflict stage (inside bd)
    nws=4, tree_levels=4,     # four upper tree levels (3..6) inside a 16-tile block, 4 stages each
    tws=30,                   # level-6 words -> spine top
    ord=4,                    # result write -> VM
    me_lat_extra=31 + 4 * 4 + 30 + 4,   # 81 cycles on every ME op's result
)
# Vector-memory x read (W12 gap): the engine's x chunk port reads S distinct elements at every K step (IL cycles,
# x held across the slots) or every cycle (x varies with the slot, xjs != 0: the attention ops).  The W5 VM
# (8 skew banks x 4 slices x 3 rows of ot_sram_1r1w_512x128) delivers 32 x 128 bits = 128 FP32 a cycle.
VM_MACRO = dict(name="ot_sram_1r1w_512x128_m4_r2c2", um2=174.096 * 29.70, elems_per_read=4, words=512)
VM_ELEMS_QWEN = 177808


def vm_banking(read_elems):
    """macros (and area) for a VM that reads `read_elems` FP32 a cycle and holds VM_ELEMS_QWEN"""
    ports = math.ceil(read_elems / VM_MACRO["elems_per_read"])
    depth = math.ceil(VM_ELEMS_QWEN / (ports * VM_MACRO["elems_per_read"]))
    rows = math.ceil(depth / VM_MACRO["words"])
    macros = ports * rows
    return dict(read_elems=read_elems, macros=macros, area_mm2=round(macros * VM_MACRO["um2"] / 1e6, 3),
                capacity_elems=macros * VM_MACRO["words"] * VM_MACRO["elems_per_read"])


def qwen_x_read_stall(G, su_width, ctx, read_elems):
    """Cycles a token adds when the engine's x reads are limited to `read_elems` a cycle (bandwidth bound,
    fully exposed: the engine never stalls in the RTL, so any shortfall delays its issue)."""
    import arch_budget_qwen3 as Q
    import hdc_isa as I
    import hdc_program as P
    import hdc_timing as T
    sw0 = I.SU_WIDTH
    I.SU_WIDTH = su_width
    try:
        prog = P.build_program(Q.capped_layout(G, None, Q.die_shape()))
    finally:
        I.SU_WIDTH = sw0
    d = T.dyn_values(ctx - 1, groups=G, H=Q.Q["H"], half=Q.Q["HD"] // 2, HD=Q.Q["HD"])
    il = I.INTERLEAVE
    stall = 0
    per_op = []
    for f in prog:
        if f.get("unit") != I.UNIT_ME:
            continue
        f = {n: f.get(n, 0) for n, _ in I.FIELDS}
        rounds, kk = T.me_loop(f, d, ctx - 1, G)
        S = 1 << f["me_split"]
        need = math.ceil(S / read_elems)
        issue = rounds * kk * il
        xc = rounds * kk * il * need if f["me_xjs"] else rounds * kk * max(il, need)
        extra = max(0, xc - issue)
        stall += extra
        if extra:
            per_op.append((f["me_wsrc"], S, rounds, kk, extra))
    return stall, per_op


QWEN_AREA = dict(
    array_mm2=560.0,          # tile array area after PHYs, UCIe, spine, corridors (W5: 1,225 x 0.4512 mm2 as
                              # instantiated, 1,470 x 0.3857 pruned)
    code_macros=33792,        # 11 banks of 4096x266 per group-pair column at G=6144 (W5 rung 2)
    macro_um2=121.824 * 62.91,
    macro_pack=1.31,          # tile macro footprint / macro area: W5 tile 976.3 x 462.2 um = 22 code + 4 KV
                              # macros x pack + 4 x 26,250 / 0.5 of logic
    logic_group_um2=26250.0,  # W5 tile logic ESTIMATE 105,000 um2 / 4 groups, placed at 50% utilisation
    logic_group_pruned_um2=18063.0,  # without unreachable fmul / tree registers (calibrated to W5 pruned tile)
    kv_sram_group_um2=94.824 * 41.04,
    util=0.5,
    port_tiles=24,
)


QWEN_EXCHANGE = "q256d64"   # ROOT DECISION 2026-09-29 (W15): the TP-2 oneshot at 256 lanes / depth 64, measured
                            # 71 cycles per all-reduce end to end (results/rtl/w15_collectives.json)
QWEN_EXCHANGE_AS_BUILT = "q16d16"   # ot_qwen_tp_host_binding's engine (16 lanes, depth 16)


def qwen_eval(G=6144, su_width=1024, wires=True, pruned=False, ctx=8192, drafter=False, wire_model="w5",
              x_read_elems=None, exchange="default"):
    """wire_model "w5": W5's per-op x/conflict/write terms plus per-token tree and UCIe terms; "w12": the W12
    floorplan's per-op engine latency (QWEN_WIRE_W12, tree included) plus the UCIe term.  x_read_elems: the VM's
    x-read width (None: unconstrained, as the RTL's per-group x ports); stalls are added per token."""
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    Q.CLOCK[0] = Q.clock_hz()
    k0 = dict(T.K)
    # W5 derived its wire terms with the unloaded fit (0.5997 ps/um); re-derive the x broadcast from its
    # 27.0 mm distance with the loaded channel constant and scale the tree/UCIe wire terms by the same ratio
    x_extra = wire_cycles(27000.0, Q.clock_hz(), WIRE_PS_PER_UM_LOADED) - 1
    wscale = x_extra / QWEN_WIRE["x_stages_extra"]
    try:
        if wires and wire_model == "w12":
            T.K["me_lat"] = k0["me_lat"] + QWEN_WIRE_W12["me_lat_extra"]
        elif wires:
            T.K["me_lat"] = k0["me_lat"] + x_extra + QWEN_WIRE["vm_conflict_reg"] \
                + QWEN_WIRE["result_write_extra"]
        r = Q.as_built(ctx, groups=G, su_width=su_width)
    finally:
        T.K.clear()
        T.K.update(k0)
    if wires and wire_model == "w12":
        per_token = round(QWEN_WIRE["ucie_wire_per_token"] * wscale)
    elif wires:
        per_token = round((QWEN_WIRE["tree_extra_per_token"] + QWEN_WIRE["ucie_wire_per_token"]) * wscale)
    else:
        per_token = 0
    x_stall = qwen_x_read_stall(G, su_width, ctx, x_read_elems)[0] if x_read_elems else 0
    cycles = r["cycles"] + per_token + x_stall
    exch_measured = None
    if exchange == "default":        # the measured exchange includes its die wires: ideal-wire rows keep the priced one
        exchange = QWEN_EXCHANGE if wires else None
    if exchange:
        # W15: replace the priced 73 exchanges (hop + transfer + add each) and their die-wire term with the RTL
        # measurement of the token's 73 exchanges, issue -> last result, wires and link layer included
        ucie_w = round(QWEN_WIRE["ucie_wire_per_token"] * wscale) if wires else 0
        exch_measured = w15_record()["configs"][exchange]["exchanges"]["token_exchange_cycles"]
        cycles += exch_measured - Q.tp_exchanges(Q.CLOCK[0])["exchange_cycles"] - ucie_w
    a = QWEN_AREA
    tiles = G / 4
    # integer banking (W12): a group-pair column holds its words in whole 4096-deep banks; 11 at G=6144,
    # 14 at G=5120 (tools/qwen_o4_rom_placement.py QWEN_O4_GROUPS); other G scale the column words
    # USER DECISION 2026-09-29: the Qwen ROM die is AR only, so the DFlash drafter (fc + 5 layers) is not in ROM.
    # Target-only column words: 38,880 at G=6144 (W5), 48,736 at G=5120 (W12); drafter adds 5,600 / 6,880.
    words = (38880 * 6144 / G) + ((5600 * 6144 / G) if drafter else 0)
    exact = {(6144, False): 38880, (6144, True): 44480, (5120, False): 48736, (5120, True): 55616}
    words = exact.get((G, drafter), words * 1.02)          # other G: scaled, +2% tile padding
    banks = math.ceil(words / 4096)
    macros_tile = 2 * banks
    # result-port groups = G / smallest split: 96 at G=6144 (S=64), 40 at G=5120 (S=128); their tiles sit in
    # the spine, and fewer of them return spine area to the array (W12)
    port_tiles = {6144: 24, 5120: 10}.get(G, 24)
    logic = a["logic_group_pruned_um2"] if pruned else a["logic_group_um2"]
    tile_um2 = macros_tile * a["macro_um2"] * a["macro_pack"] + 4 * (logic / a["util"]
                                                                     + a["kv_sram_group_um2"] * a["macro_pack"])
    need_mm2 = (tiles - port_tiles) * tile_um2 / 1e6          # port tiles sit in the spine (W5)
    avail = a["array_mm2"] + (a["port_tiles"] - port_tiles) * tile_um2 / 1e6  # spine area freed by fewer ports
    return dict(G=G, su_width=su_width, wires=wires, pruned=pruned, ctx=ctx, drafter=drafter, cycles=cycles,
                exchange=exchange, exchange_cycles_measured=exch_measured,
                arch_cycles=r["cycles"], tokens_s=Q.CLOCK[0] / cycles, clock_hz=Q.CLOCK[0],
                tile_um2=round(tile_um2), tiles=tiles, array_need_mm2=round(need_mm2, 1),
                array_avail_mm2=round(avail, 1), fits=need_mm2 <= avail, banks_per_column=banks,
                port_tiles=port_tiles, wire_model=wire_model if wires else None, x_read_elems=x_read_elems,
                x_read_stall_cycles=x_stall, vm_banking=vm_banking(x_read_elems) if x_read_elems else None,
                unit_busy=r["unit_busy"], stalls=r["sequencer_stalls"])


def qwen_rows():
    rows = [qwen_eval(6144, 1, wires=False, exchange=QWEN_EXCHANGE_AS_BUILT) | dict(design="qwen_as_built_rtl_no_wires"),
            qwen_eval(6144, 1024, wires=False) | dict(design="qwen_arch"),
            qwen_eval(6144, 1024) | dict(design="qwen_arch_plus_wires"),
            qwen_eval(6144, 1024, pruned=True) | dict(design="qwen_pruned_plus_wires")]
    for G in (3072, 4096, 4608, 5120, 5632, 6144):
        for pr in (False, True):
            rows.append(qwen_eval(G, 1024, pruned=pr) | dict(design=f"qwen_G{G}{'_pruned' if pr else ''}"))
    rows.append(qwen_eval(5120, 1024, pruned=True, drafter=True) | dict(design="qwen_G5120_pruned_with_drafter"))
    rows.append(qwen_eval(6144, 1024, pruned=True, drafter=True) | dict(design="qwen_G6144_pruned_with_drafter"))
    # W12: the floorplan's per-op engine latency, and the VM x-read width (128 = the W5 VM; 512; 2,048)
    rows.append(qwen_eval(6144, 1024, pruned=True, wire_model="w12") | dict(design="qwen_G6144_pruned_w12_wires"))
    for xr in (128, 512, 2048):
        rows.append(qwen_eval(6144, 1024, pruned=True, wire_model="w12", x_read_elems=xr)
                    | dict(design=f"qwen_G6144_pruned_w12_wires_vm{xr}"))
    for r in rows:
        print(f"{r['design']:28s} {r['tokens_s']:8.0f} tok/s  cycles {r['cycles']:>9}  array {r['array_need_mm2']:6.1f}"
              f"/{r['array_avail_mm2']}  fits={r['fits']}")
    return rows


# ---------------------------------------------------------------------------------------------------------
# HBM comparators: a replicated GPU organisation (AGENTS.md rule 3; W9 handoff /tmp/claude-1000/handoff_w9.md)
# ---------------------------------------------------------------------------------------------------------
# Element: an SM-like cluster (4 sub-partitions, Tensor-Core-style exact MMA with golden accumulation order,
# 256 KB RF, ~228 KB SMEM, a bulk-copy port from L2/NoC).  At batch 1 the die is HBM-bound, so the
# microarchitecture terms that decide the token are:
#   supply   the fraction of sustained HBM bandwidth the weight path achieves.  It needs bandwidth x latency
#            bytes in flight (3.6 TB/s x ~0.5 us = 1.8 MB per die); the measured ROM-style QE adapter keeps
#            ~7 words in flight and delivers 39 B/cycle (W4, results/rtl/v41_qe_shared_stall.json).
#   barrier  every dependent operation boundary synchronises the SMs; a hardwired sequencer pays ~7 cycles,
#            a GPU grid barrier through L2 pays more (ASSUMED 200 cycles with a hardware barrier network;
#            1,500 ns is the cooperative-groups grid.sync class -- ASSUMED, to be cited).
#   compute  SMs sized to bandwidth (W9: 32 SMs x 4,096 INT8 MAC/clk per Qwen die) never bind at batch 1.
GPU = dict(barrier_cycles_hw=200,           # superseded: the pre-W13 ASSUMED hardware barrier (kept for the
                                             # labelled comparison row); W13 derives it from the floorplan
                                             # and measures it in RTL (hbm_gpu_design()["barrier"])
           barrier_ns_grid=1430.0,           # measured: V100 cooperative-groups grid sync, 1 block/SM, 32 threads
                                             # (L. Zhang et al., "A Study of Single and Multi-device
                                             # Synchronization Methods in Nvidia GPUs", IPDPS 2020, Fig. 5)
           barrier_ns_grid_sensitivity=dict(p100_1_block_per_sm=1770.0, v100_1024_threads=2210.0),
           barrier_cycles_dsmem_ref=(181, 213),  # H800 SM-to-SM DSMEM latency, cluster 2..16 (Luo et al.,
                                             # arXiv 2501.12084 7.1): the reference for an on-die hardware barrier
           seq_gap_cycles=7,
           adapter_measured_Bpc=39.0, sustained_frac=1.0)


def qwen_hbm_rows():
    """Qwen3-8B HBM die token.  Headline: the W13 prefetching bulk-copy model (stream_overlap over the program's
    ops; a boundary is exposed only when the SMEM staging cannot hide it).  The additive rows (T = t_hbm +
    boundaries x barrier + tp) are the pre-W13 form, kept and labelled no-prefetch."""
    import arch_budget_qwen3 as Q
    clock = Q.clock_hz()
    hc = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())["hbm_comparator"]["8192"]["rom_format_int8"]
    t_hbm = hc["token_s"]                                        # 8.175 GB at 7.2 TB/s sustained (8 stacks)
    per_die_Bpc = hc["hbm_bytes_per_cycle"] / 2                  # 3,277 B/cycle per die
    # global barriers: one after every MMA op (qkv, attention pv, o, gate_up, down x 36, lm_head); heads are
    # SM-local and the norms run redundantly on the replicated x, so they need none (W13; was 217 + 2 x 36)
    boundaries = 5 * 36 + 1
    tp = Q.tp_exchanges(clock)["cycles"] / clock
    dq = hbm_gpu_design("qwen")
    bnd = dq["barrier"]["boundary_cycles"]
    rows = [dict(design="qwen_hbm_ideal", T_us=round(t_hbm * 1e6, 1), tokens_s=round(1 / t_hbm, 1), supply_frac=1.0,
                 boundaries=boundaries, form="bandwidth only")]
    t = dq["token"]
    rows.append(dict(design="qwen_hbm_gpu", T_us=round(t["cycles"] / clock * 1e6, 1), tokens_s=t["tokens_s"],
                     supply_frac=1.0, boundaries=t["boundaries"], barrier_cycles=bnd,
                     exposed_over_hbm_cycles=t["exposed_over_hbm_cycles"],
                     form="prefetching bulk copy (stream_overlap); barrier derived from the floorplan"))
    for tag, supply, barrier_s in (
            ("qwen_hbm_adapter_as_built_no_prefetch", GPU["adapter_measured_Bpc"] / per_die_Bpc, GPU["seq_gap_cycles"] / clock),
            ("qwen_hbm_gpu_derived_barrier_no_prefetch", 1.0, bnd / clock),
            ("qwen_hbm_gpu_assumed200_no_prefetch", 1.0, GPU["barrier_cycles_hw"] / clock),
            ("qwen_hbm_gpu_grid_sync_v100_no_prefetch", 1.0, GPU["barrier_ns_grid"] * 1e-9)):
        T = t_hbm / supply + boundaries * barrier_s + tp
        rows.append(dict(design=tag, T_us=round(T * 1e6, 1), tokens_s=round(1 / T, 1), supply_frac=supply,
                         barrier_us_per_token=round(boundaries * barrier_s * 1e6, 1), boundaries=boundaries,
                         form="additive (pre-W13)"))
    # grid sync with prefetch: the boundary cost enters the stream model
    ops = qwen_hbm_ops(dq["element"], GPU["barrier_ns_grid"] * 1e-9 * clock, dq["drain_cycles"])
    tg, _ = stream_overlap(ops, dq["hbm_Bpc"], dq["sm_count"] * dq["element"]["ingest_Bpc"],
                           dq["staging_kb_per_sm"] * 1024 * dq["sm_count"])
    rows.append(dict(design="qwen_hbm_gpu_grid_sync_v100", T_us=round(tg / clock * 1e6, 1),
                     tokens_s=round(clock / tg, 1), supply_frac=1.0, boundaries=boundaries,
                     form="prefetching bulk copy, V100 grid sync 1.43 us per boundary"))
    return rows


def v41_boundaries(path, nodes):
    """Global barriers on the V4.1 critical path under the W13 SM mapping: one after every matvec (its rows
    are spread over the SMs), one per attention layer (scores -> softmax -> pv is head-local in the
    dedicated attention unit), one per indexer final top-k, and the argmax.  Norms and the router top-6 run
    redundantly on the replicated x and need none."""
    n = 0
    for x in path:
        k = nodes[x]["kind"]
        if k == "matvec" or x.endswith((".attn.scores", ".idx.topk_final")) or x == "argmax":
            n += 1
    return n


def sm_op_cycles(rows_die: float, K: int, fmt: str, drain: int, group_slot: bool, n_sm: int = 32):
    """One matvec on the SM array: rows_die rows split over n_sm SMs, each row's K inside one SM.  Row-slot
    issue holds IL rows in flight, each walking its G groups x c k-steps (a single row is a K-chain);
    group-slot issue spreads a row's (row, group) items over the IL slots.  Calibrated: the RTL SM
    (results/rtl/gpu_sm_blockdot_exact.json) takes 689 cycles for 9 rows at FP8 K = 5,120 row-slot."""
    rows_sm = math.ceil(max(1.0, rows_die) / n_sm)
    if fmt in ("fp8", "fp4"):
        C, la = math.ceil(K / 256), (8 if fmt == "fp4" else 4)
    else:
        C, la = math.ceil(K / 8), 64
    G, c = math.ceil(C / la), 8
    if group_slot:
        return math.ceil(rows_sm * G / 8) * c * 8 + drain
    return math.ceil(rows_sm / 8) * G * c * 8 + drain


V41_HBM_FABRIC_US = dict(collective_latency=125.9, collective_bytes=1.5, pipeline_hops=0.9, control=2.0)
V41_HBM_DIES = 96          # G = 96: every matrix 1/96 per die (W9 handoff 8)


def v41_hbm_chain(group_slot: bool, positions: int = 1, barrier_cycles=None):
    """V4.1 HBM token on the SM design, K-chain aware: the arch DAG's critical path at 1M with every matvec
    re-priced as an SM op on its 1/96 row slice (sm_op_cycles), the dedicated units' nodes (W11 spec widths)
    at their arch price, one barrier per global boundary, and the comparator's switched-fabric terms.  The
    weight sweep streams under the chain.  With speculation, `positions` verify positions ride the MMA
    columns (one weight fetch); the dedicated units issue each position's work (their issue time repeats,
    their depth is paid once)."""
    d = hbm_gpu_design("v41")
    clock = d["clock_hz"]
    arch, b = arch_graph(1048576)
    g = b.g
    path = g.path(b.sink)
    mv = other = extra = xfill = 0.0
    for x in path:
        nd = g.nodes[x]
        t = sum(g.contrib[x].values())
        k = node_key(x) if nd["kind"] == "matvec" else ""
        if nd["kind"] == "matvec" and k and k != "hc.fn":
            rows = nd["sweep"]["macs"] / NODE_K[k] / V41_HBM_DIES
            mv += sm_op_cycles(rows, NODE_K[k], NODE_FMT[k], d["drain_cycles"], group_slot) / clock
            # every SM needs the whole x (its rows span all of K): after the collective gathers it, the
            # die's x broadcast (X_BCAST_BPC) fills the 32 SM x stores -- BF16, every verify position
            xfill += math.ceil(NODE_K[k] * positions * 2 / X_BCAST_BPC) / clock
        elif nd["kind"] in ("collective", "hop"):
            continue                                   # replaced by the comparator's fabric terms
        else:
            other += t
            if positions > 1:
                extra += (positions - 1) * nd.get("issue", 0.0)
    nb = v41_boundaries(path, g.nodes)
    bc = d["barrier"]["boundary_cycles"] if barrier_cycles is None else barrier_cycles
    parts = dict(sm_matvec=mv * 1e6, x_broadcast_fill=xfill * 1e6, dedicated_and_su=other * 1e6,
                 verify_extra_issue=extra * 1e6, barrier=nb * bc / clock * 1e6, **V41_HBM_FABRIC_US)
    parts["collective_bytes"] *= positions             # every position's activations cross the fabric
    chain = sum(parts.values())
    T = max(chain, 37.4)
    return T, parts, nb


def v41_hbm_rows():
    """V4.1 HBM die token (G=96, 1M).  Headline: the K-chain-aware SM chain (v41_hbm_chain), row-slot and
    group-slot issue.  Kept for reference, labelled: the published additive breakdown (W9 handoff 8: compute
    chain 111.7, weight sweep 37.4, collective latency 125.9, bytes 1.5, hops 0.9, control 2.0 us, priced at
    die-pooled widths), and the no-prefetch forms."""
    base = dict(compute_chain=111.7, weight_sweep=37.4, **V41_HBM_FABRIC_US)
    clock = 1.0339e9
    arch, b = arch_graph(1048576)
    path = b.g.path(b.sink)
    boundaries = v41_boundaries(path, b.g.nodes)
    per_die_Bpc = 3.6e12 / clock
    bnd = hbm_gpu_design("v41")["barrier"]["boundary_cycles"]
    rows = []
    for tag, gs, bc in (("v41_hbm_gpu_rowslot", False, None), ("v41_hbm_gpu_groupslot", True, None),
                        ("v41_hbm_gpu_groupslot_grid_sync_v100", True, GPU["barrier_ns_grid"] * 1e-9 * clock)):
        T, parts, nb = v41_hbm_chain(gs, 1, bc)
        rows.append(dict(design=tag, T_us=round(T, 1), tokens_s=round(1e6 / T, 1), supply_frac=1.0, boundaries=nb,
                         form="K-chain-aware SM chain, prefetching bulk copy",
                         breakdown_us={k: round(x, 1) for k, x in parts.items()}))
    for tag, supply, barrier_s, prefetch in (
            ("v41_hbm_published", 1.0, 0.0, False),
            ("v41_hbm_pooled_chain_prefetch", 1.0, (bnd - GPU["seq_gap_cycles"]) / clock, True),
            ("v41_hbm_adapter_as_built_no_prefetch", GPU["adapter_measured_Bpc"] / per_die_Bpc, 0.0, False),
            ("v41_hbm_gpu_derived_barrier_no_prefetch", 1.0, (bnd - GPU["seq_gap_cycles"]) / clock, False),
            ("v41_hbm_gpu_assumed200_no_prefetch", 1.0, (GPU["barrier_cycles_hw"] - GPU["seq_gap_cycles"]) / clock, False)):
        parts = dict(base, weight_sweep=base["weight_sweep"] / supply, barrier=boundaries * barrier_s * 1e6)
        if prefetch:
            chain = sum(v for k, v in parts.items() if k != "weight_sweep")
            T = max(parts["weight_sweep"], chain)
            parts["weight_sweep_exposed"] = round(T - chain, 3)
        else:
            T = sum(parts.values())
        rows.append(dict(design=tag, T_us=round(T, 1), tokens_s=round(1e6 / T, 1), supply_frac=round(supply, 4),
                         boundaries=boundaries, form=("pooled-width chain (superseded upper bound)" if prefetch
                                                      else "additive"),
                         breakdown_us={k: round(x, 1) for k, x in parts.items()}))
    return rows


# ---------------------------------------------------------------------------------------------------------
# GPU-organised HBM die, microarchitecture (W13).  The rows above price the token with two free parameters
# (supply fraction, barrier cycles).  This section sizes the element and the networks that set them:
#   element   the SM: 4 sub-partitions of an exact Tensor-Core-style MMA (lanes x columns), its x store and
#             weight staging in SMEM, SIMT FP32 lanes for the stream-unit work, one fixed pairwise FP32 tree
#             per column across the SM's lanes and a streaming pairwise stack behind it, so a row's whole K
#             and its golden tree stay inside one SM (rtl/gpu/ot_gpu_mma.sv).
#   count     the smallest symmetric SM count whose token is within 0.5% of an unbounded SM array, with the
#             weight stream overlapping every dependent boundary through the SMEM staging.
#   bulk copy HBM bandwidth x loaded latency in flight (Little's law), split over the SMs, in 64 B sectors.
#   staging   SMEM that keeps the prefetching stream running through a boundary (fluid simulation below).
#   barrier   arrival tree + release broadcast over the floorplan distances (tools/hbm_gpu_floorplan.py),
#             at the loaded wire constant, plus the node registers, plus the x-broadcast tail.
# ---------------------------------------------------------------------------------------------------------
HBM_DIE = dict(
    w_um=31800.0, h_um=815e6 / 31800.0,          # 815 mm2 outline shared with W1/W5 (qwen_o4_floorplan.DIE_W)
    stacks=4, phy_um=(12000.096, 833.49),        # ot_hbm3e_phy LEF: two on each long (north/south) edge = 48 mm
    core=(1213.488, 1555.2, 31780.0, 24078.0),   # W5 hbm_die.frame core after PHY rows, service bands, UCIe
    src="results/floorplan/qwen_o4/floorplan.json designs['hbm_die.frame']",
)
HBM_LOADED_LAT_NS = 500.0     # ASSUMED loaded HBM read latency incl. controller queue: the model's 1.8 MB in
                              # flight at 3.6 TB/s (v41 first-access 1 us is the data-dependent gather case)
SECTOR_B = 64                 # HBM3E pseudo-channel access (BL8 x 64 bit)
GPU_UNIT_UM2 = dict(
    lane=8449.0 / 16,         # ot_hdc_lane_copy: exact BF16 mul -> circulating FP32 add (IL 8), 16 lanes 8,449 um2,
                              # closed 0.9 ns (results/physical_abi3/asap7/hdc/ot_hdc_lane_copy/physical.json)
    int8_decode=40.0,         # ASSUMED registered INT8 -> BF16 decode per lane (replaced by the hardened TC)
    fp32_add=UNIT["fp32_add_um2"], fp32_mul=UNIT["fp32_mul_um2"], blockdot=UNIT["blockdot_um2"],
    simt_lane=UNIT["fp32_mac_um2"],
    sram32k=SRAM_256B_MACRO["um2"],
    dff=DFF_UM2,
)
SRAM_128X256_UM2 = 94.824 * 41.04   # ot_sram_1r1w_128x256_m1_r2c2 (physical/asap7_memory_macros)
GPU_LOGIC_UTIL = 0.5          # std-cell placement density (W5 convention; replaced by the hardened macro)
GPU_MACRO_PACK = 1.31         # macro footprint / macro area (W5 tile calibration)

SM_ELEM = {
    # Qwen3-8B: INT8 weight codes, 128 B/clk of weights = 128 lanes; 16 columns = the DFlash b16 verify block
    # (design point block 5) and batch <= 16 without re-streaming weights
    "qwen": dict(subparts=4, int8_lanes=128, bf16_lanes=0, blockdot_lanes=0, cols=16, il=8, ingest_Bpc=128,
                 k_max=12288, x_bytes=2, simt_lanes=128, scratch_kb=64, stack_levels=5),
    # DeepSeek-V4.1: FP4 routed experts (8 block-dot lanes = 256 FP4 weights = 128 B/clk), FP8 dense at the same
    # 128 B/clk on 4 of them, BF16 matrices on 64 lanes; 8 columns cover MTP (m+1 = 7 positions); the group-slot
    # x store delivers all 8 columns' fragment every cycle (16 columns would double it to 197 macros)
    "v41": dict(subparts=4, int8_lanes=0, bf16_lanes=64, blockdot_lanes=8, cols=8, il=8, ingest_Bpc=128,
                k_max=5120, x_bytes=2, simt_lanes=128, scratch_kb=64, stack_levels=3,
                # group-slot issue: a row's K groups on different accumulator slots, so a 1-2-row slice is not a
                # K-chain; the x store must then deliver a new fragment every cycle for up to gs_cols columns
                group_slot=True, gs_cols=8),
}


def gpu_hardened_columns():
    """Routed (flat, ASAP7, 0.92 ns, closed) column areas that replace the unit-sum estimate:
    ot_gpu_tc_col at 16 lanes (lanes + 15-adder tree) and ot_gpu_bd_col at 2 block-dot lanes (+ tree)."""
    out = {}
    for key, rec, lanes in (("lane_with_tree", "ot_gpu_tc_col_l16_092", 16), ("blockdot_with_tree", "ot_gpu_bd_col_lb2_092", 2)):
        p = ROOT / f"results/physical_abi3/asap7/gpu/{rec}/physical.json"
        if p.exists():
            r = json.loads(p.read_text())
            if r.get("status") == "pass" and r["design"].get("closed"):
                out[key] = r["design"]["area_um2"] / lanes
                out[key + "_source"] = str(p.relative_to(ROOT))
    return out


def sm_area(e: dict, staging_kb: float):
    """SM element area (mm2) by resource; logic placed at GPU_LOGIC_UTIL, SRAM at GPU_MACRO_PACK.  Where a
    column has been routed (gpu_hardened_columns) its measured area per lane replaces lanes + tree."""
    u = GPU_UNIT_UM2
    c = e["cols"]
    lanes = e["int8_lanes"] + e["bf16_lanes"]
    hc = gpu_hardened_columns()
    if "lane_with_tree" in hc:
        lane_tree = c * (e["int8_lanes"] * (hc["lane_with_tree"] + u["int8_decode"])
                         + e["bf16_lanes"] * hc["lane_with_tree"])
    else:
        lane_tree = c * (e["int8_lanes"] * (u["lane"] + u["int8_decode"]) + e["bf16_lanes"] * u["lane"]) \
            + c * (max(lanes, 1) - 1) * (u["fp32_add"] + 32 * u["dff"]) * (1 if lanes else 0)
    if "blockdot_with_tree" in hc:
        bd = c * e["blockdot_lanes"] * hc["blockdot_with_tree"]
    else:
        bd = c * e["blockdot_lanes"] * (u["blockdot"] + u["fp32_add"] + 8 * 32 * u["dff"]) \
            + (c * (e["blockdot_lanes"] - 1) * (u["fp32_add"] + 32 * u["dff"]) if e["blockdot_lanes"] and not lanes else 0)
    logic = dict(
        mma_lanes_and_trees=lane_tree,
        blockdot_and_trees=bd,
        stack=c * e["stack_levels"] * (u["fp32_add"] + 2 * 34 * u["dff"]),
        row_scale=c * u["fp32_mul"],
        simt=e["simt_lanes"] * u["simt_lane"],
        x_operand_regs=2 * max(lanes * 16, e["blockdot_lanes"] * 264) * c * u["dff"],   # double-buffered x fragment
    )
    x_kb = e["k_max"] * c * e["x_bytes"] / 1024
    sram_kb = dict(x_store=x_kb, staging=staging_kb, scratch=e["scratch_kb"])
    macros = {k: math.ceil(v / 32) for k, v in sram_kb.items()}
    # the x store must also deliver one x fragment (every lane, every column) per slot revolution (IL cycles):
    # 256-bit macros read every cycle into a double-buffered fragment register
    frag_bits = c * (lanes * 16 + e["blockdot_lanes"] * 266)
    macros["x_store"] = max(macros["x_store"], math.ceil(frag_bits / e["il"] / 256))
    sram_um2 = {k: u["sram32k"] for k in macros}
    if e.get("group_slot"):
        # group-slot reads a whole gs_cols-column fragment every cycle: shallow 128 x 256 macros (4 KB each)
        per_col = lanes * 16 + e["blockdot_lanes"] * 266
        bw = math.ceil(e["gs_cols"] * per_col / 256)
        macros["x_store"] = max(bw, math.ceil(x_kb / 4))
        sram_um2["x_store"] = SRAM_128X256_UM2
    logic_mm2 = sum(logic.values()) / 1e6
    sram_mm2 = sum(macros[k] * sram_um2[k] for k in macros) * GPU_MACRO_PACK / 1e6
    return dict(logic_um2={k: round(v) for k, v in logic.items()}, logic_mm2=round(logic_mm2, 3),
                hardened_columns=hc,
                footprint_logic_mm2=round(logic_mm2 / GPU_LOGIC_UTIL, 3), sram_kb=sram_kb, sram_macros=macros,
                sram_mm2=round(sram_mm2, 3), total_mm2=round(logic_mm2 / GPU_LOGIC_UTIL + sram_mm2, 3),
                macs_per_clk=c * (lanes + 32 * e["blockdot_lanes"]))


def stream_overlap(ops, r_hbm, r_sm, staging_B, chunk_B=262144):
    """Fluid simulation of one token: a prefetching bulk-copy stream (rate r_hbm B/cycle) filling SMEM staging
    of staging_B bytes, consumed by the SMs (rate r_sm) op by op; each op's first byte waits for the previous
    op's dependent latency.  ops: [(bytes, latency_after_cycles)].  Returns (cycles, peak staging bytes)."""
    deliver, consume = [], []
    t_free = 0.0            # consumer ready time
    last_d = 0.0
    peak = 0.0
    slots = max(1, int(staging_B // chunk_B))
    for by, lat in ops:
        n = max(0, math.ceil(by / chunk_B))
        start = t_free
        for i in range(n):
            c = min(chunk_B, by - i * chunk_B)
            j = len(consume)
            d = last_d + c / r_hbm
            if j >= slots:
                d = max(d, consume[j - slots])
            last_d = d
            deliver.append(d)
            t = max((consume[-1] if consume and i else start) + c / r_sm, d + 1)
            consume.append(t)
        end = consume[-1] if n else start
        t_free = end + lat
        # occupancy: chunks delivered but not consumed at the op's end
        k = len(consume)
        occ = sum(1 for x in deliver[max(0, k - slots):] if x <= end) * chunk_B if k else 0
        peak = max(peak, occ)
    return t_free, peak


def qwen_hbm_ops(e: dict, boundary_cycles: float, drain_cycles: float, cols: int = 1, ctx: int = 8192):
    """The Qwen3-8B token on one TP-2 die as (bytes, dependent latency after) in program order.  Stream-unit
    latencies are the reference graph's (qwen3_budget dependency_chain 8192/spec_widths_reference_graph);
    every MMA op ends with its drain and a global boundary (barrier + x broadcast tail)."""
    import arch_budget_qwen3 as Q
    rec = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())
    st = {s["stage"] + (f"#{i}" if s["stage"] == "residual+sumsq" else ""): s["exposed_latency"] + s["throughput"]
          for i, s in enumerate(rec["dependency_chain"][f"{ctx}/spec_widths_reference_graph"]["stages"])}
    exch = Q.tp_exchanges(Q.clock_hz())["per_exchange_cycles"]
    H, KV, HD, NH, FF = 4096, 8, 128, 32, 12288
    kv_bytes = 2 * (KV // 2) * HD * ctx            # FP8 K and V of one layer, this die's 4 KV heads
    sc = 2                                          # BF16 row scale per weight row
    b = boundary_cycles + drain_cycles
    su = lambda *names: sum(v for k, v in st.items() if k.split("#")[0] in names)   # noqa: E731
    res = [v for k, v in st.items() if k.startswith("residual+sumsq")]
    ops = []
    for _ in range(36):
        ops.append((0, su("attn_norm.rsqrt", "attn_norm.scale")))
        ops.append(((NH + 2 * KV) // 2 * HD * (H + sc), b + su("qk_norm.sumsq", "qk_norm.rsqrt", "qk_norm.scale", "rope")))
        # heads are SM-local: scores -> softmax -> pv inside the SM pair of a head; one boundary after pv
        ops.append((kv_bytes // 2, drain_cycles + su("softmax.max", "softmax.exp_sum", "softmax.recip", "softmax.scale")))
        ops.append((kv_bytes // 2, b))
        ops.append((H * (H // 2 + sc), b + exch + res[0] + su("ffn_norm.rsqrt", "ffn_norm.scale")))
        ops.append((2 * (FF // 2) * (H + sc), b + su("silu_mul")))
        ops.append((H * (FF // 2 + sc), b + exch + res[1]))
    ops.append((151936 // 2 * (H + sc), b))        # lm_head slice (row-split vocabulary) + argmax
    return ops


def hbm_floorplan_record(model: str):
    p = ROOT / f"results/floorplan/hbm_gpu/{model}_hbm_die.json"
    return json.loads(p.read_text()) if p.exists() else None


WIRE_REACH_SS_UM = 504.0   # measured (W15): routed register-to-register reach per stage at 0.833 ns, SS corner


def barrier_network(model: str, clock: float, n_sm: int):
    """Barrier latency derived from the floorplan: SM -> quadrant node -> root (arrival AND-tree) and back
    (release), every wire segment registered at the loaded channel constant, one register per tree node.
    Uses the placed floorplan record when present; otherwise the analytical central-island geometry."""
    fp = hbm_floorplan_record(model)
    if fp:
        g = fp["barrier_network"]
        src = f"results/floorplan/hbm_gpu/{model}_hbm_die.json"
        leaf_um, trunk_um, levels = g["max_leaf_um"], g["max_trunk_um"], g["levels"]
    else:
        src = "analytical: 8 x 4 SM island centred on the die, node per quadrant, root at the centre"
        sm_mm2 = 3.0
        side = math.sqrt(sm_mm2) * 1e3
        leaf_um = 2 * side + 1.5 * side                          # farthest SM of a 4 x 2 quadrant to its node
        trunk_um = 2 * side + 1 * side                           # quadrant node to root
        levels = 2
    w = lambda um: max(1, math.ceil(um / WIRE_REACH_SS_UM))  # noqa: E731  (1.2 GHz at SS, W15 reach)
    arrive = w(leaf_um) + w(trunk_um) + levels + 1               # + the SM's local all-subpartitions-done flop
    release = w(leaf_um) + w(trunk_um) + levels
    return dict(arrive_cycles=arrive, release_cycles=release, round_trip_cycles=arrive + release,
                max_leaf_um=round(leaf_um, 1), max_trunk_um=round(trunk_um, 1), levels=levels, source=src)


def gpu_measured():
    """RTL measurements that replace formula terms, read from the committed records when present:
    the SM drain (last weight line -> last row result; max over the exactness campaign's cases of the
    element's format) and the barrier round trip on the floorplan's wire stages."""
    out = dict(qwen_drain_cycles=None, v41_drain_cycles=None, qwen_barrier_cycles=None, v41_barrier_cycles=None,
               sources=[])
    for rec, key, pred in (("results/rtl/gpu_sm_exact.json", "qwen_drain_cycles", lambda c: c["fmt"] == "qwen_int8"),
                           ("results/rtl/gpu_sm_exact.json", "v41_drain_cycles", lambda c: c["fmt"] == "v41_bf16"),
                           ("results/rtl/gpu_sm_blockdot_exact.json", "v41_drain_cycles", lambda c: True)):
        p = ROOT / rec
        if p.exists():
            r = json.loads(p.read_text())
            if r.get("status") == "pass":
                d = [c["rtl"].get("drain_last_line_to_last_result") for c in r["cases"] if pred(c)]
                d = [x for x in d if x is not None]
                if d:
                    out[key] = max(d + [out[key] or 0])
                    out["sources"].append(rec)
    p = ROOT / "results/rtl/gpu_supply_barrier.json"
    if p.exists():
        r = json.loads(p.read_text())
        if r.get("status") == "pass":
            for b in r["barrier"]:
                out[f"{b['model']}_barrier_cycles"] = b["max"]
            out["sources"].append("results/rtl/gpu_supply_barrier.json")
    return out


def mma_drain_cycles(e: dict):
    """Last weight into the MMA -> row result written to SMEM, from the element's pipeline at 1.2 GHz SS (W13b
    2026-09-30: FP32 add and mul 5 -> 7, W11's keep-prefix LAT 7; block-dot term 12 = W10 bterm2 11 + a lane input
    register): decode 1, multiply 7, circulating add 7 (or the block-dot 12), then log2(lanes) tree levels and the stack
    levels at 7, row scale 7, output register 2.  Replaced by the RTL measurement when recorded (gpu_measured: Qwen
    89, V4.1 95 on main)."""
    lanes = max(e["int8_lanes"] + e["bf16_lanes"], e["blockdot_lanes"])
    front = 12 if e["blockdot_lanes"] and not e["int8_lanes"] else 15      # block-dot term, or lane decode+mul+add
    return front + 7 * math.ceil(math.log2(lanes)) + 7 * e["stack_levels"] + 7 + 2


def hbm_gpu_design(model: str):
    """Size the GPU-organised HBM die for `model` ('qwen' | 'v41')."""
    import arch_budget_qwen3 as Q
    e = dict(SM_ELEM[model])
    if model == "qwen":
        clock = Q.clock_hz()
        r_hbm = 3.6e12 / clock                   # 4 stacks x 0.9 TB/s sustained per die
    else:
        clock = 1.0339e9
        r_hbm = 3.6e12 / clock
    in_flight_B = 3.6e12 * HBM_LOADED_LAT_NS * 1e-9
    meas = gpu_measured()
    drain = meas[f"{model}_drain_cycles"] or mma_drain_cycles(e)
    out = dict(model=model, clock_hz=clock, hbm_Bpc=round(r_hbm, 1), element=e, drain_cycles=drain,
               drain_basis="measured (RTL)" if meas[f"{model}_drain_cycles"] else "formula",
               drain_formula_cycles=mma_drain_cycles(e), measured=meas)
    # ---- SM count: smallest multiple of the stack count within 0.5% of an unbounded array (Qwen token) ----
    rows = []
    n_choice = None
    if model == "qwen":
        bn = barrier_network(model, clock, 32)
        x_tail = math.ceil(H_X_TAIL_B / X_BCAST_BPC)
        boundary = (meas["qwen_barrier_cycles"] or bn["round_trip_cycles"]) + x_tail
        ops = qwen_hbm_ops(e, boundary, drain)
        t_inf, _ = stream_overlap(ops, r_hbm, 1e12, 1e15)
        for n in range(8, 65, 4):
            t, _ = stream_overlap(ops, r_hbm, n * e["ingest_Bpc"], 1e15)
            rows.append(dict(n_sm=n, cycles=round(t), tokens_s_pkg=round(clock / t, 1)))
            if n_choice is None and t <= 1.005 * t_inf:
                n_choice = n
        out["sm_count_sweep"] = rows
        out["sm_count_min"] = n_choice
    # symmetric choice: 8 SMs per HBM stack quadrant (4 x 2 per quadrant), power of two for the barrier tree
    n_sm = 32
    out["sm_count"] = n_sm
    out["sm_count_basis"] = ("8 per stack quadrant; >= the 0.5%-of-unbounded minimum" if model == "qwen" else
                             "same element count as Qwen: HBM ingest 3,482 B/clk / 128 B/clk = 27.2 -> 32")
    # ---- bulk copy: Little's law in flight, per SM, in sectors ----
    out["bulk_copy"] = dict(in_flight_B_die=in_flight_B, in_flight_B_sm=in_flight_B / n_sm,
                            outstanding_sectors_sm=math.ceil(in_flight_B / n_sm / SECTOR_B),
                            descriptor_bytes=4096,
                            outstanding_descriptors_sm=math.ceil(in_flight_B / n_sm / 4096),
                            basis=f"3.6 TB/s x {HBM_LOADED_LAT_NS:.0f} ns (ASSUMED loaded latency)")
    sp = ROOT / "results/rtl/gpu_supply_barrier.json"
    if sp.exists():
        sr = json.loads(sp.read_text())
        if sr.get("status") == "pass":
            m = [dict(outstanding_lines=x["max_out"], B_per_cycle=x["B_per_cycle"],
                      share_B_per_cycle=x["share_B_per_cycle"]) for x in sr["supply"]]
            full = [x for x in m if x["B_per_cycle"] >= 0.995 * x["share_B_per_cycle"]]
            out["bulk_copy"].update(
                measured=m, measured_source="results/rtl/gpu_supply_barrier.json (ot_gpu_bulk_copy, 128 B lines, "
                                             "500 ns +- 50 ns loaded latency)",
                outstanding_lines_sm=min(x["outstanding_lines"] for x in full) if full else None,
                note="Little's law gives 440 lines of 128 B; with latency jitter the full share needs 512")
    bn = barrier_network(model, clock, n_sm)
    x_tail = math.ceil(H_X_TAIL_B / X_BCAST_BPC)
    rt_meas = meas[f"{model}_barrier_cycles"]
    out["barrier"] = dict(bn, x_broadcast_tail_cycles=x_tail,
                          measured_round_trip_cycles=rt_meas,
                          boundary_cycles=(rt_meas or bn["round_trip_cycles"]) + x_tail,
                          basis=("derived from the floorplan, measured in RTL (tb_gpu_barrier)" if rt_meas
                                 else "derived from the floorplan"))
    boundary = out["barrier"]["boundary_cycles"]
    if model == "qwen":
        ops = qwen_hbm_ops(e, boundary, drain)
        t_inf, _ = stream_overlap(ops, r_hbm, n_sm * e["ingest_Bpc"], 1e15)
        st = []
        s_choice = None
        for kb in (16, 32, 64, 128, 256, 512, 1024):
            S = kb * 1024 * n_sm
            t, pk = stream_overlap(ops, r_hbm, n_sm * e["ingest_Bpc"], S)
            st.append(dict(staging_kb_per_sm=kb, cycles=round(t), tokens_s=round(clock / t, 1)))
            if s_choice is None and t <= 1.005 * t_inf:
                s_choice = kb
        out["staging_sweep"] = st
        staging_kb = max(s_choice or 1024, math.ceil(in_flight_B / n_sm / 1024 / 32) * 32)
        t_hbm = sum(b for b, _ in ops) / r_hbm
        t_chain = sum(b for b, _ in ops) / (n_sm * e["ingest_Bpc"]) + sum(lat for _, lat in ops)
        t_tok, _ = stream_overlap(ops, r_hbm, n_sm * e["ingest_Bpc"], staging_kb * 1024 * n_sm)
        boundaries = 5 * 36 + 1          # qkv, attention (pv), o, gate_up, down per layer + lm_head (qwen_hbm_ops)
        out["token"] = dict(
            cycles=round(t_tok), tokens_s=round(clock / t_tok, 1), hbm_cycles=round(t_hbm),
            chain_cycles_if_serial=round(t_chain), boundaries=boundaries,
            exposed_over_hbm_cycles=round(t_tok - t_hbm),
            additive_model_tokens_s=round(clock / (t_hbm + boundaries * boundary + Q.tp_exchanges(clock)["cycles"]), 1),
            note="the stream prefetches through every boundary; only what the SMEM staging cannot absorb and the "
                 "last op's tail are exposed")
    else:
        # no op-level stream model for V4.1 yet: the measured in-flight need (512 lines = 64 KB) plus the same
        # again to run through a boundary, as the Qwen sweep requires
        staging_kb = 2 * 64
    out["staging_kb_per_sm"] = staging_kb
    out["sm_area"] = sm_area(e, staging_kb)
    # ---- L2 slices and NoC ----
    out["l2"] = dict(slices=HBM_DIE["stacks"], mb_per_slice=2, macros=HBM_DIE["stacks"] * 64,
                     mm2=round(HBM_DIE["stacks"] * 64 * GPU_UNIT_UM2["sram32k"] * GPU_MACRO_PACK / 1e6, 2),
                     role="x/result gather and broadcast, TP-exchange staging, KV-write coalescing; weights "
                          "bypass it (bulk copy lands in SM SMEM, no reuse at decode)")
    out["noc"] = dict(weight_port_bits_per_sm=e["ingest_Bpc"] * 8 + 64,
                      weight_wires_per_quadrant=(n_sm // 4) * (e["ingest_Bpc"] * 8 + 64),
                      x_broadcast_bits=X_BCAST_BPC * 8, result_gather_bits_per_sm=256,
                      mapping="each SM's weight rows live in its own quadrant's stack: no weight byte crosses "
                              "the die")
    if model == "v41":
        pr = area_ledger(copy.deepcopy(PRESETS["proposal"]))
        units = dict(indexer=pr["indexer"], attention=pr["attention"], su=pr["su_lanes"], sfu=pr["sfu_lanes"],
                     hc_fp32_lanes=5120 * UNIT["fp32_mac_um2"] / 1e6,
                     sinkhorn_select_engram=(UNIT["sinkhorn_um2"] + UNIT["select_k512_um2"]
                                             + UNIT["engram_hash_um2"] + UNIT["tselect16_um2"]) / 1e6)
        out["dedicated_units_mm2"] = {k: round(v, 3) for k, v in units.items()}
        out["dedicated_units_footprint_mm2"] = round(sum(units.values()) / GPU_LOGIC_UTIL, 2)
        out["dedicated_units_source"] = "spec widths as in results/uarch/v41_rom.json proposal hub (W11 builds them)"
    sm_fp = out["sm_area"]["total_mm2"]
    out["die_fit"] = dict(sm_array_mm2=round(n_sm * sm_fp, 2), l2_mm2=out["l2"]["mm2"],
                          dedicated_mm2=out.get("dedicated_units_footprint_mm2", 0.0),
                          core_avail_mm2=round((HBM_DIE["core"][2] - HBM_DIE["core"][0])
                                               * (HBM_DIE["core"][3] - HBM_DIE["core"][1]) / 1e6, 2))
    f = out["die_fit"]
    f["used_mm2"] = round(f["sm_array_mm2"] + f["l2_mm2"] + f["dedicated_mm2"], 2)
    f["fits"] = f["used_mm2"] <= f["core_avail_mm2"]
    return out


H_X_TAIL_B = 16 * 128 * 2     # the last SM's last row block (8 rows x 16 cols... bounded by one 16-col x 128-row
                              # BF16 block) that every SM must receive before the next op's first MMA
X_BCAST_BPC = 256             # x broadcast network width (2,048 wires), root -> every SM, pipelined with release


# ---------------------------------------------------------------------------------------------------------
# Speculation (MTP / DFlash): verify p positions per step with m MAC lanes per weight word (docs/MICROARCH_MODEL.md)
# ---------------------------------------------------------------------------------------------------------
# m counts the positions that multiply one ROM weight word IN THE SAME CYCLE.  m = 1 runs the p positions through
# the existing lanes one after another: the weight words are re-read (cheap) and only issue time multiplies, while
# pipeline fill, wire stages and dependency latency are paid once per verify pass.  m >= 2 replicates every
# element's lanes beside its macro (x13,798 on a V4.1 die), plus wider x broadcast and return.
V41_TAU = 3.649        # DSpark gamma 5 (6 verified positions), results/speculative/v41_flash_dspark_onpolicy_greedy.json
V41_POSITIONS = 6
V41_DRAFT_FRACTION = 3 / 40   # ASSUMED: the 3 built-in draft blocks (mtp.0-2) ~ 3 of 40 layers of an AR token


def v41_verify_T(d, p, lm, ctx=1048576):
    """Verify-pass time of the V4.1 ROM design for p positions with lane multiplier lm."""
    r = evaluate(copy.deepcopy(d), ctx)
    g = r.pop("_g")
    E = A._env()
    clock, c = E["clock"], E["c"]
    cyc = 1.0 / clock
    rep = math.ceil(p / lm)
    for name, nd in g.nodes.items():
        k = nd["kind"]
        u = nd.get("_uarch")
        if u:
            nd["issue"] = max(u["t_read"] * rep, u["t_x"] * p, u["t_ret"] * p, u["t_mac"] * rep) * cyc
        elif k in ("vector", "reduce", "select", "collective"):
            nd["issue"] *= p
        elif k == "kvscan":
            if name.endswith("idx.score"):
                n = int(nd["desc"].split()[2])
                by = n * A.IDX_KEY_B
                macs = n * c["index_heads"] * c["index_head_dim"]
                rd = d["idx_reader_Bpc"] or (3.6e12 / clock)
                nd["issue"] = max(by / rd, p * macs / (d["idx_macs"] * lm)) * cyc   # keys read once per pass
            else:
                nd["issue"] *= rep
        elif k == "matvec" and name.endswith("hc.fn"):
            nd["issue"] *= rep
    fin = g.solve(True)
    return fin[[n for n in g.nodes if n.endswith("token.return")][0]], r["T_us"] * 1e-6


def speculation_rows():
    rows = []
    d = copy.deepcopy(PRESETS["proposal"])
    for lm in (1, 2, V41_POSITIONS):
        Tp, T1 = v41_verify_T(d, V41_POSITIONS, lm)
        Td = V41_DRAFT_FRACTION * T1
        rate = V41_TAU / (Tp + Td)
        extra_mm2 = (lm - 1) * (area_ledger(d)["blockdot_lanes"] + area_ledger(d)["bf16_lanes"])
        rows.append(dict(design=f"v41_rom_mtp_m{lm}", positions=V41_POSITIONS, lane_mult=lm, tau=V41_TAU,
                         ar_tokens_s=round(1 / T1, 1), verify_over_ar=round(Tp / T1, 3),
                         tokens_s=round(rate, 1), speedup=round(rate * T1, 3),
                         extra_lane_area_mm2=round(extra_mm2, 1),
                         fits=bool(area_ledger(d)["rom_field_strip_used_mm2"] + extra_mm2
                                   <= FLOORPLAN["rom_field_strip_mm2"])))
    # Qwen ROM: the RTL-calibrated serial draft/verify/commit step (tools/dflash_step_timing.py) prices m = 1 and 5
    q = json.loads((ROOT / "results/speculative/dflash_step_timing.json").read_text())["rom"]
    for m in ("m1", "m5"):
        blk = q[f"8192/fp8/{m}"]["blocks"] if "blocks" in q[f"8192/fp8/{m}"] else None
        src = q[f"8192/fp8/{m}"]
        best = None
        for key in src:
            if isinstance(src[key], list):
                for b in src[key]:
                    if best is None or b["tokens_s"] > best["tokens_s"]:
                        best = b
        rows.append(dict(design=f"qwen_rom_dflash_{m}", lane_mult=int(m[1:]), best_block=best["block"],
                         tokens_s=best["tokens_s"], speedup=best["speedup"], ar_tokens_s=src["plain_tokens_s"],
                         extra_lane_area_mm2=0.0 if m == "m1" else 178.66,
                         drafter_rom_mm2=29.0, basis="results/speculative/dflash_step_timing.json (m=1 never beats "
                         "AR: the Qwen token is lane-bound; weight issue is ~36% of the step)"))
    for r in rows:
        print(r)
    return rows


def hbm_speculation_rows():
    """Speculation on the GPU-organised HBM dies (user decision 2026-09-29).  The verify positions ride the
    SM's MMA columns (16 built), so one weight fetch serves the whole block with each column in its own
    golden order.
    Qwen DFlash (z-lab/Qwen3-8B-DFlash-b16): step = draft + verify + commit on the prefetching stream.  Draft
    bytes per die: the drafter's 1.05 B parameters (INT8, ASSUMED the target's format) and the shared lm_head
    over the draft slots (re-read, 311 MB); verify bytes are the AR token's (weights + one KV read); the
    in-block causal attention and the accept compare add no bytes.  tau is measured per block
    (results/speculative/dflash_block_acceptance.json, primary, cycle-weighted).
    V4.1 DSpark MTP (gamma 5, 6 positions, tau 3.649): verify = the K-chain-aware SM chain with 6 positions
    (matvecs once on the columns, the dedicated units' issue repeated); draft = V41_DRAFT_FRACTION of an AR
    token (ASSUMED, as the ROM rows)."""
    import arch_budget_qwen3 as Q
    rows = []
    dq = hbm_gpu_design("qwen")
    clock = dq["clock_hz"]
    budget = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())
    acc = json.loads((ROOT / "results/speculative/dflash_block_acceptance.json").read_text())["blocks"]
    ops = qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])
    ar_bytes = sum(b for b, _ in ops)
    t_ar, _ = stream_overlap(ops, dq["hbm_Bpc"], dq["sm_count"] * 128, dq["staging_kb_per_sm"] * 1024 * dq["sm_count"])
    draft_B = budget["dflash"]["drafter_parameters"] / 2 + 151936 // 2 * (4096 + 2)
    rows.append(dict(design="qwen_hbm_ar", block=1, tau=1.0, step_cycles=round(t_ar), tokens_s=round(clock / t_ar, 1)))
    best = None
    for b, v in sorted(acc.items(), key=lambda kv: int(kv[0])):
        b = int(b)
        if b > dq["element"]["cols"]:
            continue
        tau = v["pooled"]["primary"]["tau_direct_cycle_weighted"]
        # the draft precedes the verify (it needs the previous verify's hidden states): its stream is one more
        # op sequence; the weight streams of both prefetch, so the step is their bytes at the stream rate plus
        # the same exposed boundaries
        t_step = t_ar * (ar_bytes + draft_B) / ar_bytes + 2 * 12 * dq["barrier"]["boundary_cycles"]
        r = dict(design=f"qwen_hbm_dflash_b{b}", block=b, tau=tau, step_cycles=round(t_step),
                 tokens_s=round(tau * clock / t_step, 1), speedup=round(tau * t_ar / t_step, 3),
                 draft_bytes_per_die=draft_B, verify_bytes_per_die=ar_bytes)
        rows.append(r)
        if best is None or r["tokens_s"] > best["tokens_s"]:
            best = r
    rows.append(dict(best, design="qwen_hbm_dflash_best"))
    T_ar, parts_ar, _ = v41_hbm_chain(True, 1)
    T_v, parts_v, _ = v41_hbm_chain(True, V41_POSITIONS)
    Td = V41_DRAFT_FRACTION * T_ar
    rows.append(dict(design="v41_hbm_ar", tokens_s=round(1e6 / T_ar, 1), T_us=round(T_ar, 1)))
    rows.append(dict(design="v41_hbm_mtp", positions=V41_POSITIONS, tau=V41_TAU, verify_us=round(T_v, 1),
                     draft_us=round(Td, 1), tokens_s=round(V41_TAU * 1e6 / (T_v + Td), 1),
                     speedup=round(V41_TAU * T_ar / (T_v + Td), 3),
                     verify_breakdown_us={k: round(x, 1) for k, x in parts_v.items()}))
    return rows


# ---------------------------------------------------------------------------------------------------------
# Fabric sensitivity and GPU tiers (user request 2026-09-29)
# ---------------------------------------------------------------------------------------------------------
# Every multi-die design here assumes deterministic hardware collectives at link latency (a 668 ns switched
# hop for V4.1, a ~17.5 ns UCIe exchange for the Qwen TP-2 pair).  The sweep re-prices each design as that latency
# grows toward NCCL-class software collectives; the tiers put the designs beside what GPUs measurably do.
GPU_CAL = json.loads((ROOT / "results/arch/qwen_gpu_calibration.json").read_text())
GPU_FIT = GPU_CAL["fit"]              # t = fixed + seconds_per_weight_byte x bytes (H200 NIM fit, BF16/FP8 pair)
H200_BW = 4.8e12
B200_BW = 8.0e12                       # per GPU (NVIDIA B200 datasheet)
NCCL_ALLREDUCE_S = 8e-6                # ASSUMED NCCL-class small-message all-reduce inside an 8-GPU NVLink node
DFLASH_PAPER = ("Z. Chen, Liang, Liu, 'DFlash: Block Diffusion for Flash Speculative Decoding', arXiv 2602.06036, "
                "Table 3 (SGLang, FA4 backend, single B200, thinking disabled, temperature 0)")
TIER1 = [
    dict(tier=1, design="Qwen3-8B-class, H200, NIM FP8, AR", tokens_s=GPU_CAL["nim_h200"]["fp8_tok_s"],
         source=GPU_CAL["nim_h200"]["source"]),
    dict(tier=1, design="Qwen3-8B, RTX PRO 6000 (this lab), FP8 AR",
         tokens_s=GPU_CAL["local_gpu_rtx_pro_6000"]["concurrency_1"]["fp8"]["ar_tok_s"],
         source="results/gpu/qwen3_rtx_pro_6000_decode.json"),
    dict(tier=1, design="Qwen3-8B, RTX PRO 6000 (this lab), FP8 DFlash",
         tokens_s=GPU_CAL["local_gpu_rtx_pro_6000"]["concurrency_1"]["fp8"]["dflash_tok_s"],
         source="results/gpu/qwen3_rtx_pro_6000_decode.json"),
    dict(tier=1, design="Qwen3-8B, 1x B200, SGLang FA4, BF16, AR (DFlash paper Table 3, Math500)", tokens_s=230.0,
         source=DFLASH_PAPER),
    dict(tier=1, design="Qwen3-8B, 1x B200, SGLang FA4, DFlash b16, Math500 (tau 8.01, 5.1x)", tokens_s=1175.0,
         source=DFLASH_PAPER),
    dict(tier=1, design="Qwen3-8B, 1x B200, SGLang FA4, DFlash b16, HumanEval (tau 6.50, 4.2x)", tokens_s=955.0,
         source=DFLASH_PAPER),
    dict(tier=1, design="DeepSeek-R1 (V4.1-class anchor), 8x B200, TensorRT-LLM min-latency, 3 MTP layers "
                        "(relaxed acceptance)", tokens_s=368.0,
         source="https://nvidia.github.io/TensorRT-LLM/blogs/tech_blog/"
                "blog1_Pushing_Latency_Boundaries_Optimizing_DeepSeek-R1_Performance_on_NVIDIA_B200_GPUs.html"),
]


def gpu_tier2():
    """GPU-calibrated projection, anchored on B200 measurements.
    Qwen3-8B: the per-token fixed cost keeps the H200 fit (1.464 ms: launches and syncs, 36 layers), and the per-byte
    cost is re-fitted so that BF16 weights reproduce the measured B200 SGLang AR rate (230 tok/s, DFlash paper
    Table 3); FP8 weights and 8K FP8 KV then project the FP8 rate.  Speculation multiplies by the measured GPU
    speedup at two acceptance regimes: this lab's reasoning mix (tau ~3.7, 2.58x on the RTX PRO 6000) and the
    paper's math/code (tau 6.5-8.0, 4.2-5.1x on B200).
    V4.1-Flash: 8x B200 (TP 8), the same per-layer fixed cost and per-byte cost, NCCL-class all-reduce (5 per layer)
    and its 1M index-key reads; MTP at the HBM machine's modelled 1.94x.  Check: DeepSeek-R1 on 8x B200 measures
    368 tok/s/user with 3 MTP layers (tier 1)."""
    fixed = GPU_FIT["fixed_seconds_qwen"]
    bf16_bytes = 2 * GPU_FIT["qwen_fp8_weight_bytes"]
    s_per_B = (1 / 230.0 - fixed) / bf16_bytes                   # B200 per-byte cost, fitted
    q_bytes = GPU_FIT["qwen_fp8_weight_bytes"] + GPU_FIT["qwen_fp8_kv_bytes_8k"]
    tq = fixed + s_per_B * q_bytes
    loc = GPU_CAL["local_gpu_rtx_pro_6000"]["concurrency_1"]["fp8"]
    spec_lab = loc["dflash_tok_s"] / loc["ar_tok_s"]
    fixed_layer = fixed / 36
    v_bytes = 13.03e9 / 8 + 262144 * A.IDX_KEY_B * 4 * 38 / 8   # weights + 1M index keys (38 scanning layers)
    tv = 40 * fixed_layer + s_per_B * v_bytes + 40 * 5 * NCCL_ALLREDUCE_S
    return [dict(tier=2, design="Qwen3-8B on 1x B200, FP8 weights, 8K, calibrated", tokens_s=round(1 / tq, 1),
                 spec_tokens_s_reasoning_mix=round(spec_lab / tq, 1),
                 spec_tokens_s_math_code=[round(4.2 / tq, 1), round(5.1 / tq, 1)],
                 effective_bandwidth_TBps=round(1 / s_per_B / 1e12, 2),
                 terms_us=dict(fixed=round(fixed * 1e6), bytes=round(s_per_B * q_bytes * 1e6))),
            dict(tier=2, design="DeepSeek-V4.1-Flash on 8x B200, calibrated", tokens_s=round(1 / tv, 1),
                 spec_tokens_s=round(1.94 / tv, 1),
                 terms_us=dict(fixed=round(40 * fixed_layer * 1e6), bytes=round(s_per_B * v_bytes * 1e6),
                               collectives=round(40 * 5 * NCCL_ALLREDUCE_S * 1e6)),
                 check="DeepSeek-R1 on 8x B200 measures 368 tok/s/user with MTP (tier 1)")]


def qwen_hbm_tau_sensitivity():
    """Tier 3 (idealised HBM) Qwen DFlash at the paper's acceptance: the SM verify cost is flat to 16 columns, so the
    step rate scales with tau (W13 model: block 16 at tau 3.656 -> 2,671 tok/s)."""
    base_tau, base = 3.656, 2671.0
    return [dict(tier=3, design=f"Qwen HBM (idealised) DFlash b16 at tau {t}", tokens_s=round(base * t / base_tau, 1),
                 tau=t) for t in (3.656, 6.50, 8.01)]


FABRIC_SWEEP_S = (0.15e-6, 0.668e-6, 1e-6, 2e-6, 5e-6, 10e-6)   # 0.15 us ~ the ROM array's own board/UCIe links
                                                                # (arch-priced collective depth 145-165 cycles);
                                                                # 0.668 us = the HBM comparator's NVL-class switch
QWEN_UCIE_SWEEP_S = (17.5e-9, 100e-9, 500e-9, 1e-6, 5e-6)


# W15 (results/rtl/w15_collectives.json): collectives MEASURED end to end in RTL on physical-link models --
# per-die clocks, UCIe-A and 112G light-FEC link layers, floorplan wire stages, deterministic release.  Each
# config's latency (issue -> last VM commit on the slowest die) is fitted as fixed + per-word x words-per-rank over
# a 1..320-word payload sweep; a DAG collective is priced at its own payload (words = payload / 64 B for an
# all-reduce, payload / span / 64 B per rank for an all-gather).
W15_RECORD = ROOT / "results/rtl/w15_collectives.json"
_W15 = {}


def w15_record():
    if "r" not in _W15:
        _W15["r"] = json.loads(W15_RECORD.read_text())
    return _W15["r"]


def w15_collective_s(cfg, op, payload, span):
    c = w15_record()["configs"]
    rec = c.get(cfg + "_sweep") or c[cfg]
    f = rec["fit"]["all_reduce" if op == "all_reduce" else "all_gather"]
    words = math.ceil(payload / 64) if op == "all_reduce" else math.ceil(payload / max(1, span) / 64)
    return (f["fixed_cycles"] + f["cycles_per_word"] * max(1, words)) / rec["clock_hz"]


W15_V41 = (("v41_r1d256", "as-built placement (hub collective, edge PHYs 22/29 wire stages), relay, depth 256"),
           ("v41_r0d256", "as-built placement, direct T1 (no relay), depth 256"),
           ("v41_r0d1024", "as-built placement, direct T1, depth 1024"),
           ("v41p17_r0d256", "W3 proposed placement (collective at the channel crossing, 17 stages), direct T1, "
                             "depth 256"),
           ("v41p17_r0d1024", "W3 proposed placement, direct T1, depth 1024"))
W15_QWEN = (("q16d16", "host binding: 16 lanes, depth 16"), ("q16d128", "16 lanes, depth 128"),
            ("q256d64", "256 lanes, depth 64 (ADOPTED)"),
            ("q256d16", "256 lanes, depth 16"), ("q256d128", "256 lanes, depth 128"),
            ("q1024", "1,024 lanes (UCIe rate), depth 16"))


def w15_rows():
    """Token rates with the W15-measured collectives in place of the assumed latencies."""
    rows = []
    if not W15_RECORD.exists():
        return rows
    cf = w15_record()["configs"]
    d = copy.deepcopy(PRESETS["proposal"])
    for cfg, what in W15_V41:
        if cfg not in cf:
            continue
        r = evaluate(dict(d, collective_w15=cfg), 1048576)
        r.pop("_g", None)
        rows.append(dict(design="v41_rom_ar", w15_config=cfg, what=what, tokens_s=round(r["tokens_s"], 1),
                         collective_latency_us=r["breakdown_us"].get("collective_latency"),
                         T_us=round(r["T_us"], 3)))
    import arch_budget_qwen3 as Q
    clock = Q.clock_hz()
    x = wire_cycles(27000.0, clock, WIRE_PS_PER_UM_LOADED) - 1
    ucie_wire = round(QWEN_WIRE["ucie_wire_per_token"] * x / QWEN_WIRE["x_stages_extra"])
    assumed = Q.tp_exchanges(clock)["exchange_cycles"] + ucie_wire     # 73 x 19.27 + the wire term
    for cfg, what in W15_QWEN:
        if cfg not in cf:
            continue
        meas = cf[cfg]["exchanges"]["token_exchange_cycles"]
        cyc = qwen_eval(6144, 1024, pruned=True, exchange=cfg)["cycles"]
        rows.append(dict(design="qwen_rom_ar_G6144", w15_config=cfg, what=what, tokens_s=round(clock / cyc, 1),
                         exchange_cycles_per_token_measured=meas, exchange_cycles_per_token_assumed=assumed,
                         per_allreduce_cycles=cf[cfg]["exchanges"]["allreduce_cycles_mean"]))
    return rows


def fabric_sweep():
    rows = []
    # V4.1 ROM: re-solve the priced DAG with every collective's latency set to L (+ the measured engine cycles)
    d = copy.deepcopy(PRESETS["proposal"])
    r0 = evaluate(copy.deepcopy(d), 1048576)
    r0.pop("_g", None)
    rows.append(dict(design="v41_rom_ar", collective_latency_us="baseline (W15 measured, adopted placement)",
                     tokens_s=round(r0["tokens_s"], 1)))
    for L in FABRIC_SWEEP_S:
        r = evaluate(dict(d, collective_latency_s=L), 1048576)
        r.pop("_g", None)
        rows.append(dict(design="v41_rom_ar", collective_latency_us=L * 1e6, tokens_s=round(r["tokens_s"], 1)))
    # V4.1 HBM: its fabric term is 125.9 us at the 668 ns hop, i.e. ~188 collectives on the path
    base = [r for r in v41_hbm_rows() if r["design"] == "v41_hbm_gpu_groupslot"]
    ncoll = V41_HBM_FABRIC_US["collective_latency"] / 0.668
    for b in base:
        for L in FABRIC_SWEEP_S:
            T = b["T_us"] + ncoll * (L * 1e6 - 0.668)
            rows.append(dict(design=b["design"], collective_latency_us=L * 1e6, tokens_s=round(1e6 / T, 1)))
    # Qwen ROM and HBM: 73 serial UCIe exchanges per token on the TP-2 pair
    import arch_budget_qwen3 as Q
    clock = Q.clock_hz()
    qr = qwen_eval(6144, 1024, pruned=True, exchange=None)   # the sweep prices exchanges at L
    qh = [r for r in qwen_hbm_rows() if r["design"] == "qwen_hbm_gpu"][0]
    for L in QWEN_UCIE_SWEEP_S:
        add = 73 * (L - 19.27 / clock)
        rows.append(dict(design="qwen_rom_ar_G6144", exchange_latency_us=L * 1e6,
                         tokens_s=round(1 / (qr["cycles"] / clock + add), 1)))
        rows.append(dict(design=qh["design"], exchange_latency_us=L * 1e6,
                         tokens_s=round(1 / (qh["T_us"] * 1e-6 + add), 1)))
    for r in w15_rows():
        rows.append(dict(r, source="W15 measured (results/rtl/w15_collectives.json)"))
    for r in rows:
        print(r)
    return rows


# ---------------------------------------------------------------------------------------------------------
# Economics: batch, energy, cost (W14; user positioning decision 2026-09-29).  The paper claims single-user
# speed against GPUs, makes energy per token and cost first-class, and reports aggregate throughput under
# batching.  This section prices all four designs and the GPU tiers on the same three axes:
#   batch    per-user tok/s, aggregate tok/s and per-user latency from batch 1 to the per-user state capacity;
#   energy   J per token at batch 1 and at the saturated batch, whole system (all dies, HBM stacks, links);
#   cost     die / package / stack / ROM mask-set counts and a dollar estimate per unit of throughput.
# It calls the sections above and does not change them.  Every constant here cites its source; ASSUMED marks
# the ones with none in the repository.
# ---------------------------------------------------------------------------------------------------------
ECON_BATCHES = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)
ECON_SLO_TOKENS_S_PER_USER = 100.0   # ASSUMED illustrative interactivity floor for the "aggregate at an SLO" column
MAC_OPS = 2                   # technology.json mac_energy_j_per_op is per OPERATION and a MAC is 2 of them (as
                              # arch_budget_v41.energy_per_token).  power_ledger above charges 1 op per MAC: this
                              # section uses 2 (the V4.1 ROM MAC energy is < 1% of its token either way)
HBM_STACK_B = 22.5e9          # arch_budget_v41.hbm_comparator stack_capacity_B (HBM3E 24 GB class)
HBM_CAP_EFF = 0.9             # technology.json efficiencies.hbm_capacity (runtime reserve)
HBM_STACK_BPS = 1.0e12 * 0.9  # arch_budget_qwen3.HBM: 1.0 TB/s a stack, 0.90 sustained
B200_HBM_B = 180e9            # DGX B200: 1,440 GB HBM3E over 8 GPUs (NVIDIA DGX B200 datasheet)
B200_W_DECODE = TECH["power"]["gpu_reference_power"]["b200_measured_decode_w"]["value"]    # 689 W measured
B200_W_TDP = TECH["power"]["gpu_reference_power"]["b200_tdp_nvl72_w"]["value"]             # 1,200 W published
DFLASH_T3_B200 = {1: 230.0, 4: 861.0, 8: 1666.0, 16: 3133.0, 32: 5694.0}   # DFLASH_PAPER Table 3: B200 AR
                              # baselines at concurrency 1..32 (aggregate tok/s, SGLang FA4, BF16, Math500)
V41_ROM_SYSTEM = dict(packages=94, dies=188, layer_dies=112, head_dies=4, table_dies=72, stacks=464,
                      src="results/arch/v41_rack.json comparison[0] and logical.roles")
E_LINK = dict(ucie=TECH["energy"]["link_j_per_bit"]["ucie_advanced"]["value"],
              board=TECH["energy"]["link_j_per_bit"]["board_serdes_112g"]["value"])
V41_TP = 4                    # dies per pipeline stage (TP-4): the uarch graph is one die's work
V41_STAGES = 28
QWEN_ROM_AREA_DIE = dict(rom=265.0,                          # W12 integer placement, 34,669 macros (MICROARCH_MODEL)
                         logic=6144 * 18063.0 / 1e6 + 12.8 + 4 * 10.0 + 10.0,   # pruned groups + SU spill +
                                                             # 4 HBM PHY + UCIe PHY (arch_budget_qwen3 area constants)
                         sram=6144 * 94.824 * 41.04 / 1e6)  # KV ring SRAM per group (QWEN_AREA kv_sram_group_um2)
# ---- cost inputs (every dollar figure is ASSUMED in the repository or here) ----
_ARCHS = json.loads((ROOT / "configs/hardware/architectures.json").read_text())
_TIN = json.loads((ROOT / "configs/hardware/technology_inputs.json").read_text())["runtime_and_cost_assumptions"]


def _arch_cost(name):
    stack = [_ARCHS]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            if o.get("name") == name and "cost_per_device" in o:
                return o["cost_per_device"]
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)
    raise KeyError(name)


COST = dict(
    package_usd=_arch_cost("NVIDIA-B200-x1"),
    package_basis="iso-package: every two-reticle + 8-HBM3E CoWoS-L-class package (the ROM packages, the HBM "
                  "comparator packages and a B200 alike) at the repository's B200 device price "
                  "(configs/hardware/architectures.json NVIDIA-B200-x1 cost_per_device, graded assumed)",
    silicon_usd_per_mm2=_TIN["wafer_cost_per_device"] / TECH["wafer"]["area_mm2"]["value"],
    silicon_basis="technology_inputs.json wafer_cost_per_device (assumed) over the 46,225 mm2 wafer-scale device",
    hbm_stack_usd=360.0,      # ASSUMED: 24 GB x ~$15/GB HBM3E (2025 analyst estimates, TrendForce / Silicon Analysts;
                              # no public spot price exists)
    mask_set_usd=15e6,        # ASSUMED: a full 5 nm-class mask set, $5-15M+ (SemiAnalysis, "The Dark Side of the
                              # Semiconductor Design Renaissance"); the upper end
    rom_coding_fraction=0.10,  # ASSUMED low case: a ROM die's weights live in its coding (via/metal) layers, ~10% of a
                              # full set; the base layers are shared by dies of one role
    production_units=_TIN["production_units"],   # technology_inputs.json (assumed): NRE amortisation volume
)


def _curve(T1_s, sat_tok_s, cap, bound, extra=None):
    """Batch sweep of a design whose users interleave on one machine: per-user rate is the single-user rate until
    the machine's busiest resource saturates, then the saturated aggregate shared by the batch."""
    rows = []
    bs = [b for b in ECON_BATCHES if b <= cap] + ([cap] if cap not in ECON_BATCHES else [])
    for B in sorted(set(bs)):
        pu = min(1.0 / T1_s, sat_tok_s / B)
        rows.append(dict(batch=B, per_user_tokens_s=round(pu, 1), aggregate_tokens_s=round(B * pu, 1),
                         per_user_ms_per_token=round(1e3 / pu, 4),
                         binding="single-user chain" if 1.0 / T1_s <= sat_tok_s / B else bound,
                         **(extra(B) if extra else {})))
    return rows


def _sat_batch(rows):
    top = max(r["aggregate_tokens_s"] for r in rows)
    return next(r for r in rows if r["aggregate_tokens_s"] >= 0.999 * top)


# ---- V4.1 ROM: the priced graph, per die, by energy category and stage occupancy ----
_CONS_CTX = 1048576   # the V4.1 context of _v41_graph / the consolidation HBM chain (W16's short-context rows set it)


def _v41_graph(d, positions=1):
    """The proposal's priced graph; with positions > 1 the MTP verify pass at m = 1 (the issue scaling of
    v41_verify_T, which returns only times)."""
    r = evaluate(copy.deepcopy(d), _CONS_CTX)
    g = r.pop("_g")
    if positions > 1:
        E = A._env()
        clock, c = E["clock"], E["c"]
        cyc = 1.0 / clock
        p = positions
        for name, nd in g.nodes.items():
            k = nd["kind"]
            u = nd.get("_uarch")
            if u:
                nd["issue"] = max(u["t_read"] * p, u["t_x"] * p, u["t_ret"] * p, u["t_mac"] * p) * cyc
            elif k in ("vector", "reduce", "select", "collective"):
                nd["issue"] *= p
            elif k == "kvscan":
                if name.endswith("idx.score"):
                    n = int(nd["desc"].split()[2])
                    rd = d["idx_reader_Bpc"] or (3.6e12 / clock)
                    nd["issue"] = max(n * A.IDX_KEY_B / rd,
                                      p * n * c["index_heads"] * c["index_head_dim"] / d["idx_macs"]) * cyc
                else:
                    nd["issue"] *= p
            elif k == "matvec" and name.endswith("hc.fn"):
                nd["issue"] *= p
        g.solve(True)                               # re-time the path (contrib, fin) for the verify pass
    return r, g


def v41_rom_ledger(g, mac_ops=MAC_OPS, wire_j=WIRE_J_PER_BIT_MM):
    """Per-layer (one die) energy by category and stage occupancy: power_ledger's terms, split so that a verify
    pass can scale them (compute x positions, HBM once per pass).  The ROM field is the measured pair (PAIR_W):
    'field' is its busy excess over the clocked-idle floor.  With mac_ops=1 the busiest stage's on-die sum equals
    power_ledger's energy_per_token_uJ (tests/test_uarch_economics.py)."""
    field_mm = FLOORPLAN["cols"] * 25.628 + 20.0
    pp = pair_power(A._env()["clock"])
    lay, occ = {}, {}
    for name, nd in g.nodes.items():
        L = nd["layer"]
        if L is None or L < 0:
            continue
        e = lay.setdefault(L, dict(mac=0.0, field=0.0, xnet=0.0, units=0.0, hbm_if=0.0, stack=0.0, link=0.0))
        k = nd["kind"]
        u = nd.get("_uarch")
        if u:
            # measured pairs (PAIR_W): busy excess over the clocked idle floor, which is the die's static clock
            e["field"] += busy_pairs(nd) * nd["issue"] * (pp["busy"] - pp["clock"])
            e["xnet"] += xnet_energy(u, field_mm, wire_j)
        elif k == "matvec" and name.endswith("hc.fn"):
            e["mac"] += nd["sweep"]["macs"] * mac_ops * E_MAC["fp32"]
        elif k in ("vector", "reduce") and nd.get("_work"):
            cls, n_el = nd["_work"]
            e["units"] += n_el * E_MAC["fp32"] * (SFU_OPS_PER_ELEM if cls == "sfu" else 1) + n_el * 4 * 2 * E_SRAM_B
        elif k == "kvscan" and nd.get("_work"):
            cls, macs = nd["_work"]
            e["units"] += macs * mac_ops * (E_MAC["fp4"] if cls == "idx" else E_MAC["bf16"])
            hb = (int(nd["desc"].split()[2]) * A.IDX_KEY_B if name.endswith("idx.score")
                  else 640 * A.WIN_ROW_B / 4 if name.endswith(".scores") else 0)
            e["hbm_if"] += hb * E_HBM_IF_B
            e["stack"] += hb * (E_HBM_B - E_HBM_IF_B)
        elif k == "collective":
            e["link"] += nd.get("payload", 0) * 8 * E_LINK_BIT
        if k not in ("collective", "hop"):
            occ[L] = occ.get(L, 0.0) + nd["issue"]
    lps = 40 / V41_STAGES
    st_e, st_o = {}, {}
    for L in lay:
        s = int(L / lps)
        st_e[s] = st_e.get(s, 0.0) + sum(v for kk, v in lay[L].items() if kk != "stack")
        st_o[s] = st_o.get(s, 0.0) + occ.get(L, 0.0)
    cats = {kk: sum(x[kk] for x in lay.values()) for kk in ("mac", "field", "xnet", "units", "hbm_if", "stack", "link")}
    return dict(per_die_categories_J=cats, stage_die_energy_J=st_e, stage_occupancy_s=st_o)


def v41_rom_economics():
    d = copy.deepcopy(PRESETS["proposal"])
    r1, g1 = _v41_graph(d, 1)
    T1 = r1["T_us"] * 1e-6
    led = v41_rom_ledger(g1)
    area = area_ledger(d)
    pw = power_ledger(d, g1, r1["clock_hz"], r1["tokens_s"], area)
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]
    link_static_die = rack["per_die"]["static_w"]["serdes_always_on"] + rack["per_die"]["static_w"]["ucie_idle"]
    die_static = pw["clock_w"] + pw["leakage_w"] + pw["hbm_idle_w"] + link_static_die
    static_w = dict(layer_dies=round(V41_ROM_SYSTEM["layer_dies"] * die_static, 1),
                    head_dies=round(rack["static"]["head_dies"], 1), table_dies=round(rack["static"]["table_dies"], 1))
    P_static = sum(static_w.values())
    cats = {k: V41_TP * v for k, v in led["per_die_categories_J"].items()}      # all 4 dies of every stage
    dyn_die = sum(v for k, v in cats.items() if k != "stack")
    sat = 1.0 / max(led["stage_occupancy_s"].values())
    cap = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())["capacity"]["1048576"]["rom_users"]

    def e_ar(B):
        agg = min(B / T1, sat)
        return dict(energy_mJ_per_token=round((dyn_die + cats["stack"] + P_static / agg) * 1e3, 3),
                    system_w=round(P_static + (dyn_die + cats["stack"]) * agg, 0))
    ar = _curve(T1, sat, cap, "busiest stage occupancy", e_ar)
    # MTP m = 1: 6 positions per verify pass; compute terms x positions, HBM keys and rows once per pass
    Tp, _ = v41_verify_T(d, V41_POSITIONS, 1)
    Td = V41_DRAFT_FRACTION * T1
    _, gv = _v41_graph(d, V41_POSITIONS)
    ledv = v41_rom_ledger(gv)
    head = max(ledv["stage_occupancy_s"])
    occ_v = dict(ledv["stage_occupancy_s"])
    occ_v[head] = occ_v[head] + Td                  # the draft runs on the head (+DSpark) dies (ASSUMED serial there)
    step_sat = max(occ_v.values())
    sat_m = V41_TAU / step_sat
    step1 = Tp + Td
    P = V41_POSITIONS
    e_pass = sum(v * (1 if k in ("hbm_if", "stack") else P) for k, v in cats.items())
    dyn_m = (e_pass + V41_DRAFT_FRACTION * (dyn_die + cats["stack"])) / V41_TAU

    def e_m(B):
        agg = min(B * V41_TAU / step1, sat_m)
        return dict(energy_mJ_per_token=round((dyn_m + P_static / agg) * 1e3, 3),
                    system_w=round(P_static + dyn_m * agg, 0))
    mtp = _curve(step1 / V41_TAU, sat_m, cap, "busiest stage occupancy (verify pass)", e_m)
    return dict(
        design="V4.1 ROM array (proposal, 1M context)", system=V41_ROM_SYSTEM,
        ar=dict(tokens_s_b1=round(1 / T1, 1), saturated_tokens_s=round(sat, 1), rows=ar,
                sat_batch=_sat_batch(ar)["batch"]),
        mtp_m1=dict(tokens_s_b1=round(V41_TAU / step1, 1), saturated_tokens_s=round(sat_m, 1), rows=mtp,
                    sat_batch=_sat_batch(mtp)["batch"], tau=V41_TAU, positions=P, verify_us=round(Tp * 1e6, 1),
                    draft_us=round(Td * 1e6, 1)),
        capacity_users=cap, capacity_basis="results/arch/arch_budget_v41.json capacity[1048576].rom_users (KV + index "
                                           "keys of the busiest layer-20 group in its 4 HBM3E stacks per die, 90% usable)",
        energy=dict(dynamic_mJ_per_token_die=round(dyn_die * 1e3, 3), stack_mJ_per_token=round(cats["stack"] * 1e3, 3),
                    categories_mJ_per_token={k: round(v * 1e3, 4) for k, v in cats.items()},
                    static_w=static_w, static_w_total=round(P_static, 1),
                    layer_die_static_w=dict(clock=pw["clock_w"], leakage=pw["leakage_w"], field_clock=pw["field"]["clock_w"],
                                            hub_clock_uncalibrated=pw["hub"]["clock_w"], hbm_interface_idle=pw["hbm_idle_w"],
                                            links=round(link_static_die, 3)),
                    mtp_dynamic_mJ_per_token=round(dyn_m * 1e3, 3),
                    basis="power_ledger terms on every stage x 4 TP dies (the uarch graph is one die, busiest-die "
                          "macros for every layer); ROM field = the MEASURED pair (PAIR_W, W18): dynamic 'field' = busy "
                          "excess over the clocked-idle floor; layer-die static = the ledger's clock + leakage (field "
                          "measured per placed pair, ungated; hub from area, UNCALIBRATED) + HBM interface idle, plus "
                          "the rack's always-on SerDes and UCIe; head and Engram-table dies' "
                          "static from results/arch/v41_rack.json power.static; HBM stack DRAM energy of the index "
                          "and KV reads; stack background (refresh) power not charged"),
        stage_occupancy_us={str(k): round(v * 1e6, 2) for k, v in sorted(led["stage_occupancy_s"].items())})


# ---- Qwen3-8B ROM package (AR, G = 6,144 pruned, 8K) ----
def _qwen_wl():
    import arch_budget_qwen3 as Q
    wl = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())["workload"]["8192"]
    return wl, Q.kv_bytes(wl, Q.KV_FMT_SPEC)


def _static_w(logic, rom, sram, clock, stacks):
    return dict(clock=CLOCK_J_MM2 * clock * (logic + 0.15 * (rom + sram)),
                leakage=logic * LEAK["logic"] + rom * LEAK["rom_array"] + sram * LEAK["sram_array"],
                hbm_interface_idle=stacks * HBM_IDLE_W_STACK)


# ROOT / USER DECISION 2026-09-30 (W16): the Qwen ROM product is option C -- two B200-class packages, 4 dies,
# TP-4 with one package crossing (W15's measured TP-4 board exchange), G = 6,144 a die (W12's die), W12 floorplan
# wires, ROM at the storage-only density (75.0 Mbit/mm2 + SECDED) -- because the two-reticle package does not hold
# the AR-only ROM at that density (tools/uarch_model.py qwen_rom_options).  The 2-die W5-wire row (9,851 tok/s) is
# superseded; qwen_eval keeps both wire calibrations (w5 9,851, w12 9,194 at the 2-die reference).
QWEN_ROM_PRODUCT = dict(k=4, G=6144, link="board", packages=2, stacks_per_die=4)


def _qwen_rom_product():
    P = QWEN_ROM_PRODUCT
    q = qwen_tp_point(P["k"], P["G"], P["link"])
    a = dict(logic=P["G"] * 18063.0 / 1e6 + QWEN_TILE_FIXED_MM2, rom=q["rom_mm2_per_die"],
             sram=P["G"] * QWEN_AREA["kv_sram_group_um2"] / 1e6)
    return q, a


def qwen_rom_economics():
    import arch_budget_qwen3 as Q
    P = QWEN_ROM_PRODUCT
    q, a = _qwen_rom_product()
    clock = q["clock_hz"]
    ub = q["unit_busy"]
    T1 = q["cycles"] / clock
    wl, kvb = _qwen_wl()
    bounds = dict(q["bounds"])                  # lanes, stream unit, KV stream (4 stacks a die, its own KV heads)
    bind = min(bounds, key=bounds.get)
    sat = bounds[bind]
    cap = q["capacity_users"]
    st = {k: P["k"] * v for k, v in _static_w(a["logic"], a["rom"], a["sram"], clock, P["stacks_per_die"]).items()}
    P_static = sum(st.values())
    macs = wl["weight_macs"] + wl["attention_macs"]
    tpx = Q.tp_exchanges(clock)
    cats = dict(mac=macs * MAC_OPS * E_MAC["bf16"],                 # the lane is an exact BF16 product of a decoded INT8
                rom=wl["bytes"]["weights_rom_format"] * (E_ROM_B + E_DELIVER_B),
                kv_on_die=kvb * (E_HBM_IF_B + E_DELIVER_B + 2 * E_SRAM_B),   # PHY/controller, ring SRAM, delivery
                stream=wl["elementwise_total"] * (E_MAC["fp32"] + 2 * 4 * E_SRAM_B),
                ucie=tpx["bytes_per_direction"] * 2 * 8 * E_LINK["board"] * (P["k"] - 1),   # TP-4 exchanges
                stack=kvb * (E_HBM_B - E_HBM_IF_B))
    dyn = sum(cats.values())

    def e(B):
        agg = min(B / T1, sat)
        return dict(energy_mJ_per_token=round((dyn + P_static / agg) * 1e3, 3), package_w=round(P_static + dyn * agg, 1))
    rows = _curve(T1, sat, cap, bind.replace("_", " "), e)
    return dict(design="Qwen3-8B ROM, option C (2 packages, 4 dies, TP-4, G = 6,144 pruned, W12 wires, 8K)",
                system=dict(packages=P["packages"], dies=P["k"], stacks=P["k"] * P["stacks_per_die"]),
                product=dict(QWEN_ROM_PRODUCT, exchange=q["exchange"], wire_model="w12",
                             superseded="2-die package, W5 wires: 9,851 tok/s (does not fit at 75 Mbit/mm2)"),
                ar=dict(tokens_s_b1=round(1 / T1, 1), saturated_tokens_s=round(sat, 1), rows=rows,
                        sat_batch=_sat_batch(rows)["batch"]),
                bounds_tokens_s={k: round(v, 1) for k, v in bounds.items()}, binding=bind,
                unit_busy_cycles_per_die=ub, token_cycles=q["cycles"], capacity_users=cap,
                capacity_basis="each die's 4 HBM3E stacks x 22.5 GB x 0.90 over its 2 of 8 KV heads of one 8K user "
                               f"({kvb / 1e6:.1f} MB a user)",
                energy=dict(dynamic_mJ_per_token=round(dyn * 1e3, 3),
                            categories_mJ_per_token={k: round(v * 1e3, 4) for k, v in cats.items()},
                            static_w={k: round(v, 2) for k, v in st.items()}, static_w_total=round(P_static, 1),
                            area_mm2_per_die={k: round(v, 1) for k, v in a.items()},
                            basis="the uarch constants (technology.json), 2 ops per MAC, all 4 dies; ROM area at the "
                                  "storage-only density"),
                note="m = 1: batching reuses no weight word, so the lanes, the stream unit and the KV stream each cap "
                     "the aggregate; the KV stream (each user's 604 MB of 8K FP8 KV per token over 16 stacks) binds first")



# ---- HBM comparators (tier 3, the GPU-organised dies) ----
def qwen_hbm_economics():
    dq = hbm_gpu_design("qwen")
    clock = dq["clock_hz"]
    r = dq["hbm_Bpc"]
    cols = dq["element"]["cols"]
    ops = qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])
    ar_bytes = sum(b for b, _ in ops)
    t_ar, _ = stream_overlap(ops, r, dq["sm_count"] * 128, dq["staging_kb_per_sm"] * 1024 * dq["sm_count"])
    wl, kvb = _qwen_wl()
    kv_die = kvb / 2
    w_die = ar_bytes - kv_die
    cap = int((8 * HBM_STACK_B * HBM_CAP_EFF - 2 * w_die) // kvb)
    sa = dq["sm_area"]
    n = dq["sm_count"]
    st = {k: 2 * v for k, v in _static_w(n * sa["logic_mm2"] + 4 * 10.0 + 10.0, 0.0,
                                         n * sa["sram_mm2"] + dq["l2"]["mm2"], clock, 4).items()}
    P_static = sum(st.values())
    macs = wl["weight_macs"] + wl["attention_macs"]
    spec = {x["block"]: x for x in hbm_speculation_rows() if x["design"].startswith("qwen_hbm_dflash_b")}

    def step(B, b, s1, draft):
        passes = math.ceil(B * b / cols)
        cyc = s1 + ((passes - 1) * (w_die + draft) + (B - 1) * kv_die) / r
        byt = 2 * (passes * (w_die + draft) + B * kv_die)
        e = (B * b * (macs + 2 * draft) * MAC_OPS * E_MAC["bf16"] + byt * E_HBM_B
             + 2 * passes * (w_die + draft) * 2 * E_SRAM_B + B * b * wl["elementwise_total"] * (E_MAC["fp32"] + 8 * E_SRAM_B))
        return cyc, e

    def rows_for(pick):
        out = []
        for B in sorted(set([b for b in ECON_BATCHES if b <= cap] + [cap])):
            cyc, e, tau, blk = pick(B)
            t = cyc / clock
            pu = tau / t
            agg = B * pu
            out.append(dict(batch=B, block=blk, tau=tau, per_user_tokens_s=round(pu, 1), aggregate_tokens_s=round(agg, 1),
                            per_user_ms_per_token=round(1e3 / pu, 4),
                            binding="weight stream" if B * blk <= cols else "weight re-stream + KV stream",
                            energy_mJ_per_token=round((e / (B * tau) + P_static / agg) * 1e3, 3),
                            package_w=round(P_static + e / t, 1)))
        return out

    def ar_pick(B):
        c, e = step(B, 1, t_ar, 0.0)
        return c, e, 1.0, 1

    def df_pick(B):
        best = None
        for b, x in spec.items():
            c, e = step(B, b, x["step_cycles"], x["draft_bytes_per_die"])
            if best is None or x["tau"] / c > best[2] / best[0]:
                best = (c, e, x["tau"], b)
        return best
    ar = rows_for(ar_pick)
    df = rows_for(df_pick)
    return dict(design="Qwen3-8B HBM comparator, GPU organisation (tier 3, 8K)", system=dict(packages=1, dies=2, stacks=8),
                ar=dict(tokens_s_b1=ar[0]["per_user_tokens_s"], rows=ar, saturated_tokens_s=max(x["aggregate_tokens_s"] for x in ar),
                        sat_batch=_sat_batch(ar)["batch"]),
                dflash=dict(tokens_s_b1=df[0]["per_user_tokens_s"], rows=df,
                            saturated_tokens_s=max(x["aggregate_tokens_s"] for x in df), sat_batch=_sat_batch(df)["batch"],
                            note="best block per batch (tau per block from results/speculative/dflash_block_acceptance.json); "
                                 "users x block positions share the 16 MMA columns, a pass per 16"),
                capacity_users=cap, capacity_basis="8 stacks x 22.5 GB x 0.90 less the INT8 weights, over 604 MB per user",
                energy=dict(static_w={k: round(v, 2) for k, v in st.items()}, static_w_total=round(P_static, 1),
                            basis="SM MACs (2 ops, BF16 lane) + the whole HBM path per byte (technology.json "
                                  "hbm_j_per_byte, die + stack) + SMEM staging write and read + stream elements; "
                                  "static: SM logic, SMEM + L2 SRAM, 4 HBM PHY + UCIe as logic, HBM interface idle"))


def _v41_weight_split():
    E = A._env()
    c = E["c"]
    tot, _ = A.token_workload(c, 1048576)
    routed = c["num_layers"] * c["experts_per_token"] * 3 * c["moe_intermediate_size"] * c["hidden_size"] * A.FP4
    return tot, tot["bytes"]["rom"] - routed, routed, c


def _v41_weight_bytes(tokens):
    tot, dense, routed, c = _v41_weight_split()
    U = A.distinct_experts(tokens, c["num_routed_experts"], c["experts_per_token"])
    return dense + routed * U / c["experts_per_token"]


def _v41_system_macs_j():
    tot, *_ = _v41_weight_split()
    fmt = lambda k: "w4a8" if k == "weight:fp4" else {"fp8": "fp8", "fp4": "fp4", "fp32": "fp32"}.get(k.split(":")[1], "bf16")  # noqa: E731
    return sum(v * MAC_OPS * E_MAC[fmt(k)] for k, v in tot["macs"].items())


def v41_hbm_economics(rom_units_j_per_token):
    dv = hbm_gpu_design("v41")
    clock = dv["clock_hz"]
    sweep1 = 37.4                                       # us: the weight sweep of one token (v41_hbm_chain)
    w1 = _v41_weight_bytes(1)
    sweep = lambda toks: sweep1 * _v41_weight_bytes(toks) / w1   # noqa: E731
    cols = dv["element"]["cols"]
    cache = {}

    def chain(P):
        if P not in cache:
            _, parts, _ = v41_hbm_chain(True, P)
            cache[P] = parts
        return cache[P]
    issue1 = chain(2)["verify_extra_issue"]             # one more user's dedicated-unit issue (us)

    def T(P, toks):
        return max(sum(chain(P).values()), sweep(toks))

    def occ(P, toks):
        p = chain(P)
        return max(p["sm_matvec"] + p["x_broadcast_fill"] + p["barrier"], P * issue1, sweep(toks))
    tot, *_ = _v41_weight_split()
    per_user_hbm = tot["bytes"]["kv_hbm"] + tot["bytes"]["idx"]
    macs_j = _v41_system_macs_j()
    coll_b = tot["collective_bytes"]
    n = V41_HBM_DIES
    sa = dv["sm_area"]
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]["per_die"]["static_w"]
    st1 = _static_w(dv["sm_count"] * sa["logic_mm2"] + dv["dedicated_units_footprint_mm2"] * GPU_LOGIC_UTIL + 40.0, 0.0,
                    dv["sm_count"] * sa["sram_mm2"] + dv["l2"]["mm2"], clock, 4)
    st1["links"] = rack["serdes_always_on"] + rack["ucie_idle"]      # ASSUMED: the same link class as a ROM layer die
    st = {k: n * v for k, v in st1.items()}
    P_static = sum(st.values())
    cap = json.loads((ROOT / "results/arch/arch_budget_v41.json").read_text())["capacity"]["1048576"]["hbm_users"]

    def energy(B, P, draft_frac):
        """One step's dynamic energy: every column pass reads the union of ITS tokens' experts."""
        toks = B * P
        per = max(1, cols // P)
        passes = math.ceil(B / per)
        wb = passes * _v41_weight_bytes(min(B, per) * P)
        e = (toks * macs_j + (wb + B * per_user_hbm) * E_HBM_B + wb * 2 * E_SRAM_B + toks * rom_units_j_per_token
             + toks * coll_b * 8 * E_LINK["board"] * 2)          # ASSUMED: two switch hops at 112G SerDes energy
        return e * (1 + draft_frac)

    def rows(P, tau, draft_frac):
        out = []
        per = max(1, cols // P)                           # users per column pass
        Td = draft_frac * T(1, 1)
        for B in sorted(set([b for b in ECON_BATCHES if b <= cap] + [cap])):
            if B <= per:
                t = T(B * P, B * P) + Td
            else:
                t = max(T(per * P, per * P) + Td, math.ceil(B / per) * (occ(per * P, per * P) + Td))
            t *= 1e-6
            pu = tau / t
            agg = B * pu
            e = energy(B, P, draft_frac)
            out.append(dict(batch=B, per_user_tokens_s=round(pu, 1), aggregate_tokens_s=round(agg, 1),
                            per_user_ms_per_token=round(1e3 / pu, 4),
                            binding="chain (latency)" if B <= per else "busiest resource per column pass",
                            energy_mJ_per_token=round((e / (B * tau) + P_static / agg) * 1e3, 3),
                            system_w=round(P_static + e / t, 0)))
        return out
    ar = rows(1, 1.0, 0.0)
    mtp = rows(V41_POSITIONS, V41_TAU, V41_DRAFT_FRACTION)
    return dict(design="V4.1 HBM comparator, GPU organisation (tier 3, 96 dies, 1M)",
                system=dict(packages=n // 2, dies=n, stacks=4 * n),
                ar=dict(tokens_s_b1=ar[0]["per_user_tokens_s"], rows=ar, saturated_tokens_s=max(x["aggregate_tokens_s"] for x in ar),
                        sat_batch=_sat_batch(ar)["batch"]),
                mtp=dict(tokens_s_b1=mtp[0]["per_user_tokens_s"], rows=mtp,
                         saturated_tokens_s=max(x["aggregate_tokens_s"] for x in mtp), sat_batch=_sat_batch(mtp)["batch"],
                         tau=V41_TAU, positions=V41_POSITIONS),
                capacity_users=cap, capacity_basis="results/arch/arch_budget_v41.json capacity[1048576].hbm_users",
                occupancy_us_per_pass=dict(ar_8_users=round(occ(8, 8), 1), mtp_1_user=round(occ(6, 6), 1),
                                           dedicated_issue_per_user=round(issue1, 1)),
                energy=dict(static_w={k: round(v, 1) for k, v in st.items()}, static_w_total=round(P_static, 1),
                            basis="system MACs by format (2 ops), weights (routed union over the pass) and per-user "
                                  "KV + index keys over the whole HBM path, SMEM staging, the ROM array's dedicated-"
                                  "unit energy per token (same units), fabric bytes over two switch hops; static per die: "
                                  "SM + dedicated-unit logic, SMEM + L2, 4 PHY, HBM interface idle, links; the NVL-class "
                                  "switch itself not charged"),
                note="B <= 8 users ride the 8 MMA columns on one weight fetch (the chain re-priced with B columns: "
                     "dedicated-unit issue repeats per user); beyond, column passes interleave and the busiest of SM "
                     "time, dedicated-unit issue and the weight sweep bounds the step")


# ---- GPU tiers ----
def _fit_line(pts):
    xs = list(pts)
    ts = [b / pts[b] for b in xs]
    n = len(xs)
    mx, mt = sum(xs) / n, sum(ts) / n
    b = sum((x - mx) * (t - mt) for x, t in zip(xs, ts)) / sum((x - mx) ** 2 for x in xs)
    a = mt - b * mx
    return a, b, {x: round(x / (a + b * x), 1) for x in xs}


def gpu_economics():
    fixed = GPU_FIT["fixed_seconds_qwen"]
    s_per_B = (1 / 230.0 - fixed) / (2 * GPU_FIT["qwen_fp8_weight_bytes"])
    wl, kvb = _qwen_wl()
    t1 = fixed + s_per_B * (GPU_FIT["qwen_fp8_weight_bytes"] + GPU_FIT["qwen_fp8_kv_bytes_8k"])
    a, b, fitted = _fit_line(DFLASH_T3_B200)
    inc = max(b, s_per_B * kvb)
    capq = int((B200_HBM_B * HBM_CAP_EFF - GPU_FIT["qwen_fp8_weight_bytes"]) // kvb)

    def q_rows(W):
        out = []
        for B in sorted(set([x for x in ECON_BATCHES if x <= capq] + [capq])):
            t = t1 + (B - 1) * inc
            out.append(dict(batch=B, per_user_tokens_s=round(1 / t, 1), aggregate_tokens_s=round(B / t, 1),
                            per_user_ms_per_token=round(t * 1e3, 4),
                            energy_mJ_per_token=round(W * t / B * 1e3, 2)))
        return out
    q = q_rows(B200_W_DECODE)
    q_tdp = q_rows(B200_W_TDP)
    # V4.1-Flash on 8x B200 (tier 2 form): weights read once a step (routed union over the batch), each user's
    # index keys and KV, NCCL-class all-reduces
    tot, dense, routed, c = _v41_weight_split()
    fixed_layer = fixed / 36
    idx_user = 262144 * A.IDX_KEY_B * 4 * 38                        # gpu_tier2's per-token index-key read
    state_user = 0.0
    for L in range(c["num_layers"]):
        r = c["compress_ratios"][L]
        if L in c["kv_source_layer_ids"] and r:
            state_user += 1048576 // r * (A.CKV_ROW_B + A.IDX_KEY_B)
        state_user += c["window_tokens"] * A.WIN_ROW_B
    ckpt = json.loads((ROOT / "configs/models/candidates/deepseek-v4.1-flash.json").read_text())["checkpoint_bytes"]
    capv = int((8 * B200_HBM_B * HBM_CAP_EFF - ckpt) // state_user)
    v = []
    for B in sorted(set([x for x in ECON_BATCHES if x <= capv] + [capv])):
        t = (40 * fixed_layer + s_per_B * (_v41_weight_bytes(B) + B * idx_user) / 8 + 40 * 5 * NCCL_ALLREDUCE_S)
        v.append(dict(batch=B, per_user_tokens_s=round(1 / t, 1), aggregate_tokens_s=round(B / t, 1),
                      per_user_ms_per_token=round(t * 1e3, 4),
                      energy_mJ_per_token=round(8 * B200_W_DECODE * t / B * 1e3, 2)))
    t2 = {x["design"]: x for x in gpu_tier2()}
    qs = t2["Qwen3-8B on 1x B200, FP8 weights, 8K, calibrated"]
    vs = t2["DeepSeek-V4.1-Flash on 8x B200, calibrated"]
    anchors = [dict(tier=1, design=f"Qwen3-8B, 1x B200, SGLang FA4, BF16, AR, concurrency {B} (DFlash paper Table 3)",
                    batch=B, aggregate_tokens_s=x, per_user_tokens_s=round(x / B, 1),
                    energy_mJ_per_token_at_689W=round(B200_W_DECODE / x * 1e3, 1), line_fit_tokens_s=fitted[B])
               for B, x in DFLASH_T3_B200.items()]
    anchors += [dict(tier=1, design=x["design"], batch=1, aggregate_tokens_s=x["tokens_s"], per_user_tokens_s=x["tokens_s"],
                     energy_mJ_per_token_at_689W=round(B200_W_DECODE * (8 if "8x B200" in x["design"] else 1)
                                                      / x["tokens_s"] * 1e3, 1))
                for x in TIER1 if "B200" in x["design"] and "concurrency" not in x["design"] and "AR (DFlash" not in x["design"]]
    return dict(
        qwen=dict(design="Qwen3-8B on 1x B200, FP8, 8K (tier 2)", system=dict(gpus=1, packages=1, dies=2, stacks=8),
                  rows=q, rows_at_tdp=q_tdp, tokens_s_b1=q[0]["per_user_tokens_s"],
                  saturated_tokens_s=max(x["aggregate_tokens_s"] for x in q), sat_batch=_sat_batch(q)["batch"],
                  dflash_b1=dict(reasoning_mix=qs["spec_tokens_s_reasoning_mix"], math_code=qs["spec_tokens_s_math_code"]),
                  calibration=dict(paper_line_fixed_ms=round(a * 1e3, 4), paper_line_per_user_us=round(b * 1e6, 2),
                                   fitted_tokens_s=fitted, measured_tokens_s=DFLASH_T3_B200,
                                   per_user_increment_8k_us=round(inc * 1e6, 2),
                                   kv_8k_fp8_us=round(s_per_B * kvb * 1e6, 2),
                                   rule="step(B) = tier-2 step(1) + (B - 1) x max(the paper's fitted per-user increment, "
                                        "one 8K FP8 user's KV at the fitted B200 bytes rate); the paper's increment "
                                        "includes its own (shorter-context) KV, so the max is GPU-favourable"),
                  capacity_users=capq, capacity_basis="180 GB x 0.90 less FP8 weights over 604 MB per user"),
        v41=dict(design="DeepSeek-V4.1-Flash on 8x B200, 1M (tier 2)", system=dict(gpus=8, packages=8, dies=16, stacks=64),
                 rows=v, tokens_s_b1=v[0]["per_user_tokens_s"], saturated_tokens_s=max(x["aggregate_tokens_s"] for x in v),
                 sat_batch=_sat_batch(v)["batch"], mtp_b1=vs["spec_tokens_s"], capacity_users=capv,
                 per_user_state_bytes=state_user,
                 capacity_basis="8 x 180 GB x 0.90 less the 510.3 GB checkpoint over each user's CKV + index keys "
                                "(KV-owner layers 2, 8, 14, 20) and 40 windows"),
        anchors=anchors, power=dict(decode_w=B200_W_DECODE, tdp_w=B200_W_TDP,
                                    source="technology.json power.gpu_reference_power (measured decode 689 W; NVL72 TDP)"))


# ---- cost ----
def cost_row(name, system, rom_mask_sets, b1, sat, model_nre=True):
    pk = system["packages"]
    hw = pk * COST["package_usd"]
    comp = system["dies"] * 815.0 * COST["silicon_usd_per_mm2"] + system["stacks"] * COST["hbm_stack_usd"]
    nre_hi = rom_mask_sets * COST["mask_set_usd"]
    nre_lo = rom_mask_sets * COST["mask_set_usd"] * COST["rom_coding_fraction"]
    per_sys_hi = nre_hi / COST["production_units"]
    per_sys_lo = nre_lo / COST["production_units"]
    tot_lo, tot_hi = hw + per_sys_lo, hw + per_sys_hi
    return dict(design=name, packages=pk, dies=system["dies"], silicon_mm2=system["dies"] * 815.0,
                hbm_stacks=system["stacks"], rom_mask_sets=rom_mask_sets,
                hardware_usd_iso_package=hw, component_usd_silicon_and_stacks=round(comp),
                rom_nre_usd=dict(coding_layers_only=nre_lo, full_mask_sets=nre_hi),
                rom_nre_per_system_usd=dict(coding_layers_only=per_sys_lo, full_mask_sets=per_sys_hi),
                capex_per_system_usd=dict(low=round(tot_lo), high=round(tot_hi)),
                tokens_s_b1=b1, tokens_s_saturated=sat,
                usd_per_tokens_s_b1=dict(low=round(tot_lo / b1, 2), high=round(tot_hi / b1, 2)),
                usd_per_tokens_s_saturated=dict(low=round(tot_lo / sat, 2), high=round(tot_hi / sat, 2)))


def economics():
    v41r = v41_rom_economics()
    units_j = v41r["energy"]["categories_mJ_per_token"]["units"] * 1e-3
    qr = qwen_rom_economics()
    qh = qwen_hbm_economics()
    vh = v41_hbm_economics(units_j)
    gp = gpu_economics()

    def pick(rows, B):
        return next(x for x in rows if x["batch"] == B)
    summary = []
    for name, blk, rows_key in (("Qwen ROM AR (G = 6,144)", qr["ar"], "rows"), ("Qwen HBM tier 3 AR", qh["ar"], "rows"),
                                ("Qwen HBM tier 3 DFlash", qh["dflash"], "rows"), ("Qwen 1x B200 AR (tier 2)", gp["qwen"], "rows"),
                                ("V4.1 ROM AR", v41r["ar"], "rows"), ("V4.1 ROM MTP m = 1", v41r["mtp_m1"], "rows"),
                                ("V4.1 HBM tier 3 AR", vh["ar"], "rows"), ("V4.1 HBM tier 3 MTP", vh["mtp"], "rows"),
                                ("V4.1 8x B200 AR (tier 2)", gp["v41"], "rows")):
        rows = blk[rows_key]
        s = _sat_batch(rows)
        summary.append(dict(design=name, tokens_s_b1=rows[0]["per_user_tokens_s"], energy_mJ_b1=rows[0]["energy_mJ_per_token"],
                            sat_batch=s["batch"], sat_aggregate_tokens_s=s["aggregate_tokens_s"],
                            sat_per_user_tokens_s=s["per_user_tokens_s"], energy_mJ_sat=s["energy_mJ_per_token"],
                            capacity_users=rows[-1]["batch"]))
    S = {x["design"]: x for x in summary}
    R = {x["design"]: x for x in summary}
    modes = dict(zip([x["design"] for x in summary],
                     [qr["ar"]["rows"], qh["ar"]["rows"], qh["dflash"]["rows"], gp["qwen"]["rows"], v41r["ar"]["rows"],
                      v41r["mtp_m1"]["rows"], vh["ar"]["rows"], vh["mtp"]["rows"], gp["v41"]["rows"]]))

    def slo(names):
        """Largest aggregate with every user at >= ECON_SLO_TOKENS_S_PER_USER, over the design's modes."""
        best = 0.0
        for n_ in names:
            ok = [x["aggregate_tokens_s"] for x in modes[n_] if x["per_user_tokens_s"] >= ECON_SLO_TOKENS_S_PER_USER]
            best = max([best] + ok)
        return best or None
    systems = (("Qwen ROM (AR, G = 6,144)", qr["system"], qr["system"]["dies"], ["Qwen ROM AR (G = 6,144)"]),
               ("Qwen HBM tier 3 (AR / DFlash)", qh["system"], 0, ["Qwen HBM tier 3 AR", "Qwen HBM tier 3 DFlash"]),
               ("Qwen 1x B200 (tier 2, AR)", gp["qwen"]["system"], 0, ["Qwen 1x B200 AR (tier 2)"]),
               ("V4.1 ROM array (AR / MTP m = 1)", V41_ROM_SYSTEM, V41_ROM_SYSTEM["dies"], ["V4.1 ROM AR", "V4.1 ROM MTP m = 1"]),
               ("V4.1 HBM tier 3 (AR / MTP)", vh["system"], 0, ["V4.1 HBM tier 3 AR", "V4.1 HBM tier 3 MTP"]),
               ("V4.1 8x B200 (tier 2, AR)", gp["v41"]["system"], 0, ["V4.1 8x B200 AR (tier 2)"]))
    cost = []
    for name, system, masks, names in systems:
        b1 = max(R[n_]["tokens_s_b1"] for n_ in names)
        sat = max(x["aggregate_tokens_s"] for n_ in names for x in modes[n_])
        c_ = cost_row(name, system, masks, b1, sat)
        s_ = slo(names)
        c_["tokens_s_at_slo"] = s_
        c_["usd_per_tokens_s_at_slo"] = (dict(low=round(c_["capex_per_system_usd"]["low"] / s_, 2),
                                              high=round(c_["capex_per_system_usd"]["high"] / s_, 2)) if s_ else None)
        c_["modes"] = names
        cost.append(c_)
    return dict(summary=summary, qwen_rom=qr, qwen_hbm=qh, v41_rom=v41r, v41_hbm=vh, gpu=gp, cost=cost,
                cost_inputs=COST, mac_ops=MAC_OPS, slo_tokens_s_per_user=ECON_SLO_TOKENS_S_PER_USER,
                cost_rule="best mode of each design at each point: b1 = its fastest single-user mode, saturated = its "
                          "largest aggregate within the per-user state capacity; capex = packages at the iso-package "
                          "price + ROM mask NRE / production units (low: coding layers only; high: full mask sets)")


ECON_SOURCES = ("tools/uarch_model.py", "tools/arch_budget_v41.py", "tools/arch_budget_qwen3.py",
                "configs/hardware/technology.json", "configs/hardware/architectures.json",
                "configs/hardware/technology_inputs.json", "results/arch/arch_budget_v41.json",
                "results/arch/qwen3_budget.json", "results/arch/v41_rack.json", "results/arch/qwen_gpu_calibration.json",
                "results/arch/v41_hbm_region_preflight.json", "results/speculative/dflash_block_acceptance.json",
                "results/rtl/gpu_sm_exact.json", "results/rtl/gpu_sm_blockdot_exact.json",
                "results/rtl/gpu_supply_barrier.json", "configs/models/candidates/deepseek-v4.1-flash.json")


# ---------------------------------------------------------------------------------------------------------
# Economics levers (W14b; root 2026-09-29): V4.1 ROM static-power reduction, the adaptive MTP policy, and
# via-programmable ROM mask cost.  Calls the sections above; changes none of them.
# ---------------------------------------------------------------------------------------------------------
# Power-state constants.  ReGate = Y. Xue and J. Huang, "ReGate: Enabling Power Gating in Neural Processing Units",
# MICRO 2025 (arXiv 2508.02536): 7 nm prototype, Table 3 and section 6.1.
PG = dict(
    logic_residual=0.03,          # ReGate 6.1: power-gated logic leaks 3% of its ON static power
    sram_sleep_residual=0.25,     # ReGate 6.1: sleep-mode (retention) SRAM 25%
    sram_off_residual=0.002,      # ReGate 6.1: powered-off SRAM 0.2%
    rom_residual=0.03,            # ASSUMED: a mask ROM holds no state, so its array and periphery gate like logic
    hbm_if_residual=0.03,         # ReGate 3/4: HBM controller + PHY low-power mode (the DRAM self-refreshes); gated
                                  # like logic
    serdes_lpi_residual=0.10,     # ASSUMED: 112G PAM4 SerDes in low-power idle keeps ~10% (CDR/bias kept warm)
    cg_residual=0.10,             # ASSUMED: clock power left when a region's ICGs are closed (global spine, enables)
    stage_wake_s=1e-6,            # ASSUMED: an 815 mm2 stage domain woken as ~100 staggered sub-domains of ReGate's
                                  # 10-cycle SA-class domains to bound rush current (di/dt): ~1,000 cycles
    stage_wake_s_c6=133e-6,       # sensitivity: Haswell C6 worst-case wake (Schoene et al., "Wake-up latencies for
                                  # processor idle states on current x86 processors", 2015) -- includes state
                                  # save/restore a stateless ROM stage does not need; an upper bound
    stage_bet_s=0.5e-6,           # ASSUMED: break-even time at die scale ~ ReGate Table 3's 412-469 cycles (HBM, ICI,
                                  # whole SA) at 1 GHz; the gating overhead energy is leakage x BET (its definition)
    hbm_wake_cycles=60,           # ReGate Table 3: HBM controller & PHY power on/off delay 60 cycles
    serdes_wake_s=5e-6,           # IEEE 802.3bj EEE: Tw_PHY targeted at ~5 us for a 100 Gb/s PHY
)


def _stage_windows(g):
    """Per-stage time on the single-user critical path (the stage's active window at batch 1; the head stage
    carries the embed and argmax), and each stage's start time on the path."""
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    lps = 40 / V41_STAGES
    win, start, t = {}, {}, 0.0
    for n in g.path(sink):
        L = g.nodes[n]["layer"]
        c = sum(g.contrib[n].values())
        s = V41_STAGES if (L is None or L < 0) else int(L / lps)
        win[s] = win.get(s, 0.0) + c
        start.setdefault(s, t)
        t += c
    return win, start, t


def _region_busy(g):
    """Per-stage, per-die busy time of the ROM field (weight matvecs) and the hub (every other issued unit).  The
    field's is pair-weighted (busy pair-seconds / placed pairs): with the per-pair ICG only an op's holding pairs
    clock, so region clock gating (policy 2) charges the field clock for that equivalent full-field time."""
    lps = 40 / V41_STAGES
    out = {}
    for n, nd in g.nodes.items():
        L = nd["layer"]
        if L is None or L < 0 or nd["kind"] in ("collective", "hop"):
            continue
        s = int(L / lps)
        b = out.setdefault(s, dict(field=0.0, hub=0.0))
        if nd.get("_uarch"):
            b["field"] += nd["issue"] * busy_pairs(nd) / PAIR_W["placed_pairs"]
        else:
            b["hub"] += nd["issue"]
    return out


def v41_die_static_parts(d):
    """One layer die's static power by region and class, from the area ledger and the uarch constants (their sum is
    the economics section's ungated die static)."""
    E = A._env()
    clock = E["clock"]
    a = area_ledger(d)
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]["per_die"]["static_w"]
    cl = CLOCK_J_MM2 * clock
    N = PAIR_W["placed_pairs"]
    return dict(
        # ROM field MEASURED per pair (PAIR_W); hub from its area, UNCALIBRATED
        field=dict(clock=N * pair_power(clock)["clock"], leak_logic=N * PAIR_W["leak_cell"], leak_rom=N * PAIR_W["leak_rom"]),
        hub=dict(clock=cl * (a["hub_logic_mm2"] + 0.15 * a["vm_ports"]),
                 leak_logic=a["hub_logic_mm2"] * LEAK["logic"], leak_sram=a["vm_ports"] * LEAK["sram_array"]),
        hbm_if=4 * HBM_IDLE_W_STACK, serdes=rack["serdes_always_on"], ucie=rack["ucie_idle"])


def _die_energy(p, period, window, busy, policy, wake_s, pg_ok):
    """Static energy of one die over one token period: `window` s active (at batch 1 the critical-path window, at
    saturation the stage's occupancy), `busy` = region busy times inside it, the rest idle.
    policies: 0 ungated; 1 stage clock gating; 2 + region clock gating inside the window; 3 + power gating of the
    idle stage (retention SRAM, gated logic and ROM, HBM PHY power-down, SerDes / UCIe low-power idle) when the
    idle gap fits the wake-up and the break-even time."""
    r = PG["cg_residual"]
    idle = max(0.0, period - window)
    clk = p["field"]["clock"] + p["hub"]["clock"]
    leak = p["field"]["leak_logic"] + p["field"]["leak_rom"] + p["hub"]["leak_logic"] + p["hub"]["leak_sram"]
    io = p["hbm_if"] + p["serdes"] + p["ucie"]
    if policy == 0:
        return (clk + leak + io) * period
    if policy == 1:
        e_clk = clk * (window + r * idle)
    else:
        e_clk = sum(p[k]["clock"] * (min(busy[k], window) + r * (window - min(busy[k], window))) for k in ("field", "hub")) \
            + r * clk * idle
    if policy < 3 or not pg_ok:
        return e_clk + (leak + io) * period
    on = window + wake_s                      # the wake-up runs with the stage leaking at its ON level
    off = max(0.0, period - on)
    leak_off = (p["field"]["leak_logic"] * PG["logic_residual"] + p["field"]["leak_rom"] * PG["rom_residual"]
                + p["hub"]["leak_logic"] * PG["logic_residual"] + p["hub"]["leak_sram"] * PG["sram_sleep_residual"])
    io_off = p["hbm_if"] * PG["hbm_if_residual"] + (p["serdes"] + p["ucie"]) * PG["serdes_lpi_residual"]
    serdes_on = min(period, window + PG["serdes_wake_s"])
    e_io = p["hbm_if"] * on + p["hbm_if"] * PG["hbm_if_residual"] * off \
        + (p["serdes"] + p["ucie"]) * (serdes_on + PG["serdes_lpi_residual"] * (period - serdes_on))
    e_clk -= r * clk * off                    # a power-gated stage has no clock at all
    return e_clk + leak * on + leak_off * off + leak * PG["stage_bet_s"] + e_io


POLICIES = ("ungated", "stage clock gating", "+ region clock gating", "+ stage power gating (retention)")


def v41_static_power(ec=None):
    """V4.1 ROM array static energy per token under the four policies, at batch 1 (AR and MTP m = 1) and at
    saturation, with the wake-up schedule check (no wake may land on the single-user token path)."""
    ec = ec or economics()
    v = ec["v41_rom"]
    d = copy.deepcopy(PRESETS["proposal"])
    p = v41_die_static_parts(d)
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]
    ungated_die = sum(p["field"].values()) + sum(p["hub"].values()) + p["hbm_if"] + p["serdes"] + p["ucie"]
    assert abs(ungated_die * V41_ROM_SYSTEM["layer_dies"] / v["energy"]["static_w"]["layer_dies"] - 1) < 0.005
    table_leak = rack["per_die"]["table_leakage_w"]
    table_other = rack["per_die"]["table_static_w"] - table_leak
    head_w = rack["static"]["head_dies"] / V41_ROM_SYSTEM["head_dies"]
    out = {}
    for mode, P in (("ar", 1), ("mtp_m1", V41_POSITIONS)):
        _, g = _v41_graph(d, P)
        win, start, T = _stage_windows(g)
        busy = _region_busy(g)
        if P > 1:                                   # the MTP step adds the draft on the head dies
            Td = V41_DRAFT_FRACTION * v["ar"]["rows"][0]["per_user_ms_per_token"] * 1e-3
            win[V41_STAGES] += Td
            T += Td
        tau = V41_TAU if P > 1 else 1.0
        dyn = (v["energy"]["mtp_dynamic_mJ_per_token"] if P > 1 else
               v["energy"]["dynamic_mJ_per_token_die"] + v["energy"]["stack_mJ_per_token"]) * 1e-3
        occ = dict(v41_rom_ledger(g)["stage_occupancy_s"])
        if P > 1:
            occ[max(occ)] += Td
        per_sat = max(occ.values())
        res = {}
        for label, wake in (("wake_1us", PG["stage_wake_s"]), ("wake_c6_133us", PG["stage_wake_s_c6"])):
            pts = {}
            for point, period, act in (("batch1", T, win), ("saturated", per_sat, occ)):
                rows = []
                for pol in range(4):
                    e_layer = e_head = e_tab = 0.0
                    gated = 0
                    for s in range(V41_STAGES + 1):
                        w = act.get(s, 0.0)
                        b = busy.get(s, dict(field=w, hub=w))
                        ok = period - w >= wake + PG["stage_bet_s"]
                        gated += bool(ok and pol == 3)
                        e = _die_energy(p, period, w, b, pol, wake, ok)
                        if s < V41_STAGES:
                            e_layer += V41_TP * e
                        else:                       # head dies: the rack's static, scaled by the layer-die policy ratio
                            e_head += V41_ROM_SYSTEM["head_dies"] * head_w * period * e / (ungated_die * period)
                    # Engram table dies: ROM tables, no state; active for the gathers (L1, L14) + wake, else gated
                    tw = 2 * 0.5e-6 * (P if point == "saturated" else 1)
                    t_on = min(period, tw + wake) if pol == 3 else period
                    e_tab = V41_ROM_SYSTEM["table_dies"] * (
                        table_other * period + table_leak * (t_on + PG["logic_residual"] * (period - t_on)))
                    e_static = e_layer + e_head + e_tab
                    rate_tokens = tau / period
                    rows.append(dict(policy=POLICIES[pol], static_mJ_per_token=round(e_static / tau * 1e3, 2),
                                     energy_mJ_per_token=round((e_static / tau + dyn) * 1e3, 2),
                                     static_w=round(e_static / period, 0), stages_power_gated=gated,
                                     tokens_s=round(rate_tokens, 1)))
                pts[point] = rows
            # the wake schedule: every stage is woken `wake` before its window opens.  At batch 1 the schedule is
            # static and periodic, so a wake never lands on the token path while wake + BET <= the stage's idle
            idle_min = min(T - w for s, w in win.items())
            pts["wake_on_token_path_us"] = 0.0 if idle_min >= wake + PG["stage_bet_s"] else round((wake + PG["stage_bet_s"] - idle_min) * 1e6, 2)
            pts["min_idle_batch1_us"] = round(idle_min * 1e6, 2)
            pts["serdes_prewake_fits"] = bool(idle_min >= PG["serdes_wake_s"])
            res[label] = pts
        out[mode] = dict(period_batch1_us=round(T * 1e6, 2), period_saturated_us=round(per_sat * 1e6, 3),
                         dynamic_mJ_per_token=round(dyn * 1e3, 3),
                         window_us={str(k): round(x * 1e6, 2) for k, x in sorted(win.items())},
                         start_us={str(k): round(x * 1e6, 2) for k, x in sorted(start.items())}, **res)
    return dict(policies=POLICIES, constants=PG, die_static_w={k: (round(x, 3) if not isinstance(x, dict) else
                                                                {kk: round(vv, 3) for kk, vv in x.items()})
                                                            for k, x in p.items()},
                basis="per layer die: ROM field clock and leakage MEASURED per pair (PAIR_W, W18: 7,102 placed pairs; "
                      "region clock gating = the per-pair ICG, charged for the pair-weighted busy time); hub (dedicated "
                      "units + VM ports) clock and leakage from its area, UNCALIBRATED; HBM interface idle, always-on SerDes and UCIe from "
                      "results/arch/v41_rack.json; head dies at the rack's static scaled by the layer-die policy "
                      "ratio; Engram table dies at the rack's leakage, gated outside their gathers; dynamic "
                      "energy unchanged from the economics section", **out)


def adaptive_mtp(ec=None):
    """MTP while it gives the larger aggregate (few users), AR beyond: the per-batch best of the two curves."""
    ec = ec or economics()
    out = {}
    for key, ar, mtp in (("v41_rom", ec["v41_rom"]["ar"]["rows"], ec["v41_rom"]["mtp_m1"]["rows"]),
                         ("v41_hbm", ec["v41_hbm"]["ar"]["rows"], ec["v41_hbm"]["mtp"]["rows"])):
        A_ = {r["batch"]: r for r in ar}
        M_ = {r["batch"]: r for r in mtp}
        rows = []
        for B in sorted(A_):
            a, m = A_[B], M_[B]
            pick, mode = (m, "MTP") if m["aggregate_tokens_s"] > a["aggregate_tokens_s"] else (a, "AR")
            rows.append(dict(batch=B, mode=mode, per_user_tokens_s=pick["per_user_tokens_s"],
                             aggregate_tokens_s=pick["aggregate_tokens_s"],
                             per_user_ms_per_token=pick["per_user_ms_per_token"],
                             energy_mJ_per_token=pick["energy_mJ_per_token"],
                             ar_aggregate_tokens_s=a["aggregate_tokens_s"], mtp_aggregate_tokens_s=m["aggregate_tokens_s"]))
        # the exact switch: MTP's aggregate B x r_mtp (until it saturates) against AR's B x r_ar
        r_ar, s_ar = ar[0]["per_user_tokens_s"], max(r["aggregate_tokens_s"] for r in ar)
        r_m, s_m = mtp[0]["per_user_tokens_s"], max(r["aggregate_tokens_s"] for r in mtp)
        # AR's per-user rate is flat until its own saturation on the ROM array, so the crossing is exact there
        # (B x r_ar = MTP's saturated aggregate); where AR's per-user rate falls with batch (the HBM chain) the
        # sweep brackets it
        flat = all(abs(r["per_user_tokens_s"] - r_ar) < 0.5 for r in ar if r["batch"] * r_ar <= s_m)
        switch = s_m / r_ar if (s_m < s_ar and flat) else None
        first_ar = next((r["batch"] for r in rows if r["mode"] == "AR"), None)
        prev = max([r["batch"] for r in rows if first_ar and r["batch"] < first_ar], default=None)
        out[key] = dict(rows=rows, switch_users=round(switch, 2) if switch else None,
                        switch_bracket=[prev, first_ar],
                        rule="MTP while batch < switch_users, AR at and above it", ar_b1=r_ar, mtp_b1=r_m,
                        ar_saturated=s_ar, mtp_saturated=s_m)
    return out


MASK = dict(
    full_set_usd=COST["mask_set_usd"],
    single_mask_usd=(0.5e6, 1.0e6),   # a single EUV mask $0.5-1M (SemiEngineering, "Mask Complexity, Cost, And Change";
                                      # siliconmasters.co 2025 guide); a coding via/metal layer at the lower metals is EUV
    coding_masks_per_die=(1, 2),      # Taalas HC1: a model changes TWO metal masks (EE Times, "Taalas Specializes to
                                      # Extremes for Extraordinary Token Speed"); one via mask is the lower bound
    v41_base_designs=3,               # layer, head (+DSpark), Engram table dies: each a shared base mask set
    qwen_base_designs=1,              # both Qwen dies share one base
)


def rom_mask_sensitivity(ec=None):
    """ROM mask NRE and V4.1 / Qwen ROM $ per tok/s under via-programmable ROM: shared base masks per die role plus
    1-2 coding masks per distinct die, against the economics section's full-set and 10%-coding cases."""
    ec = ec or economics()
    c = {r["design"]: r for r in ec["cost"]}
    out = []
    for name, dies, bases in (("V4.1 ROM array (AR / MTP m = 1)", V41_ROM_SYSTEM["dies"], MASK["v41_base_designs"]),
                              ("Qwen ROM (AR, G = 6,144)", QWEN_ROM_PRODUCT["k"], MASK["qwen_base_designs"])):
        r = c[name]
        hw = r["hardware_usd_iso_package"]
        cases = [("full mask set per die (economics high)", dies * MASK["full_set_usd"], None),
                 ("10% of a set per die (economics low)", dies * MASK["full_set_usd"] * COST["rom_coding_fraction"], None)]
        for n in MASK["coding_masks_per_die"]:
            for pm in MASK["single_mask_usd"]:
                cases.append((f"via-programmable: {n} coding mask(s) x ${pm / 1e6:.1f}M per die + shared bases",
                              bases * MASK["full_set_usd"] + dies * n * pm, bases * MASK["full_set_usd"]))
        for label, nre, base in cases:
            per_sys = nre / COST["production_units"]
            per_sys_nb = (nre - base) / COST["production_units"] if base is not None else None
            tot = hw + per_sys
            out.append(dict(design=name, case=label, nre_usd=nre, nre_per_system_usd=round(per_sys),
                            capex_per_system_usd=round(tot),
                            usd_per_tokens_s_b1=round(tot / r["tokens_s_b1"], 2),
                            usd_per_tokens_s_saturated=round(tot / r["tokens_s_saturated"], 2),
                            usd_per_tokens_s_saturated_base_excluded=(round((hw + per_sys_nb) / r["tokens_s_saturated"], 2)
                                                                      if per_sys_nb is not None else None)))
    g = c["V4.1 8x B200 (tier 2, AR)"]
    return dict(rows=out, inputs=MASK, production_units=COST["production_units"],
                gpu_reference=dict(design=g["design"], usd_per_tokens_s_saturated=g["usd_per_tokens_s_saturated"]["low"],
                                   usd_per_tokens_s_at_slo=g["usd_per_tokens_s_at_slo"]["low"]),
                note="base_excluded: the shared base masks amortised over later models (a new model re-spins only the "
                     "coding masks)")


def economics_levers(ec=None, gated=True):
    ec = ec or economics()
    lv = dict(static_power=v41_static_power(ec), adaptive_mtp=adaptive_mtp(ec), rom_masks=rom_mask_sensitivity(ec))
    if gated:
        lv["gated_alike"] = gated_energy_table(ec, lv)
    return lv


LEVER_SOURCES = ECON_SOURCES


# ---------------------------------------------------------------------------------------------------------
# Gated alike (W14c; root 2026-09-29 fairness follow-up): the adopted gating policies (clock gating with the
# ICG residual; power gating of idle domains with the cited residuals; a wake scheduled from the static schedule
# only into idle gaps that fit wake + break-even, so no wake lands on the token path) applied to every design:
# the tier-3 HBM comparators (SMs, dedicated units, L2, HBM PHY, SerDes / UCIe) and the Qwen ROM package, beside
# the V4.1 ROM array's stage gating.  The same PG constants; GPU rows stay measured.
# ---------------------------------------------------------------------------------------------------------
CORE_WAKE = dict(wake=PG["stage_wake_s"], bet=PG["stage_bet_s"])          # SM array, dedicated units, lanes, SU, L2
LINK_WAKE = dict(wake=PG["serdes_wake_s"], bet=PG["stage_bet_s"])          # SerDes and UCIe low-power idle


def _hbm_wake(clock):
    return dict(wake=PG["hbm_wake_cycles"] / clock, bet=412 / clock)      # ReGate Table 3 (HBM ctrl + PHY)


def _domain(logic=0.0, rom=0.0, sram=0.0, io_w=0.0, io_res=None, clock=1e9, sram_retain=True, **wk):
    """A power domain's static parts from its area by class (uarch constants) plus interface power io_w."""
    cl = CLOCK_J_MM2 * clock
    leak = logic * LEAK["logic"] + rom * LEAK["rom_array"] + sram * LEAK["sram_array"]
    leak_off = (logic * LEAK["logic"] * PG["logic_residual"] + rom * LEAK["rom_array"] * PG["rom_residual"]
                + sram * LEAK["sram_array"] * (PG["sram_sleep_residual"] if sram_retain else PG["sram_off_residual"]))
    return dict(clock=cl * (logic + 0.15 * (rom + sram)), leak=leak, leak_off=leak_off, io=io_w,
                io_off=io_w * (PG["logic_residual"] if io_res is None else io_res), **wk)


def _domain_energy(dm, period, busy, gaps, policy):
    """Static energy of one domain over `period` with `busy` s active and the idle split into `gaps`.
    policy 0 ungated; 1 clock gating (ICG residual in idle); 2 + power gating of every gap >= wake + BET (the
    wake completes at the gap's end, so it never delays the next busy phase; overhead = static x BET)."""
    r = PG["cg_residual"]
    on = dm["leak"] + dm["io"]
    if policy == 0:
        return (dm["clock"] + on) * period
    e = (dm["clock"] + on) * busy
    for g in gaps:
        if policy == 2 and g >= dm["wake"] + dm["bet"]:
            off = g - dm["wake"]
            e += (r * dm["clock"] + on) * dm["wake"] + (dm["leak_off"] + dm["io_off"]) * off + on * dm["bet"]
        else:
            e += (r * dm["clock"] + on) * g
    return e


def _even_gaps(period, busy, n):
    idle = max(0.0, period - busy)
    return [idle / n] * n if n and idle > 0 else []


def _gaps_of(segs, dom, T):
    """Idle gaps of `dom` in an ordered segment list [(duration, {busy domains})] over one period T (the gap
    that wraps across the token boundary is one gap)."""
    gaps, cur, busy, first = [], 0.0, 0.0, None
    for dur, doms in segs:
        if dom in doms:
            if first is None:
                first = cur
            elif cur > 0:
                gaps.append(cur)
            busy += dur
            cur = 0.0
        else:
            cur += dur
    if first is None:
        return 0.0, [T]
    gaps.append(cur + first + max(0.0, T - sum(d for d, _ in segs)))
    return busy, [g for g in gaps if g > 0]


def v41_hbm_timeline(positions=1):
    """The V4.1 HBM chain (v41_hbm_chain, group-slot) as an ordered segment list: each matvec an SM op (+ its x
    fill and barrier; the HBM streams its weights), each dedicated-unit node its path time (+ the other
    positions' issue; an index scan also holds HBM), each collective its share of the fabric terms (SerDes)."""
    dv = hbm_gpu_design("v41")
    clock = dv["clock_hz"]
    _, b = arch_graph(1048576)
    g = b.g
    path = g.path(b.sink)
    bc = dv["barrier"]["boundary_cycles"] / clock
    ncoll = sum(1 for x in path if g.nodes[x]["kind"] in ("collective", "hop"))
    fab = sum(V41_HBM_FABRIC_US.values()) + V41_HBM_FABRIC_US["collective_bytes"] * (positions - 1)
    segs = []
    for x in path:
        nd = g.nodes[x]
        k = node_key(x) if nd["kind"] == "matvec" else ""
        if nd["kind"] == "matvec" and k and k != "hc.fn":
            rows = nd["sweep"]["macs"] / NODE_K[k] / V41_HBM_DIES
            t = sm_op_cycles(rows, NODE_K[k], NODE_FMT[k], dv["drain_cycles"], True) / clock
            t += math.ceil(NODE_K[k] * positions * 2 / X_BCAST_BPC) / clock + bc
            segs.append((t, {"sm", "hbm", "l2"}))
        elif nd["kind"] in ("collective", "hop"):
            segs.append((fab * 1e-6 / ncoll, {"links", "l2"}))
        else:
            t = sum(g.contrib[x].values()) + (positions - 1) * nd.get("issue", 0.0)
            if x.endswith((".attn.scores", ".idx.topk_final")) or x == "argmax":
                t += bc
            segs.append((t, {"du", "hbm"} if x.endswith("idx.score") else {"du"}))
    return segs, clock, dv


def gated_energy_table(ec=None, lv=None):
    ec = ec or economics()
    lv = lv or economics_levers(ec, gated=False)
    import arch_budget_qwen3 as Q
    rows = []

    def add(design, point, tokens_s, dyn_J, parts):
        """parts: [(count, domain, period_s, busy_s, gaps)] for one period that emits tokens_s x period tokens."""
        out = dict(design=design, point=point, tokens_s=round(tokens_s, 1))
        for pol, name in ((0, "ungated"), (1, "clock_gated"), (2, "clock_and_power_gated")):
            e = sum(n * _domain_energy(dm, T, busy, gaps, pol) for n, dm, T, busy, gaps in parts)
            T0 = parts[0][2]
            out[f"{name}_static_w"] = round(e / T0, 1)
            out[f"{name}_mJ_per_token"] = round((e / (tokens_s * T0) + dyn_J) * 1e3, 2)
        rows.append(out)

    # ---- Qwen ROM package (2 dies): lanes + ROM + KV ring, stream unit, HBM PHY, UCIe ----
    qr = ec["qwen_rom"]
    qe, a = _qwen_rom_product()
    nq = QWEN_ROM_PRODUCT["k"]
    clock = qe["clock_hz"]
    ub = qe["unit_busy"]
    wl, kvb = _qwen_wl()
    grp = QWEN_ROM_PRODUCT["G"] * 18063.0 / 1e6
    dq = dict(lanes=_domain(logic=grp, rom=a["rom"], sram=a["sram"], clock=clock, **CORE_WAKE),
              su=_domain(logic=12.8, clock=clock, **CORE_WAKE),
              hbm=_domain(logic=40.0, io_w=4 * HBM_IDLE_W_STACK, clock=clock, **_hbm_wake(clock)),
              ucie=_domain(logic=10.0, clock=clock, **LINK_WAKE))
    tpx = Q.tp_exchanges(clock)
    ops = 5 * 36 + 1
    for point, T, tok in (("batch1", qe["cycles"] / clock, 1.0), ("saturated", 1 / qr["ar"]["saturated_tokens_s"], 1.0)):
        busy = dict(lanes=(ub["weights"] + ub["attn_scores"] + ub["attn_pv"] + ub["lm_head"]) / clock,
                    su=ub["stream"] / clock, hbm=min(T, kvb / nq / (4 * HBM_STACK_BPS)),
                    ucie=qe["exchange"]["token_cycles"] / clock)
        gaps = dict(lanes=ops, su=ops, hbm=36, ucie=tpx["exchanges"])
        dyn = qr["energy"]["dynamic_mJ_per_token"] * 1e-3
        add("Qwen ROM AR (G = 6,144)", point, tok / T, dyn,
            [(nq, dq[k], T, min(T, busy[k]), _even_gaps(T, min(T, busy[k]), gaps[k])) for k in dq])
    # ---- Qwen HBM tier 3 (2 dies): SMs, L2, HBM PHY, UCIe ----
    qh = ec["qwen_hbm"]
    dh = hbm_gpu_design("qwen")
    clock = dh["clock_hz"]
    sa, n = dh["sm_area"], dh["sm_count"]
    dm = dict(sm=_domain(logic=n * sa["logic_mm2"], sram=n * sa["sram_mm2"] , clock=clock, **CORE_WAKE),
              l2=_domain(sram=dh["l2"]["mm2"], clock=clock, **CORE_WAKE),
              hbm=_domain(logic=40.0, io_w=4 * HBM_IDLE_W_STACK, clock=clock, **_hbm_wake(clock)),
              ucie=_domain(logic=10.0, clock=clock, **LINK_WAKE))
    qops = qwen_hbm_ops(dh["element"], dh["barrier"]["boundary_cycles"], dh["drain_cycles"])
    ar_bytes = sum(b_ for b_, _ in qops)
    kv_die = kvb / 2
    w_die = ar_bytes - kv_die
    spec = {x["block"]: x for x in hbm_speculation_rows() if x["design"].startswith("qwen_hbm_dflash_b")}
    for mode, rws in (("AR", qh["ar"]["rows"]), ("DFlash", qh["dflash"]["rows"])):
        for point, r_ in (("batch1", rws[0]), ("saturated", _sat_batch(rws))):
            B, blk = r_["batch"], r_.get("block", 1)
            tau = r_.get("tau", 1.0)
            T = B * tau / r_["aggregate_tokens_s"]
            draft = spec[blk]["draft_bytes_per_die"] if mode == "DFlash" else 0.0
            passes = math.ceil(B * blk / dh["element"]["cols"])
            byt = passes * (w_die + draft) + B * kv_die
            busy = dict(sm=byt / (n * dh["element"]["ingest_Bpc"]) / clock, hbm=byt / dh["hbm_Bpc"] / clock,
                        l2=ops * dh["barrier"]["boundary_cycles"] / clock, ucie=Q.tp_exchanges(clock)["cycles"] / clock)
            gaps = dict(sm=ops, hbm=ops, l2=ops, ucie=Q.tp_exchanges(clock)["exchanges"])
            dyn = r_["energy_mJ_per_token"] * 1e-3 - qh["energy"]["static_w_total"] / r_["aggregate_tokens_s"]
            add(f"Qwen HBM tier 3 {mode}", point, r_["aggregate_tokens_s"], dyn,
                [(2, dm[k], T, min(T, busy[k]), _even_gaps(T, min(T, busy[k]), gaps[k])) for k in dm])
    # ---- V4.1 HBM tier 3 (96 dies): SMs, dedicated units, L2, HBM PHY, SerDes + UCIe ----
    vh = ec["v41_hbm"]
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]["per_die"]["static_w"]
    for mode, P, tau, rws in (("AR", 1, 1.0, vh["ar"]["rows"]), ("MTP", V41_POSITIONS, V41_TAU, vh["mtp"]["rows"])):
        segs, clock, dv = v41_hbm_timeline(P)
        sa = dv["sm_area"]
        dm = dict(sm=_domain(logic=dv["sm_count"] * sa["logic_mm2"], sram=dv["sm_count"] * sa["sram_mm2"], clock=clock,
                             **CORE_WAKE),
                  du=_domain(logic=dv["dedicated_units_footprint_mm2"] * GPU_LOGIC_UTIL, clock=clock, **CORE_WAKE),
                  l2=_domain(sram=dv["l2"]["mm2"], clock=clock, **CORE_WAKE),
                  hbm=_domain(logic=40.0, io_w=4 * HBM_IDLE_W_STACK, clock=clock, **_hbm_wake(clock)),
                  links=_domain(io_w=rack["serdes_always_on"] + rack["ucie_idle"], io_res=PG["serdes_lpi_residual"],
                                clock=clock, **LINK_WAKE))
        Tseg = sum(d_ for d_, _ in segs)
        for point, r_ in (("batch1", rws[0]), ("saturated", _sat_batch(rws))):
            T = r_["batch"] * tau / r_["aggregate_tokens_s"]
            if point == "batch1":
                parts = [(V41_HBM_DIES, dm[k], T) + _gaps_of(segs, k, T) for k in dm]
            else:
                # one column pass per period, each domain's idle one contiguous gap (as the ROM's saturation rule)
                per = max(1, dv["element"]["cols"] // P)
                npass = math.ceil(r_["batch"] / per)
                Tp = T / npass
                frac = {k: _gaps_of(segs, k, Tseg)[0] / Tseg for k in dm}
                occ = vh["occupancy_us_per_pass"]
                sm_busy = min(Tp, frac["sm"] * Tseg)
                du_busy = min(Tp, per * P * occ["dedicated_issue_per_user"] * 1e-6)
                busy = dict(sm=sm_busy, du=du_busy, l2=min(Tp, frac["l2"] * Tseg), hbm=min(Tp, frac["hbm"] * Tseg),
                            links=min(Tp, frac["links"] * Tseg))
                parts = [(V41_HBM_DIES, dm[k], Tp, busy[k], _even_gaps(Tp, busy[k], 1)) for k in dm]
                T = Tp
            dyn = r_["energy_mJ_per_token"] * 1e-3 - vh["energy"]["static_w_total"] / r_["aggregate_tokens_s"]
            add(f"V4.1 HBM tier 3 {mode}", point, r_["aggregate_tokens_s"], dyn, parts)
    # ---- V4.1 ROM array: the adopted stage policies (economics_levers) ----
    sp = lv["static_power"]
    for mode, key in (("AR", "ar"), ("MTP m = 1", "mtp_m1")):
        for point in ("batch1", "saturated"):
            p_ = sp[key]["wake_1us"][point]
            summ = {x["design"]: x for x in ec["summary"]}[f"V4.1 ROM {mode}"]
            tok = summ["tokens_s_b1"] if point == "batch1" else summ["sat_aggregate_tokens_s"]
            rows.append(dict(design=f"V4.1 ROM {mode}", point=point, tokens_s=tok,
                             ungated_static_w=p_[0]["static_w"], ungated_mJ_per_token=p_[0]["energy_mJ_per_token"],
                             clock_gated_static_w=p_[2]["static_w"], clock_gated_mJ_per_token=p_[2]["energy_mJ_per_token"],
                             clock_and_power_gated_static_w=p_[3]["static_w"],
                             clock_and_power_gated_mJ_per_token=p_[3]["energy_mJ_per_token"]))
    # ---- GPUs: measured board power (whatever the GPU gates is already inside it) ----
    for name, blk, n_gpu in (("Qwen 1x B200 AR (tier 2)", ec["gpu"]["qwen"], 1), ("V4.1 8x B200 AR (tier 2)", ec["gpu"]["v41"], 8)):
        for point, r_ in (("batch1", blk["rows"][0]), ("saturated", _sat_batch(blk["rows"]))):
            e = r_["energy_mJ_per_token"]
            rows.append(dict(design=name, point=point, tokens_s=r_["aggregate_tokens_s"], ungated_mJ_per_token=e,
                             clock_gated_mJ_per_token=e, clock_and_power_gated_mJ_per_token=e,
                             measured=f"{n_gpu} x {B200_W_DECODE:.0f} W measured decode power"))
    return dict(rows=rows, policies=("ungated", "clock gated (ICG residual 10%)",
                                     "clock + power gated (cited residuals, wake only into gaps >= wake + BET)"),
                domains=dict(core=CORE_WAKE, links=LINK_WAKE, hbm="ReGate Table 3: 60-cycle wake, 412-cycle BET"),
                basis="per domain: clock and leakage from its area by class (technology.json via the uarch constants), "
                      "interface power (HBM idle, SerDes / UCIe); busy time and idle gaps from each design's own "
                      "schedule: the V4.1 HBM chain walked node by node; Qwen dies with their ops' gaps split evenly "
                      "(181 op boundaries, 36 KV streams, 73 UCIe exchanges); at saturation one contiguous idle gap "
                      "per pass or token, as the ROM array's rule")


# ---------------------------------------------------------------------------------------------------------
# Consolidation (W16; user-approved study 2026-09-30).  The physical floorplans leave spare area the analytical
# die ledger did not predict.  This section re-derives the V4.1 ROM die count from the placed field geometry, the
# Engram table dies from their own (strip-free) floorplan, right-sizes the GPU-organised HBM dies to their PHY
# shoreline, sweeps the V4.1 HBM comparator's die count, re-prices cost on die area with a yield model, and
# re-examines the comparison rule.  It calls the sections above and changes none of them.
#
# DENSITY RULE (root, 2026-09-30): the product die count is stated at the ANALYTICAL ROM density (75.0 Mbit/mm2,
# the envelope the ROM designs are built on; results/floorplan/v41_rom_capacity.json forbids substituting the
# predictive macro area).  The ASAP7 predictive macro (~150 Mbit/mm2 raw) is physical feasibility only, and ROMA's
# TSMC 7 nm compiler (57.8 Mbit/mm2) is the conservative case; both are sensitivities in every table.
# ---------------------------------------------------------------------------------------------------------
import contextlib  # noqa: E402

_V41_CFG = json.loads((ROOT / "configs/models/candidates/deepseek-v4.1-flash.json").read_text())
_V41_ASM = json.loads((ROOT / "results/arch/v41_die_assembly.json").read_text())["ledger"]["layer"]
_V41_PLACE = json.loads((ROOT / "results/arch/v41_die_placement.json").read_text())

# The W10 layer-die re-fit, REPRODUCED here (the record is not committed): tools/v41_floorplan_refit.py at
# claude/w10-v41-rom-element 1f598e0b, --q-pair and --bf-pair both pair_final_physical_p5 (no placed BF16 pair
# exists: q2 stopped at detailed placement with 184 overlaps), hub from W11 proposal_w11_p6.  p5 is NOT closed.
CONS_REFIT = dict(
    slots=9931, used_pair_rows_busiest=7102,
    busiest_macros=dict(expert=13296, dense_qe=464, me=128, vm_constant=82, engram_spill=233),
    pair_footprint_mm2=416.76 / 7102,        # pair row = 2 ot_rom_8192x274_m8 + its 225.07 um MAC strip (485.136 x 120.96 um)
    strip_pitch_um=225.072, pair_pitch_um=485.136, rom_v_pitch_um=120.96,
    hub_mm2=75.878, edge_io_mm2=64.984, hbm_service_mm2=10.368, channels_mm2=13.701,
    whitespace_mm2=233.291, unused_slots_mm2=166.012, die_mm2=814.982,
    tool="tools/v41_floorplan_refit.py", tool_sha256="77d5ee466fa70ea447e3dc3a5a57459307d68afa3914515ac62493fc48cb663c",
    branch="claude/w10-v41-rom-element", commit="1f598e0b",
    element_pair=dict(record="results/physical_abi3/asap7/chip/v41_w10_elem/pair_final_physical_p5.json",
                      sha256="4ddaf275d54096663c6918776405dbd6ffdc21e576de9a00cb67323eba7b29c7",
                      fmax_hz=886002000.0, setup_wns_ns=-0.208666, drc=1, logic_utilisation=0.801, closed=False),
    committed=False,
    caveats=["the re-fit record is not committed: reproduced from the W10 branch (tool + p5 sha pinned here)",
             "p5 is not closed (886 MHz, WNS -209 ps, 1 DRC): a wider strip to close it lowers the slot count",
             "no placed BF16 pair exists (q2 failed at detailed placement): p5 stands in for the BF16 columns"])
CONS_FIELD_MM2 = CONS_REFIT["slots"] * CONS_REFIT["pair_footprint_mm2"]           # the ROM/MAC slot field, 582.8 mm2
CONS_SLIVER_MM2 = CONS_REFIT["whitespace_mm2"] - CONS_REFIT["unused_slots_mm2"]   # whitespace outside the field
# Where that whitespace is (measured on the reproduced re-fit's rectangles): the die-edge ring outside the core
# (1.02-1.09 mm wide: die 814.98 - core 696.56 = 118.43 mm2) less the edge I/O instances in it (HBM PHYs, SerDes,
# UCIe: 64.90 mm2, all in the ring) = 53.52 mm2; and gaps inside the core (core - slot field - hub - HBM service -
# channels = 13.84 mm2: hub halos and field-edge fragments).  Neither is ROM field: no whole macro column fits the
# ~1 mm ring beside the PHYs, and the core gaps are halos.  They can hold only the NON-distributed overhead (I/O and
# ESD, PLLs, seal ring, edge decap); clock buffers, DFT/MBIST and field decap are distributed over the field.
CONS_GEOM = dict(
    w10_refit=dict(field_mm2=CONS_FIELD_MM2, ring_free_mm2=118.426 - 64.902, core_gap_mm2=13.84,
                   src="W10 re-fit reproduced (claude/w10-v41-rom-element 1f598e0b), v1 HBM PHY 12.0 x 0.833 mm"),
    w18_legal_phy=dict(field_mm2=9637 * CONS_REFIT["pair_footprint_mm2"], ring_free_mm2=138.836 - 65.001,
                       core_gap_mm2=13.72,
                       src="claude/w18-die-assembly 4f9de5b5 results/floorplan/v41_pack_refit_w18_e8p5.json (sha256 "
                           "472e9f5e9ba4a462b9042ec19d7048fd33cbc64623e2640f3c66cc3e1077afbb): the legal 8.5 mm PHY "
                           "abstract is taller, so 185 ROM rows and 9,637 slots; not on main"),
)
# ROOT RULING 2026-09-30: ring-only credit (the core halo gaps are not field; distributed overhead comes out of the
# field); the conservative case gives no credit
CONS_CREDIT = dict(ring=("ring_free_mm2",), none=())
# Element-pair pitch.  w10_budget: root's hard budget for W10's closed pair (485 x 121 um, abutment pins, no
# channel), the pack's pitch.  w18_measured: W18's tiling of the W10 p5 abstract with an 8.64 um pin channel under
# every row (claude/w18-die-assembly d1e3c0aa, results/physical_abi3/asap7/chip/v41_w18/pair_w10p5_abstract.json
# sha256 2218b6efbff9cf7bba5d7984014352f3d26ffdf75a8a481b33706cf7f5cd3f04, tiling die_floorplan_ch8.64:
# 522.72 x 140.40 um = +7.75% x +16.07%, area x 1.2507; ch4.32 x 1.2122, ch17.28 x 1.3276).  p5 is not closed.
CONS_PITCH = dict(w10_budget=dict(q_um=(485.136, 120.96), src="root hard budget for W10 p9/q7 (the pack pitch)"),
                  w18_measured=dict(q_um=(522.72, 140.40), src="W18 d1e3c0aa pair_w10p5_abstract.json tiling ch8.64"),
                  w10_q_1p2=dict(q_um=(476.0, 126.9), src="W10 (2026-09-30): the q pair at 1.2 GHz, 4096m8 ping-pong, WC "
                                                          "floorplan cells 21.9k um2 at 85% logic utilisation"),
                  w10_iii_1p2=dict(q_um=(574.0, 126.9), src="W10 (2026-09-30): the BF16_PAIR (iii) pair at 1.2 GHz, 32.3k "
                                                            "um2 cells (+20.7% tile)"))
# ROOT RULING 2026-09-30: the 1,024 BF16-capable pairs (2,048 BF16 macros) sit in their own columns at a 1,019 um
# pitch (the BF16 element strip), at the row pitch of the variant
CONS_BF16 = dict(
    pairs=1024,
    columns_outline_um=(1063.7, 131.76),
    columns_src="W10 (root relay 2026-09-30): the BF16 pair's PLANNED outline, 1,063.7 x 131.76 um = 0.1402 mm2 "
                "(four 12 um capture channels + margins), until q7 confirms; the earlier 1,019 um x row pitch is "
                "superseded",
    standard_pair_src="W10 (ab1146e5, 2026-09-30), ADOPTED by root: BF16 on the standard FP8/FP4 pair at the budget "
                      "pitch -- 16 BF16 weights a word read once per 8 cycles into 2 exact BF16 multipliers per "
                      "macro and the existing chain adders; exact (golden csum order unchanged); ~+1.1-1.3 k um2 "
                      "per pair (+5-6% of p8's 20.3 k, 85-87% utilisation: a closure risk); only wo_a slows, "
                      "~+48 cycles a layer (~-1% tok/s); not built",
    standard_pair_wo_a_extra_cycles=48,
    # ROOT DECISION 2026-09-30: option (ii) ADOPTED -- q pairs + 2 exact BF16 multipliers a macro, word cap (cap 2 was
    # +250 um2 a macro, +3.45 mm2 a die); W10 measured the BF16 ops at L = 8: wo_a 256 -> 384, cmp.wk 64 -> 128,
    # router 80 -> 128 cycles (busiest die 3,585 tok/s against 3,760 on columns)
    option_ii_extra_cycles={"wo_a": 128, "cmp.wk": 64, "router": 48}, option_ii_area_mm2=16.0,
    # USER DECISION 2026-09-30: maximum per-user rate, die count not a constraint -> option (iii) is the PRODUCT:
    # 4 BF16 multipliers a macro, 4-cycle hold, 4 chains at NCH = 24, W10's measured 574 x 126.9 um tile (every pair);
    # W10's per-op issue for the BF16 ops (cycles, busiest die): wo_a 192, cmp.wk 64, router 80, a_proj 160
    option_iii_issue_cycles={"wo_a": 192, "cmp.wk": 64, "router": 80, "a_proj": 160},
    # ROOT 2026-09-30 (update): option (ii) becomes cap 3 / NCH = 24 (cap 2 cannot place wo_a): busiest die 3,503 tok/s
    # (W10), ~+16 mm2 a die routed (ESTIMATE; W10 p12 measures it); the op cycles above are cap 2's, pending p12
)
BF16_MODES = ("standard_pair", "columns")
# ROM macro depth (W10 study, claude/w10-v41-rom-element c673fd43, results/uarch/v41_rom_depth_study.json): single-
# cycle SS limit and density per macro; element count unchanged (2 or 4 macros per element slot)
ROM_DEPTH_OPTS = {
    "8192m8": dict(ss_ghz=0.918, tt_ghz=1.14, mb_per_mm2=149.6, macros_per_slot=1, field_delta_mm2=0.0),
    "4096m8": dict(ss_ghz=1.206, tt_ghz=1.48, mb_per_mm2=142.4, macros_per_slot=2, field_delta_mm2=10.5),
    "2048m4": dict(ss_ghz=1.324, tt_ghz=1.654, mb_per_mm2=136.1, macros_per_slot=4, field_delta_mm2=20.52),
}
ROM_DEPTH_SRC = ("claude/w10-v41-rom-element c673fd43 results/uarch/v41_rom_depth_study.json (rom_gen analytical "
                 "compile, the shipped macro's calibrated generator); per-slot mux / select logic for 2-4 macros a slot "
                 "NOT included (W10 to state)")
SS_DERATE_MEASURED = 1.43   # W13 (root relay 2026-09-30): the TT-closed tc16 FP32 column re-timed at SS on its routed odb,
                            # setup -398 ps -> 759 MHz; pessimistic for logic re-hardened at WC
# W15 (root relay 2026-09-30): measured SS wire reach, period = 261 ps + 1.135 ps/um x L (routed 547-bit spans, SS setup,
# FF hold, 60/25): 504 um a stage at 0.833 ns, 748 um at 1.111 ns (the 1,118 um TT fit it replaces)
SS_REACH_UM = {1.2e9: 504.0, 0.9e9: 748.0}
MTP_KV_PER_POSITION = True    # W11 / root 2026-09-30: verify KV rows are per position (6 x 645 rows a pass), not shared
W15_V41_COLL_STAGES_SS = 48      # W18b MEASURED (claude/w18-die-assembly b359e69e die_route_layer_split.json): collective
                                 # -> farthest SerDes 48 stages at the SS reach (UCIe 37); the v41p17 fit carries 17
W18B_EXPERT_WIRE = 36 + 40       # W18b measured, M8/M9 trunks: VM x root -> farthest cluster 36 + farthest cluster -> VM
                                 # 40 (PLACEHOLDER cycles until W15's M8/M9-only reach lands; the routed lengths stand)
W11_SERIAL_MUL_EXTRA = 1         # W11 3bc74342: a LAT-3 mul misses 0.9 GHz by 17 ps -> LAT 4, +1 cycle a multiply in the
                                 # SU/SFU/softplus/Sinkhorn chains; priced as +1 slow cycle a chain node (a LOWER BOUND:
                                 # the per-node multiply count is not in the graph)
# W11 MEASURED serial build (claude/w11-suclose ddd2f725, results/physical_abi3/asap7/hdc/v41x/w11_serial/summary.json;
# root 2026-09-30): the SU light lane CLOSES at 1.111 ns SS / FF hold, 60/25 (929 MHz, sc_l5) with MLAT 5 (input-cut
# multiply) and ALAT 4.  Measured depths before -> after, in 0.9 GHz cycles: linear op 21 -> 30, exp 49 -> 71,
# sigmoid/silu 71 -> 94, rsqrt 37 -> 58, sqrt(softplus) 162 -> 216, Engram gate 104 -> 127, divide 19 -> 19, reducer
# tap 26 -> 35 and 3 -> 4 a tree/time level.  Folded as these added slow cycles on the serial-chain nodes IN PLACE OF
# the W11_SERIAL_MUL_EXTRA lower bound (the measured build already carries the slower multiply); the Sinkhorn unit
# itself is not in the serial build, so it keeps the +1 lower bound, and its SFU front (row max + exp) takes the exp
# delta.
W11_SERIAL_MEASURED = dict(linear=9, exp=22, sigmoid=23, silu=23, rsqrt=21, softplus=54, gate=23, div=0,
                           reduce_tap=9, reduce_per_level=1, sinkhorn_front_exp=22, sinkhorn_unit=W11_SERIAL_MUL_EXTRA,
                           light_lane_ss_mhz=929.0, period_ns=1.111, mlat=5, alat=4,
                           src="claude/w11-suclose ddd2f725 results/physical_abi3/asap7/hdc/v41x/w11_serial/summary.json "
                               "(depths.serial_build, added_cycles; sc_l5 pass)")


def _w11_serial_cycles(name, nd, levels):
    """Added 0.9 GHz cycles of one serial-chain node under W11's measured serial build."""
    m = W11_SERIAL_MEASURED
    if nd["kind"] == "sinkhorn":
        return m["sinkhorn_front_exp"] + m["sinkhorn_unit"]
    if nd["kind"] == "reduce":
        return m["reduce_tap"] + m["reduce_per_level"] * levels.get(name, 0)
    leaf = name.split(".")[-1]
    if leaf == "gate" and name.startswith("E"):
        return m["gate"]
    fn = A.SFU_NODE.get(leaf)
    if fn:
        return m[fn]
    return m["rsqrt"] if leaf == "rsqrt" else m["linear"]


# ROOT RULING 2026-09-30 (die size): the layer die is still sized by the old pack (815 mm2, 7,628 pair slots; W18b
# 510f376e die_assembly.json), while the product owner file needs 5,289 pairs a die (1,024 BF16 columns;
# results/arch/v41_stage_owner_product.json, max pairs_per_die_by_stage).  Shrink to 5,289 + ~10% margin; W18b
# floorplans it.  Until its crossings land, a SENSITIVITY row scales every on-die crossing by sqrt(area ratio).
DIE_SHRINK = dict(slots_now=7628, pairs_needed=5289, margin=0.10,
                  src="root ruling 2026-09-30; W18b claude/w18-die-assembly 510f376e; v41_stage_owner_product.json")
DIE_SHRINK["area_ratio"] = DIE_SHRINK["pairs_needed"] * (1 + DIE_SHRINK["margin"]) / DIE_SHRINK["slots_now"]
DIE_SHRINK["crossing_scale"] = math.sqrt(DIE_SHRINK["area_ratio"])
PRODUCT_SERIAL = "w11_measured"
SERIAL_TAG = ("ADOPTED + W15 SS wire reach (504 um) + W11 MEASURED serial build (1.111 ns SS, MLAT 5 / ALAT 4, "
              "light lane 929 MHz)")
# W18b INTERIM shrunk layer die (claude/w18-die-assembly 996f7982, results/physical_abi3/asap7/chip/v41_w18/
# shrink_p5_interim/shrunk_die.json, crossings_layer_split; root die-size ruling): 28.82 x 23.22 mm = 669 mm2 (linear
# scale 0.9062), 5,968 pair + 1,160 BF16 slots, 0 overflow.  Crossings at 504 um/stage: VM x root -> farthest cluster
# 30 (was 36), farthest cluster -> VM 33 (40), collective -> SerDes 45 (48), -> UCIe 34 (37); HBM window 25, index
# keys 39, top-k 38, selected KV 24 (not separately priced in the graph).  The field broadcast/return regions take
# the die's linear scale.  Die area, cost and power stay on the 815 mm2 ledger until the p12 floorplan lands.
DIE_OLD = dict(expert_wire=W18B_EXPERT_WIRE, coll_stages=W15_V41_COLL_STAGES_SS, field_scale=1.0)
DIE_SHRUNK_INTERIM = dict(expert_wire=30 + 33, coll_stages=45, field_scale=0.9062, mm2=669.255, pair_slots=5968,
                          bf16_slots=1160, src="claude/w18-die-assembly 996f7982 shrink_p5_interim/shrunk_die.json")
SHRINK_TAG = SERIAL_TAG + " + W18b shrunk-die interim crossings (669 mm2)"
# W11-stream (claude/w11-stream 540ef71c; record tool formulas at the shipped shape, idx_tail closed 1,249 MHz SS,
# chunk and tile routes PENDING): indexer key -> score 48 -> 100 (+52; chunk 39 -> 83, the tail's +8 is already in
# SOFTPLUS_FIX), attention tile input -> ov at TD 32 33 -> 72 (+39), engine bank guard 20 -> 44 (+24); W11 (answer,
# 2026-09-30): both are engine pipeline depths, paid once a scores pass AND once a p.v pass (the p.v pass reuses the
# tile after the softmax); throughput (II 1) unchanged
W11_STREAM_SS = {"suffix:idx.score": 52, "suffix:.attn.scores": 39 + 24, "suffix:.attn.pv": 39 + 24}
PRODUCT_TAG = SHRINK_TAG + " + W11 streaming depths (idx +52; attn tile +39 and bank guard +24 a scores and a p.v pass)"
QWEN_W12_TP4_ME_EXTRA_SS = 41 + 5 * 5 + 38 + 1 + 7   # W12 c6e6b845 at the 504 um reach: 112 cycles an ME op
PRODUCT_CLOCK_HZ = 1.2e9   # USER DECISION (AGENTS.md e7479589): 0.833 ns at SS for all logic in all four designs
PRODUCT_DYN_SCALE = 1.16   # root 2026-09-30: dynamic energy about +16% at 1.2 GHz (ASSUMED: the voltage for the clock)
SS_CURVE_GHZ = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.35)
SS_DERATE = 1.27     # USER DECISION 2026-09-30: sign-off at SS (setup) / FF (hold); logic without its own SS closure
                     # is derated by the ROM macro's SS/TT ratio (8192m8: 1.14 / 0.918 = 1.24; root: use 1.27)


def _cons_pair_mm2(pitch, bf16=False):
    x, y = CONS_PITCH[pitch]["q_um"]
    if bf16:
        return CONS_BF16["columns_outline_um"][0] * CONS_BF16["columns_outline_um"][1] / 1e6
    return x * y / 1e6
CONS_MACRO_MM2 = ROM_MACRO_UM2 / 1e6
CONS_STRIP_PER_PAIR_MM2 = CONS_REFIT["pair_footprint_mm2"] - 2 * CONS_MACRO_MM2    # MAC strip + gaps of one pair
CONS_TABLE_MACRO_MM2 = (CONS_REFIT["pair_pitch_um"] - CONS_REFIT["strip_pitch_um"]) * CONS_REFIT["rom_v_pitch_um"] / 2e6
CONS_TABLE_MACRO_B = 8192 * 33            # an Engram word: 264 payload bits of the 274-bit macro word (8 words a row)
CONS = dict(
    fill=0.90,                            # the study's slot fill (user instruction)
    overhead=0.125, overhead_band=(0.10, 0.15),
    overhead_basis=("per-die PDN bumps, IO/ESD, DFT, clock, decap not held by the floorplan.  On-chip decap alone "
                    "takes 'as much as 10%' of die area (M. Popovich, A. Mezhiba, E. Friedman, Power Distribution "
                    "Networks with On-Chip Decoupling Capacitors, Springer 2008) and 15-20% in high-performance "
                    "processors; technology.json floorplan.overhead_area_fraction is 0.10 (assumed, sweep "
                    "0.06-0.15).  ASSUMED 12.5%, band 10-15%.  The re-fit's edge slivers (whitespace outside the slot "
                    "field) hold it first ('partly holds'); the conservative case gives them no credit."),
    table_io_mm2=0.4 + 0.3888 * 1.043,    # 1 SerDes lane per table die (2 per table package, rack C4) at 0.4 mm2 +
                                          # one UCIe-A x64 module to its package peer
    table_logic_mm2=1.0,                  # ASSUMED: 24 gather slices + assembler (0.03 mm2 placed) + control, rounded up
)
# analytical: the layer-die ledger's mask-ROM area over its payload (checkpoint / 188, incl. SECDED 266/256)
CONS_A_ANALYTICAL = _V41_ASM["rom_mm2"] / (_V41_CFG["checkpoint_bytes"] / 188)
DENSITY = dict(
    analytical=dict(mm2_per_B=CONS_A_ANALYTICAL, mbit_mm2=round(_V41_ASM["rom_density_mbit_per_mm2"], 2),
                    basis="STORAGE-ONLY N5 (1 bit a mask-ROM cell): results/arch/v41_die_assembly.json ledger.layer, "
                          "N5 6T 0.021 um2 x ROMA's ROM/SRAM 0.33 / array efficiency 0.52, SECDED 266/256; the one "
                          "fit basis for both ROM designs (root ruling 2026-09-30).  Not HC1-derived: HC1 is a "
                          "cross-check only (4.31 MB/mm2 whole die)"),
    roma=dict(mm2_per_B=CONS_A_ANALYTICAL * _V41_ASM["rom_density_mbit_per_mm2"] / 57.8, mbit_mm2=57.8,
              basis="Wang et al., ROMA, ASP-DAC 2026 (TSMC 7 nm memory compiler, 8192x64: 57.8 Mbit/mm2; "
                    "technology.json rom entry): conservative sensitivity"),
    asap7=dict(mm2_per_B=None, mbit_mm2=round(8192 * 274 / ROM_MACRO_UM2, 1),
               basis="placed predictive ASAP7 ot_rom_8192x274_m8 macros of the integer macro map (physical "
                     "feasibility only; not substituted into the analytical total)"),
)


def _cons_nonexpert_macros():
    """Per-die non-expert macros (dense QE, ME, VM constants) of the integer macro map, and the expert macros."""
    mm = json.loads((ROOT / "results/floorplan/v41_die_macromap_expanded_woa.json").read_text())
    tot = {}
    for d in mm["layer_dies"]:
        for g_, v in d["macros_by_group"].items():
            tot[g_] = tot.get(g_, 0) + sum(v.values())
    return tot


def cons_stage_plan(S: int):
    """The 40 layers' ROM bytes laid out in layer order and cut into S equal-byte TP-4 stages (the placement rule of
    tools/v41_die_placement.py); a layer's fraction per stage, its start stage, and each stage's per-die macros
    (experts: 384 x 24 macros a layer a die; the non-expert macros spread over the layers by dense bytes)."""
    dense, routed = _V41_CFG["layer_dense_weight_bytes"], _V41_CFG["layer_routed_weight_bytes"]
    nl = len(dense)
    lay = [dense[L] + routed[L] for L in range(nl)]
    cap = sum(lay) / S
    tot = _cons_nonexpert_macros()
    nonexp = (tot["ROM_MAC.dense_QE"] + tot["ROM_MAC.ME"] + tot["VM.CONSTANT_HE"]) / 4
    exp_l = tot["ROM_MAC.expert"] / 4 / nl
    mac_l = [exp_l + nonexp * dense[L] / sum(dense) for L in range(nl)]
    frac, start, x = {}, {}, 0.0
    for L in range(nl):
        a, b = x, x + lay[L]
        s = int(a / cap + 1e-9)
        start[L] = min(s, S - 1)
        while a < b - 1e-6 and s < S:
            e = min(b, (s + 1) * cap)
            frac.setdefault(L, []).append((s, (e - a) / lay[L]))
            a, s = e, s + 1
        x = b
    macros = [0.0] * S
    for L, parts in frac.items():
        for s, f in parts:
            macros[s] += f * mac_l[L]
    return dict(S=S, frac=frac, start=start, macros_per_die=macros, busiest_macros=max(macros),
                payload_per_die_B=cap / 4, layers_per_stage=nl / S)


def _cons_busiest_macros(S):
    """Busiest layer die's macros at S stages, anchored to the re-fit's busiest die at 28 (layer macros, no spill)."""
    b = CONS_REFIT["busiest_macros"]
    anchor = b["expert"] + b["dense_qe"] + b["me"] + b["vm_constant"]
    return anchor * cons_stage_plan(S)["busiest_macros"] / cons_stage_plan(28)["busiest_macros"]


def _cons_need(pairs, payload_B, density, pitch, bf_pairs, depth="8192m8", extra_mm2=0.0):
    """ROM + element-strip area of `pairs` element pairs (bf_pairs of them BF16 column pairs) holding payload_B;
    `depth` scales the ROM area by the macro's density against the shipped 8192m8 (storage-only / ROMA: the array
    efficiency; ASAP7: the macro area)."""
    nq, nb = pairs - bf_pairs, bf_pairs
    fq, fb = _cons_pair_mm2(pitch), _cons_pair_mm2(pitch, True)
    dr = ROM_DEPTH_OPTS["8192m8"]["mb_per_mm2"] / ROM_DEPTH_OPTS[depth]["mb_per_mm2"]
    rom = (2 * pairs * CONS_MACRO_MM2 if density == "asap7" else payload_B * DENSITY[density]["mm2_per_B"])
    return rom * dr + nq * (fq - 2 * CONS_MACRO_MM2) + nb * (fb - 2 * CONS_MACRO_MM2) + extra_mm2


def cons_field_need_mm2(S, density, pitch="w10_budget", bf16="standard_pair", depth="8192m8"):
    """Slot-field area the busiest layer die needs at S stages: ASAP7 = its placed pair rows (FP8/FP4 pairs at the
    variant's pitch, the 1,024 BF16 pairs at 1,019 um); storage-only / ROMA = the payload at that density plus each
    pair's element strip (its footprint less its two ASAP7 macros; the element count is the read-width choice)."""
    pairs = _cons_busiest_macros(S) / 2
    return _cons_need(pairs, cons_stage_plan(S)["payload_per_die_B"], density, pitch,
                      CONS_BF16["pairs"] if bf16 == "columns" else 0, depth,
                      cons_bf16_hub_mm2(density) if bf16 == "hub_unit" else
                      CONS_BF16["option_ii_area_mm2"] if bf16 == "option_ii" else 0.0)


def cons_bf16_hub_mm2(density="analytical"):
    """Option (c) of root's BF16 lever: the BF16 weights (wo_a, router, a_proj's BF16 rows, cmp.wk: ~10.3 M a die,
    W10) in a small dedicated hub unit instead of the field -- BF16 MACs sized to keep wo_a at its 256-cycle issue
    (8.39 M products / 256 = 32,768 MACs at 509 um2, the closed mac_bf16_fp32_pipe_round_stage) plus their ROM at the
    density in shallow banks (1024x274 m8: 109.9 against 149.6 Mbit/mm2, ASSUMED to read 2,048 words a cycle)."""
    macs = 8.39e6 / 256 * 509e-6
    rom_b = 10.3e6 * 2
    dr = ROM_DEPTH_OPTS["8192m8"]["mb_per_mm2"] / 109.9
    rom = rom_b * 8 / 149.6e6 if density == "asap7" else rom_b * DENSITY[density]["mm2_per_B"]
    return macs + rom * dr


def cons_field_usable_mm2(overhead=None, credit="ring", geom="w10_refit"):
    """Usable slot field: the overhead reserve is charged to the credited whitespace first (ring: the die-edge ring
    outside the core, less its I/O instances; none), the rest to the field, then the fill factor."""
    o = CONS["overhead"] if overhead is None else overhead
    G = CONS_GEOM[geom]
    charge = max(0.0, o * FLOORPLAN["die_mm2"] - sum(G[k] for k in CONS_CREDIT[credit]))
    return CONS["fill"] * (G["field_mm2"] - charge)


def cons_min_stages(density, overhead=None, credit="ring", geom="w10_refit", pitch="w10_budget", bf16="standard_pair",
                    depth="8192m8"):
    u = cons_field_usable_mm2(overhead, credit, geom)
    return next(S for S in range(8, 90) if cons_field_need_mm2(S, density, pitch, bf16, depth) <= u)


def cons_head_dies(density, overhead=None, credit="ring", geom="w10_refit", pitch="w10_budget", depth="8192m8"):
    """The head group (lm_head, embedding, DSpark MTP; layer engines): TP-4 groups of the layer die's field."""
    b = _V41_PLACE["bytes"]
    per_die = (b["embed"] + b["head"] + b["mtp"]) / 4
    # the embedding is a row table (one row a token, no MACs): only lm_head and the drafter carry MAC strips
    m = (b["head"] + b["mtp"]) / 4 * _cons_busiest_macros(28) / cons_stage_plan(28)["payload_per_die_B"]
    need = _cons_need(m / 2, per_die, density, pitch, 0, depth)
    return 4 * math.ceil(need / cons_field_usable_mm2(overhead, credit, geom) - 1e-9)


def cons_table_dies(density, overhead=None):
    """Engram table dies: ROM, gather slices and links only (no MAC strips, hub, HBM); no floorplan exists, so the
    overhead gets no sliver credit and the layer die's channels are charged."""
    o = CONS["overhead"] if overhead is None else overhead
    usable = CONS["fill"] * (FLOORPLAN["die_mm2"] - CONS["table_io_mm2"] - CONS["table_logic_mm2"]
                             - CONS_REFIT["channels_mm2"] - o * FLOORPLAN["die_mm2"])
    cap = (usable / CONS_TABLE_MACRO_MM2 * CONS_TABLE_MACRO_B if density == "asap7"
           else usable / DENSITY[density]["mm2_per_B"])
    tb = _V41_PLACE["bytes"]["engram_table_L1"] + _V41_PLACE["bytes"]["engram_table_L14"]
    n = math.ceil(tb / cap)
    return dict(dies=n + (n % 2), usable_mm2=round(usable, 1), bytes_per_die=cap, table_bytes=tb)


def cons_engram_path(n_table, rates):
    """Engram gathers on fewer table dies: the switched path (rack record), rows per die, link load per package."""
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())
    p, tr = rack["paths"], rack["traffic"]["rows"]["T3_engram"]
    lane = rack["lanes"]["lane_net_Bps"]
    rows = 2 * A._env()["c"]["engram_hash_columns"]
    per_table = n_table // 2                                     # each Engram layer's table on half the dies
    maxrows = expected_max_load(rows // 2, per_table)
    pkgs = n_table // 2
    by_tok = tr["bytes_per_token"] - (72 + 4) * 16 + (n_table + 4) * 16    # token-id multicast to fewer dies
    out = dict(table_dies=n_table, table_packages=pkgs, rows_per_token=rows,
               expected_max_rows_per_die_per_layer=round(maxrows, 2),
               engram_l1_latency_us=round(p["engram_l1_s"] * 1e6, 3),
               engram_l1_slack_us=3.57, engram_l14_slack_us=round(p["engram_l14_slack_s"] * 1e6, 1),
               hops="unchanged: table package -> one 51.2T switch -> layer package (2 switched legs)",
               latency_basis="rack critical_paths: 2 switched legs + the 396 ns port read of all 48 rows at ONE port "
                             "(an upper bound for any table-die count) + serialisation into the consumer port",
               bytes_per_token=by_tok, link_Bps_per_package=2 * lane)
    for k, r in rates.items():
        load = r * by_tok / pkgs
        out[f"link_utilisation_{k}"] = round(load / (2 * lane), 4)
    return out


def cons_engram_slack(g):
    """Slack of each Engram delivery on the priced token DAG: the time its consumer's other input is ready minus the
    time the Engram value arrives (the DAG's E{L}.deliver hop: 2 board legs), and whether any Engram node is on the
    critical path.  The table-die count does not enter the DAG: the gather is token-addressed and prefetched."""
    fin = g.solve(True)
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    path = set(g.path(sink))
    out = {}
    for L in A._env()["c"]["engram_layer_ids"]:
        eng = f"E{L}.deliver" if f"E{L}.deliver" in g.nodes else f"E{L}.knorm"
        cons = f"L{L}.eng.dot"
        other = [x for x in g.nodes[cons]["deps"] if not x.startswith("E")]
        out[f"L{L}"] = dict(engram_ready_us=round(fin[eng] * 1e6, 3),
                            residual_ready_us=round(max(fin[x] for x in other) * 1e6, 3),
                            slack_us=round((max(fin[x] for x in other) - fin[eng]) * 1e6, 3),
                            on_critical_path=any(n.startswith(f"E{L}.") for n in path))
    return out


# ---- re-pricing the V4.1 ROM array at S stages: the arch DAG rebuilt with the packed placement at S groups ----
@contextlib.contextmanager
def _cons_stages(S):
    """Rebuild the arch DAG with the packed placement cut into S TP-4 groups: decode_critical_path.v41_machine is
    called with units = checkpoint x 4S / layer bytes (packed_placement's capacity rule), so every stage and
    substage hop moves to the new boundaries; no other node changes (tests/test_uarch_consolidation.py).  The arch
    cache is swapped for the duration and restored."""
    D_ = A.D
    orig = D_.v41_machine
    lt = sum(_V41_CFG["layer_dense_weight_bytes"]) + sum(_V41_CFG["layer_routed_weight_bytes"])
    units = _V41_CFG["checkpoint_bytes"] * 4 * S / lt

    def vm(*a, **k):
        if a and a[0] == "array" and "units" not in k:
            k["units"] = units
        return orig(*a, **k)
    saved = dict(_ARCH_CACHE)
    _ARCH_CACHE.clear()
    D_.v41_machine = vm
    try:
        yield units
    finally:
        D_.v41_machine = orig
        _ARCH_CACHE.clear()
        _ARCH_CACHE.update(saved)


@contextlib.contextmanager
def _cons_clock(hz):
    """Price the V4.1 ROM at clock `hz`: the arch environment's clock (every cycle-counted node, wire stages at the
    new period) and the W15 V4.1 collective fits' clock (their measured cycles take hz's period: conservative for the
    link flight part).  Restored on exit."""
    if hz is None:
        yield None
        return
    E = A._env()
    old = (E["clock"], E["p"])
    cf = w15_record()["configs"]
    oldw = {k: v["clock_hz"] for k, v in cf.items() if k.startswith("v41")}
    saved = dict(_ARCH_CACHE)
    _ARCH_CACHE.clear()
    E["clock"], E["p"] = hz, dataclasses.replace(E["p"], clock_hz=hz)
    for k in oldw:
        cf[k]["clock_hz"] = hz
    try:
        yield hz
    finally:
        E["clock"], E["p"] = old
        for k, v in oldw.items():
            cf[k]["clock_hz"] = v
        _ARCH_CACHE.clear()
        _ARCH_CACHE.update(saved)


def _cons_stage_of(name, nd, plan):
    L = nd["layer"]
    if L is None or L < 0 or L >= len(_V41_CFG["layer_dense_weight_bytes"]):
        return "head"
    return plan["start"][L]


def _cons_cooling(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S, tot):
    """Layer-die power at the saturated rate under the adopted per-pair ICG: die static without the field clock +
    the on-die dynamic energy (incl. the busy pairs' clock) at the rate.  Mean die, and the busiest stage (its own
    pair-seconds and hub share).  cooling_ungated: the same with every idle pair clocked (the pre-fix accounting)."""
    on_die = sum(v for k, v in cats.items() if k != "stack")
    mean_dyn = on_die * sat / (4 * S)
    busiest = max(tot, key=tot.get)
    b_pair = pair_s.get(busiest, 0.0) * pp["clock"] * dyn_scale
    share = (on_die - cats["field_clock_busy"]) / (4 * S) * max(tot.values()) / (sum(tot.values()) / len(tot))
    busiest_dyn = (share + b_pair) * sat
    return dict(limit_w_per_die=COOLING_LIMIT_W, dyn_scale=dyn_scale, busiest_stage=busiest,
                layer_die_static_w=round(die_static, 1),
                layer_die_mean_w_saturated=round(die_static + mean_dyn, 1),
                layer_die_busiest_w_saturated=round(die_static + busiest_dyn, 1),
                fits=bool(die_static + busiest_dyn <= COOLING_LIMIT_W),
                cooling_ungated=dict(static_w=round(die_static_ungated, 1),
                                     mean_w=round(die_static_ungated + mean_dyn - cats["field_clock_busy"] * sat / (4 * S), 1)),
                basis="per-pair ICG adopted: die static less the field clock + on-die dynamic energy (busy pairs' "
                      "clock included) at the saturated rate; busiest = its own pair-seconds + its occupancy share "
                      "of the rest")


def _cons_occupancy(g, plan):
    """Per-die issue seconds per stage, split ROM field / hub: routed experts over their stages in the placement's
    byte fractions, every other node on its layer's start stage (A.stage_occupancy's rule)."""
    occ = {}
    for name, nd in g.nodes.items():
        if nd["kind"] in ("collective", "hop"):
            continue
        s0 = _cons_stage_of(name, nd, plan)
        parts = ([(s, f) for s, f in plan["frac"][nd["layer"]]] if s0 != "head" and name.endswith(A.EXPERT_NODES)
                 else [(s0, 1.0)])
        for s, f in parts:
            b = occ.setdefault(s, dict(field=0.0, hub=0.0))
            b["field" if nd.get("_uarch") else "hub"] += nd["issue"] * f
    return occ


def _cons_windows(g, plan):
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    win, t = {}, 0.0
    for n in g.path(sink):
        c = sum(g.contrib[n].values())
        s = _cons_stage_of(n, g.nodes[n], plan)
        win[s] = win.get(s, 0.0) + c
        t += c
    return win, t


# Latency inventory (root 2026-09-30, user clock decision 1.2 GHz SS): every stream reports block | SS fmax | gap |
# fix | ADDED LATENCY CYCLES; the added cycles are folded in here as extra depth on the named node families (node
# name suffix -> cycles).  Empty until the inventories land.
V41_ADDED_LATENCY = {}
# W11 (a70c5d91, 2026-09-30): hub units at 1.2 GHz SS, ESTIMATES from TT x 1/1.43 until WC runs land.  The shared
# fast FP32 add/mul goes 3 -> ~6 stages; per dependent op: SU linear +12 (21 -> 33), SU reducer 26+3L -> 40+5L
# (+22 at L = 4), SFU exp +21, divide +8, sigmoid/silu +29, softplus +68, indexer +28, attention tile pass +17.
# Keys: "kind:<k>" (non-SFU nodes of that kind), "sfu:<class>" (SFU_NODE classes), "suffix:<name suffix>".
W11_LATENCY_SS_1P2 = {"kind:vector": 12, "kind:reduce": 22, "sfu:exp": 21, "sfu:div": 8, "sfu:sigmoid": 29,
                      "sfu:silu": 29, "sfu:softplus": 68, "suffix:idx.score": 28, "suffix:.attn.scores": 17}


def _cons_top(g, n=8):
    """The critical path's largest node families (us), after re-timing."""
    sink = [x for x in g.nodes if x.endswith("token.return")][0]
    fam = {}
    for x in g.path(sink):
        tail = x.split(".", 1)[1] if x.startswith(("L", "E")) and "." in x else x
        fam[tail] = fam.get(tail, 0.0) + sum(g.contrib[x].values())
    return {k: round(v * 1e6, 2) for k, v in sorted(fam.items(), key=lambda kv: -kv[1])[:n]}


def _lat_cycles(name, nd, lat):
    if not lat:
        return 0
    c = 0
    fn = A.SFU_NODE.get(name.split(".")[-1])
    if nd["kind"] in ("vector", "reduce"):
        c += lat.get(f"sfu:{fn}", 0) if fn else lat.get(f"kind:{nd['kind']}", 0)
    for k, v in lat.items():
        if k.startswith("suffix:") and name.endswith(k[7:]):
            c += v
        elif not k.startswith(("kind:", "sfu:", "suffix:")) and name.endswith(k):
            c += v
    return c
FIELD_CONCURRENCY = 0.5   # W18 (92d7f4f8 results/physical_abi3/asap7/chip/v41_w18/peak_current.json): a field-wide
                          # matvec draws 2,263 A a die (1.5x a B200-class package); adopted fix: at most 50% of the
                          # pairs read concurrently (+ a droop detector) -- the field's read time doubles


CDC_W18 = dict(fast_to_slow_slow_cycles=4, slow_to_fast_fast_cycles=5,
               vm_port_widening=dict(factor=4 / 3, bits_before_after={"VM x read": (549, 732), "result write": (4096, 5461),
                                                                      "attention scores/PV": (512, 683)},
                                     area_mm2_added=None, note="every slow-side port at a crossing 4/3 wider (no 25% "
                                                               "stalls); priced in consolidation()"),
               src="W18 cbaf864f results/physical_abi3/asap7/chip/v41_w18/clock_plan.json")
SLOW_KINDS = ("vector", "reduce", "sinkhorn")   # the serial-chain units: SU, SFU, softplus, reducer, Sinkhorn


# W11 MEASURED (root relay 2026-09-30, rtl/hdc/ot_hdc_fp32_add_lat.sv, routed at WC/SS, bit-identical LAT 3-7):
# the FP32 add's SS fmax and ns per dependent add.  1.2 GHz needs ~8-9 stages (~7-7.5 ns per add); SS/TT ~1.6.
FP32_ADD_SS = {3: (906e6, 3.31), 4: (939e6, 4.26), 5: (892e6, 5.61), 6: (889e6, 6.75), 7: (1208e6, 5.79),
               "ieee5": (992e6, 5.04)}
MODEL_CHAIN_ADD_STAGES = 3      # the model's hub chain units are priced with the 3-stage fast FP (ADD_LAT fastfp)
MODEL_ELEM_ADD_STAGES = FADD_PIPE   # the field element's chain adder (ot_fp32_add_rne_pipe, 5)
# root 2026-09-30: the old ot_hdc_softplus depth (259) is replaced by the SU's v41x softplus (162, ot_hdc_v41x_sfu.sv):
# 97 cycles a layer recovered
SOFTPLUS_FIX = {"suffix:softplus_sqrt": -97, "suffix:idx.topk_local": 8}   # + W11: idx_tail latency 8 -> 16   # ROOT RULING 2026-09-30: arch_budget_v41's SFU_DEPTH / V41 softplus
# 259 is the LEGACY standalone unit; the product uses the SU's v41x softplus (162) through this correction only.
# arch_budget_v41 stays FROZEN as the spec basis (the hardware is built to its derived widths; folding it there
# re-derives weight_macs 264,960 -> 246,528 etc.); the full re-baseline waits for the headline-restatement pass.


def _cons_adjust(g, P, clock, bf16, fc, lat, slow=None, chain_stages=None, elem_stages=None, ss_wire=False, d=None,
                 serial=None, die=None):
    """Re-time a priced V4.1 graph (one pass of P positions): the field-concurrency cap on every field read, W10's
    two-pass BF16 on wo_a, the latency inventory, and optionally a slower clock domain for the serial-chain units
    (slow = (hz, cdc_cycles)): their issue and depth stretch by clock / hz, and each crossing into the domain adds
    cdc_cycles of the slow clock (ASSUMED synchroniser); returns the pass time."""
    cyc = 1.0 / clock
    # the reducers' adder-tree levels, from the graph's as-priced depth (decode_critical_path: red_tail + FADD x levels)
    levels = {name: max(0, round((nd["depth"] * clock - A.D.K["red_tail"]) / A.D.FADD)) for name, nd in g.nodes.items()
              if nd["kind"] == "reduce"} if serial else {}
    # softplus correction and the latency inventory first (cycles at the model's 3-stage arithmetic), then the
    # serial-chain units' depth at chain_stages-deep adds (x chain_stages / 3), then the slow domain
    for name, nd in g.nodes.items():
        nd["depth"] = max(0.0, nd["depth"] + _lat_cycles(name, nd, lat) * cyc)
    if chain_stages:
        for name, nd in g.nodes.items():
            if nd["kind"] in SLOW_KINDS:
                nd["depth"] *= chain_stages / MODEL_CHAIN_ADD_STAGES
    if slow:
        # W11's domain map: the SU, SFU, reducer, Sinkhorn, the VM-H rotate network and group tiles run in the slow
        # domain; the crossing sits at the VM port, both ways (field x / results, attention, indexer, collectives):
        # every dependency edge between the domains pays cdc_cycles of the slow clock (FIFO latency, W18 to state)
        # W18 clock plan (cbaf864f, results/physical_abi3/asap7/chip/v41_w18/clock_plan.json): one PLL, 3.6 GHz /3 and
        # /4, STA-timed crossings; ratio-FIFO latency fast->slow 3.0-3.75 slow cycles (charge 4), slow->fast
        # 3.67-4.34 fast cycles (charge 5); slow = (hz, "w18") uses them, (hz, n) charges n slow cycles each way
        hz, cdc = slow
        f2s, s2f = ((CDC_W18["fast_to_slow_slow_cycles"] / hz, CDC_W18["slow_to_fast_fast_cycles"] / clock)
                    if cdc == "w18" else (cdc / hz, cdc / hz))
        for name, nd in g.nodes.items():
            sl = nd["kind"] in SLOW_KINDS
            if sl:
                nd["issue"] *= clock / hz
                nd["depth"] *= clock / hz
            if nd["kind"] not in ("hop",) and any((g.nodes[x]["kind"] in SLOW_KINDS) != sl for x in nd["deps"]):
                nd["depth"] += f2s if sl else s2f
    if ss_wire:
        # named step (root 2026-09-30): W15's SS reach -- every field broadcast/return wire term at ceil(L / 504 um)
        # (both ways) instead of the TT fit, every collective +2 x (30 - 17) stages to the link PHY, and the W11
        # LAT-4 serial multiply (+1 slow cycle a chain node)
        reach = SS_REACH_UM[1.2e9]
        dv = die or DIE_OLD
        for name, nd in g.nodes.items():
            u = nd.get("_uarch")
            if u:
                new = (dv["expert_wire"] if u["region"] == "expert" else
                       2 * math.ceil(d["bcast_um"][u["region"]] * dv["field_scale"] / reach))
                old = u["wire"] - d.get("vm_x_gather_stages", 0) - d.get("vm_ret_scatter_stages", 0)
                nd["depth"] += max(0, new - old) * cyc
            elif nd["kind"] == "collective":
                nd["depth"] += 2 * (dv["coll_stages"] - 17) * cyc
            elif nd["kind"] in SLOW_KINDS and slow and not serial:
                nd["depth"] += W11_SERIAL_MUL_EXTRA / slow[0]
    if serial == "w11_measured" and slow:
        # named step (root 2026-09-30): W11's MEASURED serial build at 1.111 ns SS replaces the 3-stage-add depths
        for name, nd in g.nodes.items():
            if nd["kind"] in SLOW_KINDS:
                nd["depth"] += _w11_serial_cycles(name, nd, levels) / slow[0]
    es = elem_stages or MODEL_ELEM_ADD_STAGES
    for name, nd in g.nodes.items():
        u = nd.get("_uarch")
        if u:
            # the element's chunk-8 chain floor and its K-split adder levels at es-stage adds
            t_read = max(u["t_read"], 8 * es) if u["t_read"] >= CHAIN_FLOOR else u["t_read"]
            nd["issue"] = max(t_read * P / fc, u["t_x"] * P, u["t_ret"] * P, u["t_mac"] * P) * cyc
            nd["depth"] += u["adder_levels"] * (es - MODEL_ELEM_ADD_STAGES) * cyc
            if bf16 == "standard_pair" and u["key"] == "wo_a":
                nd["issue"] += P * CONS_BF16["standard_pair_wo_a_extra_cycles"] * cyc
            if bf16 == "option_ii" and u["key"] in CONS_BF16["option_ii_extra_cycles"]:
                nd["issue"] += P * CONS_BF16["option_ii_extra_cycles"][u["key"]] * cyc
            if bf16 == "option_iii" and u["key"] in CONS_BF16["option_iii_issue_cycles"]:
                nd["issue"] = max(nd["issue"], P * CONS_BF16["option_iii_issue_cycles"][u["key"]] / fc * cyc)
    fin = g.solve(True)
    return fin[[n for n in g.nodes if n.endswith("token.return")][0]]


def cons_v41_rom(S, n_head=4, n_table=72, table_leak_scale=1.0, label=None, bf16="columns", clock_hz=None,
                 field_concurrency=1.0, added_latency=None, dyn_scale=1.0, slow_domain=None, chain_stages=None,
                 elem_stages=None, ss_wire=False, serial=None, die=None):
    """The V4.1 ROM array at S TP-4 stages, n_head head dies and n_table Engram table dies: AR and MTP m = 1 per
    user, the busiest-stage saturated aggregate, energy (ungated and the adopted stage power gating, 1 us wake),
    KV capacity, HBM stacks and die counts.  Same model pieces as the economics and levers sections."""
    plan = cons_stage_plan(S)
    lat = V41_ADDED_LATENCY if added_latency is None else added_latency
    with _cons_clock(clock_hz), _cons_stages(S):
        d = copy.deepcopy(PRESETS["proposal"])
        d["macros"] = round(BASE["macros"] * plan["busiest_macros"] / cons_stage_plan(28)["busiest_macros"])
        r1, g1 = _v41_graph(d, 1)
        # energy BEFORE re-timing: the field's pair-seconds per token are the work, not the (capped, stretched)
        # issue time -- the 50% cap halves the concurrent pairs and doubles the time, same pair-seconds
        led = v41_rom_ledger(g1)
        area = area_ledger(d)
        pw = power_ledger(d, g1, r1["clock_hz"], r1["tokens_s"], area)
        pp = pair_power(r1["clock_hz"])
        pair_s = {}
        for name, nd in g1.nodes.items():
            if nd.get("_uarch") and _cons_stage_of(name, nd, plan) != "head":
                for s0, f in ([(s, f) for s, f in plan["frac"][nd["layer"]]] if name.endswith(A.EXPERT_NODES)
                              else [(_cons_stage_of(name, nd, plan), 1.0)]):
                    pair_s[s0] = pair_s.get(s0, 0.0) + busy_pairs(nd) * nd["issue"] * f
        T1 = _cons_adjust(g1, 1, r1["clock_hz"], bf16, field_concurrency, lat, slow_domain, chain_stages, elem_stages,
                          ss_wire, d, serial, die)
        r1["T_us"], r1["tokens_s"] = T1 * 1e6, 1 / T1
        occ = _cons_occupancy(g1, plan)
        _, gv = _v41_graph(d, V41_POSITIONS)
        Tp = _cons_adjust(gv, V41_POSITIONS, r1["clock_hz"], bf16, field_concurrency, lat, slow_domain, chain_stages,
                          elem_stages, ss_wire, d, serial, die)
        occ_v = _cons_occupancy(gv, plan)
        win1, _ = _cons_windows(g1, plan)
        fstarts = cons_field_starts(g1, plan, r1["clock_hz"])
        eslack = cons_engram_slack(g1)
        winv, _ = _cons_windows(gv, plan)
    Td = V41_DRAFT_FRACTION * T1
    step1 = Tp + Td
    occ_v.setdefault("head", dict(field=0.0, hub=0.0))["hub"] += Td
    tot = {s: v["field"] + v["hub"] for s, v in occ.items()}
    tot_v = {s: v["field"] + v["hub"] for s, v in occ_v.items()}
    sat, sat_m = 1.0 / max(tot.values()), V41_TAU / max(tot_v.values())
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]
    link_die = rack["per_die"]["static_w"]["serdes_always_on"] + rack["per_die"]["static_w"]["ucie_idle"]
    # ADOPTED per-pair ICG (W18 / power-cal): an idle pair keeps only its 0.22 mW leakage; a busy pair's clock is
    # dynamic (pair-seconds x its clock power).  The ungated form (every idle pair clocked, 0.092 W at 1.2 GHz) is
    # kept as `cooling_ungated` for the waterfall only.
    field_clock_ungated = pw["field"]["clock_w"]
    die_static_ungated = pw["clock_w"] + pw["leakage_w"] + pw["hbm_idle_w"] + link_die
    die_static = die_static_ungated - field_clock_ungated
    head_w = rack["static"]["head_dies"] / V41_ROM_SYSTEM["head_dies"]
    tl = rack["per_die"]["table_leakage_w"] * V41_ROM_SYSTEM["table_dies"] * table_leak_scale
    to = (rack["per_die"]["table_static_w"] - rack["per_die"]["table_leakage_w"]) * n_table
    static = dict(layer_dies=4 * S * die_static, head_dies=n_head * head_w, table_dies=tl + to)
    P_static = sum(static.values())
    cats = {k: V41_TP * v * (dyn_scale if k != "stack" else 1.0) for k, v in led["per_die_categories_J"].items()}
    cats["field_clock_busy"] = V41_TP * sum(pair_s.values()) * pp["clock"] * dyn_scale    # ICG: busy pairs' clock
    dyn = sum(v for k, v in cats.items() if k != "stack") + cats["stack"]
    e_pass = sum(v * (1 if k in ("hbm_if", "stack") else V41_POSITIONS) for k, v in cats.items())
    # W11 (root 2026-09-30): each verify position attends its OWN window (w_{p-127}..w_p) and its own index selection,
    # so the attention KV rows are NOT shared across the 6 positions -- 6 x the rows a pass (the index keys stay once
    # a pass).  The attention job's time already repeats per position; the correction is the rows' HBM energy.
    kv_rows_J = V41_TP * sum(640 * A.WIN_ROW_B / 4 for n in g1.nodes if n.endswith(".attn.scores")) * E_HBM_B
    if MTP_KV_PER_POSITION:
        e_pass += (V41_POSITIONS - 1) * kv_rows_J
    dyn_m = (e_pass + V41_DRAFT_FRACTION * dyn) / V41_TAU
    # gated (the adopted stage power gating, 1 us wake): v41_static_power's rule on this plan's stages
    p = v41_die_static_parts(d)
    p["field"]["clock"] = 0.0          # per-pair ICG: the field clock is in the dynamic energy (cats field_clock_busy)
    ungated_die = sum(p["field"].values()) + sum(p["hub"].values()) + p["hbm_if"] + p["serdes"] + p["ucie"]
    table_leak_die, table_other_die = tl / max(1, n_table), to / max(1, n_table)
    wake = PG["stage_wake_s"]

    def gated(period, act, busy, P):
        out = {}
        for pol in (0, 3):
            e = 0.0
            for s in list(range(S)) + ["head"]:
                w = act.get(s, 0.0)
                b = busy.get(s, dict(field=w, hub=w))
                ok = period - w >= wake + PG["stage_bet_s"]
                ed = _die_energy(p, period, w, b, pol, wake, ok)
                e += 4 * ed if s != "head" else n_head * head_w * ed / ungated_die
            tw = 2 * 0.5e-6 * P
            t_on = min(period, tw + wake) if pol == 3 else period
            e += n_table * (table_other_die * period + table_leak_die * (t_on + PG["logic_residual"] * (period - t_on)))
            out[pol] = e
        return out
    win1["head"] = win1.get("head", 0.0)
    winv["head"] = winv.get("head", 0.0) + Td
    pts = {}
    for key, period, act, busy, P, tau, dy in (
            ("ar_b1", T1, win1, occ, 1, 1.0, dyn), ("ar_sat", 1 / sat, tot, occ, 1, 1.0, dyn),
            ("mtp_b1", step1, winv, occ_v, 1, V41_TAU, dyn_m), ("mtp_sat", V41_TAU / sat_m, tot_v, occ_v, V41_POSITIONS, V41_TAU, dyn_m)):
        e = gated(period, act, busy, P)
        rate = tau / period
        pts[key] = dict(tokens_s=round(rate, 1), ungated_mJ=round((e[0] / tau + dy) * 1e3, 2),
                        gated_mJ=round((e[3] / tau + dy) * 1e3, 2), ungated_static_w=round(e[0] / period, 1),
                        gated_static_w=round(e[3] / period, 1), gated_system_w=round(e[3] / period + dy * rate, 1))
    rows_ = _CONS_CTX
    windows_rings = max(2, math.ceil(plan["layers_per_stage"]))
    per_user = rows_ * (A.CKV_ROW_B + A.IDX_KEY_B) / 4 + _V41_CFG_WINDOW() * A.WIN_ROW_B * windows_rings
    users = int(HBM_CAP_EFF * A.ROM_DIE_HBM_STACKS * HBM_STACK_B // per_user)
    dies = 4 * S + n_head + n_table
    return dict(label=label or f"S = {S}", stages=S, bf16=bf16, clock_hz=r1["clock_hz"], layer_dies=4 * S, head_dies=n_head, table_dies=n_table,
                dies=dies, packages=dies // 2, hbm_stacks=4 * (4 * S + n_head), busiest_die_macros=d["macros"],
                ar_tokens_s_b1=round(1 / T1, 1), mtp_tokens_s_b1=round(V41_TAU / step1, 1),
                ar_saturated_tokens_s=round(sat, 1), mtp_saturated_tokens_s=round(sat_m, 1),
                stage_hops=sum(1 for n in g1.nodes.values() if n["kind"] == "hop" and n.get("hop_kind") in ("stage", "substage")),
                pipeline_hops_us=round(r1["breakdown_us"].get("pipeline_hops", 0.0), 3),
                cooling=_cons_cooling(die_static, die_static_ungated, cats, pair_s, pp, dyn_scale, sat, S, tot),
                field_concurrency=field_concurrency, added_latency=dict(lat), slow_domain=slow_domain,
                chain_stages=chain_stages, elem_stages=elem_stages, field_starts=fstarts, ss_wire=ss_wire, serial=serial,
                die=(die or DIE_OLD),
                critical_path_top_us=_cons_top(g1),
                capacity_users_1m=users, static_w_ungated=dict({k: round(v, 1) for k, v in static.items()},
                                                             total=round(P_static, 1)),
                energy=pts, busiest_stage=max(tot, key=tot.get), busiest_stage_us=round(max(tot.values()) * 1e6, 2),
                layers_per_stage=round(plan["layers_per_stage"], 3), engram_dag_slack=eslack)


def _V41_CFG_WINDOW():
    return A._env()["c"]["window_tokens"]


# ---- cost: die area with a yield model (replaces the iso-package B200 price) ----
FAB = dict(
    wafer_usd=16988.0, wafer_basis="S. Khan, A. Mann, 'AI Chips: What They Are and Why They Matter', CSET 2020: TSMC "
                                   "5 nm wafer ~ $16,988 (estimate; cited)",
    wafer_d_mm=300.0, edge_exclusion_mm=3.0,           # ASSUMED edge exclusion
    d0_per_cm2=0.10, d0_basis="TSMC 2020 Technology Symposium: N5 D0 ~0.10-0.11 /cm2 at the HVM ramp, < 0.1 after "
                              "(reported by AnandTech / Tom's Hardware); cited",
    alpha=3.0, alpha_basis="ASSUMED negative-binomial clustering (Stapper); no harvesting or redundancy on any design",
    package_usd=dict(cowos_l_2die=1100.0, cowos_s_1die=750.0),
    package_basis="Raymond James via Silicon Analysts: CoWoS-S ~$750 (H100: 814 mm2 + 5-6 HBM stacks, ~2,500 mm2 "
                  "interposer), CoWoS-L ~$1,100 (B200); cited analyst estimates",
    test_assembly_usd=920.0, test_basis="Raymond James (H100 test and assembly ~$920 a package); cited analyst estimate",
    hbm_stack_usd=COST["hbm_stack_usd"], hbm_basis="economics section (ASSUMED $360 a 24 GB stack; RJ's H100 80 GB "
                                                   "HBM3 at ~$1,350 is ~$17/GB)",
    mask_sets=dict(v41_rom_bases=MASK["v41_base_designs"], hbm_die=1, qwen_rom_bases=MASK["qwen_base_designs"]),
    mask_basis="via-programmable ROM (adopted): base sets x $15M + 1 x $0.5M (low) .. 2 x $1M (high) coding masks per "
               "ROM die; every HBM comparator die design also pays one full set; / 1,000 production units",
)


def die_cost(area_mm2):
    r = FAB["wafer_d_mm"] / 2 - FAB["edge_exclusion_mm"]
    dpw = math.pi * r * r / area_mm2 - math.pi * 2 * r / math.sqrt(2 * area_mm2)
    y = (1 + area_mm2 / 100 * FAB["d0_per_cm2"] / FAB["alpha"]) ** (-FAB["alpha"])
    return dict(area_mm2=round(area_mm2, 1), dies_per_wafer=round(dpw, 1), yield_=round(y, 4),
                usd=round(FAB["wafer_usd"] / (dpw * y), 1))


def mfg_cost(dies, packages, stacks, rom_dies=0, rom_bases=0, hbm_designs=0):
    """dies: [(count, mm2)]; packages: [(count, class)].  Returns low/high capex per system (NRE amortised)."""
    si = sum(n * die_cost(a)["usd"] for n, a in dies)
    pk = sum(n * (FAB["package_usd"][c] + FAB["test_assembly_usd"]) for n, c in packages)
    st = stacks * FAB["hbm_stack_usd"]
    base = (rom_bases + hbm_designs) * MASK["full_set_usd"]
    nre_lo = base + rom_dies * MASK["coding_masks_per_die"][0] * MASK["single_mask_usd"][0]
    nre_hi = base + rom_dies * MASK["coding_masks_per_die"][1] * MASK["single_mask_usd"][1]
    u = COST["production_units"]
    hw = si + pk + st
    return dict(silicon_usd=round(si), package_usd=round(pk), hbm_usd=round(st), hardware_usd=round(hw),
                nre_usd=dict(low=nre_lo, high=nre_hi), capex_usd=dict(low=round(hw + nre_lo / u), high=round(hw + nre_hi / u)),
                silicon_mm2=round(sum(n * a for n, a in dies), 1))


# ---- HBM dies right-sized to their PHY shoreline ----
HBM_SHORE = dict(
    phy_edge_mm=8.5, phy_edge_basis="root 2026-09-30: NVIDIA H200 = the GH100 die (~814 mm2) with six HBM3e stacks, "
                                    "three per long edge (H100: the same 6 sites, 5 active); ~8-9 mm of edge per "
                                    "HBM3E PHY = GH100 long edge / 3 (Tom's Hardware, 'Nvidia H200 GPU announced'; "
                                    "NVIDIA H200 materials).  The repository's 12 mm is a placeholder (sensitivity)",
    phy_mm2=10.0, phy_basis="technology.json hbm.hbm3e phy_area_mm2_per_stack 10 (assumed, 8-15): depth = 10 / edge",
    service_band_mm=0.63072, service_basis="results/floorplan/hbm_gpu svc_south / svc_north band height",
    corner_mm=1.0, corner_basis="ASSUMED corner keep-out per long edge end",
    demonstrated_stacks_per_die=6,
    demonstrated_note="6 stacks on one die demonstrated (GH100/H200, 3 per long edge); 8 on one die is not (B200 "
                      "splits 8 across 2 dies); more than 6 is marked not demonstrated",
    reticle_mm=(26.0, 33.0),
    route_factor_basis="the placed SM array's block over its tiles (hbm_gpu floorplan: 13,990 x 12,649 um over "
                       "32 x 4.861 mm2 = 1.138)",
)


def right_size_hbm_die(model, stacks, phy_edge_mm=None, overhead=None):
    """Smallest die that holds `stacks` HBM3E PHYs on its long edges (ceil(stacks/2) a side) and the logic of the
    model's SM element array sized to them (8 SMs a stack, W13's rule), plus L2, hub, IO and the overhead reserve."""
    dv = hbm_gpu_design(model)
    fp = json.loads((ROOT / f"results/floorplan/hbm_gpu/{model}_hbm_die.json").read_text())
    tile = fp["sm_tile"]["w"] * fp["sm_tile"]["h"] / 1e6
    route = 13990.320000000002 * 12648.960000000001 / 1e6 / (32 * 1652.4 * 2941.92 / 1e6)
    n_sm = 8 * stacks
    l2 = dv["l2"]["mm2"] * stacks / 4 + 0.0
    hub = dv.get("dedicated_units_footprint_mm2", 0.0)
    io = 10.0 + (18.0 if model == "v41" else 0.0)     # host/UCIe 10 mm2 ledger; V4.1 fabric SerDes 18 mm2 (floorplan)
    logic = n_sm * tile * route + l2 + hub + io
    e = HBM_SHORE["phy_edge_mm"] if phy_edge_mm is None else phy_edge_mm
    o = CONS["overhead"] if overhead is None else overhead
    k = math.ceil(stacks / 2)
    W = k * e + 2 * HBM_SHORE["corner_mm"]
    depth = HBM_SHORE["phy_mm2"] / e
    bands = 2 * W * (depth + HBM_SHORE["service_band_mm"])
    area = (logic + bands) / (1 - o)
    H = area / W
    fits_reticle = (max(W, H) <= HBM_SHORE["reticle_mm"][1] and min(W, H) <= HBM_SHORE["reticle_mm"][0])
    return dict(model=model, stacks=stacks, sm_count=n_sm, logic_mm2=round(logic, 1), shoreline_mm=round(W, 2),
                die_w_mm=round(W, 2), die_h_mm=round(H, 2), die_mm2=round(area, 1), fits_reticle=fits_reticle,
                demonstrated=stacks <= HBM_SHORE["demonstrated_stacks_per_die"],
                package=("1 die + %d stacks (CoWoS-S, H100/H200 class)" % stacks if stacks == 6 else
                         "2 dies + 8 stacks (CoWoS-L, B200 class)" if stacks == 4 else "not demonstrated"),
                floorplan_815_logic_used_mm2=round(sum(fp["area_used"].values()), 1))


# ---- the V4.1 HBM comparator at N dies (TP-N) ----
_HBM_CHAIN_CACHE = {}


def _hbm_chain_n(N, n_sm, positions=1):
    """v41_hbm_chain at TP-N with n_sm SMs a die (group-slot).  Equal to v41_hbm_chain at N = 96, n_sm = 32."""
    key = (N, n_sm, positions, _CONS_CTX)
    if key not in _HBM_CHAIN_CACHE:
        _HBM_CHAIN_CACHE[key] = _hbm_chain_n_uncached(N, n_sm, positions)
    return dict(_HBM_CHAIN_CACHE[key])


def _hbm_chain_n_uncached(N, n_sm, positions):
    d = hbm_gpu_design("v41")
    clock = d["clock_hz"]
    arch, b = arch_graph(_CONS_CTX)
    g = b.g
    path = g.path(b.sink)
    mv = other = extra = xfill = 0.0
    for x in path:
        nd = g.nodes[x]
        t = sum(g.contrib[x].values())
        k = node_key(x) if nd["kind"] == "matvec" else ""
        if nd["kind"] == "matvec" and k and k != "hc.fn":
            rows = nd["sweep"]["macs"] / NODE_K[k] / N
            mv += sm_op_cycles(rows, NODE_K[k], NODE_FMT[k], d["drain_cycles"], True, n_sm) / clock
            xfill += math.ceil(NODE_K[k] * positions * 2 / X_BCAST_BPC) / clock
        elif nd["kind"] in ("collective", "hop"):
            continue
        else:
            other += t
            if positions > 1:
                extra += (positions - 1) * nd.get("issue", 0.0)
    nb = v41_boundaries(path, g.nodes)
    parts = dict(sm_matvec=mv * 1e6, x_broadcast_fill=xfill * 1e6, dedicated_and_su=other * 1e6,
                 verify_extra_issue=extra * 1e6, barrier=nb * d["barrier"]["boundary_cycles"] / clock * 1e6,
                 **V41_HBM_FABRIC_US)
    parts["collective_bytes"] *= positions
    return parts


def _v41_state_user():
    c = A._env()["c"]
    s = 0.0
    for L in range(c["num_layers"]):
        r = c["compress_ratios"][L]
        if L in c["kv_source_layer_ids"] and r:
            s += 1048576 // r * (A.CKV_ROW_B + A.IDX_KEY_B)
        s += c["window_tokens"] * A.WIN_ROW_B
    return s


_HBM_N_CACHE = {}


def hbm_ss_wire_delta(stacks):
    """The V4.1 HBM die's barrier / x-broadcast / TP-root crossings at W15's SS reach (504 um), on the right-sized die
    (the 815 mm2 floorplan's distances scaled by the linear size ratio), against the floorplan's TT stage counts."""
    fp = json.loads((ROOT / "results/floorplan/hbm_gpu/v41_hbm_die.json").read_text())
    k = math.sqrt(right_size_hbm_die("v41", stacks)["die_mm2"] / 815.0)
    X = {c["name"]: c for c in fp["crossings"]}
    r = SS_REACH_UM[1.2e9]

    def st(name):
        return math.ceil(X[name]["distance_um"] * k / r)
    one_way = st("barrier_leaf") + st("barrier_trunk")
    old_one = X["barrier_leaf"]["cycles_one_way"] + X["barrier_trunk"]["cycles_one_way"]
    bnd = 2 * (one_way - old_one) + (st("x_broadcast_root_to_sm") - X["x_broadcast_root_to_sm"]["cycles_one_way"])
    coll = 2 * max(0, st("tp_root_to_ucie") - X["tp_root_to_ucie"]["cycles_one_way"])
    return dict(scale=round(k, 3), boundary_extra_cycles=bnd, collective_extra_cycles=coll,
                collectives=round(V41_HBM_FABRIC_US["collective_latency"] / 0.668))


def v41_hbm_n(N, stacks, ec, gated_rows, replicas=1, clock_hz=None):
    key = (N, stacks, replicas, id(ec), clock_hz, _CONS_CTX)
    if key not in _HBM_N_CACHE:
        _HBM_N_CACHE[key] = _v41_hbm_n(N, stacks, ec, gated_rows, replicas, clock_hz)
    return copy.deepcopy(_HBM_N_CACHE[key])


def _v41_hbm_n(N, stacks, ec, gated_rows, replicas=1, clock_hz=None):
    """V4.1 HBM comparator: `replicas` TP-N groups of dies with `stacks` HBM3E each (8 SMs a stack), 1M.  Per user
    (AR, MTP), the saturated aggregate (column passes, v41_hbm_economics' rule), capacity (every die holds 1/N of
    every layer's KV: TP-N), energy with the 96-die design's gated/ungated static ratio, power, area, cost."""
    dv = hbm_gpu_design("v41")
    cols = dv["element"]["cols"]
    n_sm = 8 * stacks
    sweep1 = 37.4 * (V41_HBM_DIES * 4) / (N * stacks)
    w1 = _v41_weight_bytes(1)
    sweep = lambda toks: sweep1 * _v41_weight_bytes(toks) / w1   # noqa: E731
    cache = {}

    ck = (dv["clock_hz"] / clock_hz) if clock_hz else 1.0   # cycle-counted terms at another clock (the fabric and
                                                             # the HBM weight sweep keep their seconds)
    bwire = hbm_ss_wire_delta(stacks) if clock_hz else None

    def chain(P):
        if P not in cache:
            c = _hbm_chain_n(N, n_sm, P)
            for k_ in ("sm_matvec", "x_broadcast_fill", "dedicated_and_su", "verify_extra_issue", "barrier"):
                c[k_] *= ck
            if bwire:          # W15 SS reach on the right-sized die: every boundary and collective grows
                bc = dv["barrier"]["boundary_cycles"]
                c["barrier"] *= (bc + bwire["boundary_extra_cycles"]) / bc
                c["collective_latency"] += bwire["collectives"] * bwire["collective_extra_cycles"] / clock_hz * 1e6
            cache[P] = c
        return cache[P]
    issue1 = chain(2)["verify_extra_issue"]

    def T(P, toks):
        return max(sum(chain(P).values()), sweep(toks))

    def occ(P, toks):
        p = chain(P)
        return max(p["sm_matvec"] + p["x_broadcast_fill"] + p["barrier"], P * issue1, sweep(toks))
    tot, *_ = _v41_weight_split()
    per_user_hbm = tot["bytes"]["kv_hbm"] + tot["bytes"]["idx"]
    macs_j = _v41_system_macs_j()
    coll_b = tot["collective_bytes"]
    units_j = ec["v41_rom"]["energy"]["categories_mJ_per_token"]["units"] * 1e-3
    W = _V41_CFG["checkpoint_bytes"]
    cap = int((N * stacks * HBM_STACK_B * HBM_CAP_EFF - W) // _v41_state_user())
    rack = json.loads((ROOT / "results/arch/v41_rack.json").read_text())["power"]["per_die"]["static_w"]
    sa = dv["sm_area"]
    st1 = _static_w(n_sm * sa["logic_mm2"] + dv["dedicated_units_footprint_mm2"] * GPU_LOGIC_UTIL + 10.0 * stacks, 0.0,
                    n_sm * sa["sram_mm2"] + dv["l2"]["mm2"] * stacks / 4, clock_hz or dv["clock_hz"], stacks)
    st1["links"] = rack["serdes_always_on"] + rack["ucie_idle"]
    P_static = replicas * N * sum(st1.values())
    gr = {(r["design"], r["point"]): r for r in gated_rows}

    def ratio(mode, point):
        r = gr[(f"V4.1 HBM tier 3 {mode}", point)]
        return r["clock_and_power_gated_static_w"] / r["ungated_static_w"]

    def energy(B, P, draft_frac):
        toks = B * P
        per = max(1, cols // P)
        passes = math.ceil(B / per)
        wb = passes * _v41_weight_bytes(min(B, per) * P)
        kvp = tot["bytes"]["kv_hbm"] * (P if MTP_KV_PER_POSITION else 1) + tot["bytes"]["idx"]
        e = (toks * macs_j + (wb + B * kvp) * E_HBM_B + wb * 2 * E_SRAM_B + toks * units_j
             + toks * coll_b * 8 * E_LINK["board"] * 2)
        return e * (1 + draft_frac)
    out = {}
    for mode, P, tau, df in (("AR", 1, 1.0, 0.0), ("MTP", V41_POSITIONS, V41_TAU, V41_DRAFT_FRACTION)):
        per = max(1, cols // P)
        Td = df * T(1, 1)
        best = None
        rows = []
        for B in sorted(set([b for b in ECON_BATCHES if b <= max(1, cap)] + [max(1, cap)])):
            t = (T(B * P, B * P) + Td if B <= per else
                 max(T(per * P, per * P) + Td, math.ceil(B / per) * (occ(per * P, per * P) + Td))) * 1e-6
            pu = tau / t
            e_dyn = energy(B, P, df) / (B * tau)
            rows.append(dict(batch=B, per_user=pu, agg=replicas * B * pu, t=t, e_dyn=e_dyn))
        b1 = rows[0]
        best = max(rows, key=lambda r: r["agg"])
        pts = {}
        for point, r in (("batch1", b1), ("saturated", best)):
            agg = r["agg"] if point == "saturated" else r["per_user"]
            stat = P_static              # the whole system is powered, for a lone user too
            g_ = ratio(mode, point)
            pts[point] = dict(batch=r["batch"] * (replicas if point == "saturated" else 1),
                              per_user_tokens_s=round(r["per_user"], 1), aggregate_tokens_s=round(agg, 1),
                              ungated_mJ=round((r["e_dyn"] + stat / agg) * 1e3, 2),
                              gated_mJ=round((r["e_dyn"] + g_ * stat / agg) * 1e3, 2),
                              gated_system_w=round(g_ * stat + r["e_dyn"] * agg, 0))
        out[mode] = pts
    die = right_size_hbm_die("v41", stacks)
    per_pkg = 1 if stacks == 6 else 2
    n_d = replicas * N
    cost = mfg_cost([(n_d, die["die_mm2"])],
                    [(math.ceil(n_d / per_pkg), "cowos_s_1die" if per_pkg == 1 else "cowos_l_2die")],
                    n_d * stacks, hbm_designs=1)
    return dict(dies=n_d, tp=N, replicas=replicas, stacks_per_die=stacks, sm_per_die=n_sm, capacity_users_1m=cap * replicas,
                capacity_users_per_group=cap, feasible=cap >= 1, weight_sweep_us=round(sweep1, 1),
                chain_us_ar=round(sum(chain(1).values()), 1), die_mm2=die["die_mm2"],
                silicon_mm2=round(n_d * die["die_mm2"], 1), static_w_ungated=round(P_static, 1),
                ar=out["AR"], mtp=out["MTP"], cost=cost)


# ---- the study ----
def consolidation(ec=None, lv=None):
    ec = ec or economics()
    lv = lv or economics_levers(ec)
    gr = lv["gated_alike"]["rows"]
    # 1. V4.1 ROM: die counts per density basis and overhead
    counts = []
    for bf in BF16_MODES + ("hub_unit",):
        for pitch in CONS_PITCH:
            for dens in ("analytical", "asap7", "roma"):
                for o in (CONS["overhead_band"][0], CONS["overhead"], CONS["overhead_band"][1]):
                    for credit in CONS_CREDIT:
                        S = cons_min_stages(dens, o, credit, "w10_refit", pitch, bf)
                        t = cons_table_dies(dens, o)
                        h = cons_head_dies(dens, o, credit, "w10_refit", pitch)
                        u = cons_field_usable_mm2(o, credit)
                        counts.append(dict(bf16=bf, pitch=pitch, density=dens, overhead=o, sliver_credit=credit,
                                           stages=S, layer_dies=4 * S, head_dies=h, table_dies=t["dies"],
                                           dies=4 * S + h + t["dies"], field_usable_mm2=round(u, 1),
                                           field_need_mm2_at_28=round(cons_field_need_mm2(28, dens, pitch, bf), 1),
                                           margin_at_28_mm2=round(u - cons_field_need_mm2(28, dens, pitch, bf), 2),
                                           table_bytes_per_die_GB=round(t["bytes_per_die"] / 1e9, 2)))
    C = {(r["bf16"], r["pitch"], r["density"], r["overhead"], r["sliver_credit"]): r for r in counts}
    PB = ("standard_pair", "w10_budget", "analytical", CONS["overhead"], "ring")      # the product basis (root)
    base = C[PB]
    stage_table = []
    for bf in BF16_MODES:
        for pitch in CONS_PITCH:
            for o in (CONS["overhead_band"][0], CONS["overhead"], CONS["overhead_band"][1]):
                for credit in CONS_CREDIT:
                    row = dict(bf16=bf, pitch=pitch, overhead=o, credit=credit)
                    for dens in ("analytical", "asap7", "roma"):
                        c = C[(bf, pitch, dens, o, credit)]
                        row[dens] = dict(stages=c["stages"], layer_dies=c["layer_dies"], head_dies=c["head_dies"],
                                         table_dies=c["table_dies"], margin_at_28_mm2=c["margin_at_28_mm2"])
                    stage_table.append(row)
    legal_phy = [dict(pitch=pitch, overhead=CONS["overhead"], credit=cr, bf16="standard_pair",
                      analytical_stages=cons_min_stages("analytical", CONS["overhead"], cr, "w18_legal_phy", pitch))
                 for pitch in CONS_PITCH for cr in CONS_CREDIT]
    # table-die ROM leakage follows the ROM area at each density (the rack's leakage is the analytical area)
    leak = dict(analytical=1.0, roma=DENSITY["roma"]["mm2_per_B"] / CONS_A_ANALYTICAL,
                asap7=CONS_TABLE_MACRO_MM2 / CONS_TABLE_MACRO_B / CONS_A_ANALYTICAL)
    pcache = {}

    def price(tag, S, h, t, dens, bf, clock=None, **meta):
        key = (S, h, t, leak[dens], bf if bf != "hub_unit" else "columns", clock)
        if key not in pcache:
            pcache[key] = cons_v41_rom(S, h, t, leak[dens], None, key[4], clock)
        pt = copy.deepcopy(pcache[key])
        pt.update(label=tag, density=dens, bf16_mode=bf, **meta)
        return pt
    t_a = C[PB]["table_dies"]
    points = [price("as placed (188 dies, BF16 columns in the model's timing, TT)", 28, 4, 72, "analytical", "columns",
                    role="reference")]
    # root's BF16 lever at the product basis (TT): (a) BF16 columns, (b) two-pass BF16 on the standard pair, (c) hub
    for bf in ("columns", "standard_pair", "hub_unit"):
        c = C[(bf,) + PB[1:]]
        points.append(price(f"BF16 lever: {bf}", c["stages"], c["head_dies"], c["table_dies"], "analytical", bf,
                            role="bf16_lever"))
    # 28 against 34 stages (TT, standard pair): more hand-offs against shallower stages
    for S in (28, 34):
        points.append(price(f"{S} stages (stage-count comparison)", S, 4, t_a, "analytical", "standard_pair",
                            role="stage_count"))
    # density sensitivities at the product basis (TT)
    for dens in ("asap7", "roma"):
        c = C[("standard_pair", "w10_budget", dens, CONS["overhead"], "ring")]
        points.append(price(f"density {dens}", c["stages"], c["head_dies"], c["table_dies"], dens, "standard_pair",
                            role="density"))
    # USER DECISION: sign-off at SS.  Macro depth x clock: logic derated SS/TT = 1.27 (no logic block has an SS
    # closure), and the upper bound where the logic is re-closed at the macro's SS clock
    tt = A._env()["clock"]
    ss_logic = tt / SS_DERATE
    ss_rows = []
    for depth, dv in ROM_DEPTH_OPTS.items():
        S = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", "w10_budget", "standard_pair", depth)
        h = cons_head_dies("analytical", CONS["overhead"], "ring", "w10_refit", "w10_budget", depth)
        for mode, hz in (("(i) ROM-limited SS clock, logic ASSUMED re-hardened at WC to meet it", dv["ss_ghz"] * 1e9),
                         ("(ii) TT-closed logic derated 1.43x (MEASURED: W13 tc16 re-timed at SS, 759 MHz)",
                          min(dv["ss_ghz"] * 1e9, tt / SS_DERATE_MEASURED)),
                         ("(iii) TT-closed logic derated 1.27x (the ROM macro's ratio)",
                          min(dv["ss_ghz"] * 1e9, ss_logic))):
            binds = ("the ROM macro (%s SS single-cycle %.3f GHz)" % (depth, dv["ss_ghz"]) if hz >= dv["ss_ghz"] * 1e9 - 1
                     else "the TT-closed logic, derated: the model clock's slowest routed block %s (%.4f GHz TT)"
                     % (min(A._env()["clock_rows"], key=lambda r: r["fmax_hz"])["block"], tt / 1e9))
            pt = price(f"SS {depth}, {mode}", S, h, t_a, "analytical", "standard_pair", clock=hz, role="ss",
                       depth=depth, clock_mode=mode, macro_ss_ghz=dv["ss_ghz"], clock_binds=binds)
            points.append(pt)
            ss_rows.append(pt)
    # USER DECISION (AGENTS.md e7479589): the V4.1 product basis is 4096m8, 2 macros a slot, at 1.2 GHz SS, BF16 on
    # the standard pair; W18's 50% field-concurrency cap adopted; dynamic energy +16% at 1.2 GHz (root, ASSUMED);
    # the latency inventory folds in as it lands (W11 hub estimates so far)
    # USER DECISION 2026-09-30: BF16 option (iii) at W10's measured 574 x 126.9 um tile (max per-user rate)
    # USER DECISION 2026-09-30 (final): maximum per-user rate, die count free -> BF16 COLUMNS are the product: on the
    # full-token basis they beat (iii) and (ii) (the busiest-die op cycles favoured (iii), but its +20.7% pair pitch
    # adds stages, i.e. hops, and its BF16 issue floors sit above the columns' full-width BF16 lanes)
    Sp = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", "w10_q_1p2", "columns", "4096m8")
    # ROOT 2026-09-30: the head group on 8192m8 WITH ping-pong (2 macros a slot, alternate reads, 2-cycle macro path:
    # 1,667 ps against 8192m8's SS clk->q 1,004 + 25 + 60 ps) fits 4 dies -- 0.4% margin at the storage-only density,
    # 13.3% at W18's floorplan (claude/w18-die-assembly 4ed60cbb head_table_fit.json): CONFIRMED at floorplan level
    hp = cons_head_dies("analytical", CONS["overhead"], "ring", "w10_refit", "w10_q_1p2", "8192m8")
    head_fit = dict(dies=hp, depth="8192m8 ping-pong", margin_storage_only=0.004, margin_w18_floorplan=0.133,
                    on_4096m8=cons_head_dies("analytical", CONS["overhead"], "ring", "w10_refit", "w10_q_1p2", "4096m8"),
                    status="CONFIRMED at floorplan level (W18 4ed60cbb); 168 dies if the head group were on 4096m8",
                    table_dies_asap7_floorplan=dict(dies=20, src="W18 4ed60cbb head_table_fit.json (ASAP7 geometry "
                                                                 "feasibility row); the product stays 36 (storage-only)"))
    bf16_ref = {k: cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", pt, bfm, "4096m8")
                for k, pt, bfm in (("option_ii cap 3 (reference)", "w10_q_1p2", "option_ii"),
                                   ("option_iii BF16_PAIR (reference)", "w10_iii_1p2", "option_iii"),
                                   ("columns (product)", "w10_q_1p2", "columns"))}
    bf16_full_token = {}
    for k, pt_, bfm in (("option_ii cap 3", "w10_q_1p2", "option_ii"), ("option_iii", "w10_iii_1p2", "option_iii")):
        S_ = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", pt_, bfm, "4096m8")
        q_ = cons_v41_rom(S_, 4, cons_table_dies("analytical")["dies"], 1.0, None, bfm, PRODUCT_CLOCK_HZ,
                          FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), PRODUCT_DYN_SCALE, (0.9e9, "w18"),
                          None, 7, True, PRODUCT_SERIAL, DIE_SHRUNK_INTERIM)
        bf16_full_token[k] = dict(stages=S_, dies=q_["dies"], ar=q_["ar_tokens_s_b1"], mtp=q_["mtp_tokens_s_b1"],
                                  saturated=q_["ar_saturated_tokens_s"], pipeline_hops_us=q_["pipeline_hops_us"])
    prod = {}
    for tag, fc, lat, cs, es in (("ideal depths, no concurrency cap", 1.0, SOFTPLUS_FIX, None, None),
                                 ("50% field-concurrency cap (W18, adopted)", FIELD_CONCURRENCY, SOFTPLUS_FIX, None, None),
                                 ("cap + W11 hub latency inventory (estimates)", FIELD_CONCURRENCY,
                                  dict(W11_LATENCY_SS_1P2, **SOFTPLUS_FIX), None, None),
                                 ("cap + measured FP32 add: chain and element adds 8 stages", FIELD_CONCURRENCY,
                                  SOFTPLUS_FIX, 8, 8),
                                 ("ADOPTED (AGENTS.md c0894b1c): cap + 1.2 GHz streaming domain (LAT-7 adds, W11: "
                                  "1,208 MHz SS) + 0.9 GHz chain domain (LAT 3), W18 ratio-FIFO CDC",
                                  FIELD_CONCURRENCY, SOFTPLUS_FIX, None, 7),  # CDC per W18 (4 slow / 5 fast)
                                 ("ADOPTED + W15 SS wire reach (504 um) + W11 LAT-4 serial mul", FIELD_CONCURRENCY,
                                  SOFTPLUS_FIX, None, 7),
                                 (SERIAL_TAG, FIELD_CONCURRENCY, SOFTPLUS_FIX, None, 7),
                                 (SHRINK_TAG, FIELD_CONCURRENCY, SOFTPLUS_FIX, None, 7),
                                 (PRODUCT_TAG, FIELD_CONCURRENCY, dict(SOFTPLUS_FIX, **W11_STREAM_SS), None, 7)):
        pt = cons_v41_rom(Sp, hp, t_a, 1.0, None, "columns", PRODUCT_CLOCK_HZ, fc, lat, PRODUCT_DYN_SCALE,
                          (0.9e9, "w18") if tag.startswith("ADOPTED") else None, cs, es, "SS wire" in tag,
                          PRODUCT_SERIAL if "MEASURED serial" in tag else None,
                          DIE_SHRUNK_INTERIM if "shrunk-die" in tag else None)
        pt["product_final"] = tag == PRODUCT_TAG
        pt.update(label=f"PRODUCT BASIS 4096m8 @ 1.2 GHz SS, BF16 columns: {tag}", density="analytical",
                  bf16_mode="columns", role="product", depth="4096m8", bf16_stage_reference=bf16_ref)
        prod[tag] = pt
        points.append(pt)
    # the SS-clock curve (root 2026-09-30): tok/s against the logic's SS clock, capped at each macro's SS limit, so
    # the depth can be read off when the WC-hardened blocks report their SS fmax
    ss_curve = []
    for depth, dv in ROM_DEPTH_OPTS.items():
        S = cons_min_stages("analytical", CONS["overhead"], "ring", "w10_refit", "w10_budget", "standard_pair", depth)
        h = cons_head_dies("analytical", CONS["overhead"], "ring", "w10_refit", "w10_budget", depth)
        for f in SS_CURVE_GHZ:
            hz = min(f, dv["ss_ghz"]) * 1e9
            pt = price(f"curve {depth} logic {f:.2f} GHz", S, h, t_a, "analytical", "standard_pair", clock=hz)
            ss_curve.append(dict(depth=depth, logic_ss_ghz=f, clock_ghz=round(hz / 1e9, 4),
                                 capped_by_macro=f > dv["ss_ghz"], stages=S, dies=pt["dies"],
                                 ar_tokens_s_b1=pt["ar_tokens_s_b1"], mtp_tokens_s_b1=pt["mtp_tokens_s_b1"],
                                 ar_saturated_tokens_s=pt["ar_saturated_tokens_s"],
                                 gated_mJ_b1=pt["energy"]["ar_b1"]["gated_mJ"],
                                 gated_mJ_saturated=pt["energy"]["ar_sat"]["gated_mJ"]))
    for pt in points:
        rate = dict(ar_saturated=pt["ar_saturated_tokens_s"], mtp_saturated=pt["mtp_saturated_tokens_s"] * V41_POSITIONS / V41_TAU)
        pt["engram"] = cons_engram_path(pt["table_dies"], rate)
        pt["cost"] = mfg_cost([(pt["dies"], FLOORPLAN["die_mm2"])],
                              [((pt["layer_dies"] + pt["head_dies"]) // 2, "cowos_l_2die"), (pt["table_dies"] // 2, "cowos_l_2die")],
                              pt["hbm_stacks"], rom_dies=pt["dies"], rom_bases=FAB["mask_sets"]["v41_rom_bases"])
        pt["cost_iso_package_usd"] = pt["packages"] * COST["package_usd"]
        pt["silicon_mm2"] = pt["dies"] * FLOORPLAN["die_mm2"]
    # the comparison-rule reference: the product basis at TT (PROVISIONAL: the product die count is open until the
    # closed pair's pitch lands, root 2026-09-30)
    head = prod[PRODUCT_TAG]   # final: SS wires and W11's measured serial build in
    die_shrink = dict(DIE_SHRINK, interim=DIE_SHRUNK_INTERIM, role="ruling",
                      note="the product row carries W18b's interim shrunk-die crossings (996f7982); the sqrt(area) "
                           "sensitivity of 9bde5a55 is superseded; die area, cost and power re-price on the p12 floorplan")
    # 2. HBM dies right-sized; the V4.1 HBM sweep; Qwen HBM
    dies = {f"{m}_{s}": right_size_hbm_die(m, s) for m in ("qwen", "v41") for s in (4, 6)}
    dies["v41_4_phy12mm"] = right_size_hbm_die("v41", 4, 12.0)
    dies["qwen_6_phy12mm"] = right_size_hbm_die("qwen", 6, 12.0)
    minN = {s: math.ceil(_V41_CFG["checkpoint_bytes"] / (s * HBM_STACK_B * HBM_CAP_EFF)) for s in (4, 6)}
    sweep = []
    for s in (4, 6):
        Ns = sorted(set([minN[s], minN[s] + 1, 8, 10, 12, 16, 20, 24, 32, 48, 64, 96]))
        for N in Ns:
            if N < minN[s]:
                continue
            r = v41_hbm_n(N, s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)
            r["capacity_minimum"] = N == minN[s]
            sweep.append(r)
    users_866 = {}
    for s in (4, 6):
        N = minN[s]
        while v41_hbm_n(N, s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)["capacity_users_1m"] < head["capacity_users_1m"]:
            N += 1
        users_866[s] = N
    for s in (4, 6):
        if not any(r["tp"] == users_866[s] and r["stacks_per_die"] == s for r in sweep):
            r = v41_hbm_n(users_866[s], s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)
            r["capacity_minimum"] = False
            sweep.append(r)
    sweep.sort(key=lambda r: (r["stacks_per_die"], r["dies"]))
    # 3. the comparison rule: equal area, equal cost, equal power against the consolidated ROM array
    def budget_N(s, key, target):
        best = None
        for N in range(minN[s], 97):
            r = v41_hbm_n(N, s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ) if key != "area" else None
            val = (N * right_size_hbm_die("v41", s)["die_mm2"] if key == "area" else
                   r["cost"]["capex_usd"]["low"] if key == "cost" else r["ar"]["saturated"]["gated_system_w"])
            if val <= target:
                best = N
            elif key == "area":
                break
        return best
    rule = []
    tgt = dict(area=head["silicon_mm2"], cost=head["cost"]["capex_usd"]["low"],
               power=head["energy"]["ar_sat"]["gated_system_w"])
    for key in ("area", "cost", "power"):
        for s in (4, 6):
            per_die = right_size_hbm_die("v41", s)["die_mm2"]
            if key == "area" and tgt["area"] >= 96 * per_die:
                N, rep = 96, int(tgt["area"] // (96 * per_die))
            else:
                N, rep = budget_N(s, key, tgt[key]), 1
                if key != "area" and N == 96:
                    r96 = v41_hbm_n(96, s, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)
                    unit = r96["cost"]["capex_usd"]["low"] if key == "cost" else r96["ar"]["saturated"]["gated_system_w"]
                    rep = max(1, int(tgt[key] // unit))
            if N is None:
                rule.append(dict(rule=f"equal {key}", stacks_per_die=s, feasible=False, target=tgt[key]))
                continue
            r = v41_hbm_n(N, s, ec, gr, replicas=rep, clock_hz=PRODUCT_CLOCK_HZ)
            rule.append(dict(rule=f"equal {key}", target=tgt[key], **r))
    # Qwen: ROM package vs right-sized HBM packages (bandwidth-bound: tok/s scales with stacks)
    qh = ec["qwen_hbm"]
    wl, kvb = _qwen_wl()
    dq = hbm_gpu_design("qwen")
    w_B = sum(b_ for b_, _ in qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])) - kvb / 2
    w_total = 2 * w_B
    qg = {(r["design"], r["point"]): r for r in gr}
    qwen = []
    # the Qwen ROM PRODUCT (root, 2026-09-30): option C, 2 B200-class packages, TP-4, G = 6,144 a die, W12 wires
    qo = qwen_rom_options(ec)
    pc = next(r for r in qo["options"]["C"]["rows"] if r["G"] == 6144)
    q_rom_cost = dict(capex_usd=pc["capex_usd"], hardware_usd=pc["hardware_usd"])
    qwen.append(dict(design="Qwen ROM product: option C (2 B200-class packages, 4 x 815 mm2, 16 stacks, TP-4, G 6,144)",
                     dies=4, stacks=16, silicon_mm2=4 * FLOORPLAN["die_mm2"], ar_tokens_s_b1=pc["tokens_s_b1"],
                     saturated_tokens_s=pc["saturated_tokens_s"], capacity_users=pc["capacity_users"],
                     gated_mJ_b1=pc["mJ_b1"], gated_mJ_sat=pc["mJ_saturated"],
                     gated_system_w=round(pc["mJ_saturated"] * pc["saturated_tokens_s"] / 1e3, 1), cost=q_rom_cost,
                     wire_calibration="W12 floorplan wires (9,194 tok/s at the 2-die reference); the economics "
                                      "section's W5 wires give 9,851 there"))
    for k, s in ((1, 6), (2, 4), (1, 4)):
        die = right_size_hbm_die("qwen", s)
        f = k * s / 8
        ar_b1 = qh["ar"]["tokens_s_b1"] * f
        df_b1 = qh["dflash"]["tokens_s_b1"] * f
        sat = max(qh["ar"]["saturated_tokens_s"], qh["dflash"]["saturated_tokens_s"]) * f
        cap = int((k * s * HBM_STACK_B * HBM_CAP_EFF - w_total) // kvb)
        g1 = qg[("Qwen HBM tier 3 DFlash", "batch1")]
        gs = qg[("Qwen HBM tier 3 DFlash", "saturated")]
        # dynamic energy per token is unchanged (same bytes); static scales with the SMs (8 a stack) and the stacks
        stat_scale = k * s / 8
        e_b1 = (g1["clock_and_power_gated_mJ_per_token"] - g1["clock_and_power_gated_static_w"] / g1["tokens_s"] * 1e3
                + g1["clock_and_power_gated_static_w"] * stat_scale / df_b1 * 1e3)
        e_sat = (gs["clock_and_power_gated_mJ_per_token"] - gs["clock_and_power_gated_static_w"] / gs["tokens_s"] * 1e3
                 + gs["clock_and_power_gated_static_w"] * stat_scale / sat * 1e3)
        cost = mfg_cost([(k, die["die_mm2"])], [(1, "cowos_s_1die" if k == 1 else "cowos_l_2die")], k * s, hbm_designs=1)
        qwen.append(dict(design=f"Qwen HBM, {k} right-sized die(s) x {s} stacks ({die['die_mm2']} mm2 each)", dies=k,
                         stacks=k * s, silicon_mm2=round(k * die["die_mm2"], 1), ar_tokens_s_b1=round(ar_b1, 1),
                         dflash_tokens_s_b1=round(df_b1, 1), saturated_tokens_s=round(sat, 1), capacity_users=cap,
                         gated_mJ_b1=round(e_b1, 1), gated_mJ_sat=round(e_sat, 1),
                         gated_system_w=round(e_sat * sat / 1e3, 1), cost=cost, demonstrated=die["demonstrated"],
                         basis="bandwidth-bound: tok/s x (stacks / 8) of the 2-die W13 design (its barrier and TP "
                               "exchange are hidden under the stream); DFlash at its best block"))
    q_rule = []
    rom_q = qwen[0]
    for key, tv in (("area", rom_q["silicon_mm2"]), ("cost", rom_q["cost"]["capex_usd"]["low"]),
                    ("power", rom_q["gated_system_w"])):
        for row in qwen[1:3]:
            unit = (row["silicon_mm2"] if key == "area" else row["cost"]["capex_usd"]["low"] if key == "cost"
                    else row["gated_system_w"])
            n = int(tv // unit)
            q_rule.append(dict(rule=f"equal {key}", design=row["design"], packages=n,
                               per_user_dflash_b1=row["dflash_tokens_s_b1"], per_user_ar_b1=row["ar_tokens_s_b1"],
                               aggregate_tokens_s=round(n * row["saturated_tokens_s"], 1),
                               capacity_users=n * row["capacity_users"]))
    return dict(
        v41_rom=dict(die_shrink_sensitivity=die_shrink, counts=counts, stage_table=stage_table, legal_phy_sensitivity=legal_phy,
                     product_basis=dict(zip(("bf16", "pitch", "density", "overhead", "credit"), PB)),
                     droop=dict(DROOP, product=cons_droop(head)), fp32_add_ss=FP32_ADD_SS,
                     cdc=dict(CDC_W18, vm_port_area_mm2=dict(
                         before=area_ledger(PRESETS["proposal"])["vm_ports"],
                         after=round(area_ledger(PRESETS["proposal"])["vm_ports"] * 4 / 3, 3)),
                              added_wires={k: b - a for k, (a, b) in CDC_W18["vm_port_widening"]["bits_before_after"].items()}),
                     ss=dict(rows=[p["label"] for p in ss_rows], curve=ss_curve, tt_clock_hz=tt, ss_logic_clock_hz=ss_logic,
                             derate=SS_DERATE, derate_measured=SS_DERATE_MEASURED,
                             depth_options=ROM_DEPTH_OPTS, depth_src=ROM_DEPTH_SRC),
                     bf16_hub_unit_mm2=round(cons_bf16_hub_mm2(), 2),
                     product=dict(status=f"{head['dies']} dies: {head['stages']} TP-4 stages ({head['layer_dies']} layer "
                                         "dies, BF16 COLUMNS (1,024 at W10's 1,063.7 x 131.76 um planned outline) with q "
                                         "pairs at W10's 476 x 126.9 um tile -- USER DECISION: maximum per-user rate, die "
                                         f"count free) + {head['head_dies']} head dies (8192m8 ping-pong, fit confirmed at "
                                         f"floorplan level) + {head['table_dies']} Engram table dies (storage-only basis; "
                                         "ASAP7 feasibility 20).  Why the columns: on the full-token basis they give the "
                                         "highest per-user rate; W10's busiest-die op cycles favoured (iii), but its +20.7% "
                                         "pair pitch adds stages (hops) and its BF16 issue floors exceed the columns' "
                                         "full-width BF16 lanes.  References in bf16_full_token",
                                  bf16_full_token=bf16_full_token,
                                  option_ii_area_breakeven_mm2_for_31_stages=11.4,
                                  head_fit=head_fit,
                                  reference_for_comparisons=dict(stages=head["stages"], layer_dies=head["layer_dies"],
                                                                 head_dies=head["head_dies"],
                                                                 table_dies=head["table_dies"], dies=head["dies"],
                                                                 label=head["label"],
                                                                 basis="storage-only 75.0, BF16 on the standard pair, "
                                                                       "W10 budget pitch, 12.5%, ring credit, 4096m8")),
                     points=points, refit=CONS_REFIT, geometries=CONS_GEOM, credit_modes=CONS_CREDIT,
                     pitches=CONS_PITCH, bf16=CONS_BF16, field_mm2=round(CONS_FIELD_MM2, 2), sliver_mm2=round(CONS_SLIVER_MM2, 2),
                     strip_per_pair_mm2=round(CONS_STRIP_PER_PAIR_MM2, 6), table_macro_mm2=round(CONS_TABLE_MACRO_MM2, 6),
                     density=DENSITY, constants=CONS),
        hbm=dict(right_sized=dies, shoreline=HBM_SHORE, v41_sweep=sweep, v41_capacity_min_dies=minN,
                 v41_dies_for_rom_users=users_866, qwen=qwen, existing_rule_note=(
                     "arch_budget_v41.hbm_comparator sizes 99 (model: 96) dies by ISO LOGIC AREA with the ROM array's "
                     "188 dies of analytical logic; capacity_limit's hbm_users (811) uses the busiest-die rule of a "
                     "pipelined placement, whereas the TP-96 comparator holds 1/96 of every layer's KV per die")),
        headline_table=cons_headline_table(head, rule, qwen, ec, pc),
        tau_sweep_1m=cons_tau_sweep([(x["design"], dict(mtp=x.get("per_user_mtp")))
                                     for x in cons_headline_table(head, rule, qwen, ec, pc)["v41"]]),
        short_context_8k=cons_short_context(Sp, hp, t_a, head, ec, gr, 8192),
        gpu_calibration=gpu_calibration_row(ec),
        qwen_context_sweep=qwen_context_sweep(ec),
        qwen_helix_200k=qwen_helix_scaleout(ec),
        qwen_product_ss=qwen_product_ss(), qwen_l0_rtl_vs_model=qwen_l0_rtl_vs_model(),
        hbm_collective_sensitivity=dict(model=188, audit=228, w19_exact_minimised=265, w19_exact_unfused=305,
                                        audit_central_ar=2394.5, at_265_ar=round(1 / (1 / 2394.5 + 37 * 0.83e-6), 1),
                                        at_305_ar=round(1 / (1 / 2394.5 + 77 * 0.83e-6), 1),
                                        src="W19 claude/w19-hbm-token f364f884 (exact TP-96 program, layer 0 bit-exact); "
                                            "collectives at the audit's 0.83 us scratch switch latency; PENDING W19's "
                                            "final count and W15's P = 48 fit"),
        comparison_rule=dict(v41_targets=tgt, v41=rule, qwen=q_rule,
                             basis="ROM = the consolidated analytical headline; power = the gated saturated AR system "
                                   "power (both sides, the adopted gated-alike policies); cost = manufacturing capex "
                                   "low (die area x yield, packages, stacks, NRE / 1,000); HBM beyond 96 dies adds "
                                   "whole TP-96 replicas"),
        karb=cons_karb_delta(Sp, clock_hz=PRODUCT_CLOCK_HZ),
        clock_basis=dict(clock_hz=PRODUCT_CLOCK_HZ, note="USER DECISION (AGENTS.md e7479589): every design at 1.2 GHz SS "
                         "for equal footing -- V4.1 ROM product rows, the V4.1 HBM sweep and comparison rule (cycle terms "
                         "at 1.2 GHz; fabric and HBM stream seconds unchanged), the Qwen ROM product; the Qwen HBM "
                         "comparator is HBM-bandwidth bound, so its rate does not move with the clock",
                         v41_hbm_96x4_tt=v41_hbm_n(96, 4, ec, gr)["ar"]["batch1"]["per_user_tokens_s"],
                         v41_hbm_96x4_1p2=v41_hbm_n(96, 4, ec, gr, clock_hz=PRODUCT_CLOCK_HZ)["ar"]["batch1"]["per_user_tokens_s"],
                         qwen_rom_c_1p2=qwen_tp_point(4, 6144, "board", clock_hz=PRODUCT_CLOCK_HZ)["tokens_s_b1"],
                         qwen_rom_c_1p2_w12_tp4_wires=qwen_tp_point(4, 6144, "board", clock_hz=PRODUCT_CLOCK_HZ,
                                                                    me_lat_extra=QWEN_W12_TP4_ME_EXTRA)["tokens_s_b1"],
                         qwen_rom_c_1p2_w12_tp4_ss_reach=qwen_tp_point(4, 6144, "board", clock_hz=PRODUCT_CLOCK_HZ,
                                                                       me_lat_extra=QWEN_W12_TP4_ME_EXTRA_SS)["tokens_s_b1"],
                         v41_hbm_w13_ss_note="W13 at SS pre-layout: an 8-stage fp32_add_rne_pipe breaks the IL = 8 "
                                             "circulating accumulator; IL = 16 gives V4.1 HBM ~2,500 AR (from ~2,920); "
                                             "a 7-stage adder keeps IL = 8 (W13 estimate, not priced here)",
                         qwen_rom_c_tt=pc["tokens_s_b1"]),
        clock_domain_cases=cons_clock_cases(Sp, hp, t_a),
        qwen_rom=dict(product="C", product_row=pc, options=qo, small_die=qwen_small_die(),
                      alternatives=dict(A="alternative: fastest per dollar, but an undemonstrated 3-reticle 12-stack "
                                          "package", B="alternative: 3 single-die packages, TP-3 over board links",
                                        D="alternative: the 2-die reference, fits only with the compute-in-ROM "
                                          "UPSIDE (assumed cell multiplier, unimplemented mechanism)"),
                      sensitivity="G 7,168 a die (9,597 tok/s, 18.6% bank padding): a new die for +2.4%"),
        fab=FAB,
        die_costs={f"{a:g} mm2": die_cost(a) for a in (815.0,) + tuple(sorted({v["die_mm2"] for v in dies.values()}))})


# ---- Qwen ROM at the storage-only density (root ruling 2026-09-30): the dies it needs, and the options priced ----
QWEN_DENSITY = dict(
    storage_n5=dict(mbit_mm2=None, label="storage-only N5 (75.0 Mbit/mm2, the ruled basis) + SECDED 266/256"),
    roma=dict(mbit_mm2=57.8, label="ROMA TSMC 7 nm compiler (conservative sensitivity) + SECDED"),
    cirom_upside=dict(mbit_mm2=None, label="compute-in-ROM UPSIDE: the Qwen ledger's 148 Mbit/mm2 = N6 storage / an "
                                         "ASSUMED 1.6x cell multiplier x a vendor-quoted 4 bits a cell; unimplemented "
                                         "mechanism (no compute-in-ROM cell in this repository's RTL)"),
)
QWEN_TILE_FIXED_MM2 = 4 * 10.0 + 10.0 + 12.8      # 4 HBM PHY + UCIe PHY + stream-unit spill: per die, not per group
QWEN_ECC = 266 / 256


def _qwen_rom_bits():
    qp = json.loads((ROOT / "results/floorplan/qwen_o4_rom_placement.json").read_text())
    t, cr = qp["totals"], qp["code_rom"]
    drafter = cr["drafter_words"] * cr["word_columns"] * 256
    return dict(stored_bits_per_die=t["stored_bits"], drafter_bits_per_die=drafter,
                target_bits_total=2 * (t["stored_bits"] - drafter),
                cirom_mbit_mm2=t["stored_bits"] / t["ledger_rom_mm2_n6"] / 1e6)


def qwen_rom_area_per_group_mm2():
    """Non-ROM tile area per group (pruned group logic at 50% + KV ring SRAM), from the G = 6,144 fit (552.9 mm2 of
    which 265.0 ROM and QWEN_TILE_FIXED_MM2 fixed)."""
    return (552.9 - QWEN_ROM_AREA_DIE["rom"] - QWEN_TILE_FIXED_MM2) / 6144


def qwen_rom_need_mm2(k, G, density="storage_n5"):
    b = _qwen_rom_bits()
    m = (_V41_ASM["rom_density_mbit_per_mm2"] if density == "storage_n5" else
         b["cirom_mbit_mm2"] if density == "cirom_upside" else QWEN_DENSITY[density]["mbit_mm2"])
    ecc = 1.0 if density == "cirom_upside" else QWEN_ECC
    rom = b["target_bits_total"] * ecc / (m * 1e6) / k
    return dict(rom_mm2=rom, need_mm2=QWEN_TILE_FIXED_MM2 + qwen_rom_area_per_group_mm2() * G + rom,
                avail_mm2=QWEN_AREA["array_mm2"])


QWEN_TP_SHAPE = {2: (16, 4), 3: (12, 3), 4: (8, 2)}   # busiest die's (query heads, KV heads): GQA groups of 4 whole


def _qwen_exchange(kind, k, clock):
    """Per-token exchange cycles (72 all-reduces + the argmax gather) and the embedding handoff, by link class."""
    cf = w15_record()["configs"]
    ref = cf[QWEN_EXCHANGE]["exchanges"]
    if kind == "ucie_measured":
        ar, ga, src = ref["allreduce_cycles_mean"], ref["argmax_gather_cycles"], "MEASURED (W15 q256d64, TP-2 UCIe)"
    elif kind == "ucie_tp3_assumed":
        ar, ga = ref["allreduce_cycles_mean"] + FADD_PIPE, ref["argmax_gather_cycles"]
        src = ("ASSUMED from the W15 TP-2 measurement: a one-shot to 2 peers over direct UCIe adds one FP32 add stage "
               "(+5 cycles) to the 71-cycle all-reduce")
    else:
        # the V4.1 TP-4 group measured over direct T1 board links (2 packages x 2 dies), W3 placement, depth 1,024:
        # transferred to the Qwen payload (H = 4,096 FP32 partials) and clock
        ar = w15_collective_s("v41p17_r0d1024", "all_reduce", 4096 * 4, 4) * clock
        ga = w15_collective_s("v41p17_r0d1024", "all_gather", 8 * k, k) * clock
        src = ("MEASURED on the V4.1 TP-4 group (W15 v41p17_r0d1024 fit: 2 packages x 2 dies, direct T1 board links), "
               "transferred to the Qwen payload and clock" + ("" if k == 4 else "; TP-3 over board links ASSUMED at the "
                                                               "TP-4 fit"))
    tok = (2 * 36) * ar + ga
    return dict(per_allreduce_cycles=round(ar, 1), argmax_gather_cycles=round(ga, 1), token_cycles=round(tok),
                source=src, per_allreduce_ns=round(ar / clock * 1e9, 1))


QWEN_W12_TP4_ME_EXTRA = 24 + 3 * 5 + 22 + 4 + 1   # W12 (a760c255, 2026-09-30): at TP-4, BD 24, NWS 3 x 5 levels,
                                                  # TWS 22, ORD 4, + MEM_EXTRA 1 (the 4096x266 pin-capture register
                                                  # b274bda5, needed at SS) = 66 cycles an ME op (W12 2-die: 81)


def qwen_tp_point(k, G, link, wire_model="w12", clock_hz=None, me_lat_extra=None, ctx=8192, su_width=1024):
    """Qwen3-8B ROM on k dies (TP-k), G groups a die, 8K, AR: the calibrated replay of the busiest die's slice, the
    W12 floorplan wires, and the exchange of the given link class."""
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    Q.CLOCK[0] = clock_hz or Q.clock_hz()
    clock = Q.CLOCK[0]
    cf = w15_record()["configs"]
    oldw = {n: v["clock_hz"] for n, v in cf.items() if n.startswith("v41")}
    if clock_hz:                   # SS: the measured board-exchange cycles take the SS period (as the V4.1 SS pass)
        for n in oldw:
            cf[n]["clock_hz"] = clock_hz
    nh, kv = QWEN_TP_SHAPE[k]
    shp = dict(Q.Q, NH=nh, KV=kv, FF=-(-Q.Q["FF"] // k), V=-(-Q.Q["V"] // k))
    k0 = dict(T.K)
    try:
        if wire_model == "w12":
            T.K["me_lat"] = k0["me_lat"] + (QWEN_WIRE_W12["me_lat_extra"] if me_lat_extra is None else me_lat_extra)
        r = Q.as_built(ctx, groups=G, su_width=su_width, shape=shp, ucie=False)
    finally:
        T.K.clear()
        T.K.update(k0)
    x = _qwen_exchange(link, k, clock)
    emb = Q.tp_exchanges(clock)["embedding_handoff_cycles"]
    if link not in ("ucie_measured", "ucie_tp3_assumed"):
        emb += w15_collective_s("v41p17_r0d1024", "all_gather", 8, k) * clock    # the row crosses a board link
    for n, v in oldw.items():
        cf[n]["clock_hz"] = v
    cycles = r["cycles"] + x["token_cycles"] + math.ceil(emb)
    ub = r["unit_busy"]
    wl, kvb = _qwen_wl()
    kvfrac = kv / Q.Q["KV"]
    lanes = ub["weights"] + ub["attn_scores"] + ub["attn_pv"] + ub["lm_head"]
    bounds = dict(lanes=clock / lanes, stream_unit=clock / ub["stream"], kv_stream=4 * HBM_STACK_BPS / (kvb * kvfrac))
    sat = min(bounds.values())
    users = int(4 * HBM_STACK_B * HBM_CAP_EFF // (kvb * kvfrac))
    # integer banks: a group-pair column holds its share of the target words in whole 4,096-deep banks
    words = 38880 * (2 / k) * 6144 / G
    banks = math.ceil(words / 4096)
    area = qwen_rom_need_mm2(k, G)
    rom_mm2 = area["rom_mm2"]
    st = _static_w(G * QWEN_AREA["logic_group_pruned_um2"] / 1e6 + QWEN_TILE_FIXED_MM2, rom_mm2,
                   G * QWEN_AREA["kv_sram_group_um2"] / 1e6, clock, 4)
    return dict(k=k, G=G, link=link, cycles=cycles, tokens_s_b1=round(clock / cycles, 1), clock_hz=clock, unit_busy=ub,
                layer_chain_cycles=r["layer_chain"]["cycles"], ctx=ctx, su_width=su_width,
                exchange=x, saturated_tokens_s=round(sat, 1), bounds={a: round(b, 1) for a, b in bounds.items()},
                binding=min(bounds, key=bounds.get), capacity_users=users,
                banks_per_column=banks, column_words=round(words), bank_padding=round(1 - words / (banks * 4096), 4),
                static_w_per_die=round(sum(st.values()), 2), area_need_mm2_per_die=round(area["need_mm2"], 1),
                rom_mm2_per_die=round(rom_mm2, 1), fits_storage_n5=area["need_mm2"] <= area["avail_mm2"])


def qwen_rom_options(ec=None):
    """Root 2026-09-30: the Qwen ROM does not fit two reticles at the storage-only density; price the options."""
    ec = ec or economics()
    qr = ec["qwen_rom"]
    ucie_ref_j = qr["energy"]["categories_mJ_per_token"]["ucie"] * 1e-3
    dyn_ref = qr["energy"]["dynamic_mJ_per_token"] * 1e-3
    import arch_budget_qwen3 as Q
    xbytes = Q.tp_exchanges(Q.clock_hz())["bytes_per_direction"]
    opts = dict(
        A=dict(k=3, link="ucie_tp3_assumed", packages=[(1, "cowos_l_3die")], demonstrated=False,
               what="3 dies in ONE package (12 stacks; not demonstrated), TP-3 over UCIe"),
        B=dict(k=3, link="board", packages=[(3, "cowos_s_1die")], demonstrated=True,
               what="3 single-die packages (4 stacks each, H100-class), TP-3 over board links"),
        C=dict(k=4, link="board", packages=[(2, "cowos_l_2die")], demonstrated=True,
               what="2 B200-class packages (2 dies + 8 stacks each), TP-4 with one package crossing"),
        D=dict(k=2, link="ucie_measured", packages=[(1, "cowos_l_2die")], demonstrated=True,
               what="the 2-die reference: fits only with the compute-in-ROM UPSIDE (148 Mbit/mm2; assumed cell "
                    "multiplier, unimplemented mechanism)"),
    )
    pk_usd = dict(FAB["package_usd"], cowos_l_3die=1.5 * FAB["package_usd"]["cowos_l_2die"])
    out = {}
    for key, o in opts.items():
        k = o["k"]
        rows = []
        for G in (2048, 3072, 4096, 5120, 6144, 7168, 8192):
            dens = "cirom_upside" if key == "D" else "storage_n5"
            fit = qwen_rom_need_mm2(k, G, dens)
            if fit["need_mm2"] > fit["avail_mm2"] and not (G == 12288 // k):
                continue
            p = qwen_tp_point(k, G, o["link"])
            p["fits"] = fit["need_mm2"] <= fit["avail_mm2"]
            p["area_need_mm2_per_die"] = round(fit["need_mm2"], 1)
            link_j = E_LINK["ucie"] if o["link"].startswith("ucie") else E_LINK["board"]
            dyn = dyn_ref - ucie_ref_j + xbytes * 2 * 8 * link_j * (k - 1)
            P_st = k * p["static_w_per_die"]
            hw = mfg_cost([(k, FLOORPLAN["die_mm2"])], [], 4 * k, rom_dies=k,
                          rom_bases=FAB["mask_sets"]["qwen_rom_bases"])
            pkg = sum(n * (pk_usd[c] + FAB["test_assembly_usd"]) for n, c in o["packages"])
            capex = dict(low=hw["capex_usd"]["low"] + round(pkg), high=hw["capex_usd"]["high"] + round(pkg))
            hw_usd = hw["hardware_usd"] + round(pkg)
            p.update(system_static_w=round(P_st, 1), dynamic_mJ=round(dyn * 1e3, 2),
                     mJ_b1=round((dyn + P_st / p["tokens_s_b1"]) * 1e3, 2),
                     mJ_saturated=round((dyn + P_st / p["saturated_tokens_s"]) * 1e3, 2),
                     die_usd=round(k * die_cost(FLOORPLAN["die_mm2"])["usd"]), package_usd=round(pkg),
                     hbm_usd=4 * k * FAB["hbm_stack_usd"], hardware_usd=hw_usd, capex_usd=capex,
                     tokens_s_per_kusd=round(p["tokens_s_b1"] / hw_usd * 1e3, 2))
            rows.append(p)
        tot = next((r for r in rows if r["G"] * k == 12288), None)
        fitting = [r for r in rows if r["fits"]]
        best = max(fitting, key=lambda r: r["tokens_s_b1"] / r["hardware_usd"]) if fitting else None
        out[key] = dict(o, total_G_12288=tot, best_tokens_s_per_usd=best, rows=rows,
                        gated_note="gated = ungated: the Qwen ROM's idle gaps are shorter than wake + break-even "
                                   "(gated-alike table)")
    import arch_budget_qwen3 as Q2
    ss_hz = Q2.clock_hz() / SS_DERATE
    ss = []
    for G, tag in ((6144, "product (option C, G 6,144)"), (4928, "ROMA-safe sensitivity (G 4,928)")):
        for hz, corner in ((None, "TT"), (ss_hz, "SS (logic derated 1.27)")):
            p = qwen_tp_point(4, G, "board", clock_hz=hz)
            ss.append(dict(point=tag, corner=corner, clock_hz=p["clock_hz"], tokens_s_b1=p["tokens_s_b1"],
                           saturated_tokens_s=p["saturated_tokens_s"], binding=p["binding"]))
    Q2.CLOCK[0] = Q2.clock_hz()
    g_search = dict(finding="the TP-4 token is not lane-bound: G 6,144 -> 6,336 buys +0.04% (9,367.6 -> 9,371.4 tok/s) "
                            "and the saturated rate is KV-stream bound at every G >= 4,096, so extra area does not buy "
                            "per-user speed; legal G step is 64 groups (the program's embedding-word rule)",
                    chosen=6144, largest_with_2pct_margin=6336, roma_safe=4928)
    return dict(options=out, rom_bits=_qwen_rom_bits(), corners=ss, g_search=g_search, per_group_mm2=round(qwen_rom_area_per_group_mm2(), 6),
                fixed_mm2=QWEN_TILE_FIXED_MM2, densities=QWEN_DENSITY,
                fit_by_density={d: {k: round(qwen_rom_need_mm2(k, 12288 // k, d)["need_mm2"], 1) for k in (2, 3, 4)}
                                for d in QWEN_DENSITY},
                package_basis=dict(FAB["package_basis"], cowos_l_3die="ASSUMED 1.5 x the 2-die CoWoS-L (no 3-reticle "
                                                                       "package is demonstrated)")
                if isinstance(FAB["package_basis"], dict) else FAB["package_basis"]
                + "; 3-die CoWoS-L ASSUMED 1.5 x the 2-die price (no 3-reticle package is demonstrated)")


# ---- K arbiter round trip (W18, root relay 2026-09-30) ----
KARB = dict(base_cycles=7, per_hop_cycles=2,
            region_distance_mm=(3.5, 2.5, 1.5, 0.5, 0.5, 1.5, 2.5, 3.5),
            reach_mm_tt=1.0, reach_mm_ss=0.75,
            src="W18: the pipelined, credited K arbiter's uncontended added K round trip is 7 + 2 x (hops - 1) cycles; "
                "regions along the 8.5 mm PHY edge give 13/11/9/7/7/9/11/13 cycles at 1 mm hops (TT), up to 15 at the "
                "likely SS reach of 0.75 mm (W15 measuring); region distances here reproduce those counts")


KARB_W18B_MERGE2 = (19, 15, 13, 9, 9, 13, 15, 19)   # W18b 996f7982 relay: shrunk die, MERGE2 +1 response cycle


def karb_region_cycles(reach_mm):
    return [KARB["base_cycles"] + KARB["per_hop_cycles"] * (math.ceil(d / reach_mm - 1e-9) - 1)
            for d in KARB["region_distance_mm"]]


def cons_karb_delta(S=None, reach_mm=None, clock_hz=None):
    """Token-path cost of the K arbiter round trip: every HBM-touching node on the critical path (the index-selected
    row gathers, the index-key scans, the window-row score reads) pays the round trip once (its stream is then
    pipelined).  Worst region (all requests from the farthest region) and region mean; the model charged none."""
    S = S or cons_min_stages("analytical")
    with _cons_stages(S):
        r, b = arch_graph(1048576)
        g = b.g
        path = g.path(b.sink)
    n = sum(1 for x in path if x.endswith((".gather", "idx.score", ".attn.scores")))
    clock = clock_hz or A._env()["clock"]
    T = r["T_s"]
    out = {}
    for tag, reach in (("tt_1mm", KARB["reach_mm_tt"]), ("ss_0p75mm", KARB["reach_mm_ss"])) + (
            (("custom", reach_mm),) if reach_mm else ()):
        cyc = karb_region_cycles(reach)
        for kind, c in (("worst", max(cyc)), ("mean", sum(cyc) / len(cyc))):
            dt = n * c / clock
            out[f"{tag}_{kind}"] = dict(reach_mm=reach, cycles_per_request=round(c, 2), requests_on_path=n,
                                        added_us=round(dt * 1e6, 3), tokens_s_delta_pct=round(-dt / (T + dt) * 100, 3))
    # W18b (996f7982, root relay): MERGE2 on proot (equivalence-clean 54/54) adds +1 response cycle in every region:
    # the K round trip on the shrunk die is 19/15/13/9/9/13/15/19 (regions 0-7); still not in the product
    cyc = KARB_W18B_MERGE2
    for kind, c in (("worst", max(cyc)), ("mean", sum(cyc) / len(cyc))):
        dt = n * c / clock
        out[f"w18b_merge2_{kind}"] = dict(cycles_per_request=round(c, 2), requests_on_path=n, added_us=round(dt * 1e6, 3),
                                          tokens_s_delta_pct=round(-dt / (T + dt) * 100, 3))
    return dict(rows=out, regions_w18b_merge2=list(KARB_W18B_MERGE2), regions_tt=karb_region_cycles(KARB["reach_mm_tt"]),
                regions_ss=karb_region_cycles(KARB["reach_mm_ss"]), stages=S, basis=KARB)


# W19 HBM feasibility audit (claude/w19-hbm-audit aa0ac6bd, results/uarch/hbm_feasibility_audit.json; root 2026-09-30):
# central estimates against main's model at 1.2 GHz (3,071.7 AR / 6,206.0 MTP): 2,394.5 AR / 5,227.7 MTP (range AR
# 2,196-2,905, MTP 4,951-6,161).  Optimistic terms: routed-expert fetch after the router, measured switch latency,
# +1 gather a MoE layer for the exact expert order, 34.6 distinct experts a layer over 6 positions, serial units in the
# 0.9 GHz domain, the drafter on the 96-die graph; pessimistic: indexer at 1/96 keys, 1 head a die.  Applied here as
# ratios to the tier-3 per-user rates (the saturated column is left at the model's pass bound, labelled).
HBM_AUDIT = dict(ar=2394.5 / 3071.7, mtp=5227.7 / 6206.0, ar_range=(2196.2 / 3071.7, 2905.0 / 3071.7),
                 mtp_range=(4951.1 / 6206.0, 6160.6 / 6206.0), qwen_dflash=0.86, qwen_dflash_block12=2296.0,
                 src="claude/w19-hbm-audit aa0ac6bd results/uarch/hbm_feasibility_audit.json (summary.realistic_range)",
                 rom_side="the exact-order extra gather does not apply to the ROM array: a macro sums its experts in id "
                          "order inside the element and the TP-4 combine is a fixed-order all-reduce (no cross-die "
                          "expert partials to re-order); the 0.9 GHz serial domain is already in the ROM product")


# W19 COMPOSED V4.1 HBM token (claude/w19-hbm-token a88743ff, results/uarch/w19_hbm_token_{ar,ar_gather,mtp}.json;
# every term priced along the executed TP-96 program, which is bit-exact on 96 ranks -> 21946 and all 6 MTP verify
# positions): AR (grouped o-reduce program, 265 collectives) 431.55 us; all-gather-only program (305) 463.33 us;
# MTP verify pass (6 positions, measured 27.6-expert union) 628.47 us, + the audit's drafter 49.9 us.  Replaces the
# audit ratios for the tier-3 per-user rates (the audit stays as a reference); collective latency PENDING W15's P=48 fit.
HBM_W19 = dict(ar_us=431.55, ar_all_gather_us=463.33, mtp_pass_us=628.47, drafter_us=49.9, collectives=265,
               src="claude/w19-hbm-token a88743ff results/uarch/w19_hbm_token_{ar,ar_gather,mtp}.json (result.total_us)")
HBM_W19["ar_tokens_s"] = 1e6 / HBM_W19["ar_us"]
HBM_W19["mtp_tokens_s"] = V41_TAU * 1e6 / (HBM_W19["mtp_pass_us"] + HBM_W19["drafter_us"])


def cons_headline_table(head, rule, qwen, ec, pc):
    """USER DECISION 2026-09-30: the V4.1 ROM headline is saturated throughput, energy per token and cost at EQUAL
    MANUFACTURING COST; per-user speed is claimed only against real GPUs (tier 1 measured, tier 2 calibrated) and
    reported against the idealised HBM machine (tier 3).  Qwen ROM keeps its per-user claim.  Every row names its
    point; ROM energies include the adopted 256-cycle pre-ramp."""
    dr = cons_droop(head)["50% cap + 256-cycle pre-ramp"]
    g = ec["gpu"]
    cst = {c["design"]: c for c in ec["cost"]}
    v41 = [dict(design="V4.1 ROM array (product basis, 1.2 GHz SS, SS wires, 50% cap + pre-ramp)", tier="ROM",
                per_user_ar=head["ar_tokens_s_b1"], per_user_mtp=head["mtp_tokens_s_b1"],
                per_user_mtp_headline_tau_3p78=round(head["mtp_tokens_s_b1"] * 3.78 / V41_TAU, 1),
                saturated_tokens_s=head["ar_saturated_tokens_s"], mJ_b1=dr["gated_mJ_b1"], mJ_saturated=dr["gated_mJ_saturated"],
                capex_usd=head["cost"]["capex_usd"], silicon_mm2=head["silicon_mm2"], users_1m=head["capacity_users_1m"],
                system_w_saturated=head["energy"]["ar_sat"]["gated_system_w"])]
    for x in rule:
        if x.get("stacks_per_die") == 4 and "ar" in x:
            v41.append(dict(design=f"V4.1 HBM tier 3 (idealised), {x['rule']}: {x['replicas']} x TP-{x['tp']} ({x['dies']} "
                                   f"right-sized dies, 1.2 GHz, SS wires; W19 composed token)", tier="3",
                            per_user_ar=round(HBM_W19["ar_tokens_s"], 1), per_user_mtp=round(HBM_W19["mtp_tokens_s"], 1),
                            per_user_ar_audit_central=round(x["ar"]["batch1"]["per_user_tokens_s"] * HBM_AUDIT["ar"], 1),
                            per_user_mtp_audit_central=round(x["mtp"]["batch1"]["per_user_tokens_s"] * HBM_AUDIT["mtp"], 1),
                            per_user_ar_model=x["ar"]["batch1"]["per_user_tokens_s"],
                            per_user_mtp_model=x["mtp"]["batch1"]["per_user_tokens_s"],
                            per_user_ar_audit_range=[round(x["ar"]["batch1"]["per_user_tokens_s"] * f, 1)
                                                     for f in HBM_AUDIT["ar_range"]],
                            per_user_mtp_audit_range=[round(x["mtp"]["batch1"]["per_user_tokens_s"] * f, 1)
                                                      for f in HBM_AUDIT["mtp_range"]],
                            saturated_note="the model's column-pass bound (the audit prices single-user latency)",
                            saturated_tokens_s=x["ar"]["saturated"]["aggregate_tokens_s"],
                            mJ_b1=x["ar"]["batch1"]["gated_mJ"], mJ_saturated=x["ar"]["saturated"]["gated_mJ"],
                            capex_usd=x["cost"]["capex_usd"], silicon_mm2=x["silicon_mm2"], users_1m=x["capacity_users_1m"]))
    gv = g["v41"]
    v41.append(dict(design="DeepSeek-V4.1-Flash on 8x B200 (tier 2, calibrated)", tier="2", per_user_ar=gv["tokens_s_b1"],
                    per_user_mtp=gv.get("mtp_b1"), saturated_tokens_s=gv["saturated_tokens_s"],
                    mJ_b1=gv["rows"][0]["energy_mJ_per_token"], mJ_saturated=_sat_batch(gv["rows"])["energy_mJ_per_token"],
                    capex_usd=cst["V4.1 8x B200 (tier 2, AR)"]["capex_per_system_usd"], users_1m=gv["capacity_users"],
                    cost_basis="purchase price (iso-package $25k a B200), not manufacturing cost"))
    for a in g["anchors"]:
        if "DeepSeek" in a["design"]:
            v41.append(dict(design=a["design"], tier="1", per_user_mtp=a["per_user_tokens_s"],
                            mJ_b1=a["energy_mJ_per_token_at_689W"]))
    qs = qwen_product_ss()
    q = [dict(design="Qwen ROM option C (4 dies, 2 packages, TP-4, G 6,144), TT", tier="ROM",
              per_user_ar=pc["tokens_s_b1"], saturated_tokens_s=pc["saturated_tokens_s"], mJ_b1=pc["mJ_b1"],
              mJ_saturated=pc["mJ_saturated"], capex_usd=pc["capex_usd"], users_8k=pc["capacity_users"]),
         dict(design="Qwen ROM option C at 1.2 GHz SS (W12 SS wires, LAT-7 ME, KV_PREP, droop cap75 + preramp256)", tier="ROM",
              per_user_ar=qs["tokens_s_b1"], saturated_tokens_s=pc["saturated_tokens_s"],
              mJ_b1=round(pc["mJ_b1"] + QWEN_SS["droop_mJ"], 1), mJ_saturated=round(pc["mJ_saturated"] + QWEN_SS["droop_mJ"], 1),
              capex_usd=pc["capex_usd"], users_8k=pc["capacity_users"]),
         dict(design=f"Qwen ROM option C at 1.2 GHz SS, RTL-CALIBRATED (per-layer body x {qs['rtl_calibrated']['ratio']}, "
                     "W12b measured L0; pending attribution)", tier="ROM",
              per_user_ar=qs["rtl_calibrated"]["tokens_s_b1"], saturated_tokens_s=pc["saturated_tokens_s"],
              capex_usd=pc["capex_usd"], users_8k=pc["capacity_users"])]
    for row in qwen[1:3]:
        q.append(dict(design=row["design"] + " (tier 3, idealised; DFlash W19 audit -14%)", tier="3",
                      per_user_ar=row["ar_tokens_s_b1"],
                      per_user_dflash=round(row["dflash_tokens_s_b1"] * HBM_AUDIT["qwen_dflash"], 1),
                      per_user_dflash_model=row["dflash_tokens_s_b1"], saturated_tokens_s=row["saturated_tokens_s"],
                      mJ_b1=row["gated_mJ_b1"], mJ_saturated=row["gated_mJ_sat"], capex_usd=row["cost"]["capex_usd"],
                      users_8k=row["capacity_users"]))
    gq = g["qwen"]
    q.append(dict(design="Qwen3-8B on 1x B200, FP8 (tier 2, calibrated)", tier="2", per_user_ar=gq["tokens_s_b1"],
                  per_user_dflash=gq["dflash_b1"], saturated_tokens_s=gq["saturated_tokens_s"],
                  mJ_b1=gq["rows"][0]["energy_mJ_per_token"], mJ_saturated=_sat_batch(gq["rows"])["energy_mJ_per_token"],
                  capex_usd=cst["Qwen 1x B200 (tier 2, AR)"]["capex_per_system_usd"], users_8k=gq["capacity_users"],
                  cost_basis="purchase price"))
    for a in g["anchors"]:
        if "Qwen" in a["design"] and a["batch"] == 1:
            q.append(dict(design=a["design"], tier="1", per_user_ar=a["per_user_tokens_s"],
                          mJ_b1=a["energy_mJ_per_token_at_689W"]))
    return dict(v41=v41, qwen=q, hbm_audit=HBM_AUDIT, rule="USER DECISION 2026-09-30: V4.1 ROM headline = saturated throughput, J/token and "
                                     "cost at equal manufacturing cost; per-user speed claimed against GPUs (tier 1-2) "
                                     "only; Qwen ROM keeps its per-user claim")


def cons_clock_cases(S, h, t):
    """Root 2026-09-30, with W11's MEASURED ns per dependent FP32 add (FP32_ADD_SS).  Every case carries the 50%
    field-concurrency cap and the softplus correction.
    (a) everything at 1.2 GHz: the serial-chain units' adds at 8 or 9 stages (6.7 / 7.5 ns an add), the field
        element's adds at 8 (its chunk-8 chain floor and K-split levels);
    (b) the field, elements, index scan and attention tiles at 1.2 GHz (element adds 8 stages); the serial-chain units
        (SU, SFU, softplus, reducer, Sinkhorn) at 0.9 GHz with LAT 3 (906 MHz SS measured, 3:4) or 0.8 GHz (2:3);
        CDC 2 slow cycles a crossing (ASSUMED);
    (c) everything at 0.9 GHz, LAT 3 (element adds IEEE 5-stage, 992 MHz SS)."""
    out = {}
    for tag, hz, dyn, slow, cs, es in (
            ("a: all 1.2 GHz, chain adds 8 stages", 1.2e9, 1.16, None, 8, 8),
            ("a: all 1.2 GHz, chain adds 9 stages", 1.2e9, 1.16, None, 9, 8),
            ("b: 1.2 GHz field (LAT 7) + 0.9 GHz chain units (LAT 3), W18 CDC", 1.2e9, 1.16, (0.9e9, "w18"), None, 7),
            ("b: 1.2 GHz field (LAT 7) + 0.8 GHz chain units (LAT 3), W18 CDC", 1.2e9, 1.16, (0.8e9, "w18"), None, 7),
            ("c: all 0.9 GHz, LAT 3", 0.9e9, 1.0, None, None, None)):
        p = cons_v41_rom(S, h, t, 1.0, None, "option_iii", hz, FIELD_CONCURRENCY, SOFTPLUS_FIX, dyn, slow, cs, es)
        out[tag] = dict(ar_tokens_s_b1=p["ar_tokens_s_b1"], mtp_tokens_s_b1=p["mtp_tokens_s_b1"],
                        ar_saturated_tokens_s=p["ar_saturated_tokens_s"], mtp_saturated_tokens_s=p["mtp_saturated_tokens_s"],
                        gated_mJ_b1=p["energy"]["ar_b1"]["gated_mJ"], gated_mJ_saturated=p["energy"]["ar_sat"]["gated_mJ"],
                        busiest_stage_us=p["busiest_stage_us"], critical_path_top_us=p["critical_path_top_us"],
                        droop=cons_droop(p))
    return out


# ---- droop at 1.2 GHz (W18 67b0bd49 results/physical_abi3/asap7/chip/v41_w18/droop_schemes_1p2ghz.json) ----
DROOP = dict(field_ops_per_layer_die_per_token=6,
             schemes={"50% cap + 256-cycle pre-ramp": dict(mJ_per_op_start=0.098, extra_latency="the cap's (priced)"),
                      "1,024-cycle pre-ramp, no cap": dict(mJ_per_op_start=0.78, extra_latency=0),
                      "256-cycle pre-ramp, no cap (64 mV at 2 pH: fails 35 mV)": dict(mJ_per_op_start=0.196,
                                                                                      extra_latency=0)},
             src="W18 (root relay 2026-09-30): no fast-start scheme meets 35 mV at L_eff 1-10 pH; a schedule-driven "
                 "pre-ramp dummy-clocks the next op's pairs ahead of time")


PRERAMP_TAU_CYCLES = 256    # ASSUMED droop time constant: a field op after an idle gap longer than the pre-ramp
                            # window needs a ramp (W18 to state the current-decay constant)


def cons_field_starts(g, plan, clock):
    """Field-op starts per layer die per token on the priced single-user graph, and those that follow an idle field
    gap longer than the droop time constant (the only ones that need a pre-ramp; back-to-back field ops keep the
    current up).  A field op is a weight matvec on the ROM field; its start is its finish less its issue and depth."""
    fin = g.solve(True)
    per = {}
    for name, nd in g.nodes.items():
        if not nd.get("_uarch"):
            continue
        s0 = _cons_stage_of(name, nd, plan)
        if s0 == "head":
            continue
        end = fin[name]
        start = end - nd["issue"] - nd["depth"]
        per.setdefault(s0, []).append((start, end))
    tau = PRERAMP_TAU_CYCLES / clock
    out = dict(starts={}, ramps={}, held={})
    for s0, ops in per.items():
        ops.sort()
        ramps, busy_end, held = 1, ops[0][1], 0.0
        for st, en in ops[1:]:
            gap = st - busy_end
            if gap > tau:
                ramps += 1
            elif gap > 0:
                held += gap                  # W18's gap policy: the field is held on through a short gap
            busy_end = max(busy_end, en)
        out["starts"][s0] = len(ops)
        out["ramps"][s0] = ramps
        out["held"][s0] = held * clock
    n = len(per)
    return dict(mean_starts_per_die=round(sum(out["starts"].values()) / n, 2),
                mean_ramps_per_die=round(sum(out["ramps"].values()) / n, 2),
                held_cycles_per_token=round(4 * sum(out["held"].values())),
                max_ramps_per_die=max(out["ramps"].values()), tau_cycles=PRERAMP_TAU_CYCLES,
                layer_die_ramps_per_token=4 * sum(out["ramps"].values()),
                layer_die_starts_per_token=4 * sum(out["starts"].values()))


def cons_droop(p):
    """Pre-ramp energy per token on the layer dies: ops a layer die a token x layer dies x mJ an op start."""
    n = DROOP["field_ops_per_layer_die_per_token"] * p["layer_dies"]
    fs = p.get("field_starts")
    out = {}
    for k, v in DROOP["schemes"].items():
        e = n * v["mJ_per_op_start"]
        row = dict(pre_ramp_mJ_per_token=round(e, 1),
                   gated_mJ_b1=round(p["energy"]["ar_b1"]["gated_mJ"] + e, 1),
                   gated_mJ_saturated=round(p["energy"]["ar_sat"]["gated_mJ"] + e, 1))
        if fs:      # ramp only after an idle gap (root lever / W18's gap policy), counted on the priced graph; a held
                    # gap costs the ramp's energy per cycle (cfg_gap ~ cfg_ramp is energy-optimal, W18)
            eg = fs["layer_die_ramps_per_token"] * v["mJ_per_op_start"] + \
                fs.get("held_cycles_per_token", 0) * v["mJ_per_op_start"] / PRERAMP_TAU_CYCLES
            row.update(gap_only_pre_ramp_mJ_per_token=round(eg, 1),
                       gap_only_gated_mJ_b1=round(p["energy"]["ar_b1"]["gated_mJ"] + eg, 1),
                       gap_only_gated_mJ_saturated=round(p["energy"]["ar_sat"]["gated_mJ"] + eg, 1))
        out[k] = row
    return out


# ---- a smaller Qwen die (root 2026-09-30): the area extra G does not use ----
def qwen_small_die(tiles_mm2=(308.0, 359.0), spine_mm=1.4, margin=0.10):
    """Size the option-C Qwen die to its placed tiles (W12's TP-4 estimate, 1,536 tiles, 308-359 mm2; the routed
    tile area replaces it when it lands) + spine + 4 HBM PHY + UCIe + stream-unit spill + 10% margin, with 4 stacks'
    PHYs on the long edges (2 a side at 8.5 mm).  Also at the ruled storage-only density (the model's tile need)."""
    fixed = QWEN_TILE_FIXED_MM2
    W = 2 * HBM_SHORE["phy_edge_mm"] + 2 * HBM_SHORE["corner_mm"]
    rows = []
    rom75 = qwen_rom_need_mm2(4, 6144)
    pad = qwen_tp_point(4, 6144, "board")["bank_padding"]
    ruled = rom75["need_mm2"] - rom75["rom_mm2"] + rom75["rom_mm2"] / (1 - pad) - fixed
    for tag, t in [(f"W12 estimate {x:g} mm2 (ASAP7 tiles)", x) for x in tiles_mm2] + [
            ("storage-only 75 + ECC tile need (the ruled basis)", ruled)]:
        H, Wd = 0.0, W
        for _ in range(30):                          # the spine runs the die's length; the PHY edge grows past
            area = (t + spine_mm * max(Wd, H) + fixed) * (1 + margin)   # 19 mm when the other side would exceed 26
            Wd = max(W, area / 26.0)
            H = area / Wd
        L = max(Wd, H)
        dc = die_cost(area)
        hw = 4 * dc["usd"] + 2 * (FAB["package_usd"]["cowos_l_2die"] + FAB["test_assembly_usd"]) + 16 * FAB["hbm_stack_usd"]
        rows.append(dict(basis=tag, tiles_mm2=round(t, 1), die_mm2=round(area, 1), outline_mm=(round(Wd, 2), round(H, 2)),
                         fits_reticle=L <= 33.0 and min(Wd, H) <= 26.0, phy_edge_ok=Wd >= W - 1e-9,
                         yield_=dc["yield_"], die_usd=dc["usd"], hardware_usd_4die=round(hw)))
    ref = die_cost(FLOORPLAN["die_mm2"])
    rows.append(dict(basis="815 mm2 reference", die_mm2=815.0, yield_=ref["yield_"], die_usd=ref["usd"],
                     hardware_usd_4die=round(4 * ref["usd"] + 2 * (FAB["package_usd"]["cowos_l_2die"]
                                                                   + FAB["test_assembly_usd"]) + 16 * FAB["hbm_stack_usd"])))
    return dict(rows=rows, spine_mm=spine_mm, margin=margin, phy_long_edge_mm=W,
                note="the die keeps its 4 PHYs on the long edges (2 x 8.5 mm + corners = 19 mm); the smaller die is "
                     "priced at the same G = 6,144 and tok/s")


# ---------------------------------------------------------------------------------------------------------
# W16 follow-ups (root, 2026-09-30): the product stage-owner file, the MTP tau sweep, short-context rows, the GPU
# calibration row, and the Qwen context sweep.
# ---------------------------------------------------------------------------------------------------------
# MTP acceptance (root / user direction 2026-09-30): the headline tau is third-party.  LMSYS, "DSpark in SGLang"
# (https://www.lmsys.org/blog/2026-07-06-dspark-sglang/, Figure 4, reproduction appendix): DeepSeek-V4-FLASH, H200,
# TP4 + DP-attention, draft block 6 (gamma = 5), cap-accept verify mode ("to expose the acceptance ceiling"):
# gsm8k 5.24, arena-hard 3.78, poetry 2.91.  V4-Flash, not V4.1-Flash; our measured 3.649 corroborates.
TAU_SWEEP = (("poetry (creative, lower; LMSYS V4-Flash)", 2.91),
             ("measured on V4.1-Flash, reasoning mix (OpenTallas; corroboration)", V41_TAU),
             ("HEADLINE: arena-hard (general chat; LMSYS V4-Flash, cap-accept ceiling)", 3.78),
             ("4.5 (interpolated)", 4.5),
             ("gsm8k (math, upper; LMSYS V4-Flash)", 5.24))
TAU_SRC = ("LMSYS, 'DSpark in SGLang' (2026-07-06), https://www.lmsys.org/blog/2026-07-06-dspark-sglang/ Figure 4: "
           "DeepSeek-V4-Flash, H200 TP4 DP-attention, block 6, cap-accept verify (acceptance ceiling)")


def cons_tau_sweep(rows, positions=V41_POSITIONS):
    """MTP per-user rate at each tau from the rows' measured-tau MTP rate: a verify step's time does not depend on how
    many positions are accepted, so tok/s scales with tau / V41_TAU (tau <= gamma + 1 = positions)."""
    out = []
    for name, x in rows:
        base = x.get("mtp")
        if base is None:
            continue
        r = dict(design=name)
        for lab, tau in TAU_SWEEP:
            assert tau <= positions, "tau above gamma + 1 is impossible"
            r[f"tau_{tau:g}"] = round(base * tau / V41_TAU, 1)
        out.append(r)
    return dict(rows=out, taus={lab: t for lab, t in TAU_SWEEP}, headline_tau=3.78, source=TAU_SRC,
                gamma=positions - 1, note="tau <= gamma + 1 = 6 always holds here; GPU rows scale their tier-2 MTP "
                                          "the same way (their draft is modelled per step)")


@contextlib.contextmanager
def _cons_ctx(ctx):
    """Price the V4.1 graphs at context `ctx` instead of 1M (the consolidation section's own graphs only)."""
    global _CONS_CTX
    old = _CONS_CTX
    _CONS_CTX = ctx
    _HBM_CHAIN_CACHE.clear()
    _HBM_N_CACHE.clear()
    try:
        yield ctx
    finally:
        _CONS_CTX = old
        _HBM_CHAIN_CACHE.clear()
        _HBM_N_CACHE.clear()


# public GPU single-user records (root 2026-09-30).  TensorRT-LLM tech blog 1, "Pushing Latency Boundaries: Optimizing
# DeepSeek-R1 Performance on NVIDIA B200 GPUs": 8x B200, ISL 1K / OSL 2K, FP4, MTP extended to 3 layers (relaxed
# acceptance), 368 tok/s a user.  TensorRT-LLM blog 15 (DeepSeek-V3.2 on Blackwell): B200 min-latency ~312 tok/s a
# user with MTP-3.  NVIDIA's 1,038 tok/s a user on one DGX B200 is Llama 4 Maverick (not DeepSeek).  B300: the public
# interactivity points (SemiAnalysis InferenceX) are 73-150 tok/s a user at throughput-optimal settings; no
# min-latency B300 DeepSeek record was found.
GPU_PUBLIC = [
    dict(design="DeepSeek-R1 (671B), 8x B200, TensorRT-LLM min-latency", tok_s_user=368.0, ctx=3072, mtp_layers=3,
         src="TensorRT-LLM tech blog 1 (ISL 1K / OSL 2K, FP4)"),
    dict(design="DeepSeek-V3.2, B200, TensorRT-LLM min-latency", tok_s_user=312.0, ctx=None, mtp_layers=3,
         src="TensorRT-LLM tech blog 15"),
    dict(design="Llama 4 Maverick (400B MoE, 17B active), 1x DGX B200", tok_s_user=1038.0, ctx=None, mtp_layers=None,
         src="NVIDIA / Tom's Hardware, 2025-05: the ~1,000 tok/s/user public record is NOT a DeepSeek model"),
]
B300_OVER_B200 = dict(hbm_bw=8.0 / 8.0, note="B300 keeps 8 TB/s of HBM3E a GPU (288 GB); per-user decode at low batch "
                                             "is bandwidth- and latency-bound, so the tier-2 B300 row equals B200 "
                                             "within the model (ASSUMED; no public min-latency B300 DeepSeek record)")


def gpu_tier2_v41_ctx(ctx, positions=1):
    """Tier-2 8x B200 V4.1-Flash step at context ctx (gpu_economics' form: fixed per layer + weight + index/KV bytes
    at the fitted B200 byte rate + NCCL-class all-reduces), batch 1."""
    fixed = GPU_FIT["fixed_seconds_qwen"]
    s_per_B = (1 / 230.0 - fixed) / (2 * GPU_FIT["qwen_fp8_weight_bytes"])
    c = A._env()["c"]
    idx_user = 262144 * A.IDX_KEY_B * 4 * 38 * ctx / 1048576     # gpu_economics' 1M index-key read, scaled to ctx
    t = (40 * fixed / 36 + s_per_B * (_v41_weight_bytes(positions) + idx_user) / 8 + 40 * 5 * NCCL_ALLREDUCE_S)
    return t


def cons_short_context(Sp, hp, t_a, head, ec, gr, ctx=8192):
    """Short-context rows (root 2026-09-30): the public GPU records are short-context, and the 1M headline is dominated
    by the index scan and attention.  The ROM product, the HBM tier 3 at equal cost (audited) and GPU tier 2, at ctx."""
    with _cons_ctx(ctx):
        p = cons_v41_rom(Sp, hp, t_a, 1.0, None, "columns", PRODUCT_CLOCK_HZ, FIELD_CONCURRENCY,
                         dict(SOFTPLUS_FIX, **W11_STREAM_SS), PRODUCT_DYN_SCALE, (0.9e9, "w18"), None, 7, True,
                         PRODUCT_SERIAL, DIE_SHRUNK_INTERIM)
        h = v41_hbm_n(96, 4, ec, gr, replicas=2, clock_hz=PRODUCT_CLOCK_HZ)
    h1 = v41_hbm_n(96, 4, ec, gr, replicas=2, clock_hz=PRODUCT_CLOCK_HZ)      # 1M: the W19 composition's context
    w_ar = HBM_W19["ar_tokens_s"] / h1["ar"]["batch1"]["per_user_tokens_s"]
    w_mtp = HBM_W19["mtp_tokens_s"] / h1["mtp"]["batch1"]["per_user_tokens_s"]
    t_ar = gpu_tier2_v41_ctx(ctx)
    gv = ec["gpu"]["v41"]
    mtp_ratio = gv["mtp_b1"] / gv["tokens_s_b1"]
    return dict(ctx=ctx, rows=[
        dict(design="V4.1 ROM product (columns, 1.2 GHz SS)", ar=p["ar_tokens_s_b1"], mtp=p["mtp_tokens_s_b1"],
             saturated=p["ar_saturated_tokens_s"], dies=p["dies"], silicon_mm2=p["dies"] * FLOORPLAN["die_mm2"],
             capex_usd=head["cost"]["capex_usd"]["low"], users=p["capacity_users_1m"]),
        dict(design="V4.1 HBM tier 3, equal cost (2 x TP-96), W19 composed/model ratio at 1M applied at ctx", ar=round(
            h["ar"]["batch1"]["per_user_tokens_s"] * w_ar, 1),
             mtp=round(h["mtp"]["batch1"]["per_user_tokens_s"] * w_mtp, 1), w19_ratio_ar=round(w_ar, 4),
             w19_ratio_mtp=round(w_mtp, 4),
             saturated=h["ar"]["saturated"]["aggregate_tokens_s"], dies=h["dies"], silicon_mm2=h["silicon_mm2"],
             capex_usd=h["cost"]["capex_usd"]["low"], users=h["capacity_users_1m"]),
        dict(design="V4.1-Flash, 8x B200 (tier 2, calibrated)", ar=round(1 / t_ar, 1), mtp=round(mtp_ratio / t_ar, 1),
             gpus=8, silicon_mm2=16 * 800.0, capex_usd=8 * COST["package_usd"], cost_basis="purchase price"),
        dict(design="V4.1-Flash, 8x B300 (tier 2; = B200 within the model, ASSUMED)", ar=round(1 / t_ar, 1),
             mtp=round(mtp_ratio / t_ar, 1), gpus=8, silicon_mm2=16 * 800.0, note=B300_OVER_B200["note"])])


def gpu_calibration_row(ec):
    """Our tier-2 model at DeepSeek-R1's published min-latency conditions (8x B200, ~3K context, MTP-3) against its
    368 tok/s: R1 is 671B / 37B active (FP4 in the record) against V4.1-Flash's 284B / 13B, so the row reports the
    model's V4.1 short-context step and states the model mismatch."""
    t = gpu_tier2_v41_ctx(3072)
    gv = ec["gpu"]["v41"]
    mtp = gv["mtp_b1"] / gv["tokens_s_b1"] / t
    return dict(conditions="8x B200, context ~3K (ISL 1K / OSL 2K), MTP", published=GPU_PUBLIC,
                model_v41_ar=round(1 / t, 1), model_v41_mtp=round(mtp, 1),
                error_vs_r1_record=round(mtp / 368.0 - 1, 3),
                note="the model prices V4.1-Flash (13B active) and R1 is 37B active: a like-for-like error needs an R1 "
                     "run of the tier-2 form; the ratio shown mixes model size with model error")


QWEN_CTX_SWEEP = (8192, 32768, 131072, 200000)
QWEN_CTX_NOTE = ("W12b context audit (claude/w12-qwen-rom b4d2715f): KV read 18,432 x T bytes a token a die; HBM "
                 "binds from ~32K (W12b ~1.4k tok/s at 128K, ~0.9k at 200K with SW 1,024, matching this sweep); 32K "
                 "needs parameters and 2 larger SRAMs (+~10 mm2 a die); 128K and 200K need a 27-bit address and a "
                 "larger VM (or head-serial scores).  "
                 "Qwen3-8B is natively 32K and 128K with YaRN; 200K is beyond official support.  FP8 KV (baseline); "
                 "the FP4/INT4-KV rows halve the KV bytes and are QUALITY-UNTESTED")


def qwen_context_sweep(ec):
    """Qwen3-8B per-user AR, KV bytes a token and KV read time, users that fit, saturated tok/s and J/token at 8K-200K
    for the ROM product (option C: TP-4, 4 x 4 stacks), its 6-stack-a-die and FP4-KV sensitivities, the HBM tier 3
    (2 x 4-stack right-sized dies) and GPU tier 2 (1x B200).  Rule: a token is the longer of the replayed compute
    chain at ctx (the attention work grows with ctx) and the KV stream of the busiest die (overlapped, ASSUMED)."""
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    wl, kvb8 = _qwen_wl()
    qr, qh = ec["qwen_rom"], ec["qwen_hbm"]
    cats = qr["energy"]["categories_mJ_per_token"]
    kv_e8 = (cats["kv_on_die"] + cats["stack"]) * 1e-3
    other_e = sum(v for k, v in cats.items() if k not in ("kv_on_die", "stack")) * 1e-3
    P_static = qr["energy"]["static_w_total"]
    dq = hbm_gpu_design("qwen")
    w_B = sum(b_ for b_, _ in qwen_hbm_ops(dq["element"], dq["barrier"]["boundary_cycles"], dq["drain_cycles"])) - kvb8 / 2
    w_total = 2 * w_B
    t_h8 = 1 / qh["ar"]["tokens_s_b1"]
    fixed = GPU_FIT["fixed_seconds_qwen"]
    s_per_B = (1 / 230.0 - fixed) / (2 * GPU_FIT["qwen_fp8_weight_bytes"])
    rows = []
    for ctx in QWEN_CTX_SWEEP:
        k0 = dict(T.K)
        Q.CLOCK[0] = Q.clock_hz()
        clock = Q.CLOCK[0]
        try:
            T.K["me_lat"] = k0["me_lat"] + QWEN_WIRE_W12["me_lat_extra"]
            nh, kv = QWEN_TP_SHAPE[4]
            shp = dict(Q.Q, NH=nh, KV=kv, FF=-(-Q.Q["FF"] // 4), V=-(-Q.Q["V"] // 4))
            r = Q.as_built(ctx, groups=6144, su_width=1024, shape=shp, ucie=False)
        finally:
            T.K.clear()
            T.K.update(k0)
        x = _qwen_exchange("board", 4, clock)
        chain = (r["cycles"] + x["token_cycles"]) / clock
        for tag, stacks, kvf in (("ROM option C (4 stacks a die, FP8 KV)", 4, 1.0),
                                 ("ROM option C, 6 stacks a die", 6, 1.0),
                                 ("ROM option C, FP4/INT4 KV (quality untested)", 4, 0.5)):
            kvb = kvb8 * ctx / 8192 * kvf
            kv_die = kvb * kv / Q.Q["KV"]
            t_kv = kv_die / (stacks * HBM_STACK_BPS)
            t = max(chain, t_kv)
            users = int(stacks * HBM_STACK_B * HBM_CAP_EFF // kv_die)
            ub = r["unit_busy"]
            lanes = ub["weights"] + ub["attn_scores"] + ub["attn_pv"] + ub["lm_head"]
            sat = min(clock / lanes, clock / ub["stream"], stacks * HBM_STACK_BPS / kv_die)
            dyn = other_e + kv_e8 * kvb / kvb8
            rows.append(dict(ctx=ctx, design=tag, ar_tokens_s=round(1 / t, 1), kv_bytes_per_token=round(kvb),
                             kv_read_us=round(t_kv * 1e6, 1), chain_us=round(chain * 1e6, 1),
                             binding="KV stream" if t_kv > chain else "compute chain", users=users,
                             saturated_tokens_s=round(min(sat, users / t), 1),
                             mJ_b1=round((dyn + P_static * t) * 1e3, 1),
                             mJ_saturated=round((dyn + P_static / min(sat, users / t)) * 1e3, 1)))
        kvb = kvb8 * ctx / 8192
        t_h = t_h8 * (w_total + kvb) / (w_total + kvb8)
        users_h = int((8 * HBM_STACK_B * HBM_CAP_EFF - w_total) // kvb)
        rows.append(dict(ctx=ctx, design="Qwen HBM tier 3 (2 x 4-stack right-sized dies), AR", ar_tokens_s=round(1 / t_h, 1),
                         kv_bytes_per_token=round(kvb), kv_read_us=round(t_h * kvb / (w_total + kvb) * 1e6, 1),
                         binding="HBM stream", users=users_h))
        t_g = fixed + s_per_B * (GPU_FIT["qwen_fp8_weight_bytes"] + kvb)
        users_g = int((B200_HBM_B * HBM_CAP_EFF - GPU_FIT["qwen_fp8_weight_bytes"]) // kvb)
        rows.append(dict(ctx=ctx, design="Qwen3-8B on 1x B200, FP8 (tier 2, calibrated), AR", ar_tokens_s=round(1 / t_g, 1),
                         kv_bytes_per_token=round(kvb), kv_read_us=round(s_per_B * kvb * 1e6, 1), users=users_g,
                         mJ_b1=round(B200_W_DECODE * t_g * 1e3, 1)))
    return dict(rows=rows, note=QWEN_CTX_NOTE,
                rule="per-user token = max(replayed compute chain at ctx, busiest die's KV stream) for the ROM; the HBM "
                     "tier 3 and GPU scale their 8K step by the streamed bytes (weights + KV)")


# Qwen ROM product at 1.2 GHz SS (root 2026-09-30, W12b claude/w12-qwen-rom 8289866f): W12's TP-4 wire stages at the SS
# reach (112 cycles an ME op incl. MEM_EXTRA) + LAT-7 ME adders (+54 an op), and the droop product choice cap75 +
# preramp256 (x0.956 tok/s, +22.2 mJ a token of ramp energy; results/floorplan/qwen_rom_w12/droop_1p2ghz.json)
QWEN_SS = dict(me_lat_extra=QWEN_W12_TP4_ME_EXTRA_SS + 54, droop_rate=0.956, droop_mJ=22.2,
               src="W12b 775f5279 / 8289866f: LAT-7 ME +54 cycles an op; droop cap75 + preramp256")


# W12b (claude/w12-qwen-rom 42ecf382, root relay 2026-09-30): 1.2 GHz ME deltas -- LAT-7 adders +54 an ME op (ALREADY in
# QWEN_SS since 775f5279, not added again), KV_PREP +3 a KV op (+216 a token), FAST_ISSUE 0
QWEN_KV_PREP_CYCLES_TOKEN = 216
# W12b MEASURED (42ecf382 results/rtl/qwen_rom_w12_runtime/layer0_tp4_g6144_sw64.json, status pass): TP-4 layer 0
# bit-exact on 4 dies, G 6,144, SU width 64, SS wire stages (BD 41, NWS 5, TWS 38, ORD 7, MEM_EXTRA 1 = ME extra 112),
# N=4 oneshot collective at LAT 339 / DEPTH 1024, ME adders and issue loop the originals: 4,669 cycles
QWEN_L0_RTL = dict(cycles=4669, total_cycles=4676, collective_lat_cycles=339, su_width=64, groups=6144, tp=4,
                   me_extra=QWEN_W12_TP4_ME_EXTRA_SS, position=0,
                   src="claude/w12-qwen-rom 42ecf382 results/rtl/qwen_rom_w12_runtime/layer0_tp4_g6144_sw64.json "
                       "(stages.L0.cycles)")


def qwen_l0_rtl_vs_model():
    """The model's layer at W12b's RTL configuration (position 0, SU width 64, ME extra 112, TP-4, G 6,144, SS) against
    the measured layer 0: the layer chain plus its two all-reduces.  Until the gap is attributed per stage, the
    product carries an RTL-CALIBRATED row that scales the per-layer body by the measured ratio (root 2026-09-30)."""
    m = QWEN_L0_RTL
    p = qwen_tp_point(4, m["groups"], "board", clock_hz=PRODUCT_CLOCK_HZ, me_lat_extra=m["me_extra"], ctx=1,
                      su_width=m["su_width"])
    ar = p["exchange"]["per_allreduce_cycles"]
    model = p["layer_chain_cycles"] + 2 * ar
    model_rtl_coll = p["layer_chain_cycles"] + 2 * m["collective_lat_cycles"]
    return dict(rtl=m, model_layer_chain_cycles=p["layer_chain_cycles"], model_allreduce_cycles=ar,
                model_layer_cycles=round(model, 1), ratio=round(m["cycles"] / model, 4),
                model_short_pct=round(100 * (1 - model / m["cycles"]), 1),
                model_layer_cycles_at_rtl_collective=round(model_rtl_coll, 1),
                gap_cycles_at_rtl_collective=round(m["cycles"] - model_rtl_coll, 1),
                status="UNATTRIBUTED: per-stage RTL cycles requested from W12b (QKV, attention, O, gate/up, down, "
                       "collectives)")


def qwen_product_ss():
    p = qwen_tp_point(4, 6144, "board", clock_hz=PRODUCT_CLOCK_HZ, me_lat_extra=QWEN_SS["me_lat_extra"])
    cyc = p["cycles"] + QWEN_KV_PREP_CYCLES_TOKEN
    out = dict(p, cycles=cyc, tokens_s_b1=round(p["clock_hz"] / cyc * QWEN_SS["droop_rate"], 1), droop=QWEN_SS,
               kv_prep_cycles=QWEN_KV_PREP_CYCLES_TOKEN)
    # RTL-CALIBRATED (root 2026-09-30, labelled): the per-layer body (36 x (layer chain + 2 all-reduces)) x the
    # measured layer-0 ratio; the head and embedding stay at the model
    cal = qwen_l0_rtl_vs_model()
    body = 36 * (p["layer_chain_cycles"] + 2 * p["exchange"]["per_allreduce_cycles"])
    cyc_c = cyc + body * (cal["ratio"] - 1)
    out["rtl_calibrated"] = dict(cycles=round(cyc_c), body_cycles=round(body), ratio=cal["ratio"],
                                 tokens_s_b1=round(p["clock_hz"] / cyc_c * QWEN_SS["droop_rate"], 1),
                                 label=f"RTL-calibrated: model per-layer body x measured L0 {QWEN_L0_RTL['cycles']:,} / "
                                       f"model {cal['model_layer_cycles']:,.0f} (W12b 42ecf382); the body includes the "
                                       "LAT-7 ME +54, so the scale is slightly pessimistic; pending per-stage attribution")
    return out


def qwen_helix_scaleout(ec, ctx=200000, extra=(0, 4, 8, 16)):
    """Long-context KV scale-out (root 2026-09-30): extra HBM + attention dies hold context slices (KV split by
    position, Helix-style) with an exact ordered merge of the partial softmax; weights stay on the 4 ROM dies.  Per
    user at ctx: max(compute chain, KV stream over all dies' stacks) + one ordered merge a layer (a board all-gather of
    the partial (max, sum, output) vectors, W15's measured TP-4 board fit, ASSUMED to span the added dies)."""
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    wl, kvb8 = _qwen_wl()
    Q.CLOCK[0] = Q.clock_hz()
    clock = Q.CLOCK[0]
    k0 = dict(T.K)
    try:
        T.K["me_lat"] = k0["me_lat"] + QWEN_WIRE_W12["me_lat_extra"]
        nh, kv = QWEN_TP_SHAPE[4]
        shp = dict(Q.Q, NH=nh, KV=kv, FF=-(-Q.Q["FF"] // 4), V=-(-Q.Q["V"] // 4))
        r = Q.as_built(ctx, groups=6144, su_width=1024, shape=shp, ucie=False)
    finally:
        T.K.clear()
        T.K.update(k0)
    chain = (r["cycles"] + _qwen_exchange("board", 4, clock)["token_cycles"]) / clock
    kvb = kvb8 * ctx / 8192
    merge = w15_collective_s("v41p17_r0d1024", "all_gather", Q.Q["H"] * 4 + 64, 4)
    rows = []
    for n in extra:
        stacks = 4 * (4 + n)
        t_kv = kvb / (stacks * HBM_STACK_BPS)
        t = max(chain, t_kv) + (Q.Q["L"] * merge if n else 0.0)
        rows.append(dict(extra_kv_dies=n, total_dies=4 + n, ar_tokens_s=round(1 / t, 1), kv_read_us=round(t_kv * 1e6, 1),
                         merge_us=round(Q.Q["L"] * merge * 1e6, 1) if n else 0.0,
                         users=int(stacks * HBM_STACK_B * HBM_CAP_EFF // kvb)))
    return dict(ctx=ctx, rows=rows, chain_us=round(chain * 1e6, 1),
                rule="KV split by position over the 4 ROM dies + n KV dies (4 stacks each); one ordered partial-softmax "
                     "merge a layer on the board fit (ASSUMED); weights stay on the ROM dies")


CONS_SOURCES = ECON_SOURCES + ("results/arch/v41_die_assembly.json", "results/arch/v41_die_placement.json",
                               "results/floorplan/v41_die_macromap_expanded_woa.json",
                               "results/floorplan/v41_rom_capacity.json", "results/floorplan/qwen_o4_rom_placement.json",
                               "results/floorplan/hbm_gpu/qwen_hbm_die.json", "results/floorplan/hbm_gpu/v41_hbm_die.json",
                               "tools/decode_critical_path.py")


def sweep(ctx: int):
    """Design-point search over the microarchitecture knobs that the evaluation shows binding."""
    rows = []
    base = PRESETS["proposal"]
    for vm in (16, 32, 64, 128, 256):
        for nb in (1024, 2048, 3072, 4096):
            d = dict(base, name=f"sweep_vm{vm}_bf{nb or 'all'}", vm_read_elems=vm, vm_write_elems=2 * vm,
                     bf16_stripe_macros=nb)
            r = evaluate(d, ctx)
            clock = r["clock_hz"]
            rows.append(dict(vm_read_elems=vm, vm_write_elems=2 * vm, bf16_stripe_macros=nb or d["macros"],
                             tokens_s=round(r["tokens_s"], 1), T_us=round(r["T_us"], 2),
                             weight_sweep_us=r["breakdown_us"].get("weight_sweep"),
                             area=area_ledger(d), network=network_ledger(d, clock)))
            print(f"vm{vm:4d} bf16 {nb or 'all':>5}: {r['tokens_s']:8.1f} tok/s  strip "
                  f"{rows[-1]['area']['rom_field_strip_used_mm2']:6.1f}  hub {rows[-1]['area']['hub_logic_mm2']:6.1f}"
                  f"  spines {rows[-1]['network']['spine_corridors_needed']}  col util "
                  f"{rows[-1]['network']['column_utilisation']}")
    return rows


POWER_CLOCKS = (1.25e9, 1.5e9)


def power_clock_sensitivity(name="proposal", ctx=1048576, clocks=POWER_CLOCKS):
    """The design re-priced at a faster clock (the architecture DAG rebuilt at that clock, then the uarch pricing;
    wire flight, HBM streams and the W15 collectives keep their times) with the measured pair power scaled linearly
    with the clock at the same 0.7 V (ASSUMED: a faster clock may need a higher supply, which this under-states)."""
    E = A._env()
    base = E["clock"]
    saved = dict(_ARCH_CACHE)
    rows = []
    try:
        for f in clocks:
            E["clock"] = f
            _ARCH_CACHE.clear()                  # the architecture DAG prices cycle terms at E["clock"]
            d = copy.deepcopy(PRESETS[name])
            r = evaluate(d, ctx)
            g = r.pop("_g")
            pw = power_ledger(d, g, f, r["tokens_s"], area_ledger(d))
            rows.append(dict(clock_hz=f, tokens_s=round(r["tokens_s"], 1), power=pw))
    finally:
        E["clock"] = base
        _ARCH_CACHE.clear()
        _ARCH_CACHE.update(saved)
    return dict(design=name, basis="architecture DAG and uarch pricing rebuilt at each clock; pair power x f / "
                                   "1.087 GHz at 0.7 V (ASSUMED)", rows=rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ctx", type=int, default=1048576)
    ap.add_argument("--preset", action="append")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--qwen", action="store_true", help="the Qwen3-8B ROM die rows only")
    ap.add_argument("--hbm", action="store_true", help="the GPU-organised HBM comparators only")
    ap.add_argument("--spec", action="store_true", help="speculation (MTP / DFlash) rows")
    ap.add_argument("--fabric", action="store_true", help="collective-latency sweep and GPU tiers")
    ap.add_argument("--dedicated", action="store_true", help="the dedicated-unit ledger (W11) of each preset only")
    ap.add_argument("--economics", action="store_true", help="batch, energy and cost of every design and GPU tier")
    ap.add_argument("--levers", action="store_true", help="V4.1 static-power gating, adaptive MTP, ROM mask cost")
    ap.add_argument("--consolidation", action="store_true",
                    help="V4.1 ROM die consolidation, right-sized HBM dies, HBM die-count sweep, comparison rule")
    a = ap.parse_args(argv)
    if a.consolidation:
        import hashlib
        cs = consolidation()
        for r in cs["v41_rom"]["points"]:
            print(f"ROM {r['label']:44s} dies {r['dies']:4d} (L {r['layer_dies']} H {r['head_dies']} T {r['table_dies']})  "
                  f"AR {r['ar_tokens_s_b1']:8.1f} MTP {r['mtp_tokens_s_b1']:8.1f}  sat {r['ar_saturated_tokens_s']:9.1f}  "
                  f"gated mJ b1 {r['energy']['ar_b1']['gated_mJ']:8.1f} sat {r['energy']['ar_sat']['gated_mJ']:7.1f}  "
                  f"capex ${r['cost']['capex_usd']['low']:,}-{r['cost']['capex_usd']['high']:,}")
        for r in cs["hbm"]["v41_sweep"]:
            print(f"HBM N={r['dies']:3d} x{r['stacks_per_die']}  users {r['capacity_users_1m']:6d}  AR {r['ar']['batch1']['per_user_tokens_s']:8.1f}"
                  f"  MTP {r['mtp']['batch1']['per_user_tokens_s']:8.1f}  sat {r['ar']['saturated']['aggregate_tokens_s']:9.1f}"
                  f"  gated mJ b1 {r['ar']['batch1']['gated_mJ']:8.1f}  capex ${r['cost']['capex_usd']['low']:,}")
        for r in cs["comparison_rule"]["v41"]:
            print("RULE", r["rule"], r["stacks_per_die"], r.get("dies"), r.get("replicas"),
                  r.get("ar", {}).get("batch1", {}).get("per_user_tokens_s"), r.get("ar", {}).get("saturated", {}).get("aggregate_tokens_s"))
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            pins = {q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in CONS_SOURCES}
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.consolidation.v1", **cs, source_sha256=pins),
                                              indent=1, default=str) + "\n")
        return
    if a.levers:
        import hashlib
        lv = economics_levers()
        sp = lv["static_power"]
        for mode in ("ar", "mtp_m1"):
            for wk in ("wake_1us", "wake_c6_133us"):
                for pt in ("batch1", "saturated"):
                    for r in sp[mode][wk][pt]:
                        print(f"{mode:6s} {wk:14s} {pt:9s} {r['policy']:34s} static {r['static_mJ_per_token']:9.2f} mJ  "
                              f"total {r['energy_mJ_per_token']:9.2f} mJ  {r['static_w']:8.0f} W  gated {r['stages_power_gated']}")
                print(f"   wake on token path {sp[mode][wk]['wake_on_token_path_us']} us, min idle {sp[mode][wk]['min_idle_batch1_us']} us")
        for r in lv["gated_alike"]["rows"]:
            print(f"GATED {r['design']:28s} {r['point']:9s} {r['tokens_s']:9.1f} tok/s  ungated {r['ungated_mJ_per_token']:9.2f}"
                  f"  clock {r['clock_gated_mJ_per_token']:9.2f}  clock+power {r['clock_and_power_gated_mJ_per_token']:9.2f} mJ")
        for k, v in lv["adaptive_mtp"].items():
            print(k, "switch", v["switch_users"], [(r["batch"], r["mode"], r["per_user_tokens_s"], r["aggregate_tokens_s"]) for r in v["rows"]])
        for r in lv["rom_masks"]["rows"]:
            print(f"{r['design'][:10]:10s} {r['case']:70s} NRE {r['nre_usd'] / 1e6:8.1f}M  capex {r['capex_per_system_usd']:>10,}  "
                  f"$/tok/s b1 {r['usd_per_tokens_s_b1']:8.2f} sat {r['usd_per_tokens_s_saturated']:7.2f} "
                  f"(base excl. {r['usd_per_tokens_s_saturated_base_excluded']})")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            pins = {q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in LEVER_SOURCES}
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.economics_levers.v1", **lv, source_sha256=pins),
                                              indent=1, default=str) + "\n")
        return
    if a.economics:
        import hashlib
        ec = economics()
        for r in ec["summary"]:
            print(f"{r['design']:28s} b1 {r['tokens_s_b1']:9.1f} tok/s {r['energy_mJ_b1']:9.2f} mJ | sat B={r['sat_batch']:4d} "
                  f"{r['sat_aggregate_tokens_s']:10.1f} tok/s ({r['sat_per_user_tokens_s']:8.1f}/user) "
                  f"{r['energy_mJ_sat']:8.2f} mJ | cap {r['capacity_users']}")
        for r in ec["cost"]:
            print(f"{r['design']:32s} ${r['capex_per_system_usd']['low']:>12,}-{r['capex_per_system_usd']['high']:>12,}  "
                  f"$/tok/s b1 {r['usd_per_tokens_s_b1']}  sat {r['usd_per_tokens_s_saturated']}  "
                  f"slo {r['tokens_s_at_slo']} {r['usd_per_tokens_s_at_slo']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            pins = {q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in ECON_SOURCES}
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.economics.v1", **ec, source_sha256=pins),
                                              indent=1, default=str) + "\n")
        return
    if a.fabric:
        t2 = gpu_tier2()
        t3 = qwen_hbm_tau_sensitivity()
        for r in TIER1 + t2 + t3:
            print(r)
        rows = fabric_sweep()
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.fabric.v1", tier1=TIER1, tier2=t2,
                                                   tier3_qwen_tau=t3,
                                                   sweep=rows, nccl_allreduce_s_assumed=NCCL_ALLREDUCE_S),
                                              indent=1, default=str) + "\n")
        return
    if a.dedicated:
        rows = [dedicated_ledger(copy.deepcopy(PRESETS[n]), a.ctx) for n in (a.preset or ("as_built", "proposal"))]
        # root decisions of 2026-09-29 (W11): 16 NK=4 index slices, NL=4 attention with the two-word loader;
        # single position and the MTP verify pass (6 positions, m = 1)
        w11 = dict(copy.deepcopy(PRESETS["proposal"]), idx_macs=262144, att_macs=32768, att_pwords=2,
                   su_bcast_stages=SU_BCAST_STAGES_W1, su_ret_stages=SU_RET_STAGES_W1)
        for P in (1, 6):
            rows.append(dedicated_ledger(dict(w11, name=f"proposal_w11_p{P}"), a.ctx, positions=P))
        for r in rows:
            print(f"{r['design']:14s} hub {r['hub_logic_mm2']:7.2f}/{r['hub_avail_mm2']} mm2  "
                  + "  ".join(f"{k}:{v['area_mm2'] if 'area_mm2' in v else '-'}" for k, v in r["units"].items())
                  + (f"  DISCREPANCIES {r['discrepancies']}" if r["discrepancies"] else ""))
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            import hashlib
            pins = {q: hashlib.sha256((ROOT / q).read_bytes()).hexdigest() for q in (
                "tools/uarch_model.py", "tools/arch_budget_v41.py", "tools/rtl_hdc_v41x_vec_campaign.py",
                "results/arch/arch_budget_v41.json")}
            for u in DEDICATED.values():
                for k, q in u.items():
                    if k.startswith(("hardened_record", "measured_record")) and (ROOT / q).exists():
                        pins[q] = hashlib.sha256((ROOT / q).read_bytes()).hexdigest()
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.v41_dedicated.v1", ctx=a.ctx, rows=rows,
                                                   elements=DEDICATED, source_sha256=pins), indent=1, default=str)
                                   + "\n")
        return
    if a.spec:
        rows = speculation_rows()
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.speculation.v1", rows=rows,
                                                   decisions=dict(v41_rom="MTP m=1 time-multiplexed",
                                                                  qwen_rom="AR only (no drafter in ROM)",
                                                                  hbm="DFlash / MTP on the SM design (W13)")),
                                              indent=1, default=str) + "\n")
        return
    if a.hbm:
        rows = qwen_hbm_rows() + v41_hbm_rows()
        dq = hbm_gpu_design("qwen")
        spec = hbm_speculation_rows()
        for r in spec:
            print(f"   spec {r['design']:24s} {r['tokens_s']:9.1f} tok/s  tau {r.get('tau', 1.0)}  speedup {r.get('speedup', 1.0)}")
        for r in rows:
            print(f"{r['design']:30s} {r['tokens_s']:9.1f} tok/s  T {r['T_us']:9.1f} us  supply {r['supply_frac']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.hbm_gpu.v2", rows=rows, gpu=GPU,
                                                   speculation=spec,
                                                   designs=dict(qwen=dq, v41=hbm_gpu_design("v41"))),
                                              indent=1, default=str) + "\n")
        return
    if a.qwen:
        rows = qwen_rows()
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.qwen_rom.v1", rows=rows,
                                                   wire=QWEN_WIRE, area=QWEN_AREA), indent=1, default=str) + "\n")
        return
    names = a.preset or list(PRESETS)
    rows = []
    for n in names:
        d = copy.deepcopy(PRESETS[n])
        r = evaluate(d, a.ctx)
        r["params"] = {k: v for k, v in d.items()}
        r["area"] = area_ledger(d)
        r["network"] = network_ledger(d, r["clock_hz"])
        g = r.pop("_g")
        r["power"] = power_ledger(d, g, r["clock_hz"], r["tokens_s"], r["area"])
        r["power_wire_0p4"] = power_ledger(d, g, r["clock_hz"], r["tokens_s"], r["area"], wire_j=0.4e-12)
        rows.append(r)
        print(f"{n:22s} T={r['T_us']:9.1f} us  {r['tokens_s']:8.1f} tok/s   (arch {r['arch_tokens_s']:.0f})"
              f"  strip {r['area']['rom_field_strip_used_mm2']}/{r['area']['rom_field_strip_avail_mm2']}"
              f"  hub {r['area']['hub_logic_mm2']}/{r['area']['hub_avail_mm2']}"
              f"  P1 {r['power']['total_w_single_user']} W  Psat {r['power']['total_w_saturated']} W")
        print("   ", {k: v for k, v in list(r["breakdown_us"].items())[:6]})
        print("   top:", list(r["critical_path_by_node_us"].items())[:8])
    out = dict(schema="opentallas.uarch.v41_rom.v1", ctx=a.ctx, rows=rows)
    if "proposal" in names:
        out["power_clock_sensitivity"] = power_clock_sensitivity("proposal", a.ctx)
    if a.sweep:
        out["sweep"] = sweep(a.ctx)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
