#!/usr/bin/env python3
"""Top-down architecture budget of the Qwen3-8B decode core (docs/ARCH_SPEC_QWEN3.md).

    python3 tools/arch_budget_qwen3.py [--out results/arch/qwen3_budget.json]

Requirements first, then per-block specs: this model derives, from the model
graph alone, the per-token WORKLOAD (MACs by op class, bytes by storage level,
elementwise element-ops, reductions, the dependent-stage chain of a layer), the
per-resource ROOFLINE of the two Qwen3-8B designs

* ROM -- the two-reticle package (user decision 2026-09-28; O4 of
  results/arch/qwen3_8bit_design.json): two HC1-class N6 dies of 815 mm2 in
  one B200-class package, every layer split across both (tensor-parallel 2,
  73 UCIe exchanges a token on the chain), 8-bit weights (INT8, a BF16 scale
  per output channel) in ROM, 6,144 weight-lane groups a die (the most its
  half of the 8-bit ROM feeds: 12,288 groups = 196,608 BF16 MAC lanes in the
  pair), lane multiplier 5 in the area each die has left; users' KV in 8
  HBM3E stacks (4 a die, what each die's free edge holds);
* HBM -- the iso-area comparator: the same package (two reticles of logic,
  the same core, the same 8 stacks), the ROM's 8-bit weights and the KV
  streamed;

then a BUDGET (each non-binding resource gets a share of the token time) and,
from it, PER-BLOCK REQUIREMENTS: MAC lanes, ROM/HBM read width, KV banks and
bytes a cycle, stream-unit width, reduction-tree depth, the largest exposed
latency a dependent stage may have, buffers, issue rate, argmax.  The GAP table
holds each requirement against the RTL as built, priced by the RTL-calibrated
sequencer model (tools/hdc_timing.simulate, 32,191 model vs 32,196 RTL cycles
on the reduced vehicle) replaying the decode program at the shipped shapes.

Everything here is derived; the only inputs are the model's config.json shapes
(tools/hdc_timing.SHAPES), the reticle split of the analytical study, routed
ASAP7 areas and clocks, and the RTL-calibrated unit latencies.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dflash_step_timing as DST  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_timing as T  # noqa: E402

SCHEMA = "opentallas.arch-budget-qwen3.v1"
OUT = ROOT / "results/arch/qwen3_budget.json"
BASELINE = ROOT / "results/arch/qwen3_baseline_as_built.json"   # as built before the spec work (92f2c723)
MATVEC_PHYS = ROOT / "results/physical_abi3/asap7/hdc/ot_hdc_matvec/physical.json"
STREAM_PHYS = ROOT / "results/physical_abi3/asap7/hdc/ot_hdc_stream/physical.json"

Q = T.SHAPES["qwen3-8b"]
CTX_HEAD = 8192                   # user decision: the design target context
CONTEXTS = (8192, 2048)
KV_FORMATS = {"bf16": 2, "fp8": 1, "int4": 0.5}   # bytes per KV element
KV_FMT_SPEC = "fp8"               # the design point's KV format (a golden change: BF16 today)
CLOCK = [1.0e9]                   # set by evaluate()
W, IL = I.W_LANES, I.INTERLEAVE

# -- the two designs ---------------------------------------------------------------
# User decisions (2026-09-28): Qwen3-8B weights are 8-bit (INT8 weight-only, a BF16 scale per output channel), and
# the 8-bit weights do not fit one reticle (results/arch/qwen3_8bit_design.json: 64.2 mm2 short with no lane copy),
# so the ROM design is O4 of that record: TWO reticles in one package over UCIe, every layer split across both dies
# (tensor-parallel 2), 4 HBM3E stacks a die for the users' KV, each die's MAC groups the most its half of the ROM
# can feed at 8 bits (6,144).  The iso-area HBM comparator is the same two-reticle package with the same core.
FLOORPLAN = dict(die_mm2=815.0, node="N6", compute_mm2_8192_groups=146.7, interconnect_mm2=65.2, overhead_mm2=81.5,
                 source="opentallas.roofline.taalas_hc1_anchor on configs/models/qwen3-8b.json (the HC1-class "
                        "reticle split: compute share 18%, interconnect 8%, overhead 10% of 815 mm2); the compute "
                        "share scales with the MAC groups a die")
DIES = 2                          # reticles in the package
GROUPS_DIE = 6144                 # MAC groups a die: the most (a multiple of 512) the die's 8-bit ROM feeds
GROUPS_ROM = DIES * GROUPS_DIE    # 12,288: the tensor-parallel pair works as one engine of both dies' groups
LANES_ROM = GROUPS_ROM * W
LANES_DIE = GROUPS_DIE * W
WEIGHT_FORMAT = "int8_per_channel"   # INT8 weight-only, per-output-channel BF16 scales (user decision)
WEIGHT_BITS = 8
MAC_UM2 = 1071.8171875            # routed ot_hdc_matvec area / 64 lanes (ASAP7, not scaled to N6)
SU_LANE_UM2 = 42443.2             # routed ot_hdc_stream area per element/cycle (ASAP7)
SRAM_BITS_PER_MM2 = 24.07e6       # usable SRAM bits/mm2 (configs/hardware/technology.json)
# The HBM comparator's MAC array: the ROM package's lanes (the same core on both dies).
GROUPS_HBM = GROUPS_ROM
LANES_HBM = GROUPS_HBM * W
ISA_MAX_SPLIT_AS_BUILT = 1 << ((1 << 2) - 1)    # me_split is 2 bits: S <= 8
DIE_EDGES_MM = (26.0, 33.0)       # the reticle-class die's edges (the beachfront rule's 2 x (26 + 33) mm)
BEACHFRONT_USE, STACK_EDGE_MM = 0.6, 12.0     # 60% edge use of shipping parts, 12 mm of edge a stack


def stacks_per_die_by_beachfront(dies=DIES):
    """HBM3E stacks one die of a `dies`-die package carries: its free edge (the perimeter less the edge it shares
    with its neighbour, which carries the UCIe link) at 60% use over 12 mm a stack, the less favourable of the two
    abutments (short or long edge shared)."""
    per = 2 * sum(DIE_EDGES_MM)
    if dies == 1:
        return round(per * BEACHFRONT_USE / STACK_EDGE_MM)
    return min(math.floor((per - e) * BEACHFRONT_USE / STACK_EDGE_MM) for e in DIE_EDGES_MM)


STACKS_PER_DIE = stacks_per_die_by_beachfront()      # 4 (B200 also carries 4 a die, 8 a package)
HBM = dict(stacks=DIES * STACKS_PER_DIE, stacks_per_die=STACKS_PER_DIE, dies=DIES, stack_bytes_s=1.0e12,
           efficiency=0.90, phy_mm2_per_stack=10.0,
           basis="HBM3E 1.0 TB/s a stack (B200: 8 TB/s over 8 stacks), 0.90 sustained "
                 "(configs/hardware/technology.json efficiencies.hbm_bandwidth); the comparator is the ROM "
                 "package's silicon, two reticles, each carrying the stacks its free edge holds: 2 x (26 + 33) mm "
                 "less the edge shared with the other die, at 60% edge use and 12 mm a stack = 4 a die (B200: 4 a "
                 "die, 8 a package)")
ROM_KV_HBM = dict(stacks=DIES * STACKS_PER_DIE, stacks_per_die=STACKS_PER_DIE,
                  basis="each die's free edge at 60% use holds 4 stacks of 12 mm (the other die takes one edge); "
                        "all 8 carry KV (the ROM dies have no weight traffic), each die streaming its own KV heads "
                        "from its own 4 stacks")
LANE_COPY_UM2 = 528.08            # routed MAC-only lane copy (ot_hdc_lane_copy, 16 lanes 8,449.24 um2, closed 1.2 GHz)
SU_SPILL_MM2 = 12.8               # the vector stream unit beyond the compute share (estimated, 25,000 um2 a lane)
SPEC_SU_WIDTH = 1024              # the stream unit the spec sizes (requirements(): the one-pass softmax at 8k)
TECH_PATH = ROOT / "configs/hardware/technology.json"
MODEL_PATH = ROOT / "configs/models/qwen3-8b.json"
UCIE_PHY_MM2 = 10.0               # ASSUMED: one advanced-package UCIe module a die (~6.4 mm of the shared edge at
                                  # 5.27 Tb/s/mm, ~1.5 mm deep), carrying the 4.2 TB/s link of technology.json
REDUCE_ADD_CYCLES = 4             # the pipelined FP32 add of a partial sum received over the link
PARTIAL_BYTES = 4                 # the all-reduce adds FP32 partials (tools/hdc_golden.fold adds the dies' FP32 matvec
                                  # outputs in rank order); BF16 partials would be a golden and quality change
SCALE_MUL_CYCLES = 5              # the per-output-row scale multiply after the K sum (the INT8 contract): the qualified
                                  # rtl/proto/ot_fp32_mul_rne_pipe.sv, 5 register stages, one result a cycle
EMB_ROW_BYTES = Q["H"] + 2        # an INT8 embedding row and its BF16 scale, handed to the other die once a token


# -- the two-die split: which work runs on which die, and what crosses UCIe ----------------------------------------
def die_shape(s=Q):
    """One die's tensor-parallel slice of the model (tools/hdc_golden.Model.die_slices, Megatron): half the query and
    KV heads, FFN rows and vocabulary; the hidden size, the residual stream and the norms whole (replicated)."""
    return dict(s, NH=s["NH"] // DIES, KV=s["KV"] // DIES, FF=s["FF"] // DIES, V=s["V"] // DIES)


def die_split(s=Q):
    """Tensor-parallel 2 over the package: all 36 layers on BOTH dies, each die holding half of every layer.  The
    column-parallel matrices (QKV, gate/up, lm_head) split their output rows, the row-parallel ones (O, down)
    their reduction dimension; the FP32 partial sums of O and down are all-reduced over the link, the vocabulary
    halves' argmax candidates are exchanged once a token, and the die owning the emitted token's embedding row hands
    it to the other (docs/QWEN_TWO_RETICLE_RTL_CONTRACT.md)."""
    NH, KV, FF, V, L = (s[k] for k in ("NH", "KV", "FF", "V", "L"))

    def half(n):
        return (0, n // 2 - 1), (n // 2, n - 1)
    dies = []
    for d in range(DIES):
        dies.append(dict(die=d, layers=f"0-{L - 1} (all {L})", query_heads=list(half(NH)[d]),
                         kv_heads=list(half(KV)[d]), ffn_columns=list(half(FF)[d]), vocabulary_rows=list(half(V)[d]),
                         embedding="half the table a die by rows; the owning die hands the emitted token's INT8 row "
                                   "(and its scale) to the other once a token",
                         kv="its own KV heads' K and V, streamed from its own %d stacks" % STACKS_PER_DIE))
    return dict(kind="tensor-parallel 2 (TP-2: every layer split across both dies)", dies=dies,
                exchanges_per_token=2 * L + 1,
                exchanges=["after O (row-parallel): all-reduce of the H-element FP32 partial sum",
                           "after down (row-parallel): all-reduce of the H-element FP32 partial sum",
                           "after the lm_head halves: the argmax candidates of each half, once a token (priced as an "
                           "all-reduce exchange, an upper bound)",
                           "then the embedding-row handoff of the emitted token (hop + one INT8 row)"],
                replicated="RMSNorm, the residual adds, RoPE of the die's own heads, and the sampler run on both "
                           "dies on the full H-element vector after each all-reduce",
                why_not_a_layer_cut="a contiguous cut (layers 0-19 on die A, 20-35 on die B) runs each layer on one "
                                    "die's groups and streams each layer's KV from its die's 4 stacks, so the KV "
                                    "floor doubles and binds: results/arch/qwen3_8bit_design.json "
                                    "o4_contiguous_cut_scenario (layer_cut_alternative)")


def ucie_link():
    """The package's die-to-die link (configs/hardware/technology.json links.rom_package_ucie, the V4.1 array's
    link) and its energy (configs/hardware/power_scenarios.json die.link_j_per_bit.ucie)."""
    t = json.loads(TECH_PATH.read_text())["links"]["rom_package_ucie"]
    ps = json.loads((ROOT / "configs/hardware/power_scenarios.json").read_text())["die"]["link_j_per_bit"]["ucie"]
    return dict(hop_latency_s=t["hop_latency_s"]["value"], hop_latency_range_s=[t["hop_latency_s"]["range_low"],
                                                                              t["hop_latency_s"]["range_high"]],
                bytes_s_per_direction=t["bytes_s"]["value"], j_per_bit=ps["value"], phy_mm2_per_die=UCIE_PHY_MM2,
                source="configs/hardware/technology.json links.rom_package_ucie (hop_latency_s, bytes_s); "
                       "configs/hardware/power_scenarios.json die.link_j_per_bit.ucie")


def tp_exchanges(clock, slots=1, phase="target", hop_s=None):
    """The UCIe exchanges on one pass's dependency chain under TP-2 (every exchange is serial: the residual add needs
    the other die's partial and the next norm's sum of squares the whole residual).  target: 2 all-reduces a layer
    (after O and after down) of H FP32 partials a slot and the argmax gather of the vocabulary halves, each hop +
    transfer + the receive-side add; then the embedding-row handoff (hop + the INT8 rows).  draft: the fc output
    all-gather, 2 all-reduces in each drafter layer and the draft argmax gather, priced the same way, and the bonus
    token's embedding row.  The same rule as tools/qwen3_8bit_design.tp_exchanges."""
    lk = ucie_link()
    hop = (lk["hop_latency_s"] if hop_s is None else hop_s) * clock
    bpc = lk["bytes_s_per_direction"] / clock
    part = slots * Q["H"] * PARTIAL_BYTES
    per = hop + part / bpc + REDUCE_ADD_CYCLES
    if phase == "target":
        n, rows = 2 * Q["L"] + 1, slots
        nbytes = 2 * Q["L"] * part + 8 * slots + rows * EMB_ROW_BYTES
    else:
        n, rows = 2 * DST.DRAFTER_LAYERS + 2, 1
        nbytes = slots * DST.DFLASH_FC[0] // DIES * PARTIAL_BYTES + 2 * DST.DRAFTER_LAYERS * part + 8 * slots + \
            EMB_ROW_BYTES
    emb = hop + rows * EMB_ROW_BYTES / bpc
    return dict(exchanges=n, slots=slots, per_exchange_cycles=round(per, 2), exchange_cycles=math.ceil(n * per),
                embedding_handoff_cycles=round(emb, 2), cycles=math.ceil(n * per + emb),
                bytes_per_direction=nbytes, partial_bytes_per_slot=Q["H"] * PARTIAL_BYTES)


def ucie_exchange(clock, hop_s=None):
    """The autoregressive token's die-to-die traffic and its place on the chain (tp_exchanges at one slot)."""
    x = tp_exchanges(clock, hop_s=hop_s)
    lk = ucie_link()
    return dict(exchanges_per_token=x["exchanges"], bytes_per_exchange_per_direction=x["partial_bytes_per_slot"],
                bytes_per_token_per_direction=x["bytes_per_direction"],
                hop_latency_cycles=round((lk["hop_latency_s"] if hop_s is None else hop_s) * clock, 2),
                transfer_cycles=round(x["partial_bytes_per_slot"] / lk["bytes_s_per_direction"] * clock, 2),
                add_cycles=REDUCE_ADD_CYCLES, cycles_per_exchange=x["per_exchange_cycles"],
                exchange_cycles=x["exchange_cycles"], embedding_handoff_cycles=x["embedding_handoff_cycles"],
                cycles_per_token=x["cycles"], energy_j_per_token=x["bytes_per_direction"] * 2 * 8 * lk["j_per_bit"],
                partials="FP32 (the golden's rank-order fold of the dies' FP32 matvec outputs)",
                on_critical_path="yes: each exchange sits between a row-parallel matrix and the next stage "
                                 "(residual + RMSNorm), so all of its latency is on the token's chain")


