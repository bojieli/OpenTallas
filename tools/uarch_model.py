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


def wire_cycles(um: float, clock_hz: float) -> int:
    """One-way cycles to cross `um` of registered wire (W1 rule: registers = ceil(L/seg) - 1, +1 cycle)."""
    period_ps = 1e12 / clock_hz
    seg = (period_ps - UNCERTAINTY_PS - WIRE_OVERHEAD_PS) / WIRE_PS_PER_UM
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
    elem_fill=55,                 # weight tile descriptor -> row group (W8: 3+1+RL+CL+3plg+1+3nlev+2 = 45-60)
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
                           bf16_stripe_macros=4096, collective_cycles=232)
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
    if d["mapping"] == "striped":
        n = d["macros"]
        if fmt == "bf16" and d.get("bf16_stripe_macros"):
            n = min(n, d["bf16_stripe_macros"])
        holding = min(n, words)
        t_read = math.ceil(words / n)
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
    t_x = K / d["vm_read_elems"]
    t_ret = rows / d["vm_write_elems"]
    issue_c = max(t_read, t_mac, t_x, t_ret)
    bind = max((("rom_read", t_read), ("mac", t_mac), ("vm_read_x", t_x), ("vm_write_ret", t_ret)),
               key=lambda kv: kv[1])[0]
    leaves = holding if d["return_leaf_elems"] is None else d["return_leaf_elems"]
    tree = math.ceil(math.log(max(2, leaves), d["return_fanin"]))
    wire = 2 * wire_cycles(d["bcast_um"][region], clock)
    depth_c = d["elem_fill"] + wire + tree
    return dict(key=key, fmt=fmt, K=K, rows=rows, words=words, holding=holding, region=region,
                t_read=t_read, t_mac=t_mac, t_x=t_x, t_ret=t_ret, issue=issue_c, bind=bind,
                depth=depth_c, wire=wire, tree=tree)


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
        indexer=d["idx_macs"] / 32 * UNIT["blockdot_um2"],
        attention=d["att_macs"] * UNIT["mac_bf16_um2"],
        su_lanes=d["su_lanes"] * UNIT["su_light_lane_um2"],
        sfu_lanes=d["sfu_lanes"] * UNIT["su_lane_um2"],
        vm_ports=(math.ceil(d["vm_read_elems"] * 32 / 256) + math.ceil(d["vm_write_elems"] * 32 / 256))
        * SRAM_256B_MACRO["um2"],
    )
    out = {k: v / 1e6 for k, v in out.items()}
    strip = out["blockdot_lanes"] + out["bf16_lanes"] + out["capture_regs"] + out["chunk_partials"]
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


def sweep(ctx: int):
    """Design-point search over the microarchitecture knobs that the evaluation shows binding."""
    rows = []
    base = PRESETS["proposal"]
    for vm in (16, 32, 64, 128, 256):
        for nb in (256, 1024, 4096, None):
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
    a = ap.parse_args(argv)
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
