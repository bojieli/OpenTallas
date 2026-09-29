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
                           bf16_stripe_macros=2048, collective_cycles=232, row_split="ksplit")
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
                nd["issue"] = d["att_measured_job_cycles"] * cyc
                nd["depth"] = 0.0
            elif d["use_measured_attention"] and name.endswith(".pv"):
                nd["issue"] = 0.0      # the measured job covers scores + PV
        elif k == "collective" and d["collective_cycles"]:
            nd["depth"] = max(nd["depth"], d["collective_cycles"] * cyc)
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
                layer20_matvecs=mv)


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
    hub = out["indexer"] + out["attention"] + out["su_lanes"] + out["sfu_lanes"] + out["vm_ports"]
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


def qwen_eval(G=6144, su_width=1024, wires=True, pruned=False, ctx=8192):
    import arch_budget_qwen3 as Q
    import hdc_timing as T
    Q.CLOCK[0] = Q.clock_hz()
    k0 = dict(T.K)
    # W5 derived its wire terms with the unloaded fit (0.5997 ps/um); re-derive the x broadcast from its
    # 27.0 mm distance with the loaded channel constant and scale the tree/UCIe wire terms by the same ratio
    x_extra = wire_cycles(27000.0, Q.clock_hz(), WIRE_PS_PER_UM_LOADED) - 1
    wscale = x_extra / QWEN_WIRE["x_stages_extra"]
    try:
        if wires:
            T.K["me_lat"] = k0["me_lat"] + x_extra + QWEN_WIRE["vm_conflict_reg"] \
                + QWEN_WIRE["result_write_extra"]
        r = Q.as_built(ctx, groups=G, su_width=su_width)
    finally:
        T.K.clear()
        T.K.update(k0)
    cycles = r["cycles"] + (round((QWEN_WIRE["tree_extra_per_token"] + QWEN_WIRE["ucie_wire_per_token"]) * wscale)
                            if wires else 0)
    a = QWEN_AREA
    tiles = G / 4
    macros_tile = a["code_macros"] / tiles
    logic = a["logic_group_pruned_um2"] if pruned else a["logic_group_um2"]
    tile_um2 = macros_tile * a["macro_um2"] * a["macro_pack"] + 4 * (logic / a["util"]
                                                                     + a["kv_sram_group_um2"] * a["macro_pack"])
    need_mm2 = (tiles - a["port_tiles"]) * tile_um2 / 1e6      # port tiles sit in the spine (W5)
    return dict(G=G, su_width=su_width, wires=wires, pruned=pruned, ctx=ctx, cycles=cycles,
                arch_cycles=r["cycles"], tokens_s=Q.CLOCK[0] / cycles, clock_hz=Q.CLOCK[0],
                tile_um2=round(tile_um2), tiles=tiles, array_need_mm2=round(need_mm2, 1),
                array_avail_mm2=a["array_mm2"], fits=need_mm2 <= a["array_mm2"],
                unit_busy=r["unit_busy"], stalls=r["sequencer_stalls"])


def qwen_rows():
    rows = [qwen_eval(6144, 1, wires=False) | dict(design="qwen_as_built_rtl_no_wires"),
            qwen_eval(6144, 1024, wires=False) | dict(design="qwen_arch"),
            qwen_eval(6144, 1024) | dict(design="qwen_arch_plus_wires"),
            qwen_eval(6144, 1024, pruned=True) | dict(design="qwen_pruned_plus_wires")]
    for G in (3072, 4096, 4608, 5120, 5632, 6144):
        for pr in (False, True):
            rows.append(qwen_eval(G, 1024, pruned=pr) | dict(design=f"qwen_G{G}{'_pruned' if pr else ''}"))
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
GPU = dict(barrier_cycles_hw=200,           # ASSUMED dedicated hardware barrier network
           barrier_ns_grid=1770.0,           # measured: V100 cooperative-groups grid sync, 1 block/SM
                                             # (L. Zhang et al., "A Study of Single and Multi-device
                                             # Synchronization Methods in Nvidia GPUs", IPDPS 2020, Fig. 5)
           seq_gap_cycles=7,
           adapter_measured_Bpc=39.0, sustained_frac=1.0)


