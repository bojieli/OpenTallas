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
                           bf16_stripe_macros=2048, collective_cycles=232, row_split="ksplit",
                           # W11 decisions (2026-09-29): indexer = 16 NK=4 score slices, 64 keys/cycle (beat-aligned
                           # with the reader; reader-bound); attention NL=4 tiles (32,768 products) + PWORDS=2
                           # loader; SU per the RTL layout rule (+14 cycles/layer) with its own VM ports (~6 mm2)
                           idx_macs=262144, att_macs=32768, su_layout_extra_cycles=14, su_vm_ports_mm2=6.0)
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


def power_ledger(d, g, clock, tokens_s, area, wire_j=WIRE_J_PER_BIT_MM):
    stage_of = {}
    stack_e = {}
    per_layer = {}
    occ_layer = {}
    field_mm = FLOORPLAN["cols"] * 25.628 + 20.0          # broadcast tree wire length (column runs + trunk)
    for name, nd in g.nodes.items():
        L = nd["layer"]
        if L is None or L < 0:
            continue
        e = 0.0
        k = nd["kind"]
        u = nd.get("_uarch")
        if u:
            macs = u["rows"] * u["K"]
            e += macs * E_MAC["fp4" if u["fmt"] == "fp4" else "fp8" if u["fmt"] == "fp8" else "bf16"]
            e += u["words"] * BYTES_PER_WORD[u["fmt"]] * E_ROM_B
            xbits = u["K"] * (16 if u["fmt"] == "bf16" else 8)
            e += xbits * field_mm * wire_j                              # x broadcast over the field
            e += u["K"] * 4 * E_SRAM_B                                  # x read out of the VM
            e += u["K"] * u["holding"] * E_DELIVER_B / 32               # x delivered into each holding element
            e += u["rows"] * u["ksplit"] * 32 * (field_mm / FLOORPLAN["cols"] / 2 + 10.0) * wire_j  # partial return
            e += u["rows"] * 4 * E_SRAM_B                               # result write into the VM
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
    stages = {}
    occ = {}
    for L, e in per_layer.items():
        st = int(L / lps)
        stages[st] = stages.get(st, 0.0) + e
        occ[st] = occ.get(st, 0.0) + occ_layer.get(L, 0.0)
    busiest = max(stages, key=stages.get)
    e_tok = stages[busiest]
    stack_tok = sum(v for L, v in stack_e.items() if int(L / lps) == busiest)
    logic_mm2 = area["rom_field_strip_used_mm2"] + area["hub_logic_mm2"]
    rom_mm2 = area["rom_macros"]
    sram_mm2 = area["vm_ports"]
    clock_w = CLOCK_J_MM2 * clock * (logic_mm2 + 0.15 * (rom_mm2 + sram_mm2))
    leak_w = logic_mm2 * LEAK["logic"] + rom_mm2 * LEAK["rom_array"] + sram_mm2 * LEAK["sram_array"]
    idle_w = 4 * HBM_IDLE_W_STACK
    static_w = clock_w + leak_w + idle_w
    sat_rate = 1.0 / max(occ.values())
    out = dict(busiest_stage=busiest, energy_per_token_uJ=round(e_tok * 1e6, 2),
               hbm_stack_energy_per_token_uJ=round(stack_tok * 1e6, 2),
               hbm_stack_w_saturated=round(stack_tok / max(occ.values()), 1),
               dynamic_w_single_user=round(e_tok * tokens_s, 1), dynamic_w_saturated=round(e_tok * sat_rate, 1),
               saturated_tokens_s_per_stage=round(sat_rate, 1),
               clock_w=round(clock_w, 1), leakage_w=round(leak_w, 1), hbm_idle_w=idle_w,
               total_w_single_user=round(static_w + e_tok * tokens_s, 1),
               total_w_saturated=round(static_w + e_tok * sat_rate, 1), cooling_limit_w=COOLING_LIMIT_W,
               fits_cooling_saturated=bool(static_w + e_tok * sat_rate <= COOLING_LIMIT_W),
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
    # integer banking (W12): a group-pair column holds its words in whole 4096-deep banks; 11 at G=6144,
    # 14 at G=5120 (tools/qwen_o4_rom_placement.py QWEN_O4_GROUPS); other G scale the column words
    banks = {6144: 11, 5120: 14}.get(G) or math.ceil(44480 * 6144 / G / 4096 * 1.04)
    macros_tile = 2 * banks
    # result-port groups = G / smallest split: 96 at G=6144 (S=64), 40 at G=5120 (S=128); their tiles sit in
    # the spine, and fewer of them return spine area to the array (W12)
    port_tiles = {6144: 24, 5120: 10}.get(G, 24)
    logic = a["logic_group_pruned_um2"] if pruned else a["logic_group_um2"]
    tile_um2 = macros_tile * a["macro_um2"] * a["macro_pack"] + 4 * (logic / a["util"]
                                                                     + a["kv_sram_group_um2"] * a["macro_pack"])
    need_mm2 = (tiles - port_tiles) * tile_um2 / 1e6          # port tiles sit in the spine (W5)
    avail = a["array_mm2"] + (a["port_tiles"] - port_tiles) * tile_um2 / 1e6  # spine area freed by fewer ports
    return dict(G=G, su_width=su_width, wires=wires, pruned=pruned, ctx=ctx, cycles=cycles,
                arch_cycles=r["cycles"], tokens_s=Q.CLOCK[0] / cycles, clock_hz=Q.CLOCK[0],
                tile_um2=round(tile_um2), tiles=tiles, array_need_mm2=round(need_mm2, 1),
                array_avail_mm2=round(avail, 1), fits=need_mm2 <= avail, banks_per_column=banks,
                port_tiles=port_tiles,
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


def v41_hbm_rows():
    """V4.1 HBM die token (G=96, 1M).  The published breakdown (W9 handoff 8) is additive: compute chain 111.7,
    weight sweep 37.4, collective latency 125.9, bytes 1.5, hops 0.9, control 2.0 us.  With the prefetching
    bulk copy the weight sweep streams under the dependent chain (T = max(sweep, chain + barriers)); the
    additive rows are kept, labelled no-prefetch.  OPEN: the chain was priced at die-pooled widths; the SM's
    per-op latency on 1/96-die row slices is not yet in it."""
    base = dict(compute_chain=111.7, weight_sweep=37.4, collective_latency=125.9, collective_bytes=1.5,
                pipeline_hops=0.9, control=2.0)
    clock = 1.0339e9
    arch, b = arch_graph(1048576)
    path = b.g.path(b.sink)
    boundaries = v41_boundaries(path, b.g.nodes)
    per_die_Bpc = 3.6e12 / clock
    bnd = hbm_gpu_design("v41")["barrier"]["boundary_cycles"]
    rows = []
    for tag, supply, barrier_s, prefetch in (
            ("v41_hbm_published", 1.0, 0.0, False),
            ("v41_hbm_gpu", 1.0, (bnd - GPU["seq_gap_cycles"]) / clock, True),
            ("v41_hbm_gpu_grid_sync_v100", 1.0, GPU["barrier_ns_grid"] * 1e-9, True),
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
                         boundaries=boundaries, form="prefetching bulk copy" if prefetch else "additive",
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
GPU_LOGIC_UTIL = 0.5          # std-cell placement density (W5 convention; replaced by the hardened macro)
GPU_MACRO_PACK = 1.31         # macro footprint / macro area (W5 tile calibration)

SM_ELEM = {
    # Qwen3-8B: INT8 weight codes, 128 B/clk of weights = 128 lanes; 16 columns = the DFlash b16 verify block
    # (design point block 5) and batch <= 16 without re-streaming weights
    "qwen": dict(subparts=4, int8_lanes=128, bf16_lanes=0, blockdot_lanes=0, cols=16, il=8, ingest_Bpc=128,
                 k_max=12288, x_bytes=2, simt_lanes=128, scratch_kb=64, stack_levels=5),
    # DeepSeek-V4.1: FP4 routed experts (8 block-dot lanes = 256 FP4 weights = 128 B/clk), FP8 dense at the same
    # 128 B/clk on 4 of them, BF16 matrices on 64 lanes; 16 columns cover MTP (m+1 = 7) and batch 16
    "v41": dict(subparts=4, int8_lanes=0, bf16_lanes=64, blockdot_lanes=8, cols=16, il=8, ingest_Bpc=128,
                k_max=5120, x_bytes=2, simt_lanes=128, scratch_kb=64, stack_levels=3),
}


def sm_area(e: dict, staging_kb: float):
    """SM element area (mm2) by resource; logic placed at GPU_LOGIC_UTIL, SRAM at GPU_MACRO_PACK."""
    u = GPU_UNIT_UM2
    c = e["cols"]
    lanes = e["int8_lanes"] + e["bf16_lanes"]
    logic = dict(
        mma_lanes=c * (e["int8_lanes"] * (u["lane"] + u["int8_decode"]) + e["bf16_lanes"] * u["lane"]),
        blockdot=c * e["blockdot_lanes"] * (u["blockdot"] + u["fp32_add"] + 8 * 32 * u["dff"]),
        # one fixed pairwise tree per column over the widest lane set, output-registered adders
        tree=c * (max(lanes, e["blockdot_lanes"]) - 1) * (u["fp32_add"] + 32 * u["dff"]),
        stack=c * e["stack_levels"] * (u["fp32_add"] + 2 * 34 * u["dff"]),
        row_scale=c * u["fp32_mul"],
        simt=e["simt_lanes"] * u["simt_lane"],
        x_operand_regs=2 * max(lanes * 16, e["blockdot_lanes"] * 264) * c * u["dff"],   # double-buffered x fragment
    )
    x_kb = e["k_max"] * c * e["x_bytes"] / 1024
    sram_kb = dict(x_store=x_kb, staging=staging_kb, scratch=e["scratch_kb"])
    macros = {k: math.ceil(v / 32) for k, v in sram_kb.items()}
    logic_mm2 = sum(logic.values()) / 1e6
    sram_mm2 = sum(macros.values()) * u["sram32k"] * GPU_MACRO_PACK / 1e6
    return dict(logic_um2={k: round(v) for k, v in logic.items()}, logic_mm2=round(logic_mm2, 3),
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
    w = lambda um: wire_cycles(um, clock, WIRE_PS_PER_UM_LOADED)  # noqa: E731
    arrive = w(leaf_um) + w(trunk_um) + levels + 1               # + the SM's local all-subpartitions-done flop
    release = w(leaf_um) + w(trunk_um) + levels
    return dict(arrive_cycles=arrive, release_cycles=release, round_trip_cycles=arrive + release,
                max_leaf_um=round(leaf_um, 1), max_trunk_um=round(trunk_um, 1), levels=levels, source=src)


GPU_MEASURED = dict(
    # RTL measurements that replace formula terms (rtl/gpu, results/rtl/gpu_sm_exact.json); None = formula
    qwen_drain_cycles=None, v41_drain_cycles=None, barrier_node_cycles=None,
)


def mma_drain_cycles(e: dict):
    """Last weight into the MMA -> row result written to SMEM, from the element's pipeline: decode 1,
    multiply 5, circulating add 5, then log2(lanes) tree levels and the stack levels at 5, row scale 5,
    output register 2.  Replaced by the RTL measurement when recorded."""
    lanes = max(e["int8_lanes"] + e["bf16_lanes"], e["blockdot_lanes"])
    front = 16 if e["blockdot_lanes"] and not e["int8_lanes"] else 11      # block-dot P0..P8 + add, or lane
    return front + 5 * math.ceil(math.log2(lanes)) + 5 * e["stack_levels"] + 5 + 2


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
    drain = GPU_MEASURED[f"{model}_drain_cycles"] or mma_drain_cycles(e)
    out = dict(model=model, clock_hz=clock, hbm_Bpc=round(r_hbm, 1), element=e, drain_cycles=drain)
    # ---- SM count: smallest multiple of the stack count within 0.5% of an unbounded array (Qwen token) ----
    rows = []
    n_choice = None
    if model == "qwen":
        bn = barrier_network(model, clock, 32)
        x_tail = math.ceil(H_X_TAIL_B / X_BCAST_BPC)
        boundary = bn["round_trip_cycles"] + x_tail
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
    bn = barrier_network(model, clock, n_sm)
    x_tail = math.ceil(H_X_TAIL_B / X_BCAST_BPC)
    out["barrier"] = dict(bn, x_broadcast_tail_cycles=x_tail,
                          boundary_cycles=bn["round_trip_cycles"] + x_tail,
                          measured_node_cycles=GPU_MEASURED["barrier_node_cycles"])
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
        staging_kb = math.ceil(in_flight_B / n_sm / 1024 / 32) * 32
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
        dq = hbm_gpu_design("qwen")
        for r in rows:
            print(f"{r['design']:30s} {r['tokens_s']:9.1f} tok/s  T {r['T_us']:9.1f} us  supply {r['supply_frac']}")
        if a.out:
            Path(a.out).parent.mkdir(parents=True, exist_ok=True)
            Path(a.out).write_text(json.dumps(dict(schema="opentallas.uarch.hbm_gpu.v2", rows=rows, gpu=GPU,
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
    if a.sweep:
        out["sweep"] = sweep(a.ctx)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