def k_split_fc(groups=GROUPS_DIE):
    """The drafter fc's slice on one die at the golden's K-split (tools/hdc_golden.split_for) under the RTL's
    whole-tile rounds: at 6,144 groups the golden takes S = 4,096 where the RTL rule would take 1,024, and the model
    prices the golden's (the target's matrices agree)."""
    import hdc_golden as G
    n, k = DST.DFLASH_FC[0] // DIES, DST.DFLASH_FC[1]
    sg = G.split_for(n, k, groups)
    sr = split_rounds(n, k, groups)[0]
    tiles = -(-n // (W * IL))
    return dict(n=n, k=k, golden_split=sg, rtl_split=sr, rtl_cycles=mv_cycles(n, k, groups)[0],
                golden_split_cycles_rtl_tiling=-(-tiles // (groups // sg)) * (k // sg) * IL)


# -- ROM capacity at 8 bits (the tensor inventory, the HC1-referenced cell) ------------------------------------------
def rom_inventory(s=Q):
    """Every stored tensor of the target and the DFlash drafter: matrices (n rows x k), the embedding table (a
    lookup), and the 1-D norm weights; checked against the model config's parameter count."""
    L, H, HD, V = s["L"], s["H"], s["HD"], s["V"]
    per_layer, _ = matrices(s)
    target = [dict(name=f"layer.{k}", n=n, k=kk, count=L) for k, (n, kk) in per_layer.items()]
    target += [dict(name="lm_head", n=V, k=H, count=1), dict(name="embedding", n=V, k=H, count=1)]
    target_norms = L * (2 * H + 2 * HD) + H
    layer_elems = sum(n * k for n, k in per_layer.values())
    fc_n, fc_k = DST.DFLASH_FC
    drafter = [dict(name=f"drafter.layer.{k}", n=n, k=kk, count=DST.DRAFTER_LAYERS)
               for k, (n, kk) in per_layer.items()] + [dict(name="drafter.fc", n=fc_n, k=fc_k, count=1)]
    drafter_norms = DST.DRAFTER_PARAMS - DST.DRAFTER_LAYERS * layer_elems - fc_n * fc_k
    tot = sum(m["n"] * m["k"] * m["count"] for m in target) + target_norms
    assert tot == json.loads(MODEL_PATH.read_text())["total_parameters"], tot
    return dict(target=target, target_norms=target_norms, drafter=drafter, drafter_norms=drafter_norms,
                target_params=tot, drafter_params=DST.DRAFTER_PARAMS)


@functools.lru_cache(maxsize=None)
def rom_capacity():
    """ROM mm2 and bytes of the INT8 per-channel weights (+ BF16 scales, BF16 norms) at the repository's
    HC1-referenced density: src/opentallas/roofline.py rom_bits_per_mm2 / cim_cell_area_multiplier select cells a
    mm2, one select cell per <= 4-bit nibble (an 8-bit weight is 2 cells), a 16-bit scale or norm 4 cells."""
    sys.path.insert(0, str(ROOT / "src"))
    from opentallas.roofline import Technology
    tech = Technology.load(TECH_PATH)
    storage = tech.rom_bits_per_mm2(FLOORPLAN["node"]).value
    mult = tech.graded("rom", "cim_cell_area_multiplier").value
    cells_mm2 = storage / mult
    inv = rom_inventory()
    ecells = math.ceil(WEIGHT_BITS / 4)
    rows = {}
    for part, mats, norms in (("target", inv["target"], inv["target_norms"]),
                              ("drafter", inv["drafter"], inv["drafter_norms"])):
        for m in mats:
            key = m["name"] if m["name"] in ("embedding", "lm_head") else part
            d = rows.setdefault(key, dict(elements=0, scales=0, scale_bytes=0, cells=0, norms=0))
            d["elements"] += m["n"] * m["k"] * m["count"]
            d["scales"] += m["n"] * m["count"]
            d["scale_bytes"] += m["n"] * m["count"] * 2
            d["cells"] += m["n"] * m["k"] * m["count"] * ecells + m["n"] * m["count"] * 16 / 4
        rows[part]["norms"] = norms
        rows[part]["cells"] += norms * 16 / 4
    for v in rows.values():
        v["mm2"] = v["cells"] / cells_mm2
        v["bytes"] = v["elements"] + v["scale_bytes"] + 2 * v["norms"]
    return dict(format=WEIGHT_FORMAT, weight_bits=WEIGHT_BITS, select_cells_per_mm2=cells_mm2,
                storage_rom_bits_per_mm2=storage, cim_cell_area_multiplier=mult, rows=rows,
                target_mm2=sum(rows[k]["mm2"] for k in ("target", "lm_head", "embedding")),
                drafter_mm2=rows["drafter"]["mm2"],
                swept_scale_bytes=rows["target"]["scale_bytes"] + rows["lm_head"]["scale_bytes"],
                weight_bytes_per_mac=1 + (rows["target"]["scale_bytes"] + rows["lm_head"]["scale_bytes"]) /
                (sum(n * k for n, k in matrices()[0].values()) * Q["L"] + Q["V"] * Q["H"]),
                basis="INT8 weight-only, one BF16 scale an output channel (the embedding: one a token row); an "
                      "8-bit weight is 2 select cells, a scale or norm 4; select cells a mm2 = N6 storage ROM "
                      "bits a mm2 / cim_cell_area_multiplier (src/opentallas/roofline.py, technology.json)")


def rom_read_density():
    """The ROM read bandwidth a mm2 at 8 bits a parameter (opentallas.roofline.taalas_hc1_anchor) and the sustained
    efficiency (technology.json efficiencies.rom_read_bandwidth)."""
    sys.path.insert(0, str(ROOT / "src"))
    from opentallas.roofline import Technology, taalas_hc1_anchor
    from opentallas.schema import ModelProfile
    tech = Technology.load(TECH_PATH)
    a8 = taalas_hc1_anchor(tech, ModelProfile.load(MODEL_PATH), weight_bits_per_parameter=8.0).detail["budget"]
    return (a8["provenance"]["rom_read_bandwidth_density_bytes_s_mm2"]["value"],
            json.loads(TECH_PATH.read_text())["efficiencies"]["rom_read_bandwidth"]["value"])


def clock_hz():
    """Slowest routed Qwen3 token-path unit (matrix engine, stream unit)."""
    return min(json.loads(p.read_text())["place_and_route"]["metrics"]["fmax_hz"] for p in (MATVEC_PHYS, STREAM_PHYS))


# -- workload -----------------------------------------------------------------------
def matrices(s=Q):
    H, NH, KV, HD, FF, V = s["H"], s["NH"], s["KV"], s["HD"], s["FF"], s["V"]
    per_layer = {"qkv": ((NH + 2 * KV) * HD, H), "o": (H, NH * HD), "gate_up": (2 * FF, H), "down": (H, FF)}
    return per_layer, {"lm_head": (V, H)}


def workload(T_ctx, s=Q, kv_bytes_per_elem=2, weight_bits=WEIGHT_BITS):
    """Per-token work of one decode position with T_ctx positions of context."""
    L, H, NH, KV, HD, FF, V = (s[k] for k in ("L", "H", "NH", "KV", "HD", "FF", "V"))
    per_layer, head = matrices(s)
    macs = {k: L * n * k_ for k, (n, k_) in per_layer.items()}
    macs.update({k: n * k_ for k, (n, k_) in head.items()})
    macs["attn_scores"] = L * NH * HD * T_ctx
    macs["attn_pv"] = L * NH * HD * T_ctx
    weight_macs = sum(v for k, v in macs.items() if not k.startswith("attn"))
    kv_elems_read = 2 * L * KV * HD * T_ctx            # every K and V element once (GQA-shared)
    ew = {  # elementwise element-ops (one element through the stream datapath)
        "embedding_copy": H,
        "norm_scale": L * 2 * H + H,                    # input/post-attention norm + final norm
        "qk_norm": L * 2 * (NH + KV) * HD,               # sum of squares + scale
        "rope": L * (NH + KV) * HD,
        "kv_write": L * 2 * KV * HD,
        "softmax": L * 3 * NH * T_ctx,                   # max, exp(+sum), scale
        "silu_mul": L * FF,
        "residual": L * 2 * H,
        "rsqrt_recip": L * (2 + (NH + KV) + NH) + 1,
    }
    reductions = {  # (count per token, length)
        "sum_of_squares_H": (2 * L + 1, H),
        "qk_norm_HD": (L * (NH + KV), HD),
        "softmax_max_T": (L * NH, T_ctx),
        "softmax_sum_T": (L * NH, T_ctx),
        "argmax_V": (1, V),
    }
    return dict(
        context=T_ctx, macs=macs, weight_macs=weight_macs, attention_macs=macs["attn_scores"] + macs["attn_pv"],
        bytes=dict(weights_rom_format=weight_macs * weight_bits / 8, weights_bf16=2 * weight_macs,
                   weights_fp8=weight_macs, kv_read=kv_elems_read * kv_bytes_per_elem,
                   kv_write=2 * L * KV * HD * kv_bytes_per_elem,
                   kv_capacity=kv_elems_read * kv_bytes_per_elem),
        elementwise=ew, elementwise_total=sum(ew.values()), reductions=reductions)


# -- dependent-stage chain of one layer ---------------------------------------------------
# kind: 'mv' matrix-vector (a full reduction over K), 'attn' KV-sourced, 'red'
# reduction (its result needs every input), 'ew' elementwise (can chain into its
# consumer element by element), 'sfu' a few elements through a special function.
LAYER_STAGES = [
    ("attn_norm.rsqrt", "sfu", "RSQRT"), ("attn_norm.scale", "ew", "NONE"), ("qkv", "mv", None),
    ("qk_norm.sumsq", "red", "NONE"), ("qk_norm.rsqrt", "sfu", "RSQRT"), ("qk_norm.scale", "ew", "NONE"),
    ("rope", "ew", "NONE"), ("scores", "attn", None), ("softmax.max", "red", "NONE"),
    ("softmax.exp_sum", "red", "EXP"), ("softmax.recip", "sfu", "RECIP"), ("softmax.scale", "ew", "NONE"),
    ("pv", "attn", None), ("o", "mv", None), ("residual+sumsq", "red", "NONE"),
    ("ffn_norm.rsqrt", "sfu", "RSQRT"), ("ffn_norm.scale", "ew", "NONE"), ("gate_up", "mv", None),
    ("silu_mul", "ew", "SIGM"), ("down", "mv", None), ("residual+sumsq", "red", "NONE"),
]

# The spec's attention: the row max is taken on the matrix engine's result path
# as the scores emerge (a compare tree beside the argmax tree, 'mvred'), the
# stream unit makes ONE pass (exp and its sum), and the 1/Z scale moves after
# the weighted sum (32 x 128 elements instead of 32 x T; a change of the
# golden's rounding order, normalise-after-sum, as flash attention does).  The
# reciprocal then runs beside P.V, off the chain.
LAYER_STAGES_SPEC = [
    ("attn_norm.rsqrt", "sfu", "RSQRT"), ("attn_norm.scale", "ew", "NONE"), ("qkv", "mv", None),
    ("qk_norm.sumsq", "red", "NONE"), ("qk_norm.rsqrt", "sfu", "RSQRT"), ("qk_norm.scale", "ew", "NONE"),
    ("rope", "ew", "NONE"), ("scores", "attn", None), ("scores.max", "mvred", None),
    ("softmax.exp_sum", "red", "EXP"), ("pv", "attn", None), ("pv.scale", "ew", "NONE"),
    ("o", "mv", None), ("residual+sumsq", "red", "NONE"),
    ("ffn_norm.rsqrt", "sfu", "RSQRT"), ("ffn_norm.scale", "ew", "NONE"), ("gate_up", "mv", None),
    ("silu_mul", "ew", "SIGM"), ("down", "mv", None), ("residual+sumsq", "red", "NONE"),
]

AS_BUILT_LAT = dict(me_lat=T.K["me_lat"], me_tree=T.K["me_tree"], red_tail=T.K["red_tail"],
                    su={"NONE": 29, "EXP": 121, "RECIP": 75, "RSQRT": 90, "SIGM": 172}, xlane_level=6,
                    seq_gap=T.K["seq_gap"])


def split_rounds(n, k, groups, max_split=None):
    """(split, rounds, kc) of an n x k matrix under the engine's tiling rule
    (rtl/hdc/ot_hdc_matvec.sv): S = 2^split contiguous K chunks, floor(G/S)
    tiles a round, fewest cycles, the smaller split on a tie; max_split caps S
    (the ISA field)."""
    tiles = -(-n // (W * IL))
    best = None
    s = 1
    while s <= groups and (max_split is None or s <= max_split):
        if k % s == 0:
            rounds = -(-tiles // (groups // s))
            c = rounds * (k // s) * IL
            if best is None or c < best[0]:
                best = (c, s, rounds)
        s *= 2
    return best[1], best[2], k // best[1]


def mv_cycles(n, k, groups, max_split=None):
    """Engine cycles of an n x k matrix (and its split)."""
    s, rounds, kc = split_rounds(n, k, groups, max_split)
    return rounds * kc * IL, s


def tiling_eff(groups):
    """The token's weight sweep: ideal cycles over tiled cycles at this many groups."""
    per_layer, head = matrices()
    mats = [*per_layer.values()] * Q["L"] + [*head.values()]
    return sum(n * k for n, k in mats) / (W * groups) / sum(mv_cycles(n, k, groups)[0] for n, k in mats)


def attn_cycles(T_ctx, groups, s=Q, mapping="as_built", golden_pv=False):
    """(scores, pv) engine cycles per layer.  as_built: tools/hdc_program.py's
    KV ops (scores: positions on lanes, IL heads per op, k = head_dim in order;
    P.V: head_dim on lanes, k = positions in order), each op on the groups its
    tiles cover.  ksplit: the same ops with K cut over every free group (scores
    over head_dim, P.V over positions), the chunk sums added by the split tree."""
    NH, HD = s["NH"], s["HD"]
    batches = -(-NH // IL)
    ptiles = -(-T_ctx // W)
    if mapping == "as_built":
        sc = batches * (-(-ptiles // groups)) * HD * IL
        pv = batches * (-(-(HD // W) // groups)) * T_ctx * IL
        return sc, pv
    ssc = 1
    while ssc * 2 <= HD and ptiles * ssc * 2 <= groups:
        ssc *= 2
    sc = batches * (-(-ptiles * ssc // groups)) * (HD // ssc) * IL
    spv = max(1, groups // (HD // W))
    if golden_pv:                   # the golden's attn_splits: a power of two (512, not 768, at 6,144 groups)
        spv = 1 << (spv.bit_length() - 1)
    pv = batches * (-(-T_ctx // spv)) * IL
    return sc, pv, ssc, spv


def chain(T_ctx, groups, su_width, lat, mapping, chained=True, seq_gap=None, stages=None, shape=None,
          golden_pv=False, scale_cycles=0):
    """Cycles of one layer as the sum over its dependent stages of (throughput +
    exposed latency).  An elementwise stage that chains into its consumer
    contributes only its pipeline depth; a reduction or matrix stage cannot
    produce before its last input, so its throughput and its tail are exposed.
    Returns per-stage rows and totals by component."""
    s = Q if shape is None else shape
    H, NH, KV, HD, FF = s["H"], s["NH"], s["KV"], s["HD"], s["FF"]
    per_layer, _ = matrices(s)
    lv = max(0, math.ceil(math.log2(groups)))
    me_res = lat["me_lat"] + lat["me_tree"] * lv
    xl = lat["xlane_level"] * max(0, math.ceil(math.log2(su_width))) if su_width > 1 else 0
    att = attn_cycles(T_ctx, groups, s, mapping, golden_pv)
    elems = {"attn_norm.scale": H, "qk_norm.sumsq": (NH + KV) * HD, "qk_norm.scale": (NH + KV) * HD,
             "rope": (NH + KV) * HD, "softmax.max": NH * T_ctx, "softmax.exp_sum": NH * T_ctx,
             "softmax.scale": NH * T_ctx, "residual+sumsq": H, "ffn_norm.scale": H, "silu_mul": FF,
             "attn_norm.rsqrt": 1, "qk_norm.rsqrt": NH + KV, "softmax.recip": NH, "ffn_norm.rsqrt": 1,
             "pv.scale": NH * HD}
    rows = []
    tot = dict(weights=0, attention=0, elementwise=0, latency=0, control=0)
    for name, kind, cls in (stages or LAYER_STAGES):
        if kind == "mvred":             # a compare tree over the result lanes: 2 cycles a level
            thr, ex, comp = 0, 2 * max(1, math.ceil(math.log2(groups * W))), "elementwise"
        elif kind == "mv":
            thr, _ = mv_cycles(*per_layer[name], groups)
            ex = me_res + scale_cycles          # the INT8 per-row scale multiply after the K sum
            comp = "weights"
        elif kind == "attn":
            thr = att[0] if name == "scores" else att[1]
            # INT8_WEIGHT inserts the post-tree FP32 multiplier on KV-sourced
            # matvecs too. Its operand is one, but its latency is still exposed.
            ex = me_res + scale_cycles
            comp = "attention"
        else:
            n = elems[name]
            thr = -(-n // su_width)
            ex = lat["su"][cls] + (lat["red_tail"] + xl if kind == "red" else 0)
            comp = "elementwise"
            if kind == "ew" and chained:
                thr = 0                # hidden under the consumer's loop
        g = lat["seq_gap"] if seq_gap is None else seq_gap
        rows.append(dict(stage=name, kind=kind, throughput=thr, exposed_latency=ex))
        tot[comp] += thr
        tot["latency"] += ex
        tot["control"] += g
    return rows, tot


def roofline_rom(wl, clock, groups=GROUPS_ROM, su_width=SPEC_SU_WIDTH, kv_fmt=KV_FMT_SPEC):
    lanes = groups * W
    bw = rom_kv_bw()
    r = {"weights_mac": wl["weight_macs"] / lanes, "attention_mac": wl["attention_macs"] / lanes,
         "kv_hbm_read": kv_bytes(wl, kv_fmt) / bw * clock, "elementwise": wl["elementwise_total"] / su_width}
    return {k: dict(cycles=round(v), us=round(v / clock * 1e6, 3)) for k, v in r.items()}


MATCHED_FMT = "rom_format_int8"   # the comparator at the ROM's own weight format (INT8 + per-channel BF16 scales)
HBM_BYTE_FORMATS = ("bf16", "fp8", MATCHED_FMT)


def hbm_weight_bytes_per_mac(fmt):
    return {"bf16": 2.0, "fp8": 1.0, MATCHED_FMT: rom_capacity()["weight_bytes_per_mac"]}[fmt]


def hbm_design(wl, clock, fmt, kv_fmt=KV_FMT_SPEC):
    """The iso-area HBM comparator (the two-reticle package, 8 stacks): weights (fmt) and KV (kv_fmt) streamed."""
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    wbytes = wl["weight_macs"] * hbm_weight_bytes_per_mac(fmt)
    kvb = kv_bytes(wl, kv_fmt)
    t = (wbytes + kvb) / bw
    mac_rate = wl["weight_macs"] / t
    return dict(weight_format=fmt, kv_format=kv_fmt, bytes_per_token=wbytes + kvb, sustained_bytes_s=bw,
                token_s=t, tokens_s=round(1 / t, 1), mac_rate_needed=mac_rate,
                lanes_needed_at_clock=math.ceil(mac_rate / clock), hbm_bytes_per_cycle=round(bw / clock))


# -- the ROM reticle with its KV in HBM --------------------------------------------------
def rom_kv_bw():
    return ROM_KV_HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]


def kv_bytes(wl, fmt):
    return wl["bytes"]["kv_read"] * KV_FORMATS[fmt] / 2


def area_ledger():
    """One die of the two-reticle package (both dies are alike): the compute share of its 6,144 groups, the
    floorplan's interconnect and overhead, 4 HBM3E PHYs, the UCIe PHY, the KV ring, the stream unit's spill beyond
    the compute share, half of the target's 8-bit ROM (every layer is split, so every tensor is halved), half of the
    8-bit drafter's ROM, and MAC lane copies (the lane multiplier m) in what is left, at the routed MAC-only copy
    area."""
    cap = rom_capacity()
    die = FLOORPLAN["die_mm2"]
    compute = FLOORPLAN["compute_mm2_8192_groups"] * GROUPS_DIE / 8192
    inter, over = FLOORPLAN["interconnect_mm2"], FLOORPLAN["overhead_mm2"]
    phy = STACKS_PER_DIE * HBM["phy_mm2_per_stack"]
    buf_bytes = kv_prefetch_buffer_bytes()
    buf = round(buf_bytes * 8 / SRAM_BITS_PER_MM2, 1)
    rom = cap["target_mm2"] / DIES
    drafter = cap["drafter_mm2"] / DIES
    fixed = compute + inter + over + phy + UCIE_PHY_MM2 + buf + SU_SPILL_MM2
    rest = die - fixed - rom - drafter
    copy_mm2 = LANES_DIE * LANE_COPY_UM2 * 1e-6
    copies = max(0, int(rest // copy_mm2))
    rd, eff = rom_read_density()
    swept = (cap["rows"]["target"]["mm2"] + cap["rows"]["lm_head"]["mm2"]) / DIES
    need = LANES_DIE * WEIGHT_BITS / 8
    return dict(die_mm2=die, dies=DIES, groups_per_die=GROUPS_DIE, lanes_per_die=LANES_DIE,
                compute_mm2=round(compute, 2), interconnect_mm2=inter, overhead_mm2=over,
                hbm_phy_mm2=phy, ucie_phy_mm2=UCIE_PHY_MM2, kv_prefetch_buffer_mm2=buf,
                kv_prefetch_buffer_bytes=buf_bytes, target_rom_mm2=round(rom, 2), drafter_rom_mm2=round(drafter, 2),
                stream_unit_spill_mm2=SU_SPILL_MM2, lane_copy_mm2=round(copy_mm2, 2), lane_copies_added=copies,
                lane_multiplier_m=1 + copies, slack_mm2=round(rest - copies * copy_mm2, 2), fits=rest >= 0,
                package=dict(dies=DIES, logic_silicon_mm2=DIES * die, hbm_stacks=DIES * STACKS_PER_DIE,
                             target_rom_mm2=round(cap["target_mm2"], 2), drafter_rom_mm2=round(cap["drafter_mm2"], 2),
                             rom_mask_sets=DIES,
                             interposer="CoWoS-L-class two-reticle interposer (~3.3 reticles, the B200 class)"),
                rom_read=dict(groups_per_die=GROUPS_DIE, required_bytes_per_cycle_per_die=need,
                              swept_rom_mm2_per_die=round(swept, 2), read_density_bytes_s_per_mm2=rd,
                              efficiency=eff, available_bytes_s_per_die=swept * rd * eff,
                              required_bytes_s_per_die=need * CLOCK[0],
                              headroom=round(swept * rd * eff / (need * CLOCK[0]), 3),
                              next_step_groups=GROUPS_DIE + 512,
                              next_step_headroom=round(swept * rd * eff / ((GROUPS_DIE + 512) * W * CLOCK[0]), 3),
                              basis="one 8-bit weight a lane a cycle from the die's swept ROM (its half of the "
                                    "layers' and the lm_head's weights; the embedding is a lookup); available = "
                                    "swept mm2 x the 8-bit read density (taalas_hc1_anchor at 8 bits a parameter) "
                                    "x rom_read_bandwidth efficiency; groups a die in steps of 512 (the tiling "
                                    "rule's power-of-two splits)"),
                beachfront_mm_free=round(min((2 * sum(DIE_EDGES_MM) - e) for e in DIE_EDGES_MM) * BEACHFRONT_USE, 1),
                stacks_per_die_by_beachfront=STACKS_PER_DIE,
                stacks_note="each die's free edge (the perimeter less the edge it shares with the other die) at "
                            "60% use and 12 mm a stack: 4 a die, 8 a package, as on B200",
                lane_copy_basis="routed ot_hdc_lane_copy (16 lanes: the exact BF16 multiplier, the circulating "
                                "FP32 adder and its interleave registers, sharing the group's weight word; the "
                                "split tree, result port and argmax shared): 8,449 um2, closed at 1.2 GHz "
                                "(results/physical_abi3/asap7/hdc/ot_hdc_lane_copy/physical.json)")


T_RFC_S = 350e-9                  # HBM3E all-bank refresh (the controller rules, section 12)


def kv_prefetch_buffer_bytes(ctx=CTX_HEAD, fmt=KV_FMT_SPEC):
    """A RING, on each die, of one layer of KV at the head context plus the package's refresh cover (bandwidth x
    tRFC) -- the O4 record's sizing (results/arch/qwen3_8bit_design.json ledger kv_ring_mm2), twice what the die's
    own KV heads need, kept so both records price the same die; a die's half would free 3.0 mm2 a die.  The stream runs continuously (it binds
    the token) and the engine drains a layer's KV in its attention burst, so
    the peak occupancy is the layer being consumed plus what lands while a
    channel refreshes.  (Two layers, double-buffered, was the first sizing:
    the utilisation gate found it half used -- qwen3_utilization.json.)"""
    return kv_bytes(workload(ctx), fmt) / Q["L"] + rom_kv_bw() * T_RFC_S


def rom_token(out, ctx, fmt, slots=1, users=1, m=1, drafter=False):
    """Cycles of one step on the ROM reticle: the dependency chain's latency
    (shared by every slot and user) plus unit work, against the KV stream.
    Slots (speculative positions of ONE user) share the KV reads and the
    weight words; users share weight words only.  Lane copies m divide the
    weight and attention MAC work of positions that share their operand word
    (slots: weights and KV; users: weights)."""
    comp = out["dependency_chain"][f"{ctx}/spec"]["components"]
    lat = comp["latency"] + comp["control"] + comp.get("ucie", 0)
    Wc, A, E = comp["weights"], comp["attention"], comp["elementwise"]
    n = slots * users
    compute = lat + math.ceil(n / m) * Wc + (math.ceil(slots / m) * users) * A + n * E
    kvb = users * kv_bytes(out["workload"][str(ctx)], fmt) * ((1 + DRAFTER_LAYERS / Q["L"]) if drafter else 1)
    kv = kvb / rom_kv_bw() * CLOCK[0]
    return max(compute, kv), compute, kv


BUDGET_SHARES = dict(attention=0.15, elementwise=0.10, latency=0.30, control=0.03)


def budget(out, clock):
    """Target per context and KV format = max(the weight sweep over 55% of the
    token, the KV stream over 95% of it); the non-weight shares of that target
    are the blocks' budgets.  The spec's design point: 8k, FP8 KV."""
    per_layer, head = matrices()
    wl = out["workload"][str(CTX_HEAD)]
    w_cyc = Q["L"] * sum(mv_cycles(n, k, GROUPS_ROM)[0] for n, k in per_layer.values()) + \
        sum(mv_cycles(n, k, GROUPS_ROM)[0] for n, k in head.values())
    ideal = wl["weight_macs"] / LANES_ROM
    targets = {}
    for ctx in CONTEXTS:
        for fmt in KV_FORMATS:
            kvc = kv_bytes(out["workload"][str(ctx)], fmt) / rom_kv_bw() * clock
            tgt = max(ideal / 0.55, kvc / 0.95)
            targets[f"{ctx}/{fmt}"] = dict(context=ctx, kv_format=fmt, kv_stream_cycles=round(kvc),
                                           target_cycles=round(tgt), target_tokens_s=round(clock / tgt, 1),
                                           binding="kv_stream" if kvc / 0.95 > ideal / 0.55 else "weights")
    head_t = targets[f"{CTX_HEAD}/{KV_FMT_SPEC}"]
    target = head_t["target_cycles"]
    alloc = {k: round(v * target) for k, v in BUDGET_SHARES.items()}
    alloc["weights"] = round(ideal)
    return dict(context=CTX_HEAD, kv_format=KV_FMT_SPEC, weight_sweep_ideal_cycles=round(ideal),
                weight_sweep_tiled_cycles=w_cyc, weight_tiling_efficiency=round(ideal / w_cyc, 4),
                target_cycles=target, target_tokens_s=head_t["target_tokens_s"],
                ceiling_tokens_s=round(clock / ideal, 1), binding=head_t["binding"],
                shares=dict(BUDGET_SHARES, weights=round(ideal / target, 4)), cycles=alloc, targets=targets)


def requirements(out, clock):
    """Per-block requirements at the design point (8k, FP8 KV, batch 1)."""
    bud = out["budget"]
    L, NH, HD, KV = Q["L"], Q["NH"], Q["HD"], Q["KV"]
    cyc = bud["cycles"]
    ctx = CTX_HEAD
    wl = out["workload"][str(ctx)]
    stages = len(LAYER_STAGES_SPEC)
    attn_lanes = wl["attention_macs"] / cyc["attention"]
    su_w = 1
    while su_w < 1 << 14 and L * chain(ctx, GROUPS_ROM, su_w, dict(AS_BUILT_LAT, seq_gap=1), "ksplit", True,
                                        stages=LAYER_STAGES_SPEC)[1]["elementwise"] > cyc["elementwise"]:
        su_w *= 2
    lat_stage = cyc["latency"] / (L * stages)
    kvb = kv_bytes(wl, KV_FMT_SPEC)
    ledger = out["area"]
    return dict(
        mac_lanes=dict(requirement=LANES_ROM, per_die=LANES_DIE,
                       basis=f"{GROUPS_DIE:,} groups of 16 a die on {DIES} dies: the most each die's half of the "
                             f"8-bit ROM can feed (area.rom_read: headroom {ledger['rom_read']['headroom']}; "
                             f"{ledger['rom_read']['next_step_groups']:,} groups a die would be "
                             f"{ledger['rom_read']['next_step_headroom']})"),
        lane_multiplier=dict(requirement=ledger["lane_multiplier_m"],
                             basis="MAC-only lane copies in the area each die has left after its ROM (area ledger); "
                                   "they serve speculative slots and batched users"),
        weight_tiling_efficiency=dict(requirement=">= 0.90 of the ideal sweep (split/tile quantisation)"),
        rom_read_bytes_per_cycle=dict(requirement=round(LANES_ROM * WEIGHT_BITS / 8),
                                      per_die=round(LANES_DIE * WEIGHT_BITS / 8),
                                      basis="one 8-bit weight per lane per cycle; lane copies share the word"),
        ucie=dict(exchanges_per_token=out["ucie"]["exchange"]["exchanges_per_token"],
                  bytes_per_exchange_per_direction=out["ucie"]["exchange"]["bytes_per_exchange_per_direction"],
                  cycles_per_token=out["ucie"]["exchange"]["cycles_per_token"],
                  requirement="one FP32 H-vector each way per exchange (the golden's rank-order fold), latency on "
                              "the chain, plus the emitted token's embedding row once a token: hop <= 10 ns "
                              "(technology.json links.rom_package_ucie), the received partial added in the "
                              "pipelined FP32 adder; credit-controlled so a stalled receiver never drops a flit"),
        attention_lanes_min=dict(requirement=math.ceil(attn_lanes),
                                 basis=f"{wl['attention_macs']:.3e} MACs in {cyc['attention']} cycles"),
        kv_hbm=dict(stacks=ROM_KV_HBM["stacks"], stacks_per_die=STACKS_PER_DIE, format=KV_FMT_SPEC,
                    bytes_per_token=kvb,
                    sustained_bytes_s=rom_kv_bw(), stream_cycles=round(kvb / rom_kv_bw() * clock),
                    efficiency_min="0.90 of raw peak with refresh on (REFab measured 0.904 / 0.910)",
                    controller_queue_beats_per_pseudo_channel_min=512,
                    prefetch="layer l+1's KV (positions < t) streams while layer l computes; the token's own K/V "
                             "row is kept on die (tail buffer) and written back behind the stream",
                    prefetch_buffer_bytes=ledger["kv_prefetch_buffer_bytes"],
                    streamer="rtl/hdc/kv/ot_hdc_kv_stream.sv extended to the K-split attention word order"),
        stream_unit_elements_per_cycle=dict(requirement=su_w,
                                            basis=f"the spec chain's exposed elementwise cycles at 8k within "
                                                  f"{cyc['elementwise']}"),
        reduction_tree=dict(requirement=f"lane partials + a {int(math.log2(su_w))}-level cross-lane pairwise tree"),
        exposed_latency_per_dependent_stage_max=dict(
            requirement=round(lat_stage), stages_per_layer=stages,
            basis=f"{cyc['latency']} cycles over {L} layers x {stages} dependent stages"),
        instruction_issue=dict(requirement=f"<= {cyc['control']} control cycles a token exposed",
                               per_instruction_max=round(cyc["control"] / 4540, 2)),
        argmax=dict(requirement="streaming compare tree over each result word (as built)"),
        vector_buffer=dict(requirement_elements=max(2 * Q["FF"], NH * ctx),
                           basis="score/probability rows (NH x T at 8k) and gate/up outputs"))


def capped_layout(groups, max_split, shape=None):
    """tools/hdc_timing.ShapeLayout with every matrix's split capped (the ISA's
    me_split field) and tiled by the RTL's floor(G/S) rule."""
    lay = T.ShapeLayout(Q if shape is None else shape, groups)
    for key, m in lay.mat.items():
        s, rounds, kc = split_rounds(m["n"], m["k"] * m["split"], groups, max_split)
        m.update(k=kc, tiles=rounds, split=s)
    return lay


def layer_chain(prog, iss, d, T_ctx, groups, layer=None):
    """One decoder layer of the replayed program (the middle one), cut at the
    matrix engine's weight-op issues: each stage's span in cycles, the engine's
    busy cycles in it (the weight sweep, or the attention passes), and the rest,
    the exposed chain (stream-unit work and latency not hidden under the engine)."""
    me = [i for i, f in enumerate(prog) if f.get("unit") == I.UNIT_ME]
    wt = [i for i in me if not prog[i].get("me_wsrc") and not prog[i].get("me_amax")]
    layer = Q["L"] // 2 if layer is None else layer
    q0, o, gu, dn, q1 = (wt[4 * layer + j] for j in range(5))

    def busy(lo, hi):
        tot = 0
        for i in me:
            if lo <= i < hi:
                f = {n: prog[i].get(n, 0) for n, _ in I.FIELDS}
                rr, kk = T.me_loop(f, d, T_ctx - 1, groups)
                tot += rr * kk * IL
        return tot
    att0 = next(i for i in me if q0 < i and prog[i].get("me_wsrc"))
    cuts = (("QKV projection, then q/k norm, RoPE", q0, att0),
            ("attention: scores, softmax, P·V, 1/Z", att0, o),
            ("O projection, residual, FFN norm", o, gu),
            ("gate/up projection, fused SiLU·up", gu, dn),
            ("down projection, residual, next norm", dn, q1))
    rows = []
    for name, lo, hi in cuts:
        span = iss[hi] - iss[lo]
        b = busy(lo, hi)
        rows.append(dict(stage=name, cycles=span, engine_busy=b, exposed=span - b))
    return dict(layer=layer, cycles=iss[q1] - iss[q0], stages=rows)


def as_built(T_ctx, groups=GROUPS_DIE, su_width=SPEC_SU_WIDTH, max_split=None, lv=None, ucie=True, shape="die"):
    """The calibrated sequencer model replaying the decode program the core runs
    AT THIS COMMIT (tools/hdc_program.build_program), with the RTL's parameters
    set to the spec's: by default ONE die of the TP-2 package -- its slice of
    every layer (die_shape: half the heads, FFN rows and vocabulary) on its
    6,144 groups, a stream unit of SPEC_SU_WIDTH lanes whose reducer has LV =
    log2(max segment vectors) time levels, KV on core (the KV stream is priced
    separately).  cycles = the replay with the INT8 post-tree stage on every
    exposed ME result, including KV-sourced attention, plus the token's serial
    UCIe exchanges (tp_exchanges)
    when ucie.  shape=None replays the whole model (a one-die program).  The
    pre-work figures (7,680 groups, split <= 8, a 1-wide stream unit) are
    frozen in BASELINE."""
    import collections
    import hdc_program as P
    if lv is None:
        lv = max(1, math.ceil(math.log2(max(T_ctx, Q["H"]) / su_width))) if su_width > 1 else 0
    sw0 = I.SU_WIDTH
    I.SU_WIDTH = su_width            # the program's chase thresholds count vectors of this width
    try:
        shp = die_shape() if shape == "die" else shape
        lay = capped_layout(groups, max_split, shp)
        prog = P.build_program(lay)
    finally:
        I.SU_WIDTH = sw0
    dyn = dict(H=Q["H"], half=Q["HD"] // 2, HD=Q["HD"])
    tr = []
    k = dict(T.K, red_lv=lv)
    iss, cyc = T.simulate(prog, T_ctx - 1, groups=groups, dyn_shape=dyn, su_width=su_width, trace=tr, k=k)
    d = T.dyn_values(T_ctx - 1, groups=groups, **dyn)
    busy = collections.Counter()
    stall = collections.Counter()
    for f, (why, g) in zip(prog, tr):
        f = {n: f.get(n, 0) for n, _ in I.FIELDS}
        if f["unit"] == I.UNIT_ME:
            c = "attn_scores" if f["me_wsrc"] and f["me_d_tiles"] else "attn_pv" if f["me_wsrc"] else \
                "lm_head" if f["me_amax"] else "weights"
            rr, kk = T.me_loop(f, d, T_ctx - 1, groups)
            busy[c] += rr * kk * IL
        elif f["unit"] == I.UNIT_SU:
            busy["stream"] += T.su_vectors(f, d, su_width)
        stall[why] += g
    n = sum(1 for f in prog if f.get("unit") != I.UNIT_END)
    xc = tp_exchanges(CLOCK[0])["cycles"] if ucie else 0
    # Replay the uniform RTL post-tree pipeline. Head-batch instructions can
    # overlap, so charging every ME instruction separately would overcount.
    k_scaled = dict(k, me_lat=k["me_lat"] + SCALE_MUL_CYCLES)
    _, scaled_cyc = T.simulate(prog, T_ctx - 1, groups=groups, dyn_shape=dyn,
                               su_width=su_width, k=k_scaled)
    sc = scaled_cyc - cyc
    return dict(context=T_ctx, groups=groups, su_width=su_width, reducer_time_levels=lv, max_split=max_split,
                shape="one die's TP-2 slice" if shape == "die" else "whole model", instructions=n,
                sequencer_cycles=cyc, scale_multiply_cycles=sc, ucie_exchange_cycles=xc, cycles=cyc + sc + xc,
                layer_chain=layer_chain(prog, iss, d, T_ctx, groups),
                unit_busy=dict(busy), sequencer_stalls={k: v for k, v in stall.items() if k != "issue"},
                seq_gap_total=n * T.K["seq_gap"])


def core():
    """The package's workload, area, chains, budget, requirements and per-token steps: everything the DFlash step
    model (tools/dflash_step_timing.py) prices on, and nothing that reads its record."""
    clock = clock_hz()
    CLOCK[0] = clock
    out = dict(schema=SCHEMA, tool="tools/arch_budget_qwen3.py", model="Qwen3-8B", shape=Q, clock_hz=clock,
               clock_basis="slowest routed Qwen3 token-path unit (ot_hdc_matvec, ot_hdc_stream; ASAP7 TT)",
               design_point=dict(context=CTX_HEAD, kv_format=KV_FMT_SPEC, batch=1,
                                 decision="user: 8k is the target context; users' KV lives in HBM beside the ROM "
                                          "dies; 8-bit weights on a two-reticle package"),
               floorplan=FLOORPLAN, rom_design=dict(groups=GROUPS_ROM, lanes=LANES_ROM, dies=DIES,
                                                    groups_per_die=GROUPS_DIE, lanes_per_die=LANES_DIE,
                                                    mac_um2_asap7=MAC_UM2, kv_hbm=ROM_KV_HBM),
               hbm_design=dict(HBM, groups=GROUPS_HBM, lanes=LANES_HBM))
    out["workload"] = {str(t): workload(t) for t in CONTEXTS}
    out["package"] = dict(dies=DIES, groups_per_die=GROUPS_DIE, lanes_per_die=LANES_DIE, weight_format=WEIGHT_FORMAT,
                          weight_bits=WEIGHT_BITS, hbm_stacks=ROM_KV_HBM["stacks"], stacks_per_die=STACKS_PER_DIE,
                          decision="user 2026-09-28: 8-bit weights; two reticles in one package (O4 of "
                                   "results/arch/qwen3_8bit_design.json), 8 HBM3E stacks, 6,144 groups a die",
                          evidence="results/arch/qwen3_8bit_design.json (why 8-bit does not fit one reticle, and "
                                   "the options priced)")
    out["rom_capacity"] = rom_capacity()
    out["die_split"] = die_split()
    out["ucie"] = dict(link=ucie_link(), exchange=ucie_exchange(clock),
                       exchange_at_hop_range=[ucie_exchange(clock, hop_s=h)["cycles_per_token"]
                                              for h in ucie_link()["hop_latency_range_s"]],
                       dflash_block5=dict(verify=tp_exchanges(clock, 5), draft=tp_exchanges(clock, 5, "draft")))
    out["die_shape"] = {k: die_shape()[k] for k in ("NH", "KV", "FF", "V", "H")}
    xchg = out["ucie"]["exchange"]
    out["area"] = area_ledger()
    out["roofline_rom"] = {str(t): roofline_rom(out["workload"][str(t)], clock) for t in CONTEXTS}
    out["hbm_comparator"] = {str(t): {f: hbm_design(out["workload"][str(t)], clock, f)
                                      for f in HBM_BYTE_FORMATS} for t in CONTEXTS}
    spec_lat = dict(AS_BUILT_LAT, seq_gap=1)
    chains = {}
    for t in CONTEXTS:
        for label, sw, lat, mp, ch, st in (
                ("as_built_units", 1, AS_BUILT_LAT, "as_built", False, LAYER_STAGES),
                ("spec_widths_reference_graph", SPEC_SU_WIDTH, AS_BUILT_LAT, "ksplit", True, LAYER_STAGES),
                ("spec", SPEC_SU_WIDTH, spec_lat, "ksplit", True, LAYER_STAGES_SPEC)):
            ds = die_shape()
            rows, tot = chain(t, GROUPS_DIE, sw, lat, mp, ch, stages=st, shape=ds, golden_pv=(label == "spec"),
                              scale_cycles=SCALE_MUL_CYCLES)
            layer = sum(tot.values())
            per_tok = {k: v * Q["L"] for k, v in tot.items()}
            per_tok["weights"] += mv_cycles(ds["V"], ds["H"], GROUPS_DIE)[0]
            per_tok["ucie"] = xchg["cycles_per_token"]      # the UCIe exchanges, serial on the chain
            total = sum(per_tok.values())
            chains[f"{t}/{label}"] = dict(context=t, su_width=sw, attention_mapping=mp, chained_elementwise=ch,
                                          layer_cycles=layer, token_cycles=total, components=per_tok,
                                          ucie_exchange_cycles=xchg["cycles_per_token"],
                                          tokens_s=round(clock / total, 1), stages=rows)
    out["dependency_chain"] = chains
    out["budget"] = budget(out, clock)
    out["requirements"] = requirements(out, clock)
    # the spec machine's token: its chain against the KV stream, per context and format
    out["rom_token"] = {}
    for t in CONTEXTS:
        for fmt in KV_FORMATS:
            step, comp, kv = rom_token(out, t, fmt)
            out["rom_token"][f"{t}/{fmt}"] = dict(cycles=round(step), compute_cycles=round(comp),
                                                 kv_stream_cycles=round(kv), tokens_s=round(clock / step, 1),
                                                 binding="kv_stream" if kv > comp else "compute")
    return out


def timing_basis():
    """The hardware basis tools/dflash_step_timing.py prices the DFlash step on: the package's clock, engine,
    KV stacks, spec dependency chains (UCIe exchanges included), token steps and workload."""
    out = core()
    return {
        "what": "hardware basis of tools/dflash_step_timing.py: the two-reticle package of tools/arch_budget_qwen3.core",
        "source": "tools/arch_budget_qwen3.py core()", "clock_hz": out["clock_hz"], "shape": out["shape"],
        "rom_design": out["rom_design"], "hbm_design": out["hbm_design"], "design_point": out["design_point"],
        "lane_multiplier_m": out["area"]["lane_multiplier_m"],
        "dependency_chain": {k: v for k, v in out["dependency_chain"].items() if k.endswith("/spec")},
        "rom_token": out["rom_token"],
        "workload": {k: {"weight_macs": v["weight_macs"], "attention_macs": v["attention_macs"],
                         "bytes": v["bytes"]} for k, v in out["workload"].items()},
        "hbm_weight_bytes_per_mac": {f: hbm_weight_bytes_per_mac(f) for f in HBM_BYTE_FORMATS},
        "matched_format": MATCHED_FMT,
        "tp": dict(dies=DIES, die_shape=out["die_shape"], hop_cycles=ucie_link()["hop_latency_s"] * out["clock_hz"],
                   link_bytes_per_cycle=ucie_link()["bytes_s_per_direction"] / out["clock_hz"],
                   partial_bytes=PARTIAL_BYTES, reduce_add_cycles=REDUCE_ADD_CYCLES, emb_row_bytes=EMB_ROW_BYTES,
                   fc_mv=k_split_fc()["golden_split_cycles_rtl_tiling"],
                   kvproj_mv=mv_cycles(2 * die_shape()["KV"] * Q["HD"], Q["H"], GROUPS_DIE)[0],
                   fc_k_split=k_split_fc()),
    }


O8_REC = ROOT / "results/arch/qwen3_8bit_design.json"


def layer_cut_alternative():
    """The rejected split, from the O4 record: a contiguous cut (layers 0-19 on die A, 20-35 on die B).  Each layer
    runs on one die's groups and streams its KV from that die's 4 stacks, so the KV floor doubles and binds."""
    c = json.loads(O8_REC.read_text())["o4_contiguous_cut_scenario"]
    return dict(c, source="results/arch/qwen3_8bit_design.json#o4_contiguous_cut_scenario",
                verdict="rejected: TP-2 is the only split that reaches the O4 rates at batch 1")


def evaluate():
    out = core()
    clock = out["clock_hz"]
    out["baseline_as_built"] = json.loads(BASELINE.read_text())
    out["as_built_calibrated"] = {str(t): as_built(t) for t in CONTEXTS}
    out["layer_cut_alternative"] = layer_cut_alternative()
    out["gap"] = gap_table(out)
    out["hbm_requirements"] = hbm_requirements(out, clock)
    out["dflash"] = dflash_budget(out, clock)
    out["batch"] = batch_model(out, clock)
    out["power"] = power_budget(out, clock)
    out["power_production"] = power_production(out, clock)
    return out


# Power and energy inputs: ONE source.  Every energy, leakage, clock, HBM-path, MAC-lane and cooling figure is read
# from the sourced power-scenario model (configs/hardware/power_scenarios.json through tools/power_scenarios.py,
# where each input carries its evidence class, boundary and source); nothing is restated here.  Two SEPARATE
# scenarios price the multiply-accumulates:
#   A_measured_implementation -- every MAC, whatever its format, at our routed ASAP7 matrix engine's reported
#     energy (3.97 pJ/MAC on the reduced Qwen3 step);
#   B_proposed_production -- a floating-point lane derived from published per-OPERATION energies: multiplier +
#     one FP32 add per product (0.59 pJ an 8-bit-weight MAC, priced as the BF16/FP8 lane: an INT8 weight is exact in
#     BF16; 0.45 for W4A8, not used here).  The per-op technology.json w4a8 entry an
#     earlier model charged once per MAC (9e-14) is not used: that under-charged its own input 2x.
# The HBM path (13.64 pJ/bit, SC'25 MI250X) is split, every joule counted once: 3.45 pJ/bit inside the DRAM stack
# (O'Connor), the other 10.19 pJ/bit (controller, PHY, both ends' I/O, control plane) charged to the logic die;
# stack idle power is charged to the die.  Cooling is the per-class die limit of a shipping two-die package (B200
# HGX 1,000 W air / GB200 NVL72 1,200 W liquid, less their 8 stacks at peak: 374.6 / 474.6 W a die), checked with the
# package rating; both dies of the package carry half its work.  Only the die-to-wall conversion and the B200 reference rows, which the power
# scenarios do not model, are read from configs/hardware/technology.json.
import copy  # noqa: E402

import power_scenarios as PS  # noqa: E402

TECH = ROOT / "configs/hardware/technology.json"
PS_CFG = PS.load_cfg(resolve_dflash=False)   # the DFlash point: _dflash_point()
COOLING_CLASS = PS_CFG["design_points"]["qwen3"].get("cooling_class", "air")   # liquid (user decision 2026-09-28)
SCENARIOS = PS.SCENARIOS
GPU_TENSOR = "B_gpu_tensor_sensitivity"        # the lane no better than a shipping tensor core (A100, 1.40 pJ/MAC)


def _prod_inputs():
    cfg, v = PS_CFG, PS.val
    d, mem = cfg["die"], cfg["memory"]
    t = json.loads(TECH.read_text())
    pw, b = t["power"], t["reference_parts"]["b200_sxm"]
    ro, gp = pw["rack_overheads"], pw["gpu_reference_power"]
    lim = PS.cooling_limits(cfg)
    return dict(
        source="configs/hardware/power_scenarios.json via tools/power_scenarios.py (die, memory, MAC lane, "
               "cooling); configs/hardware/technology.json (die-to-wall conversion, B200 reference only)",
        mac_pj={s: {f: PS.mac_pj(cfg, s, "qwen3", f) for f in ("w4a8", "fp8", "bf16")}
                for s in SCENARIOS + (GPU_TENSOR,)},
        hbm_pj_per_bit=PS.hbm_split(cfg), hbm_idle_w_stack=v(mem["idle_w_per_stack"]),
        leak_w_mm2={k: v(d["leakage_w_per_mm2"][k]) for k in ("logic", "rom_array", "sram_array")},
        clock_j_mm2_cycle=v(d["clock_j_per_mm2_per_cycle"]), clock_mult=dict(d["clock_region_multiplier"]),
        rom_read_j_b=v(d["rom_read_j_per_byte"]), delivery_j_b=v(d["operand_delivery_j_per_byte"]),
        sram_j_b=v(d["sram_j_per_byte"]), stream_fp32_op_j=v(d["stream_fp32_op_j"]),
        cooling={cls: dict(reference=lim[cls][str(DIES)]["reference"], die_limit_w=lim[cls][str(DIES)]["die_w"],
                           package_limit_w=lim[cls][str(DIES)]["package_w"], dies_per_package=DIES)
                 for cls in PS.COOLING_CLASSES},
        psu=v(ro["psu_efficiency"]), vr=v(ro["vr_efficiency_48v_to_core"]), cdu=v(ro["cdu_fraction_of_it"]),
        fans=v(ro["fan_fraction_of_it"]), margin=1.2,
        b200=dict(tdp_hgx_w=v(b["power_w"]), tdp_nvl72_w=v(gp["b200_tdp_nvl72_w"]),
                  wall_saturated_w=v(gp["b200_measured_wall_w_per_gpu_saturated"]),
                  decode_measured_w=v(gp["b200_measured_decode_w"]),
                  hbm_bytes_s=v(b["hbm_bandwidth_bytes_s"]), efficiency=v(t["efficiencies"]["hbm_bandwidth"])),
    )


PROD = _prod_inputs()


def _package(die_w, stacks_w):
    """die_w: ONE die (both dies of the package dissipate alike); stacks_w: the package's 8 stacks."""
    P = PROD
    it = DIES * die_w + stacks_w
    wall = it / (P["psu"] * P["vr"]) * (1 + P["cdu"] + P["fans"])
    return dict(die_w=round(die_w, 1), dies=DIES, stacks_w=round(stacks_w, 1), package_w=round(it, 1),
                wall_w=round(wall, 1))


def _classes(c):
    return {cls: dict(reference=x["reference"], die_limit_w=round(x["die_limit_w"], 1),
                      package_limit_w=x["package_limit_w"], capped_tokens_s=round(x["capped_rate"], 1),
                      binds=x["binds"], bound_by=x["bound_by"], die_w_at_cap=round(x["die_w_at_cap"], 1))
            for cls, x in c.items()}


def _dflash_point():
    """The DFlash operating point of the power config, read from the serial step record (power_scenarios.dflash_point)."""
    return PS.dflash_point(PS_CFG["design_points"]["qwen3"])


WEIGHT_MAC_FORMAT = "fp8"   # the 8-bit weight's MAC on scenario B: bf16_mult + fp32_add (an INT8 or FP8 weight is exact
                            # in BF16; the power_scenarios 'fp8' lane, an upper bound for an 8 x 8-bit significand)


def qwen_design_point(out, clock):
    """This tool's ROM-package step points in the power-scenario schema: the steps, rates and PACKAGE areas the power
    model prices.  Its ar_batch1 and dflash rows are the ones configs/hardware/power_scenarios.json pins
    (tests/test_arch_budget_qwen3.py holds them equal)."""
    a = out["area"]
    m = a["lane_multiplier_m"]
    wl = out["workload"][str(CTX_HEAD)]
    kv_cyc = kv_bytes(wl, KV_FMT_SPEC) / rom_kv_bw() * clock
    batch = {r["batch"]: r for r in out["batch"]["per_context"][str(CTX_HEAD)]["rom"] if r["lane_multiplier"] == m}
    b_kv = min(b for b, r in batch.items() if r["binding"] == "kv_stream")
    best = out["dflash"]["rom"][f"{CTX_HEAD}/{KV_FMT_SPEC}/m{m}"]["best"]
    dfl = _dflash_point()
    assert (dfl["block"], dfl["step_cycles"], dfl["tokens_per_step"]) == \
        (best["block"], best["step_cycles"], best["tokens_per_step"]), "power config and budget read different points"
    one = dict(users=1, slots=1, drafter=False)
    cap = out["rom_capacity"]
    dp = dict(context=CTX_HEAD, kv_format_bytes_per_elem=KV_FORMATS[KV_FMT_SPEC], clock_hz=clock,
              hbm_stacks=ROM_KV_HBM["stacks"], dies_per_package=DIES, weight_bits=WEIGHT_BITS,
              drafter_weight_bits=WEIGHT_BITS, weight_scale_bytes=cap["swept_scale_bytes"],
              weight_mac_format=WEIGHT_MAC_FORMAT,
              ar_batch1=dict(step_cycles=round(max(out["as_built_calibrated"][str(CTX_HEAD)]["cycles"], kv_cyc)),
                             tokens_per_step=1, lane_copies_on=0, **one),
              dflash=dfl,
              area_mm2=dict(compute=DIES * a["compute_mm2"], interconnect=DIES * a["interconnect_mm2"],
                            overhead=DIES * a["overhead_mm2"], hbm_phy=DIES * a["hbm_phy_mm2"],
                            ucie_phy=DIES * a["ucie_phy_mm2"], stream_unit_spill=DIES * a["stream_unit_spill_mm2"],
                            lane_copy=round(DIES * a["lane_copy_mm2"], 2), lane_multiplier_m=m,
                            rom=round(DIES * a["target_rom_mm2"], 2), drafter_rom=round(DIES * a["drafter_rom_mm2"], 2),
                            sram=round(DIES * a["kv_prefetch_buffer_mm2"], 2)))
    dp[f"kv_bound_batch{b_kv}"] = dict(step_cycles=batch[b_kv]["step_cycles"], tokens_per_step=b_kv, users=b_kv,
                                       slots=1, drafter=False, lane_copies_on=min(m, b_kv) - 1)
    dp["batch128"] = dict(step_cycles=batch[128]["step_cycles"], tokens_per_step=128, users=128, slots=1,
                          drafter=False, lane_copies_on=m - 1)
    return dp


def _ps_cfg(dp):
    cfg = copy.deepcopy(PS_CFG)
    cfg["design_points"]["qwen3"] = dict(cfg["design_points"]["qwen3"], **dp)
    return cfg


def _rom_points(dp, scenario):
    """Every ROM point priced by tools/power_scenarios.qwen_point on this tool's design point."""
    cfg = _ps_cfg(dp)
    res = {}
    for key in (k for k, v in dp.items() if isinstance(v, dict) and "step_cycles" in v):
        r = PS.qwen_point(cfg, scenario, key)
        label = f"dflash_block{dp['dflash']['block']}" if key == "dflash" else key
        res[label] = dict(step_cycles=r["step_cycles"], tokens_per_step=r["tokens_per_step"],
                          tokens_s=round(r["design_rate_tokens_s"], 1),
                          energy_per_token_mj=round(r["energy_per_token_mj"], 3),
                          die_energy_per_token_mj=round(r["die_energy_per_token_mj"], 3),
                          stack_energy_per_token_mj=round(r["stack_energy_per_token_mj"], 3),
                          die_components_mj_per_token={k: round(v, 4) for k, v in r["die_components_mj_per_token"].items()},
                          die_static_w={k: round(v, 2) for k, v in r["die_static_w"].items()},
                          cooling=_classes(r["cooling_classes"]),
                          **_package(r["die_w_at_design_rate"], r["stacks_w_at_design_rate"]))
    return res


def _hbm_comparator(out, clock, scenario):
    """The iso-area HBM comparator: the ROM package's silicon (two 815 mm2 reticles of logic, the same core and
    12,288 groups, every layer split across both dies over the same UCIe link) with the 8 stacks its free edges hold,
    the ROM's own 8-bit weights (INT8 + per-channel BF16 scales) AND the users' KV read from HBM, priced on the same
    inputs as the ROM package: die = leakage + clock over each whole reticle + stack idle + MACs (the same 8-bit
    weight lane) + operand delivery + stream unit + the UCIe exchanges + the die's share of every HBM bit; stacks =
    their in-DRAM share.  Each die dissipates half; the per-die limit is the two-die package class's."""
    P = PROD
    hb = P["hbm_pj_per_bit"]
    wl = out["workload"][str(CTX_HEAD)]
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    comp = out["dependency_chain"][f"{CTX_HEAD}/spec"]["components"]
    lat = (comp["latency"] + comp["control"] + comp.get("ucie", 0)) / clock
    mm2 = DIES * FLOORPLAN["die_mm2"]
    static = dict(leakage_w=mm2 * P["leak_w_mm2"]["logic"], clock_w=P["clock_j_mm2_cycle"] * clock * mm2,
                  hbm_idle_w=HBM["stacks"] * P["hbm_idle_w_stack"])
    static_w = sum(static.values())
    bpp = hbm_weight_bytes_per_mac(MATCHED_FMT)
    res = {}
    for B in (1, 16, 128):
        byt = wl["weight_macs"] * bpp + B * kv_bytes(wl, KV_FMT_SPEC)
        macs_w, macs_a = B * wl["weight_macs"], B * wl["attention_macs"]
        t = max(byt / bw, (macs_w + macs_a) / (LANES_HBM * clock), lat)
        dyn = dict(mac_weights=macs_w * P["mac_pj"][scenario][WEIGHT_MAC_FORMAT] * 1e-12,
                   mac_attention=macs_a * P["mac_pj"][scenario]["bf16"] * 1e-12,
                   operand_delivery=byt * P["delivery_j_b"],
                   stream_unit=B * wl["elementwise_total"] * (P["stream_fp32_op_j"] + 12 * P["sram_j_b"]),
                   ucie_exchange=tp_exchanges(clock, B)["bytes_per_direction"] * 2 * 8 * ucie_link()["j_per_bit"],
                   hbm_controller_phy_io=byt * 8 * hb["die"] * 1e-12)
        rate = B / t
        dyn_tok = sum(dyn.values()) / B
        stack_tok = byt * 8 * hb["stack"] * 1e-12 / B
        classes = PS._class_caps(PS_CFG, DIES, static_w / DIES, dyn_tok / DIES,
                                 byt * 8 * hb["stack_high"] * 1e-12 / B / DIES, rate, mm2 / DIES)
        comps = {k: round(v / B * 1e3, 4) for k, v in dyn.items()}
        comps.update({k.replace("_w", ""): round(v / rate * 1e3, 4) for k, v in static.items()})
        res[f"batch{B}"] = dict(weight_format=MATCHED_FMT, tokens_s=round(rate, 1),
                                binding="bytes" if t == byt / bw else "macs" if t > lat else "latency",
                                energy_per_token_mj=round((dyn_tok + static_w / rate + stack_tok) * 1e3, 3),
                                die_energy_per_token_mj=round((dyn_tok + static_w / rate) * 1e3, 3),
                                stack_energy_per_token_mj=round(stack_tok * 1e3, 3),
                                die_components_mj_per_token=comps, cooling=_classes(classes),
                                **_package((static_w + dyn_tok * rate) / DIES, stack_tok * rate))
    return res


def _worst_case(out, clock, scenario, dp):
    """The saturated hardwired schedule, which the ROM package cannot exceed: every lane copy MACs every cycle (at the
    lane's BF16 energy, the costlier product), each die's 1,024-lane stream unit and ROM read path run every cycle,
    the 8 stacks stream at full raw bandwidth; clock on every mm2, leakage, stack idle.  Per die (half the package)."""
    P = PROD
    hb = P["hbm_pj_per_bit"]
    m = out["area"]["lane_multiplier_m"]
    st = PS._die_static(PS_CFG, PS._qwen_areas(dp, m - 1), clock, ROM_KV_HBM["stacks"])
    raw_b_s = ROM_KV_HBM["stacks"] * HBM["stack_bytes_s"]
    pkg = (LANES_ROM * m * clock * P["mac_pj"][scenario]["bf16"] * 1e-12
           + DIES * SPEC_SU_WIDTH * clock * (P["stream_fp32_op_j"] + 12 * P["sram_j_b"])
           + LANES_ROM * WEIGHT_BITS / 8 * clock * (P["rom_read_j_b"] + P["delivery_j_b"])
           + raw_b_s * (8 * hb["die"] * 1e-12 + 2 * P["sram_j_b"] + P["delivery_j_b"]) + sum(st.values()))
    stacks = raw_b_s * 8 * hb["stack"] * 1e-12
    return dict(_package(pkg / DIES, stacks),
                provisioned_w_per_die=round(P["margin"] * (pkg + stacks) / DIES / (P["vr"] * P["psu"]), 1),
                basis="saturated hardwired schedule, per die of the package: every lane copy MACs every cycle (BF16 "
                      "lane energy), the die's 1,024-lane stream unit and ROM read path run every cycle, its 4 stacks "
                      "at full raw bandwidth (the die's share of the HBM path on the die), clock on every mm2, "
                      "leakage, stack idle; provisioned = 1.2 x (die + stacks) / (VR x PSU)")


def power_production(out, clock):
    """Energy per token and die / package / wall power for the ROM package, the HBM comparator and a B200 at the
    design point (8K, FP8 KV), in the two power scenarios, every input read from the sourced power-scenario model
    (PROD); per point the rate each cooling class allows; the saturated worst case and the provisioned power."""
    P = PROD
    wl = out["workload"][str(CTX_HEAD)]
    dp = qwen_design_point(out, clock)
    g = P["b200"]
    gbyt = wl["weight_macs"] + kv_bytes(wl, KV_FMT_SPEC)
    g_tok_s = g["hbm_bytes_s"] * g["efficiency"] / gbyt
    gpu = dict(tokens_s_batch1_fp8=round(g_tok_s, 1),
               energy_per_token_mj_at_measured_decode_draw=round(g["decode_measured_w"] / g_tok_s * 1e3, 1),
               energy_per_token_mj_at_saturated_wall=round(g["wall_saturated_w"] / g_tok_s * 1e3, 1),
               basis="illustration, not a matched ratio: the measured B200 decode draw (689 W, arXiv:2609.11133) "
                     "over the HBM-roofline batch-1 rate (8 TB/s x 0.90 over FP8 weights + FP8 KV at 8K); the "
                     "saturated wall figure (1.30 kW a GPU, MLPerf v5.1) is the upper bound. The B200 is the "
                     "iso-silicon GPU: two reticle-limited dies and 8 HBM3E stacks, as the ROM package", **g)
    scen = {}
    for s in SCENARIOS:
        rom, hbm = _rom_points(dp, s), _hbm_comparator(out, clock, s)
        r1 = rom["ar_batch1"]["energy_per_token_mj"]
        h1 = hbm["batch1"]["energy_per_token_mj"]
        scen[s] = dict(mac_pj=P["mac_pj"][s], rom=rom, hbm_comparator=hbm, worst_case=_worst_case(out, clock, s, dp),
                       ratios_batch1=dict(hbm_over_rom=round(h1 / r1, 2),
                                          b200_measured_over_rom=round(gpu["energy_per_token_mj_at_measured_decode_draw"] / r1, 2)))
    lim = PROD["cooling"]
    return dict(basis="two power scenarios on the sourced inputs of configs/hardware/power_scenarios.json (read "
                      "through tools/power_scenarios.py): A = every MAC at the routed ASAP7 matrix engine's "
                      "3.97 pJ/MAC, B = the derived floating-point production lane (0.59 pJ an 8-bit-weight MAC "
                      "(BF16 multiplier + FP32 add), the same for BF16 attention); HBM path 13.64 pJ/bit = 10.19 on "
                      "the die + 3.45 in the stacks; KV read from HBM on the ROM package and the comparator alike; "
                      "cooling per shipping two-die package class, the design class liquid (GB200 NVL72 1,200 W -> "
                      "%.1f W a die; B200 HGX 1,000 W air -> %.1f W a die as the sensitivity), each less its 8 "
                      "stacks at peak; wall = package through VR "
                      "0.87 and PSU 0.96 with CDU and fans" % (lim["liquid"]["die_limit_w"], lim["air"]["die_limit_w"]),
                inputs=PROD, design_point=dp, scenarios=scen, b200=gpu)


UTIL_OUT = ROOT / "results/arch/qwen3_utilization.json"
SRAM_READ_B_PER_CYCLE = GROUPS_ROM * W   # the engine's KV port: one FP8 word of W elements a group a cycle


def _blk(name, peak, unit, demand, step, *, busy=None, area_mm2=None, kind="compute", **kw):
    u = demand / (peak * step) if peak else 0.0
    r = dict(block=name, kind=kind, peak_per_cycle=peak, unit=unit, demand_per_step=demand,
             utilization=round(u, 4))
    if busy is not None:
        r["busy_cycles"] = round(busy)
        r["busy_fraction"] = round(busy / step, 4)
    if area_mm2 is not None:
        r["area_mm2"] = area_mm2
    r.update(kw)
    return r


def utilization(out, clock):
    """The utilisation gate (user, binding before the core P&R): for every block
    of the ROM package and of the HBM comparator, its peak, its demand at batch
    1 (autoregressive and DFlash at its best block), at the KV-bound batch and at the
    largest batch; utilisation (MFU for compute, MBU for memory and bandwidth)
    and busy fraction over the step; area and energy share; and a verdict:
    RIGHT-SIZED (binding, or smaller would slow the single user -- measured by
    the calibrated model where it can be), JUSTIFIED (idle capacity that buys
    batch-1 latency), or OVER-PROVISIONED with the right-sizing applied."""
    wl = out["workload"][str(CTX_HEAD)]
    m = out["area"]["lane_multiplier_m"]
    ar = out["as_built_calibrated"][str(CTX_HEAD)]
    kvb1 = kv_bytes(wl, KV_FMT_SPEC)
    kv_cyc = kvb1 / rom_kv_bw() * clock
    macs_tok = wl["weight_macs"] + wl["attention_macs"]
    wbytes = wl["bytes"]["weights_rom_format"] + out["rom_capacity"]["swept_scale_bytes"]
    drafter_bytes = DRAFTER_PARAMS * WEIGHT_BITS / 8
    rom_peak_b = LANES_ROM * WEIGHT_BITS / 8
    raw_hbm_b = ROM_KV_HBM["stacks"] * HBM["stack_bytes_s"] / clock
    trans = Q["NH"] * CTX_HEAD * Q["L"] + Q["FF"] * Q["L"] + wl["elementwise"]["rsqrt_recip"]
    red = sum(n * k for n, k in wl["reductions"].values())
    layer_kv = kvb1 / Q["L"] / DIES                     # one die's half of a layer (its own KV heads)
    ring_need = layer_kv + rom_kv_bw() / DIES * T_RFC_S
    buf = out["area"]["kv_prefetch_buffer_bytes"]
    buf_first = 2 * layer_kv
    batch = {r["batch"]: r for r in out["batch"]["per_context"][str(CTX_HEAD)]["rom"] if r["lane_multiplier"] == m}
    b_kv = min(b for b, r in batch.items() if r["binding"] == "kv_stream")
    b_max = max(batch)
    best = out["dflash"]["rom"][f"{CTX_HEAD}/{KV_FMT_SPEC}/m{m}"]["best"]
    Bd = best["block"]
    draft_macs = best["draft_weight_macs"] + best["draft_attention_macs"]
    area = out["area"]
    ub = ar["unit_busy"]
    attn_busy = ub["attn_scores"] + ub["attn_pv"]
    # scenarios: (label, step cycles, positions sharing a weight word, users, slots, drafter, basis)
    scen = [("ar_batch1", max(ar["cycles"], kv_cyc), 1, 1, 1, False,
             "calibrated sequencer model at HEAD (unit busy measured on the replayed program)"),
            (f"dflash_block{Bd}", best["step_cycles"], min(m, Bd), 1, Bd, True,
             f"serial draft + verify + commit step (results/speculative/dflash_step_timing.json), best ROM block "
             f"at m = {m} ({best['tokens_per_step']} tokens a step, measured at this block)"),
            (f"kv_bound_batch{b_kv}", batch[b_kv]["step_cycles"], min(m, b_kv), b_kv, 1, False,
             "budget model, smallest KV-bound batch"),
            (f"max_batch{b_max}", batch[b_max]["step_cycles"], m, b_max, 1, False, "budget model")]
    rom = {}
    for label, step, share, users, slots, drafter, basis in scen:
        n = users * slots
        macs = n * macs_tok + (draft_macs if drafter else 0)
        k = max(1, min(m, share))
        sweeps = 1 if drafter else math.ceil(n / m)
        rbytes = sweeps * wbytes + (drafter_bytes if drafter else 0)
        kvb = users * kvb1 * ((1 + DRAFTER_LAYERS / Q["L"]) if drafter else 1)
        su_el = n * wl["elementwise_total"]
        su_busy = ub["stream"] * n
        a_busy = attn_busy * users * math.ceil(slots / k)
        me_busy = (ub["weights"] + ub["lm_head"]) * math.ceil(n / k) + a_busy
        if drafter:
            me_busy += draft_macs / (LANES_ROM * k)
        instr = ar["instructions"] * users * (1 + (DRAFTER_LAYERS / Q["L"] if drafter else 0))
        t = step / clock
        e = dict(matrix_engine=macs * E_ME_PER_MAC, other_logic_upper=macs * (E_LOGIC_PER_MAC - E_ME_PER_MAC),
                 rom_read=rbytes * E_ROM_PER_BYTE, rom_leakage=LEAK_W_ROM * t,
                 kv_hbm_stacks=kvb * E_HBM_PER_BYTE)
        et = sum(e.values())
        blocks = [
            _blk("matrix engine, base lanes (both dies)", LANES_ROM, "MAC", macs / k, step, busy=min(me_busy, step),
                 area_mm2=round(DIES * area["compute_mm2"], 2), kind="compute (MFU)"),
            _blk(f"matrix engine, {m - 1} lane copies (both dies)", LANES_ROM * (m - 1), "MAC", macs * (k - 1) / k,
                 step, busy=min(me_busy, step) if k > 1 else 0,
                 area_mm2=round(DIES * area["lane_copy_mm2"] * (m - 1), 1),
                 kind="compute (MFU)", copies_in_use=k - 1),
            _blk("weight ROM macros and read path", rom_peak_b, "byte", rbytes, step,
                 busy=rbytes / rom_peak_b, area_mm2=round(DIES * area["target_rom_mm2"], 2), kind="memory (MBU)",
                 weight_sweeps=sweeps),
            _blk("drafter ROM", rom_peak_b, "byte", drafter_bytes if drafter else 0, step,
                 area_mm2=round(DIES * area["drafter_rom_mm2"], 2), kind="memory (MBU)"),
            _blk("attention path (engine share: scores, P.V)", LANES_ROM * k, "MAC",
                 n * wl["attention_macs"], step, busy=a_busy, kind="compute (MFU)"),
            _blk(f"vector stream unit ({SPEC_SU_WIDTH} lanes a die; the chain model runs one)", SPEC_SU_WIDTH,
                 "element", su_el, step, busy=min(su_busy, step), area_mm2=DIES * SU_SPILL_MM2, kind="compute (MFU)"),
            _blk("SFUs (exp, SiLU, rsqrt/recip: one a stream lane)", SPEC_SU_WIDTH, "transcendental", n * trans,
                 step, kind="compute (MFU)"),
            _blk("reducers (R-ARITH segments, split tree)", SPEC_SU_WIDTH, "element", n * red, step,
                 kind="compute (MFU)"),
            _blk(f"KV streamer, HBM controllers and PHYs ({ROM_KV_HBM['stacks']} stacks, raw peak)", raw_hbm_b,
                 "byte", kvb, step, busy=min(kvb / (raw_hbm_b * HBM["efficiency"]), step),
                 area_mm2=DIES * area["hbm_phy_mm2"],
                 kind="bandwidth (MBU)",
                 mbu_of_sustained=round(kvb / (raw_hbm_b * HBM["efficiency"] * step), 4)),
            _blk("KV ring buffer (SRAM, one a die): capacity", buf, "byte", ring_need, 1,
                 area_mm2=area["kv_prefetch_buffer_mm2"], kind="capacity",
                 first_sizing_bytes=buf_first, first_sizing_utilization=round(ring_need / buf_first, 4)),
            _blk("UCIe exchanges (on the chain)", out["ucie"]["exchange"]["exchanges_per_token"], "exchange",
                 out["ucie"]["exchange"]["exchanges_per_token"] * n, step,
                 busy=out["ucie"]["exchange"]["cycles_per_token"], area_mm2=DIES * UCIE_PHY_MM2, kind="latency"),
            _blk("KV ring buffer (SRAM): engine read port", SRAM_READ_B_PER_CYCLE, "byte", kvb, step,
                 busy=kvb / SRAM_READ_B_PER_CYCLE, kind="bandwidth (MBU)"),
            _blk("sequencer / issue", 1, "instruction", instr, step, busy=instr, kind="control"),
            _blk("argmax (streaming compare tree on the LM head's results)", LANES_ROM, "compare",
                 Q["V"] * (n + (Bd - 1 if drafter else 0)), step,
                 busy=ub["lm_head"] * math.ceil(n / k), kind="compute"),
        ]
        rom[label] = dict(step_cycles=round(step), basis=basis, users=users, slots=slots,
                          tokens_s_total=round(users * (best["tokens_per_step"] if drafter else 1) * clock / step, 1),
                          energy_per_step_mj={k2: round(v * 1e3, 3) for k2, v in e.items()},
                          energy_share={k2: round(v / et, 4) for k2, v in e.items()}, blocks=blocks)
    # ---- the HBM comparator (the ROM's 8-bit weights and the KV on its 8 stacks) -------------------------
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    raw = HBM["stacks"] * HBM["stack_bytes_s"] / clock
    comp = out["dependency_chain"][f"{CTX_HEAD}/spec"]["components"]
    lat = (comp["latency"] + comp["control"] + comp.get("ucie", 0)) / clock
    bpp = hbm_weight_bytes_per_mac(MATCHED_FMT)
    dh = out["dflash"]["hbm"][MATCHED_FMT]
    n16 = dh["block"]
    step_macs16 = dh["macs_per_step"]
    hbatch = [r["batch"] for r in out["batch"]["per_context"][str(CTX_HEAD)]["hbm"][MATCHED_FMT]]
    hb_kv = min(b for b in hbatch if b * kvb1 >= wl["weight_macs"] * bpp)
    wl2 = out["workload"]["2048"]
    kvb2 = kv_bytes(wl2, KV_FMT_SPEC)
    hscen = [("ar_batch1", 1, None, wl, kvb1), (f"dflash_block{n16}", None, dh["step_s"], wl, kvb1),
             (f"kv_bound_batch{hb_kv}", hb_kv, None, wl, kvb1), (f"max_batch{b_max}", b_max, None, wl, kvb1),
             (f"ctx2048_max_batch{b_max}", b_max, None, wl2, kvb2)]
    # the right-sizing candidate: the fewest groups (a multiple of 512 a die) whose tiled lanes still meet the
    # DFlash step's lane need
    cand = GROUPS_HBM
    for g in range(GROUPS_HBM, 1023, -1024):
        if g * W * tiling_eff(g) >= dh["mac_lanes_min"]:
            cand = g
        else:
            break
    hbm = {}
    for lanes, groups, role in ((LANES_HBM, GROUPS_HBM, "the comparator as specified"),
                                (cand * W, cand, "right-sizing candidate")):
        eff = tiling_eff(groups)
        rows = {}
        for label, B, fixed, w_, kvb_ in hscen:
            if fixed:
                macs = step_macs16
                # the draft phase re-reads the shared lm_head at the weight format
                byt = (w_["weight_macs"] + DRAFTER_PARAMS + Q["V"] * Q["H"]) * bpp + kvb_ * (1 + DRAFTER_LAYERS / Q["L"])
                bound_t = fixed
                t = max(fixed, macs / (lanes * eff * clock))
            else:
                byt = w_["weight_macs"] * bpp + B * kvb_
                macs = B * (w_["weight_macs"] + w_["attention_macs"])
                bound_t = max(byt / bw, lat)
                t = max(bound_t, macs / (lanes * eff * clock))
            step = t * clock
            rows[label] = dict(step_cycles=round(step), slowed_by_lanes=round(t / bound_t - 1, 4), blocks=[
                _blk("matrix engine", lanes, "MAC", macs, step, busy=macs / (lanes * eff), kind="compute (MFU)"),
                _blk(f"HBM ({HBM['stacks']} stacks, raw peak): weights + KV", raw, "byte", byt, step,
                     busy=min(byt / (raw * HBM["efficiency"]), step), kind="bandwidth (MBU)",
                     mbu_of_sustained=round(byt / (bw / clock * step), 4)),
                _blk(f"vector stream unit ({SPEC_SU_WIDTH} lanes)", SPEC_SU_WIDTH, "element",
                     (B or n16) * w_["elementwise_total"], step, kind="compute (MFU)"),
                _blk("sequencer / issue", 1, "instruction", ar["instructions"] * (B or 1), step, kind="control"),
            ])
        hbm[f"{lanes}_lanes"] = dict(role=role, groups=groups, lanes=lanes, tiling_efficiency=round(eff, 4),
                                     scenarios=rows)
    spec_rows = hbm[f"{LANES_HBM}_lanes"]["scenarios"]
    cand_rows = hbm[f"{cand * W}_lanes"]["scenarios"]
    cand_loss = max(cand_rows[k]["step_cycles"] / spec_rows[k]["step_cycles"] - 1 for k in spec_rows)
    su_sweep = {sw: as_built(CTX_HEAD, su_width=sw)["cycles"] for sw in (512, 1024, 2048)}
    g_half = as_built(CTX_HEAD, groups=GROUPS_DIE // 2)["cycles"]
    ar_step = max(ar["cycles"], kv_cyc)
    pw_cool = PROD["cooling"][COOLING_CLASS]["die_limit_w"]
    ar_bind = "the compute chain" if ar["cycles"] >= kv_cyc else "the KV stream"
    hb1 = spec_rows["ar_batch1"]["blocks"][0]["utilization"]

    def pw_cap(point, scenario):
        return out["power"]["points"][point]["lanes"][scenario]["cooling"][COOLING_CLASS]["capped_tokens_s"]

    rr = out["area"]["rom_read"]
    verdicts = [
        dict(block=f"ROM: matrix engine base lanes ({LANES_ROM:,} on {DIES} dies)", verdict="RIGHT-SIZED (ROM-read bound)",
             why=f"each die's {GROUPS_DIE:,} groups are the most its half of the 8-bit ROM feeds (read headroom "
                 f"{rr['headroom']}; {rr['next_step_groups']:,} groups a die would be {rr['next_step_headroom']}); "
                 f"{ar_bind} binds the autoregressive token ({ar['cycles']:,} vs a {round(kv_cyc):,}-cycle KV floor); "
                 f"half the groups is {g_half:,} cycles (+{g_half / ar_step - 1:.0%} a token) in the calibrated model"),
        dict(block=f"ROM: {m - 1} lane copies a die", verdict="JUSTIFIED (DFlash only), conditional on power",
             why=f"idle in autoregressive decode and in KV-bound batches (each user's KV is its own); they carry "
                 f"the DFlash block-{Bd} verify ({best['speedup']}x single-user tokens/s). Under the "
                 f"{pw_cool:.1f} W per-die {COOLING_CLASS} limit the capped DFlash / autoregressive rates are "
                 f"{pw_cap('dflash', 'B_proposed_production'):,.0f} / {pw_cap('ar_batch1', 'B_proposed_production'):,.0f} "
                 f"tokens/s on the production lane (scenario B: the copies pay) and "
                 f"{pw_cap('dflash', 'A_measured_implementation'):,.0f} / {pw_cap('ar_batch1', 'A_measured_implementation'):,.0f} "
                 f"on the routed 3.97 pJ/MAC lane (scenario A: they do not)"),
        dict(block="ROM: weight ROM read path", verdict="RIGHT-SIZED (binding on the lane count)",
             why=f"one 8-bit weight a lane a cycle, {rr['required_bytes_per_cycle_per_die']:,} B a cycle a die at "
                 f"read headroom {rr['headroom']}; the sweep is on the single user's chain "
                 f"({ub['weights'] + ub['lm_head']:,} cycles)"),
        dict(block="ROM: vector stream unit (1,024 lanes; SFUs and reducers on its lanes)", verdict="RIGHT-SIZED",
             why=f"calibrated: 512 lanes is {su_sweep[512]:,} cycles (+{su_sweep[512] / ar_step - 1:.1%} a token), "
                 f"2,048 is {su_sweep[2048]:,} ({su_sweep[2048] / ar_step - 1:+.1%})"),
        dict(block=f"ROM: KV streamer, controllers, {ROM_KV_HBM['stacks']} PHYs ({STACKS_PER_DIE} a die)",
             verdict="RIGHT-SIZED (beachfront-limited)",
             why=f"the KV floor ({round(kv_cyc):,} cycles) sits {1 - kv_cyc / ar['cycles']:.0%} under the "
                 f"autoregressive chain; the stacks are what each die's free edge holds, and KV-bound batches "
                 f"bind on them"),
        dict(block="ROM: KV ring buffer (one a die)", verdict="JUSTIFIED (the O4 record's sizing; halving it is an open lever)",
             why=f"each die's ring holds one layer plus the package's refresh cover ({buf / 1e6:.1f} MB, the O4 "
                 f"record's sizing); the die's own KV heads fill {ring_need / buf:.0%} of it, so halving it would "
                 f"free about 3 mm2 a die"),
        dict(block="ROM: KV ring buffer's engine read port", verdict="JUSTIFIED (latency)",
             why="one FP8 word a group a cycle is the engine's attention operand rate: the scores and P.V passes "
                 f"read a layer's KV in {attn_busy // Q['L']} cycles on the chain; a narrower port lengthens "
                 "every layer's attention stage"),
        dict(block="ROM: UCIe link", verdict="JUSTIFIED (latency)",
             why=f"{out['ucie']['exchange']['exchanges_per_token']} exchanges a token of "
                 f"{out['ucie']['exchange']['bytes_per_exchange_per_direction']:,} B each way, "
                 f"{out['ucie']['exchange']['cycles_per_token']:,} cycles on the chain "
                 f"({out['ucie']['exchange']['cycles_per_token'] / ar['cycles']:.1%} of the token); latency, not "
                 f"bandwidth, is what it costs"),
        dict(block="ROM: drafter ROM", verdict="JUSTIFIED (DFlash only)", why="read once a DFlash step; idle otherwise"),
        dict(block="ROM: sequencer, argmax", verdict="JUSTIFIED (latency)",
             why="small; both sit on the token's chain (the issue gap, the LM head's tail)"),
        dict(block="HBM: matrix engine", verdict="JUSTIFIED (same core as the ROM package)",
             why=f"{LANES_HBM:,} lanes are {hb1:.1%} used at batch 1 and bytes bind every 8k row. The smallest "
                 f"array that keeps the DFlash step ({cand * W:,} lanes, tiling {tiling_eff(cand):.3f}, against a "
                 f"{dh['mac_lanes_min']:,}-lane need) costs the batch rows up to {cand_loss:.0%} of their "
                 f"throughput; the comparator keeps the ROM package's core, so the ratio isolates the weight store"),
        dict(block="HBM: stacks and controllers", verdict="RIGHT-SIZED (binding)",
             why=f"{HBM['stacks']} stacks ({STACKS_PER_DIE} a die, what each die's free edge holds); bytes bind "
                 "every 8k row"),
    ]
    return dict(schema="opentallas.arch-utilization-qwen3.v1", tool="tools/arch_budget_qwen3.py",
                context=CTX_HEAD, kv_format=KV_FMT_SPEC, clock_hz=clock, lane_multiplier=m, dies=DIES,
                rule="improve utilisation without slowing the single user",
                rom=rom, hbm=hbm, su_width_sweep_cycles=su_sweep, half_groups_cycles=g_half,
                verdicts=verdicts, energy_basis=out["batch"]["energy_basis"],
                notes=["busy fractions of the autoregressive row are the calibrated model's; the other rows "
                       "scale the per-position busy by positions over copies in use",
                       "SFU and reducer demand counts operations whose peak is the stream unit's lanes; their "
                       "busy time is inside the stream unit's",
                       f"the other rows' steps are the budget model's (analytical chain, conservative against the "
                       f"calibrated {ar['cycles']:,}); KV-bound rows are exact either way"])


def hbm_requirements(out, clock):
    """The iso-area HBM comparator: the weight stream binds, so the design goal
    is a stream that never stalls.  Weights are data-independent, so the
    stream runs ahead across every dependency point; the prefetch buffer must
    hold what the stacks deliver during the longest interval in which the core
    consumes no weights (the non-matrix stages between two weight ops of the
    spec chain), and the MAC rate must exceed the stream so the buffer drains."""
    bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
    rows = out["dependency_chain"][f"{CTX_HEAD}/spec"]["stages"]
    gap = cur = 0
    for r in rows:
        if r["kind"] == "mv":
            gap, cur = max(gap, cur), 0
        else:
            cur += r["throughput"] + r["exposed_latency"]
    gap = max(gap, cur)
    res = {}
    for t in CONTEXTS:
        per = {}
        for f, r in out["hbm_comparator"][str(t)].items():
            per[f] = dict(tokens_s_target=round(0.95 * r["tokens_s"], 1), tokens_s_bound=r["tokens_s"],
                          mac_lanes_min=2 * r["lanes_needed_at_clock"])
        res[str(t)] = per
    return dict(stacks=HBM["stacks"], sustained_efficiency_min=HBM["efficiency"],
                address_map="refresh-aware: pseudo-channels interleaved at the stream's word size and refresh phases "
                            "staggered, so no weight op meets the same refresh on every channel",
                efficiency_measured_with_refresh=True,
                controller_queue_beats_per_pseudo_channel_min=512,
                controller_queue_basis="bandwidth x tRFC (350 ns) = ~350 beats; on the V4.1 HBM vehicle a "
                                       "refreshing channel's full 64-beat queue stalled the in-order stream for "
                                       "~tRFC (up to 15% of a token); neutral for Qwen3 (+0.1%)",
                refresh_policy="0.90 of RAW peak with refresh on: REFab (tRFC 350 ns / tREFI 3.9 us, 9.0% floor) "
                               "meets it as measured on the Qwen3 reduced vehicle (0.904 / 0.910 at 1 / 2 pseudo-"
                               "channels); REFpb is allowed only with a record showing >= 0.90; a refreshing "
                               "channel must not stall requests to other channels",
                longest_weight_free_interval_cycles=gap,
                prefetch_buffer_bytes_min=math.ceil(bw * gap / clock),
                hbm_bytes_per_cycle=round(bw / clock), per_context=res,
                note="95% of the byte bound: the stream stalls only at the token start (the first weights' latency)")


def gap_table(out):
    req = out["requirements"]
    ab = out["baseline_as_built"]["as_built_calibrated"]["2048"]
    head = out["as_built_calibrated"][str(CTX_HEAD)]
    wsum = ab["unit_busy"].get("weights", 0) + ab["unit_busy"].get("lm_head", 0)
    hb = head["unit_busy"]
    return [
        dict(block="stream unit", requirement=f"{req['stream_unit_elements_per_cycle']['requirement']} elements/cycle",
             as_built=f"vector stream unit, SW lanes (landed: RTL parameter; {SPEC_SU_WIDTH} at the spec), "
                      f"R-ARITH reducer; one a die, {DIES * SPEC_SU_WIDTH:,} lanes in the package (the chain model "
                      f"prices the split elementwise work on one)", cycles_baseline_2k=ab["unit_busy"].get("stream", 0),
             cycles_head_8k=hb.get("stream", 0), status="MEETS"),
        dict(block="attention P.V", requirement="K-split over positions across every free group",
             as_built="interleaved K-split over positions (landed)", cycles_baseline_2k=ab["unit_busy"].get("attn_pv", 0),
             cycles_head_8k=hb.get("attn_pv", 0), status="MEETS"),
        dict(block="attention Q.K", requirement="K-split over head_dim across free groups",
             as_built="interleaved K-split over head_dim (landed)",
             cycles_baseline_2k=ab["unit_busy"].get("attn_scores", 0), cycles_head_8k=hb.get("attn_scores", 0),
             status="MEETS"),
        dict(block="dependency handling",
             requirement=f"<= {req['exposed_latency_per_dependent_stage_max']['requirement']} cycles exposed a stage",
             as_built="per-unit waits (landed: wait_me / wait_su, barrier = both), element chaining across "
                      "units; still whole-op granular within a unit",
             cycles_baseline_2k=ab["sequencer_stalls"].get("barrier_me", 0) + ab["sequencer_stalls"].get("barrier_su", 0),
             cycles_head_8k=sum(v for k2, v in head["sequencer_stalls"].items() if k2 != "unit_busy"),
             status="MISS"),
        dict(block="softmax", requirement="one stream-unit pass over the scores, 1/Z beside P.V",
             as_built="landed: the row max on the engine's result path (me_rmax), one exp pass, "
                      "normalise-after-sum (1/Z on 32 x 128 beside P.V), P.V chasing the exp pass by rows",
             cycles_baseline_2k=None, cycles_head_8k=None, status="MEETS"),
        dict(block="sequencer issue", requirement=req["instruction_issue"]["requirement"],
             as_built=f"prefetched issue pipeline: {head['instructions']} instructions at gap {T.K['seq_gap']} (landed)",
             cycles_baseline_2k=ab["seq_gap_total"], cycles_head_8k=head["seq_gap_total"], status="MEETS"),
        dict(block="matrix engine (weights)", requirement=req["weight_tiling_efficiency"]["requirement"] +
             f"; {GROUPS_ROM} groups and a 4-bit K-split field",
             as_built="4-bit me_split (landed); the reticle's groups are the RTL parameter G",
             cycles_baseline_2k=wsum, cycles_head_8k=hb.get("weights", 0) + hb.get("lm_head", 0), status="MEETS"),
        dict(block="KV in HBM (ROM package)", requirement=f"{ROM_KV_HBM['stacks']} stacks ({STACKS_PER_DIE} a die), "
                                                     f"{req['kv_hbm']['bytes_per_token'] / 1e6:.0f} MB/token FP8 KV, "
                                                     "streamed with prefetch",
             as_built="KV streamer (ot_hdc_kv_stream) exists for the unsplit attention order; BF16 KV only",
             cycles_baseline_2k=None, cycles_head_8k=req["kv_hbm"]["stream_cycles"], status="MISS"),
    ]


# DFlash: ONE source.  The drafter's shape and the operating points -- tokens a step measured at each block (not a
# block-16 histogram cut at B), the serial draft + verify + commit step (the draft phase on the critical path, not
# overlapped), and the MACs of both phases -- are tools/dflash_step_timing.py's record; nothing is restated here.
DFLASH_REC = ROOT / "results/speculative/dflash_step_timing.json"
DRAFTER_PARAMS, DRAFTER_LAYERS, DFLASH_FC = DST.DRAFTER_PARAMS, DST.DRAFTER_LAYERS, DST.DFLASH_FC
_ROW_KEYS = ("block", "tokens_per_step", "tokens_per_step_band", "step_cycles", "draft_cycles", "verify_cycles",
             "commit_cycles", "tokens_s", "tokens_s_band", "speedup", "draft_weight_macs", "draft_attention_macs",
             "verify_weight_macs", "verify_attention_macs", "macs_per_step")


def dflash_budget(out, clock):
    """DFlash at the design point and at 2k, m = 1 and the area ledger's m, read from the serial step record
    (results/speculative/dflash_step_timing.json).  This tool checks the record prices the same machine -- the
    clock, and its plain token equal to rom_token at each context -- and restates none of its figures.  On the ROM
    reticle the MACs of every slot are real work and the drafter's forward is a serial phase; on the HBM comparator
    each phase is max(bytes, MACs / lanes, latency) and the bytes bind."""
    raw = DFLASH_REC.read_bytes()
    rec = json.loads(raw)
    assert rec["clock_hz"] == clock, "the DFlash step record prices another clock"
    assert rec["checks"]["all"], rec["checks"]
    m_max = out["area"]["lane_multiplier_m"]
    rom = {}
    for ctx in CONTEXTS:
        plain = out["rom_token"][f"{ctx}/{KV_FMT_SPEC}"]["cycles"]
        for m in sorted({1, m_max}):
            key = f"{ctx}/{KV_FMT_SPEC}/m{m}"
            r = rec["rom"][key]
            assert r["plain_cycles"] == plain, (key, r["plain_cycles"], plain)
            rom[key] = dict(context=ctx, kv_format=KV_FMT_SPEC, lane_multiplier=m, plain_tokens_s=r["plain_tokens_s"],
                            sweep=[{k: x[k] for k in _ROW_KEYS} for x in r["sweep"]],
                            best={k: r["best"][k] for k in _ROW_KEYS})
    hbm = {}
    for fmt, h in rec["hbm"].items():
        b = h["best"]
        d_s, v_s = b["draft_us"] * 1e-6, b["verify_us"] * 1e-6
        need = max((b["draft_weight_macs"] + b["draft_attention_macs"]) / d_s,
                   (b["verify_weight_macs"] + b["verify_attention_macs"]) / v_s) / clock
        hbm[fmt] = dict(context=h["context"], tokens_s_plain=h["plain_tokens_s"], block=b["block"],
                        tokens_per_step=b["tokens_per_step"], tokens_per_step_band=b["tokens_per_step_band"],
                        step_s=b["step_us"] * 1e-6, draft_s=d_s, verify_s=v_s, binding=b["binding"],
                        tokens_s=b["tokens_s"], tokens_s_band=b["tokens_s_band"], speedup=b["speedup"],
                        macs_per_step=b["macs_per_step"], mac_lanes_min=math.ceil(need),
                        block16_tokens_s=h["block16"]["tokens_s"])
    best = rom[f"{CTX_HEAD}/{KV_FMT_SPEC}/m{m_max}"]["best"]
    return dict(source=str(DFLASH_REC.relative_to(ROOT)), source_sha256=hashlib.sha256(raw).hexdigest(),
                acceptance=rec["acceptance"]["path"], tau_convention=rec["acceptance"]["central"],
                tau_band=rec["acceptance"]["band"], tau_design_point=best["tokens_per_step"],
                block_design_point=best["block"], drafter_parameters=DRAFTER_PARAMS, rom=rom, hbm=hbm,
                requirements=["lane multiplier m (one weight or KV word feeds m slots)",
                              "the draft phase is serial with the verify: the drafter's layers, fc, K/V projections "
                              "and the shared lm_head over the draft slots run on the same engine before each verify",
                              "KV-shared verify attention: one K/V read serves every slot, the causal mask per slot",
                              "slot-parallel non-weight work: one op over all slots (the stream unit's lanes take "
                              "slots), never serial ops",
                              "16 DYN banks (token, pos + j); CTL TOKX/AMAX/DYN/ACCEPT/END; the shared accept unit",
                              "KV ring >= 17 entries; rollback is a commit pointer"])


BATCHES = (1, 2, 4, 8, 16, 32, 64, 128)
# Energy basis of the batch rows and the utilisation gate's energy shares: scenario A of the power-scenario model
# (the measured reduced Qwen3 step on the routed ASAP7 core), every figure read from PROD / PS_CFG.
_LANE_A = PS_CFG["mac_lane"]["scenario_A"]["qwen3"]
E_LOGIC_PER_MAC = _LANE_A["whole_step_pj_per_mac"] * 1e-12       # whole step (upper: a tiny vehicle's clock, registers)
E_ME_PER_MAC = PS.val(_LANE_A) * 1e-12                           # the matrix engine alone (lower)
E_HBM_PER_BYTE = PROD["hbm_pj_per_bit"]["total"] * 8 * 1e-12    # the whole HBM path, die and stack shares
E_ROM_PER_BYTE = PROD["rom_read_j_b"]
LEAK_W_ROM = rom_capacity()["target_mm2"] * PROD["leak_w_mm2"]["rom_array"]   # both dies' target ROM


def batch_model(out, clock):
    """Batch B users decoding together at the design point (8k, FP8 KV) and at
    2k.  ROM package: the users share the chain's latency and the weight words
    (lane copies m divide the weight MACs), each has its own attention and KV
    stream: step = max(latency + ceil(B/m) x weights + B x (attention +
    elementwise), B x KV bytes / bandwidth).  KV in HBM: capacity is no longer
    a limit (8 x 24 GB).  HBM comparator: one weight read serves the batch:
    step = max((weights + B x KV) / bandwidth, B x MACs / lanes, latency)."""
    m = out["area"]["lane_multiplier_m"]
    res = {}
    for ctx in CONTEXTS:
        wl = out["workload"][str(ctx)]
        macs = wl["weight_macs"] + wl["attention_macs"]
        rom = []
        for mm in sorted({1, m}):
            for B in BATCHES:
                step, comp, kv = rom_token(out, ctx, KV_FMT_SPEC, users=B, m=mm)
                t = step / clock
                kvb = kv_bytes(wl, KV_FMT_SPEC)
                mem = (wl["bytes"]["weights_rom_format"] + out["rom_capacity"]["swept_scale_bytes"]) * E_ROM_PER_BYTE \
                    + kvb * E_HBM_PER_BYTE
                e_hi = B * (macs * E_LOGIC_PER_MAC + mem) + LEAK_W_ROM * t
                e_lo = B * (macs * E_ME_PER_MAC + mem) + LEAK_W_ROM * t
                rom.append(dict(lane_multiplier=mm, batch=B, step_cycles=round(step),
                                per_user_tokens_s=round(clock / step, 1), total_tokens_s=round(B * clock / step, 1),
                                binding="kv_stream" if kv > comp else "compute",
                                energy_per_token_mj=round(e_hi / B * 1e3, 2),
                                energy_per_token_mj_matrix_engine_only=round(e_lo / B * 1e3, 2)))
        bw = HBM["stacks"] * HBM["stack_bytes_s"] * HBM["efficiency"]
        comp = out["dependency_chain"][f"{ctx}/spec"]["components"]
        lat = comp["latency"] + comp["control"]
        hbm = {}
        for fmt in HBM_BYTE_FORMATS:
            bpp = hbm_weight_bytes_per_mac(fmt)
            rows = []
            for B in BATCHES:
                byt = wl["weight_macs"] * bpp + B * kv_bytes(wl, KV_FMT_SPEC)
                t = max(byt / bw, B * macs / (LANES_HBM * clock), lat / clock)
                e_hi = B * macs * E_LOGIC_PER_MAC + byt * E_HBM_PER_BYTE
                e_lo = B * macs * E_ME_PER_MAC + byt * E_HBM_PER_BYTE
                rows.append(dict(batch=B, step_cycles=round(t * clock), per_user_tokens_s=round(1 / t, 1),
                                 total_tokens_s=round(B / t, 1), energy_per_token_mj=round(e_hi / B * 1e3, 2),
                                 energy_per_token_mj_matrix_engine_only=round(e_lo / B * 1e3, 2),
                                 binding="bytes" if t == byt / bw else "macs" if t > lat / clock else "latency"))
            hbm[fmt] = rows
        res[str(ctx)] = dict(rom=rom, hbm=hbm, kv_format=KV_FMT_SPEC)
    return dict(per_context=res,
                note=f"HBM comparator rows at {LANES_HBM:,} lanes on {HBM['stacks']} stacks and the same KV format "
                     f"as the ROM package",
                lane_copies_serve_batch="yes: one weight word feeding m users' MACs is the DFlash lane multiplier",
                energy_basis=f"scenario A of configs/hardware/power_scenarios.json: logic at the measured reduced "
                             f"step on the routed ASAP7 core, {E_LOGIC_PER_MAC * 1e12:.2f} pJ/MAC whole step (upper), "
                             f"{E_ME_PER_MAC * 1e12:.2f} pJ/MAC the matrix engine alone (lower); ROM "
                             f"{E_ROM_PER_BYTE * 1e12:.2f} pJ/B, the whole HBM path {E_HBM_PER_BYTE * 1e12:.2f} pJ/B, ROM "
                             "leakage; no clock or stream-unit energy. A ranking of batch sizes, not the power figure: "
                             "power_production prices die, package and wall")


def power_budget(out, clock):
    """Power as a first-class requirement, on the sourced power-scenario inputs (PROD).  The die limit is the
    per-class limit of a shipping two-die package (the rating less its own 8 stacks at peak, per die: B200 HGX
    1,000 W air, GB200 NVL72 1,200 W liquid).  Both dies carry the same work, so each is half the package.  At each
    step point's design rate (autoregressive batch 1; the best DFlash configuration) a die's power other than its
    MACs -- static (leakage, clock, stack
    idle) and dynamic (ROM and KV reads, stream unit, the die's share of the HBM path) -- is the same in every
    scenario; what the limit leaves, over the MAC rate, is the MAC energy that fits.  Each lane -- scenario A
    (routed ASAP7 matrix engine), scenario B (derived production lane), and a lane no better than an A100 tensor
    core -- then gives the die power and the rate each cooling class allows (tools/power_scenarios: die and
    package checks)."""
    P = PROD
    dp = qwen_design_point(out, clock)
    cfg = _ps_cfg(dp)
    wl = out["workload"][str(CTX_HEAD)]
    macs_tok = wl["weight_macs"] + wl["attention_macs"]
    target = out["budget"]["target_tokens_s"]
    lim = P["cooling"]
    points = {}
    for key in ("ar_batch1", "dflash"):
        pt = dp[key]
        n = pt["users"] * pt["slots"]
        step_macs = pt["macs_per_step"] if pt["drafter"] else n * macs_tok   # drafter MACs: the step record's
        lanes = {s: PS.qwen_point(cfg, s, key) for s in SCENARIOS + (GPU_TENSOR,)}
        r = lanes["B_proposed_production"]
        c = r["die_components_mj_per_token"]
        nonmac_dyn_j = (r["die_dynamic_mj_per_token"] - c["mac_weights"] - c["mac_attention"]) * 1e-3 / DIES
        static_w = sum(r["die_static_w"].values())          # one die
        rates = dict(design=r["design_rate_tokens_s"])
        if key == "ar_batch1":
            rates["target"] = target
        fits = {}
        for which, rate in rates.items():
            mac_rate = step_macs / pt["tokens_per_step"] * rate / DIES      # one die's half of the MACs
            nonmac_w = static_w + nonmac_dyn_j * rate
            fits[which] = dict(tokens_s=round(rate, 1), mac_rate_per_s=mac_rate, die_w_without_macs=round(nonmac_w, 1),
                               die_energy_budget_mj_per_token={cls: round(x["die_limit_w"] / rate * 1e3, 2)
                                                               for cls, x in lim.items()},
                               pj_per_mac_that_fits={cls: round((x["die_limit_w"] - nonmac_w) / mac_rate * 1e12, 3)
                                                     for cls, x in lim.items()})
        points[key] = dict(
            macs_per_step=step_macs, tokens_per_step=pt["tokens_per_step"], die_static_w=round(static_w, 1),
            die_non_mac_dynamic_mj_per_token=round(nonmac_dyn_j * 1e3, 3), at=fits,
            rate_cap_with_free_macs={cls: round((x["die_limit_w"] - static_w) / nonmac_dyn_j, 1) for cls, x in lim.items()},
            lanes={s: dict(pj_per_mac_w8=P["mac_pj"][s][WEIGHT_MAC_FORMAT], pj_per_mac_bf16=P["mac_pj"][s]["bf16"],
                           energy_per_token_mj=round(x["energy_per_token_mj"], 3),
                           die_w_at_design_rate=round(x["die_w_at_design_rate"], 1),
                           cooling=_classes(x["cooling_classes"])) for s, x in lanes.items()})
    kvb = kv_bytes(wl, KV_FMT_SPEC)
    ar, df = points["ar_batch1"], points["dflash"]
    fit_ar = ar["at"]["design"]["pj_per_mac_that_fits"][COOLING_CLASS]
    fit_df = df["at"]["design"]["pj_per_mac_that_fits"][COOLING_CLASS]
    return dict(cooling=lim, cooling_class=COOLING_CLASS,
                basis="per-class die limit of a shipping two-die package (configs/hardware/power_scenarios.json "
                      "cooling); the design class is liquid (GB200 NVL72-class, user decision), air a sensitivity; "
                      "every energy from the same file; per die",
                target_tokens_s=target, macs_per_token=macs_tok, points=points,
                stack_w_at_target=round(kvb * target * 8 * P["hbm_pj_per_bit"]["stack"] * 1e-12, 1),
                mac_requirements=["the lane takes the ROM's weight format: an INT8 weight (exact in BF16) x a BF16 "
                                  "activation into FP32, the per-output-channel BF16 scale applied once per output "
                                  "row after accumulation -- the routed exact BF16 lane with a weight decode, no "
                                  "datapath change (a golden change: the INT8 per-channel checkpoint)",
                                  "operand isolation and clock gating of idle lanes: groups outside an op's tiles, "
                                  "masked elements, idle lane copies",
                                  "accumulation width FP32 (the golden's order), products exact",
                                  f"at the design rate the die's non-MAC power leaves {fit_ar:.3f} pJ/MAC for "
                                  f"autoregressive decoding and {fit_df:.3f} pJ/MAC for the best DFlash "
                                  f"configuration under the {lim[COOLING_CLASS]['die_limit_w']:.1f} W per-die "
                                  f"{COOLING_CLASS} limit (negative: "
                                  "the die is over the limit with free MACs; the die's share of the HBM path binds)"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    out = evaluate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1, default=float) + "\n")
    UTIL_OUT.write_text(json.dumps(utilization(out, out["clock_hz"]), indent=1, default=float) + "\n")
    b = out["budget"]
    print(f"clock {out['clock_hz']/1e9:.4f} GHz; design point {CTX_HEAD} {KV_FMT_SPEC}: target {b['target_cycles']} "
          f"cycles = {b['target_tokens_s']} tok/s ({b['binding']}); weight ceiling {b['ceiling_tokens_s']}")
    print("area", out["area"])
    for k, v in out["rom_token"].items():
        print("rom token", k, v)
    for k, v in out["as_built_calibrated"].items():
        print(f"as built {k}: {v['cycles']} cycles")
    print(json.dumps(out["requirements"], indent=1)[:2500])


if __name__ == "__main__":
    main()