def qwen_hbm_rows():
    import arch_budget_qwen3 as Q
    clock = Q.clock_hz()
    hc = json.loads((ROOT / "results/arch/qwen3_budget.json").read_text())["hbm_comparator"]["8192"]["rom_format_int8"]
    t_hbm = hc["token_s"]                                        # 8.175 GB at 7.2 TB/s sustained (8 stacks)
    per_die_Bpc = hc["hbm_bytes_per_cycle"] / 2                  # 3,277 B/cycle per die
    boundaries = 217 + 2 * 36                                    # ME ops + two norm barriers per layer (one die)
    tp = Q.tp_exchanges(clock)["cycles"] / clock
    rows = []
    for tag, supply, barrier_s in (
            ("qwen_hbm_ideal", 1.0, 0.0),
            ("qwen_hbm_adapter_as_built", GPU["adapter_measured_Bpc"] / per_die_Bpc, GPU["seq_gap_cycles"] / clock),
            ("qwen_hbm_gpu_hw_barrier", 1.0, GPU["barrier_cycles_hw"] / clock),
            ("qwen_hbm_gpu_grid_sync_v100", 1.0, GPU["barrier_ns_grid"] * 1e-9)):
        T = t_hbm / supply + boundaries * barrier_s + tp
        rows.append(dict(design=tag, T_us=round(T * 1e6, 1), tokens_s=round(1 / T, 1), supply_frac=supply,
                         barrier_us_per_token=round(boundaries * barrier_s * 1e6, 1), boundaries=boundaries))
    return rows


def v41_hbm_rows():
    v = json.loads((ROOT / "results/arch/v41_hbm_switched.json").read_text())
    cfg = v["configs"][v["headline_config"]] if isinstance(v["configs"], dict) else None
    # the published comparator breakdown (docs: G=96, 1M): compute chain 111.7, weight sweep 37.4,
    # collective latency 125.9, bytes 1.5, hops 0.9, control 2.0 us (W9 handoff 8)
    base = dict(compute_chain=111.7, weight_sweep=37.4, collective_latency=125.9, collective_bytes=1.5,
                pipeline_hops=0.9, control=2.0)
    clock = 1.0339e9
    # dependent boundaries on the V4.1 critical path: the arch DAG's path nodes per token (priced below)
    arch, b = arch_graph(1048576)
    path = b.g.path(b.sink)
    # elementwise ('vector') ops fuse into a neighbouring kernel's prologue/epilogue; a matvec, scan, select,
    # Sinkhorn or reduction needs every SM's result before its consumer starts: a global barrier
    boundaries = sum(1 for n in path if b.g.nodes[n]["kind"] in ("matvec", "kvscan", "reduce", "select", "sinkhorn"))
    per_die_Bpc = 3.6e12 / clock
    rows = []
    for tag, supply, barrier_s in (
            ("v41_hbm_published", 1.0, 0.0),
            ("v41_hbm_adapter_as_built", GPU["adapter_measured_Bpc"] / per_die_Bpc, 0.0),
            ("v41_hbm_gpu_hw_barrier", 1.0, (GPU["barrier_cycles_hw"] - GPU["seq_gap_cycles"]) / clock),
            ("v41_hbm_gpu_grid_sync_v100", 1.0, GPU["barrier_ns_grid"] * 1e-9)):
        parts = dict(base, weight_sweep=base["weight_sweep"] / supply,
                     barrier=boundaries * barrier_s * 1e6)
        T = sum(parts.values())
        rows.append(dict(design=tag, T_us=round(T, 1), tokens_s=round(1e6 / T, 1), supply_frac=round(supply, 4),
                         boundaries=boundaries, breakdown_us={k: round(x, 1) for k, x in parts.items()}))
    return rows


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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ctx", type=int, default=1048576)
    ap.add_argument("--preset", action="append")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--qwen", action="store_true", help="the Qwen3-8B ROM die rows only")
    ap.add_argument("--hbm", action="store_true", help="the GPU-organised HBM comparators only")
    a = ap.parse_args(argv)
    if a.hbm:
        rows = qwen_hbm_rows() + v41_hbm_rows()
        for r in rows:
            print(f"{r['design']:28s} {r['tokens_s']:9.1f} tok/s  T {r['T_us']:9.1f} us  supply {r['supply_frac']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.hbm_gpu.v1", rows=rows, gpu=GPU),
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
        rows.append(r)
        print(f"{n:22s} T={r['T_us']:9.1f} us  {r['tokens_s']:8.1f} tok/s   (arch {r['arch_tokens_s']:.0f})"
              f"  strip {r['area']['rom_field_strip_used_mm2']}/{r['area']['rom_field_strip_avail_mm2']}"
              f"  hub {r['area']['hub_logic_mm2']}/{r['area']['hub_avail_mm2']}")
        print("   ", {k: v for k, v in list(r["breakdown_us"].items())[:6]})
        print("   top:", list(r["critical_path_by_node_us"].items())[:8])
    out = dict(schema="opentallas.uarch.v41_rom.v1", ctx=a.ctx, rows=rows)
    if a.sweep:
        out["sweep"] = sweep(a.ctx)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
