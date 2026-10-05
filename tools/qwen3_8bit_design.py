#!/usr/bin/env python3
"""The Qwen3-8B ROM design re-derived at 8-bit weights: the evidence behind the two-reticle baseline.

    python3 tools/qwen3_8bit_design.py [--out results/arch/qwen3_8bit_design.json]

STATUS (2026-09-28).  This record priced 8-bit weights against the then-baseline (one 815 mm2 reticle, 3.5-bit
HC1-style weights) and found that they do not fit one reticle; the user then ADOPTED its option O4 (two reticles in
one package over UCIe, every layer split across both dies, 8 HBM3E stacks, 6,144 groups a die, m = 5).
tools/arch_budget_qwen3.py now implements O4 as the baseline (results/arch/qwen3_budget.json), so this tool's inputs
-- the single-reticle baseline it compared against -- no longer exist at HEAD: the record is frozen evidence of the
decision (why 8-bit, why two reticles).  To reproduce it, run this tool at the commit that added the record
(`git log --diff-filter=A --format=%H -- results/arch/qwen3_8bit_design.json`); tests/test_qwen3_8bit_design.py
checks its internal consistency and that O4 in it matches the adopted baseline.  The text below describes the
derivation as it was run.

User decision (2026-09-28): Qwen3-8B uses 8-bit weights; the 3.5-bit HC1-style INT3/INT6 format fails the quality
bar.  Every Qwen ROM figure (tools/arch_budget_qwen3.py, results/arch/qwen3_budget.json, the power scenarios, the
DFlash step record) was derived at 3.5 bits a weight.  This tool re-derives the design at 8 bits WITHOUT touching the
baseline records, so the user can choose a configuration first:

1. CAPACITY.  The exact tensor inventory from the model shapes (tools/hdc_timing.SHAPES, = configs/models/qwen3-8b.json
   total_parameters: 36 layers, the untied embedding and lm_head, the RMSNorm weights) and the DFlash drafter
   (tools/dflash_step_timing.DRAFTER_PARAMS), in the baseline format INT8 weight-only with per-output-channel BF16
   scales, and the alternative FP8 E4M3 with 128 x 128 FP32 block scales.  ROM cells at the repository's
   HC1-referenced density (src/opentallas/roofline.py CimCellAccounting: one select cell per <= 4-bit nibble, the
   cell 1.6x a storage-only mask-ROM bit; an 8-bit weight is 2 cells; a scale or a norm weight is stored at full
   cell width), cross-checked against opentallas.roofline.taalas_hc1_anchor at 8 bits a parameter, and the 3.5-bit
   figure (261.98 mm2) reproduced.
2. FIT.  The reticle's area ledger (tools/arch_budget_qwen3.area_ledger at the baseline: compute share, interconnect,
   overhead, 6 HBM3E PHYs, the KV ring, the stream unit's spill, the drafter's ROM, lane copies).  If the 8-bit
   weights do not fit, the deficit and the options: weights moved to the KV stacks, fewer MAC lanes, two reticles in
   one package over UCIe, and the floorplan-fraction assumptions -- each priced for per-user rate, power and cost.
   NONE IS ADOPTED: the standing decision is one reticle, so the choice is the user's.
3. PERFORMANCE AND POWER per configuration, on the same models as the baseline: the ROM read requirement at 8 bits,
   the per-token chain (RTL-calibrated sequencer model, tools/arch_budget_qwen3.as_built -> tools/hdc_timing, read
   only) against the 8K FP8 KV floor, the DFlash serial step (tools/dflash_step_timing.Machine, measured acceptance),
   energy per token and die power in power scenarios A and B (tools/power_scenarios.qwen_point with the 8-bit weight
   fields), the 549.5 W cooling cap; and the HBM comparator at 8-bit weights (bytes-bound, weights double vs 3.5 bits)
   with its DFlash step, and the ROM / HBM ratios.
4. FIGURE CHANGES: every atlas / docs/ARCH_SPEC_QWEN3.md figure that moves (old -> new per configuration).

MAC lane at 8 bits: an INT8 weight and an FP8 E4M3 weight are both exact in BF16, so the routed exact BF16 x BF16
lane (ot_hdc_matvec) takes either with a format decode and no datapath change; INT8 applies its per-channel scale
once per output row after FP32 accumulation, FP8 its block scale once per 128-element K chunk.  Scenario A prices
every MAC at the routed engine's 3.97 pJ (unchanged); scenario B prices the 8-bit weight MAC at the published
bf16_mult + fp32_add (0.59 pJ, the power_scenarios 'fp8' lane, an upper bound for an 8 x 8-bit significand product),
with int8_mult + fp32_add (0.45 pJ, an INT8 x FP8 lane) as the lower sensitivity.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import arch_budget_qwen3 as QB  # noqa: E402
import dflash_step_timing as DST  # noqa: E402
import power_scenarios as PS  # noqa: E402

SCHEMA = "opentallas.qwen3-8bit-design.v1"
OUT = ROOT / "results/arch/qwen3_8bit_design.json"
TECH = ROOT / "configs/hardware/technology.json"
MODEL = ROOT / "configs/models/qwen3-8b.json"
BASE_REC = ROOT / "results/arch/qwen3_budget.json"
DFLASH_REC = ROOT / "results/speculative/dflash_step_timing.json"

Q = QB.Q
CTX = QB.CTX_HEAD                 # 8K, the user's design context
KV_FMT = QB.KV_FMT_SPEC           # FP8 KV, the baseline
NODE = "N6"
ELEMENT_BITS = 8
CELL_BITS_OF = {"bf16": 16, "fp32": 32}
FP8_BLOCK = 128                   # Qwen's FP8 releases use 128 x 128 weight blocks with FP32 scales
# An HBM row read on the token's dependent path (the embedding row of the token just emitted, when the table lives
# in the KV stacks).  ASSUMED: no HBM latency figure exists in this repository (configs/hardware/
# abi3_cost_rom_array_v1.json hbm.read_latency_cycles says so); 500 ns is a loaded HBM3 random-read latency class.
HBM_ROW_LATENCY_S = 500e-9
UCIE_PHY_MM2 = 10.0               # ASSUMED: one advanced-package UCIe module at 4.2 TB/s a direction (~6.4 mm of edge
                                  # at 5.27 Tb/s/mm, ~1.5 mm deep), per die
REDUCE_ADD_CYCLES = 4             # the FP32 add of a partial sum received over the link (pipelined)
PARTIAL_BYTES = 4                 # the all-reduce adds FP32 partials (tools/hdc_golden.fold adds the dies' FP32 matvec
                                  # outputs in rank order); a BF16 partial would be a golden and quality change
SCALE_MUL_CYCLES = 5              # the per-output-row scale multiply after the K sum (the INT8 contract's C3): the
                                  # qualified rtl/proto/ot_fp32_mul_rne_pipe.sv, 5 register stages, one result a cycle
EMB_ROW_BYTES = QB.Q["H"] + 2     # an INT8 embedding row and its BF16 scale
FC_TP_ROWS = DST.DFLASH_FC[0]     # the drafter's fc output rows, split by rows under TP (each die half, all-gathered)
FLOORPLAN_LOW = dict(interconnect=0.05, overhead=0.06)   # the low ends of technology.json floorplan sweeps (notes)


# -- 1. inventory -----------------------------------------------------------------------------------------------------
def _layer_mats(s=Q):
    per_layer, head = QB.matrices(s)
    return per_layer, head


def inventory():
    """Every stored tensor of the target and the drafter: matrices (n rows x k), the embedding table (V x H, a
    lookup), and 1-D norm weights.  Checked against the model config's parameter count and DRAFTER_PARAMS."""
    L, H, HD, V = Q["L"], Q["H"], Q["HD"], Q["V"]
    per_layer, head = _layer_mats()
    target = [dict(name=f"layer.{k}", n=n, k=kk, count=L, swept=True) for k, (n, kk) in per_layer.items()]
    target += [dict(name="lm_head", n=V, k=H, count=1, swept=True),
               dict(name="embedding", n=V, k=H, count=1, swept=False)]
    target_norms = L * (2 * H + 2 * HD) + H           # input/post-attention norms, q/k norms, final norm
    layer_elems = sum(n * k for n, k in per_layer.values())
    fc_n, fc_k = DST.DFLASH_FC
    drafter = [dict(name=f"drafter.layer.{k}", n=n, k=kk, count=DST.DRAFTER_LAYERS, swept=True)
               for k, (n, kk) in per_layer.items()] + [dict(name="drafter.fc", n=fc_n, k=fc_k, count=1, swept=True)]
    drafter_norms = DST.DRAFTER_PARAMS - DST.DRAFTER_LAYERS * layer_elems - fc_n * fc_k
    tot = sum(m["n"] * m["k"] * m["count"] for m in target) + target_norms
    model_params = json.loads(MODEL.read_text())["total_parameters"]
    assert tot == model_params, (tot, model_params)
    assert drafter_norms == DST.DRAFTER_LAYERS * (2 * H + 2 * HD) + 2 * H, drafter_norms   # + final and fc norms
    return dict(target=target, target_norms=target_norms, drafter=drafter, drafter_norms=drafter_norms,
                target_params=tot, drafter_params=DST.DRAFTER_PARAMS, model_config_total_parameters=model_params)


def scales(m, fmt):
    """(scale count, bits a scale) of one matrix of the inventory in weight format fmt."""
    if fmt == "int8_per_channel":
        return m["n"] * m["count"], CELL_BITS_OF["bf16"]       # one per output row (embedding: one per token row)
    if fmt == "fp8_e4m3_block128":
        return math.ceil(m["n"] / FP8_BLOCK) * math.ceil(m["k"] / FP8_BLOCK) * m["count"], CELL_BITS_OF["fp32"]
    raise ValueError(fmt)


def density():
    """ROM select cells a mm2 at N6 and the ROM read density at 8 bits, from the roofline technology model, with the
    HC1 anchor at 8 bits a parameter as the cross-check."""
    from opentallas.roofline import Technology, taalas_hc1_anchor
    from opentallas.schema import ModelProfile
    tech = Technology.load(TECH)
    storage = tech.rom_bits_per_mm2(NODE).value
    mult = tech.graded("rom", "cim_cell_area_multiplier").value
    width = tech.graded("rom", "cim_bits_per_cell").value
    cells_mm2 = storage / mult
    prof = ModelProfile.load(MODEL)
    a8 = taalas_hc1_anchor(tech, prof, weight_bits_per_parameter=8.0).detail["budget"]
    a35 = taalas_hc1_anchor(tech, prof).detail["budget"]
    cap8 = a8["provenance"]["rom_capacity_density_bits_mm2"]["value"]
    rd8 = a8["provenance"]["rom_read_bandwidth_density_bytes_s_mm2"]["value"]
    eff = json.loads(TECH.read_text())["efficiencies"]["rom_read_bandwidth"]["value"]
    assert abs(cap8 / width - cells_mm2) / cells_mm2 < 1e-9
    return dict(node=NODE, storage_rom_bits_per_mm2=storage, cim_cell_area_multiplier=mult, cim_bits_per_cell=width,
                select_cells_per_mm2=cells_mm2, anchor_8bit_capacity_bits_per_mm2=cap8,
                anchor_8bit_rom_read_bytes_s_per_mm2=rd8, rom_read_efficiency=eff,
                anchor_8bit_rom_mm2_required=prof.total_parameters * 2 / cells_mm2,
                anchor_35bit_rom_mm2=a35["area_split_per_device"]["rom_mm2"],
                anchor_8bit_reasons=a8["area_split_per_device"]["reasons"],
                basis="src/opentallas/roofline.py rom_bits_per_mm2 (N6 6T cell 0.027 um2 x ROM/SRAM cell ratio 0.33 / "
                      "array efficiency 0.52) / cim_cell_area_multiplier 1.6 = select cells a mm2; an 8-bit weight is "
                      "ceil(8 / 4) = 2 cells (CimCellAccounting), a scale or a norm weight bits / 4 cells")


def rom_cells(inv, fmt):
    """Cells by tensor class at ELEMENT_BITS + the format's scales; norms stored BF16."""
    ecells = math.ceil(ELEMENT_BITS / 4)
    out = {}
    for part, mats, norms in (("target", inv["target"], inv["target_norms"]),
                              ("drafter", inv["drafter"], inv["drafter_norms"])):
        for m in mats:
            key = "embedding" if m["name"] == "embedding" else "lm_head" if m["name"] == "lm_head" else part
            ns, sb = scales(m, fmt)
            d = out.setdefault(key, dict(elements=0, scales=0, scale_bytes=0, cells=0, norms=0))
            d["elements"] += m["n"] * m["k"] * m["count"]
            d["scales"] += ns
            d["scale_bytes"] += ns * sb // 8
            d["cells"] += m["n"] * m["k"] * m["count"] * ecells + ns * sb / 4
        out[part]["norms"] = norms
        out[part]["cells"] += norms * CELL_BITS_OF["bf16"] / 4
    return out


def capacity(inv, dens):
    """ROM mm2 and bytes per weight format, and the 3.5-bit baseline reproduced."""
    cm = dens["select_cells_per_mm2"]
    res = {}
    for fmt in ("int8_per_channel", "fp8_e4m3_block128"):
        c = rom_cells(inv, fmt)
        rows = {k: dict(v, mm2=round(v["cells"] / cm, 3), bytes=v["elements"] + v["scale_bytes"] + 2 * v["norms"])
                for k, v in c.items()}
        rows["target_total"] = dict(mm2=round(sum(rows[k]["mm2"] for k in ("target", "lm_head", "embedding")), 3),
                                    bytes=sum(rows[k]["bytes"] for k in ("target", "lm_head", "embedding")))
        res[fmt] = rows
    six = 1 / 6                                   # HC1 3/6-bit mixture at 3.5 bits: (1 - six) x 1 + six x 2 cells
    base = inv["target_params"] * ((1 - six) * 1 + six * 2) / cm
    base_d = DST.DRAFTER_PARAMS * ((1 - six) * 1 + six * 2) / cm
    res["storage_only_rom_mm2_target_int8"] = round(res["int8_per_channel"]["target_total"]["bytes"] * 8 /
                                                    dens["storage_rom_bits_per_mm2"], 1)
    res["baseline_3p5bit"] = dict(target_mm2=round(base, 2), drafter_mm2=round(base_d, 2),
                                  record_rom_mm2=QB.RETICLE["rom_mm2"],
                                  record_drafter_rom_mm2=QB.area_ledger()["drafter_rom_mm2"],
                                  bytes=inv["target_params"] * 3.5 / 8)
    return res


# -- 2. configurations and their area ledgers ------------------------------------------------------------------------
def configurations():
    """The single reticle as specified, and the options.  groups: MAC groups of 16 lanes a die; tp: dies splitting
    every layer (tensor-parallel over UCIe); stacks: HBM3E stacks a die."""
    base = dict(groups=QB.GROUPS_ROM, dies=1, stacks_per_die=QB.ROM_KV_HBM["stacks"], embed_in_hbm=False,
                lm_head_in_hbm=False, drafter=True, floorplan=None, adopt=False)
    C = [
        dict(base, id="C0_single_reticle", label="one reticle as specified: every 8-bit weight in ROM (embedding, "
             "lm_head, 8-bit drafter), 8,192 groups, 6 stacks", option=False),
        dict(base, id="C0b_no_drafter", drafter=False, option=False,
             label="C0 without the DFlash drafter (violates the standing MTP requirement; shows the target alone)"),
        dict(base, id="O1_embedding_in_hbm", embed_in_hbm=True,
             label="the embedding table (a per-token row lookup) moved to the KV stacks"),
        dict(base, id="O2_embedding_and_lm_head_in_hbm", embed_in_hbm=True, lm_head_in_hbm=True,
             label="embedding and lm_head in the KV stacks: the lm_head's 622 MB streamed every token beside the KV"),
    ]
    C += [dict(base, id="O3a_fewer_lanes_all_rom", groups="max_ar",
               label="fewer MAC lanes, every weight in ROM: the most groups (a multiple of 512) that fit"),
          dict(base, id="O3b_fewer_lanes_embedding_in_hbm", groups="max_ar", embed_in_hbm=True,
               label="fewer MAC lanes with the embedding in the KV stacks: the most groups that fit (best "
                     "autoregressive rate)"),
          dict(base, id="O3c_fewer_lanes_embedding_in_hbm_lane_copy", groups="max_dflash", embed_in_hbm=True,
               label="fewer MAC lanes with the embedding in the KV stacks, sized for the best DFlash rate (a lane "
                     "copy fits, so speculation pays)")]
    C.append(dict(base, id="O4_two_reticles_one_package", dies=2, stacks_per_die=4, groups="rom_read",
                  label="two reticles in one CoWoS-L-class package over UCIe, every layer split across both "
                        "(tensor-parallel 2: half the heads, half the FFN, half the vocabulary a die), 4 stacks a die "
                        "(8 a package, the user's per-package rule); each die's MAC groups limited to what its half of "
                        "the ROM can feed at 8 bits"))
    C.append(dict(base, id="O5_floorplan_low_end_embedding_in_hbm", embed_in_hbm=True, floorplan=FLOORPLAN_LOW,
                  label="an ASSUMPTION change, not hardware: interconnect 5% and overhead 6% of the die (the low ends "
                        "of the technology.json floorplan sweeps) with the embedding in the KV stacks"))
    return C


def ledger(cfg, cap, fmt="int8_per_channel"):
    """The per-die area ledger: fixed items as the baseline's, the ROM at 8 bits, lane copies in what is left."""
    a0 = QB.area_ledger()
    R = QB.RETICLE
    rows = cap[fmt]
    dies = cfg["dies"]
    groups = cfg["groups"]
    compute = R["compute_mm2"] * groups / QB.GROUPS_ROM            # the compute share scales with the MAC groups
    fp = cfg["floorplan"]
    inter = R["interconnect_mm2"] if fp is None else fp["interconnect"] * R["die_mm2"]
    over = R["overhead_mm2"] if fp is None else fp["overhead"] * R["die_mm2"]
    phy = cfg["stacks_per_die"] * QB.HBM["phy_mm2_per_stack"]
    ucie = UCIE_PHY_MM2 if dies > 1 else 0.0
    rom = rows["target"]["mm2"] + rows["lm_head"]["mm2"] * (not cfg["lm_head_in_hbm"]) + \
        rows["embedding"]["mm2"] * (not cfg["embed_in_hbm"])
    drafter = rows["drafter"]["mm2"] if cfg["drafter"] else 0.0
    fixed = compute + inter + over + phy + ucie + a0["kv_prefetch_buffer_mm2"] + a0["stream_unit_spill_mm2"]
    rom_die, drafter_die = rom / dies, drafter / dies
    rest = R["die_mm2"] - fixed - rom_die - drafter_die
    copy_mm2 = QB.LANE_COPY_UM2 * groups * QB.W * 1e-6
    copies = max(0, int(rest // copy_mm2)) if rest > 0 else 0
    return dict(die_mm2=R["die_mm2"], dies=dies, groups_per_die=groups, lanes_per_die=groups * QB.W,
                compute_mm2=round(compute, 2), interconnect_mm2=round(inter, 2), overhead_mm2=round(over, 2),
                hbm_phy_mm2=phy, ucie_phy_mm2=ucie, kv_ring_mm2=a0["kv_prefetch_buffer_mm2"],
                stream_unit_spill_mm2=a0["stream_unit_spill_mm2"], target_rom_mm2=round(rom_die, 2),
                drafter_rom_mm2=round(drafter_die, 2), lane_copy_mm2=round(copy_mm2, 2), lane_copies_added=copies,
                lane_multiplier_m=1 + copies, slack_mm2=round(rest - copies * copy_mm2, 2),
                fits=rest >= 0, deficit_mm2=round(max(0.0, -rest), 2))


LANE_SWEEP_GROUPS = range(QB.GROUPS_ROM, 2047, -512)


def lane_sweep(cfg, cap, clock, basis, tau):
    """Every group count (a multiple of 512, 8,192 down to 2,048) that fits with this placement: its lane
    multiplier, autoregressive and best DFlash rates."""
    rows = []
    for g in LANE_SWEEP_GROUPS:
        c = dict(cfg, groups=g)
        led = ledger(c, cap)
        if not led["fits"]:
            continue
        pf = perf(c, led, cap, clock, basis, tau)
        rows.append(dict(groups=g, lane_multiplier_m=led["lane_multiplier_m"], slack_mm2=led["slack_mm2"],
                         rom_read_ok=pf["rom_read"]["ok"],
                         ar_tokens_s=pf["ar_tokens_s"], dflash_tokens_s=pf["dflash"]["best"]["tokens_s"],
                         dflash_block=pf["dflash"]["best"]["block"]))
    return rows


def pick_groups(sel, sweep):
    key = "ar_tokens_s" if sel == "max_ar" else "dflash_tokens_s"
    return max((r for r in sweep if r["rom_read_ok"]), key=lambda r: (r[key], r["groups"]))["groups"]


def most_groups_the_rom_feeds(cfg, cap, clock):
    """The most groups a die (a multiple of 512) whose 8-bit weight read its own ROM sustains."""
    for g in LANE_SWEEP_GROUPS:
        c = dict(cfg, groups=g)
        led = ledger(c, cap)
        if led["fits"] and rom_read(c, led, cap, clock)["ok"]:
            return g
    raise AssertionError("no group count is fed")


# -- 3. performance -------------------------------------------------------------------------------------------------
def die_shape(tp):
    """One die's tensor-parallel slice of the model (tools/hdc_golden.Model.die_slices, Megatron): its query and KV
    heads, FFN rows and vocabulary; the hidden size, the residual stream and the norms whole (replicated)."""
    if tp == 1:
        return Q
    return dict(Q, NH=Q["NH"] // tp, KV=Q["KV"] // tp, FF=Q["FF"] // tp, V=Q["V"] // tp)


def _spec_chain(groups, shape=None, golden_pv=False):
    """tools/arch_budget_qwen3.evaluate's '<ctx>/spec' dependency chain at this many groups (of one die's slice under
    TP), with the INT8 contract's per-row scale multiply after every matrix (SCALE_MUL_CYCLES on each 'mv' stage's
    exposed latency).  golden_pv: the golden's power-of-two P.V split (the TP-2 design point, 6,144 groups)."""
    s = Q if shape is None else shape
    rows, tot = QB.chain(CTX, groups, QB.SPEC_SU_WIDTH, dict(QB.AS_BUILT_LAT, seq_gap=1), "ksplit", True,
                         stages=QB.LAYER_STAGES_SPEC, shape=shape, golden_pv=golden_pv)
    for r in rows:
        if r["kind"] == "mv":
            r["exposed_latency"] += SCALE_MUL_CYCLES
            tot["latency"] += SCALE_MUL_CYCLES
    per_tok = {k: v * Q["L"] for k, v in tot.items()}
    per_tok["weights"] += QB.mv_cycles(s["V"], s["H"], groups)[0]
    return dict(context=CTX, su_width=QB.SPEC_SU_WIDTH, components=per_tok, stages=rows,
                token_cycles=sum(per_tok.values()))


def _link(clock):
    L = json.loads(TECH.read_text())["links"]["rom_package_ucie"]
    return L["hop_latency_s"]["value"] * clock, L["bytes_s"]["value"] / clock     # hop cycles, bytes a cycle


def tp_exchanges(clock, tp, slots=1, phase="target"):
    """The UCIe exchanges on one pass's dependency chain under TP (every exchange is serial: the residual add needs
    the other die's partial and the next norm's sum of squares the whole residual).  target: 2 all-reduces a layer
    (after o and after down) of H FP32 partials a slot, and the argmax gather of the vocabulary halves (priced as an
    exchange, as docs/ARCH_QWEN3_O4_RTL_SPEC.md section 4 does), each hop + transfer + the receive-side add; then the
    embedding-row handoff (the die owning the token's vocabulary row sends it: hop + the INT8 rows).  draft: the fc
    output all-gather, 2 all-reduces in each drafter layer and the draft argmax gather, priced the same way (the
    all-gather's 8 KiB a slot at an all-reduce's 16 KiB: conservative), and the bonus token's embedding row."""
    if tp == 1:
        return dict(exchanges=0, per_exchange_cycles=0, exchange_cycles=0, embedding_handoff_cycles=0, cycles=0,
                    bytes_per_direction=0)
    hop, bpc = _link(clock)
    part = slots * Q["H"] * PARTIAL_BYTES
    per = hop + part / bpc + REDUCE_ADD_CYCLES
    if phase == "target":
        n, rows = 2 * Q["L"] + 1, slots
        nbytes = 2 * Q["L"] * part + 8 * slots + rows * EMB_ROW_BYTES
    else:
        n, rows = 2 * DST.DRAFTER_LAYERS + 2, 1
        nbytes = slots * FC_TP_ROWS // tp * PARTIAL_BYTES + 2 * DST.DRAFTER_LAYERS * part + 8 * slots + EMB_ROW_BYTES
    emb = hop + rows * EMB_ROW_BYTES / bpc
    return dict(exchanges=n, slots=slots, per_exchange_cycles=round(per, 2), exchange_cycles=math.ceil(n * per),
                embedding_handoff_cycles=round(emb, 2), cycles=math.ceil(n * per + emb),
                bytes_per_direction=nbytes, partial_bytes_per_slot=Q["H"] * PARTIAL_BYTES)


def k_split_check(groups, tp):
    """The golden's K-split (tools/hdc_golden.split_for: fractional packing, ceil(tiles x S / G)) against the RTL's
    (arch_budget_qwen3.split_rounds: floor(G / S) whole tiles a round) for every matrix one die runs, and the engine
    cycles of the golden's split executed under the RTL's tiling (the price when the RTL adopts the golden's order)."""
    import hdc_golden as G
    s = die_shape(tp)
    per_layer, head = QB.matrices(s)
    mats = {**per_layer, **head, "drafter_fc": (FC_TP_ROWS // tp, DST.DFLASH_FC[1])}
    rows = []
    for name, (n, k) in mats.items():
        sg = G.split_for(n, k, groups)
        sr, rounds, kc = QB.split_rounds(n, k, groups)
        tiles = -(-n // (QB.W * QB.IL))
        rows.append(dict(matrix=name, n=n, k=k, golden_split=sg, rtl_split=sr, rtl_cycles=rounds * kc * QB.IL,
                         golden_split_cycles_rtl_tiling=-(-tiles // (groups // sg)) * (k // sg) * QB.IL))
    return rows


def rom_read(cfg, led, cap, clock, fmt="int8_per_channel"):
    """The ROM read the lanes need at 8 bits against what the die's swept ROM supplies (the repository's read
    density at 8 bits x its sustained efficiency).  Lane copies share their group's weight word and need none."""
    rows = cap[fmt]
    swept_mm2 = (rows["target"]["mm2"] + rows["lm_head"]["mm2"] * (not cfg["lm_head_in_hbm"])) / cfg["dies"]
    need = led["lanes_per_die"] * ELEMENT_BITS / 8 * clock
    have = swept_mm2 * QB_READ[0] * QB_READ[1]
    return dict(required_bytes_per_cycle_per_die=led["lanes_per_die"] * ELEMENT_BITS // 8,
                required_bytes_s_per_die=need, available_bytes_s_per_die=have, headroom=round(have / need, 3),
                ok=have >= need,
                basis="one 8-bit weight a lane a cycle; available = swept ROM mm2 a die x the 8-bit read density "
                      "(taalas_hc1_anchor at 8 bits a parameter) x rom_read_bandwidth efficiency 0.75")


class _Step(DST.Machine):
    """The serial DFlash step of tools/dflash_step_timing.Machine with the configuration's extras: weights read from
    the KV stacks once a phase (lm_head: the verify's and the draft's shared head), the dependent embedding-row read
    once a phase, and the tensor-parallel exchanges once a layer."""

    def __init__(self, basis, extra_hbm_cycles, extra_chain_cycles, tp=1, clock=None, fc_mv=None, kvproj_mv=None):
        super().__init__(basis, CTX, KV_FMT)
        self.xh = extra_hbm_cycles
        self.xc = extra_chain_cycles
        self.tp, self.clk = tp, clock
        if fc_mv is not None:            # one die's slice at the golden's K-split (TP)
            self.fc_mv = fc_mv
        if kvproj_mv is not None:
            self.kvproj_mv = kvproj_mv

    def verify(self, B, m):
        v = super().verify(B, m)
        comp, kv = v["compute"] + self.xc + tp_exchanges(self.clk, self.tp, B)["cycles"], v["kv"] + self.xh
        return dict(compute=comp, kv=kv, cycles=max(comp, kv))

    def draft(self, B, m, ctx_positions=None):
        d = super().draft(B, m, ctx_positions)
        comp, kv = d["compute"] + self.xc + tp_exchanges(self.clk, self.tp, B, "draft")["cycles"], d["kv"] + self.xh
        return dict(d, compute=comp, kv=kv, cycles=max(comp, kv))


def perf(cfg, led, cap, clock, basis, tau, fmt="int8_per_channel"):
    """Per-token rates.  Under TP (dies > 1) each die runs its slice of every layer on its own groups, so the chain is
    ONE die's: the RTL-calibrated replay of the die's slice (arch_budget_qwen3.as_built with die_shape) plus the
    serial UCIe exchanges (tp_exchanges, FP32 partials) and the scale multiply after every matrix; the DFlash step on
    the die's specification chain at the golden's K-splits, with the verify's and the draft's exchanges at their slot
    counts.  The throughput figures (weight sweep, MACs) are the package's."""
    tp = cfg["dies"]
    g_die = led["groups_per_die"]
    g_eff = g_die * tp                                 # the package's groups (sweep and MAC throughput)
    lanes_eff = g_eff * QB.W
    shape = die_shape(tp)
    wl = QB.workload(CTX, weight_bits=ELEMENT_BITS)
    rows = cap[fmt]
    stacks = cfg["stacks_per_die"] * tp
    bw = stacks * QB.HBM["stack_bytes_s"] * QB.HBM["efficiency"]
    kv_b = QB.kv_bytes(wl, KV_FMT)
    lm_b = rows["lm_head"]["bytes"] if cfg["lm_head_in_hbm"] else 0
    emb_row = (Q["H"] + 2) if cfg["embed_in_hbm"] else 0      # one INT8 row and its BF16 scale
    hbm_w = lm_b + emb_row
    kv_cyc = kv_b / bw * clock
    hbm_cyc = (kv_b + hbm_w) / bw * clock
    tpx = tp_exchanges(clock, tp)
    xc = (HBM_ROW_LATENCY_S * clock if cfg["embed_in_hbm"] else 0) + tpx["cycles"]
    ab = QB.as_built(CTX, groups=g_die, shape=None if tp == 1 else shape)
    scale_cyc = SCALE_MUL_CYCLES * (4 * Q["L"] + 1)    # after each of a layer's 4 matrices and the lm_head
    cal = ab["cycles"] + scale_cyc
    chain = cal + xc
    step = max(chain, hbm_cyc)
    # ROM read at 8 bits: one weight a lane a cycle, from the swept matrices' ROM (the embedding is not swept)
    rr = rom_read(cfg, led, cap, clock, fmt)
    # DFlash: the serial step at this engine, KV floor and lane multiplier
    b = copy.deepcopy(basis)
    b["rom_design"] = dict(b["rom_design"], groups=g_die, lanes=g_die * QB.W)
    ch = _spec_chain(g_die, None if tp == 1 else shape, golden_pv=True)
    b["dependency_chain"][f"{CTX}/spec"] = ch
    b["rom_token"] = dict(b["rom_token"])
    b["rom_token"][f"{CTX}/{KV_FMT}"] = dict(b["rom_token"][f"{CTX}/{KV_FMT}"], kv_stream_cycles=round(kv_cyc))
    ks = k_split_check(g_die, tp)
    over = {}
    if tp > 1:
        # one die's slices at the golden's K-split: the target's agree with the RTL rule (asserted); the drafter's fc
        # does not at 6,144 groups, and is priced at the golden's split under the RTL's whole-tile rounds
        assert all(r["golden_split"] == r["rtl_split"] for r in ks if r["matrix"] != "drafter_fc"), ks
        fc = next(r for r in ks if r["matrix"] == "drafter_fc")
        over = dict(fc_mv=fc["golden_split_cycles_rtl_tiling"],
                    kvproj_mv=QB.mv_cycles(2 * shape["KV"] * Q["HD"], Q["H"], g_die)[0])
    mc = _Step(b, hbm_cyc - kv_cyc if lm_b else 0, HBM_ROW_LATENCY_S * clock if cfg["embed_in_hbm"] else 0,
               tp=tp, clock=clock, **over)
    m = led["lane_multiplier_m"]
    sweep = []
    for B in DST.BLOCKS:
        if B not in tau or (B > 1 and not cfg["drafter"]):
            continue
        s = mc.serial_step(B, m)
        t = tau[B]
        sweep.append(dict(block=B, tokens_per_step=t["direct"], tokens_per_step_band=t["direct_mean_of_workloads"],
                          step_cycles=round(s["cycles"]), draft_cycles=round(s["draft"]),
                          verify_cycles=round(s["verify"]), commit_cycles=s["commit"],
                          tokens_s=round(t["direct"] * clock / s["cycles"], 1),
                          tokens_s_band=round(t["direct_mean_of_workloads"] * clock / s["cycles"], 1),
                          **mc.step_macs(B, CTX)))
    best = max(sweep, key=lambda r: r["tokens_s"])
    res_tp = {}
    if tp > 1:
        import hdc_golden as G
        B, t = best["block"], tau[best["block"]]
        vx, dx = tp_exchanges(clock, tp, B), tp_exchanges(clock, tp, B, "draft")
        # the verify on the calibrated core: the calibrated plain chain plus the specification model's extra-slot work
        # at this m (the shipped program has no verify slots, so the extra slots are the spec model's)
        extra = mc.verify(B, m)["compute"] - vx["cycles"] - (mc.verify(1, 1)["compute"] - tpx["cycles"])
        v_cal = max(cal + vx["cycles"] + extra, mc.verify(B, m)["kv"])
        s_cal = best["draft_cycles"] + v_cal + best["commit_cycles"]
        res_tp = dict(
            tp=tp, groups_per_die=g_die, die_shape={k: shape[k] for k in ("NH", "KV", "FF", "V", "H")},
            calibrated_die_replay_cycles=ab["cycles"], layer_chain_cycles=ab["layer_chain"]["cycles"],
            layer_stages=ab["layer_chain"]["stages"], unit_busy=ab["unit_busy"],
            scale_multiply=dict(cycles_per_token=scale_cyc, pipe_cycles=SCALE_MUL_CYCLES,
                                matrices_per_token=4 * Q["L"] + 1),
            ucie_ar=tpx, ucie_verify=vx, ucie_draft=dx,
            ucie_bytes_per_step_per_direction=dict(ar=tpx["bytes_per_direction"],
                                                   dflash=vx["bytes_per_direction"] + dx["bytes_per_direction"]),
            k_split=ks, k_split_divergent=[r["matrix"] for r in ks if r["golden_split"] != r["rtl_split"]],
            attention_splits_golden=dict(zip(("scores", "pv"), G.attn_splits(Q["HD"], g_die))),
            verify_calibrated_estimate=dict(block=B, verify_cycles=round(v_cal), step_cycles=round(s_cal),
                                            tokens_s=round(t["direct"] * clock / s_cal, 1)))
    return dict(
        engine_groups=g_eff, engine_lanes=lanes_eff, hbm_stacks_total=stacks, hbm_sustained_bytes_s=bw,
        weight_sweep_ideal_cycles=round(wl["weight_macs"] / lanes_eff),
        weight_sweep_tiled_cycles=round(wl["weight_macs"] / lanes_eff / QB.tiling_eff(g_eff)),
        rom_read=rr,
        kv_bytes_per_token=kv_b, hbm_weight_bytes_per_token=hbm_w, kv_floor_cycles=round(kv_cyc),
        hbm_stream_cycles=round(hbm_cyc), calibrated_chain_cycles=cal, extra_chain_cycles=round(xc),
        ar_step_cycles=round(step), ar_tokens_s=round(clock / step, 1),
        ar_binding="hbm_stream" if hbm_cyc >= chain else "compute_chain",
        spec_chain_cycles=round(ch["token_cycles"]), scale_multiply_cycles=scale_cyc,
        dflash=dict(lane_multiplier_m=m, plain_cycles=mc.plain(), best=best, sweep=sweep,
                    speedup_over_plain=round(best["tokens_s"] * mc.plain() / clock, 3)),
        **({"tp": res_tp} if res_tp else {}))


QB_READ = [0.0, 0.0]              # (8-bit read density, efficiency), set by evaluate()


# -- power -------------------------------------------------------------------------------------------------------
LANE_SCEN = (("A_measured_implementation", "A_measured_implementation", "fp8"),
             ("B_proposed_production", "B_proposed_production", "fp8"),
             ("B_int8xfp8_lane_lower", "B_proposed_production", "w4a8"))


def design_point(cfg, led, pf, cap, clock, fmt="int8_per_channel"):
    """The configuration in tools/power_scenarios' Qwen design-point schema, summed over the package's dies."""
    n = cfg["dies"]
    rows = cap[fmt]
    wl = QB.workload(CTX)
    swept_scale = rows["target"]["scale_bytes"] + rows["lm_head"]["scale_bytes"] * (not cfg["lm_head_in_hbm"])
    b = pf["dflash"]["best"]
    ucie = pf["tp"]["ucie_bytes_per_step_per_direction"] if "tp" in pf else dict(ar=0, dflash=0)
    one = dict(users=1, slots=1, drafter=False, lane_copies_on=0, tokens_per_step=1,
               ucie_bytes_per_direction=ucie["ar"])
    dp = dict(context=CTX, kv_format_bytes_per_elem=QB.KV_FORMATS[KV_FMT], clock_hz=clock,
              hbm_stacks=pf["hbm_stacks_total"], dies_per_package=1, weight_bits=ELEMENT_BITS,
              drafter_weight_bits=ELEMENT_BITS, weight_scale_bytes=swept_scale,
              ar_batch1=dict(one, step_cycles=pf["ar_step_cycles"], hbm_weight_bytes=pf["hbm_weight_bytes_per_token"]),
              area_mm2=dict(compute=n * led["compute_mm2"], interconnect=n * led["interconnect_mm2"],
                            overhead=n * led["overhead_mm2"], hbm_phy=n * (led["hbm_phy_mm2"] + led["ucie_phy_mm2"]),
                            stream_unit_spill=n * led["stream_unit_spill_mm2"], lane_copy=n * led["lane_copy_mm2"],
                            lane_multiplier_m=led["lane_multiplier_m"], rom=n * led["target_rom_mm2"],
                            drafter_rom=n * led["drafter_rom_mm2"], sram=n * led["kv_ring_mm2"]))
    if b["block"] > 1:
        dp["dflash"] = dict(block=b["block"], slots=b["block"], users=1, drafter=True,
                            tokens_per_step=b["tokens_per_step"], step_cycles=b["step_cycles"],
                            lane_copies_on=min(led["lane_multiplier_m"], b["block"]) - 1,
                            ucie_bytes_per_direction=ucie["dflash"],
                            hbm_weight_bytes=2 * pf["hbm_weight_bytes_per_token"],
                            **{k: b[k] for k in ("draft_weight_macs", "draft_attention_macs", "verify_weight_macs",
                                                 "verify_attention_macs", "macs_per_step")})
    assert wl["weight_macs"] == b["verify_weight_macs"] / b["block"]
    return dp


def price(cfg, dp, cfgps):
    """Energy per token, die power and cooling-capped rate per lane scenario.  Two dies: the energy is the package's
    (both dies' static, one token's dynamic work, UCIe exchanges), the power a die is half, against the two-die
    package's per-die limit."""
    n = cfg["dies"]
    res = {}
    lim = PS.cooling_limits(cfgps)
    link_j_bit = PS.val(cfgps["die"]["link_j_per_bit"]["ucie"])
    for tag, scen, wfmt in LANE_SCEN:
        c = copy.deepcopy(cfgps)
        c["design_points"]["qwen3"] = dict(dp, weight_mac_format=wfmt)
        out = {}
        for key in [k for k in ("ar_batch1", "dflash") if k in dp]:
            r = PS.qwen_point(c, scen, key)
            rate = r["design_rate_tokens_s"]
            static = sum(r["die_static_w"].values())
            dyn = r["die_dynamic_mj_per_token"] * 1e-3
            if n > 1:          # the TP exchanges over UCIe, both directions: a step's bytes over its tokens
                dyn += 2 * 8 * link_j_bit * dp[key]["ucie_bytes_per_direction"] / dp[key]["tokens_per_step"]
            stk = r["stack_energy_per_token_mj"] * 1e-3
            stk_high = r["stacks_w_high"] / rate
            logic = PS._qwen_areas(dp, 0)["logic"]
            caps = PS._class_caps(cfgps, n, static / n, dyn / n, stk_high / n, rate, logic / n)
            die_w = (static + dyn * rate) / n
            out[key] = dict(tokens_s=round(rate, 1), energy_per_token_mj=round((dyn + static / rate + stk) * 1e3, 3),
                            die_energy_per_token_mj=round((dyn + static / rate) * 1e3, 3),
                            stack_energy_per_token_mj=round(stk * 1e3, 3),
                            die_components_mj_per_token={k: round(v, 4) for k, v in
                                                         r["die_components_mj_per_token"].items()},
                            static_w_package=round(static, 2), die_w_each=round(die_w, 1), dies=n,
                            cooling_die_limit_w=round(lim["air"][str(n)]["die_w"], 1),
                            over_cooling=round(die_w / lim["air"][str(n)]["die_w"], 3),
                            capped_tokens_s={k: round(v["capped_rate"], 1) for k, v in caps.items()},
                            binds={k: v["binds"] for k, v in caps.items()})
        res[tag] = out
    return res


# -- HBM comparator at 8-bit weights ------------------------------------------------------------------------------------
def hbm_comparator(out, clock, basis, tau, cap):
    wl = QB.workload(CTX)
    res = {}
    for fmt, prefix in (("int8_per_channel", "w8_"), ("fp8_e4m3_block128", "w8fp8_")):
        sb = cap[fmt]["target"]["scale_bytes"] + cap[fmt]["lm_head"]["scale_bytes"]
        bpp = 1 + sb / wl["weight_macs"]
        scen = {tag: QB._hbm_comparator(out, clock, s, formats=((fmt, bpp, w, prefix),))
                for tag, s, w in LANE_SCEN}
        mc = DST.Machine(basis, CTX, KV_FMT)
        p = mc.hbm_step(1, bpp)
        rows = []
        for B in DST.BLOCKS:
            if B == 1 or B not in tau:
                continue
            s = mc.hbm_step(B, bpp)
            rows.append(dict(block=B, tokens_per_step=tau[B]["direct"], step_us=round(s["seconds"] * 1e6, 2),
                             binding=s["binding"], tokens_s=round(tau[B]["direct"] / s["seconds"], 1)))
        res[fmt] = dict(weight_bytes_per_mac=bpp, weight_bytes_per_token=wl["weight_macs"] * bpp,
                        ar_batch1_tokens_s=round(1 / p["seconds"], 1),
                        dflash_best=max(rows, key=lambda r: r["tokens_s"]), dflash_sweep=rows, power=scen)
    return res


# -- 4. figure changes ----------------------------------------------------------------------------------------------
def figure_changes(base, dfl, res):
    """Atlas / ARCH_SPEC_QWEN3 figures that move at 8 bits: (figure, where, record path, old, new by configuration)."""
    pp = base["power_production"]["scenarios"]
    bB, bA = pp["B_proposed_production"], pp["A_measured_implementation"]
    h8 = res["hbm_comparator_8bit"]["int8_per_channel"]
    cfgs = res["configurations"]

    def per(f):
        return {k: f(v) for k, v in cfgs.items()}

    def pw(v, scen, key, field):
        p = v["power"][scen]
        return p[key][field] if key in p else p["ar_batch1"][field]

    rows = [
        ("ROM area for the target's weights, mm2", "ARCH_SPEC §0 (262.0), atlas area table",
         "reticle.rom_mm2", QB.RETICLE["rom_mm2"], per(lambda v: v["ledger"]["target_rom_mm2"] * v["ledger"]["dies"])),
        ("DFlash drafter ROM, mm2 (1.05 B parameters)", "ARCH_SPEC §4 (33.5 at 3.5 bits), atlas area table",
         "area.drafter_rom_mm2", base["area"]["drafter_rom_mm2"],
         per(lambda v: v["ledger"]["drafter_rom_mm2"] * v["ledger"]["dies"])),
        ("lane multiplier m (lane copies + 1)", "ARCH_SPEC §4/§5/§9 (m = 3), atlas", "area.lane_multiplier_m",
         base["area"]["lane_multiplier_m"], per(lambda v: v["ledger"]["lane_multiplier_m"])),
        ("area slack, mm2 a die", "ARCH_SPEC §4 (8.6)", "area.slack_mm2", base["area"]["slack_mm2"],
         per(lambda v: v["ledger"]["slack_mm2"] if v["ledger"]["fits"] else -v["ledger"]["deficit_mm2"])),
        ("MAC lanes a die", "ARCH_SPEC §5 (131,072)", "rom_design.lanes", QB.LANES_ROM,
         per(lambda v: v["ledger"]["lanes_per_die"])),
        ("ROM read bytes a cycle a die", "ARCH_SPEC requirements", "requirements.rom_read_bytes_per_cycle",
         base["requirements"]["rom_read_bytes_per_cycle"]["requirement"],
         per(lambda v: v["performance"]["rom_read"]["required_bytes_per_cycle_per_die"])),
        ("autoregressive design rate, tok/s (8K FP8 KV)", "ARCH_SPEC §6/§11, atlas S3 8,910",
         "as_built_calibrated.8192.cycles", round(base["clock_hz"] / base["power_production"]["design_point"]
                                                 ["ar_batch1"]["step_cycles"], 1),
         per(lambda v: v["performance"]["ar_tokens_s"])),
        ("DFlash design rate, tok/s (best block)", "ARCH_SPEC §9 (13,052 at block 3, m = 3), atlas headline",
         "results/speculative/dflash_step_timing.json#rom.8192/fp8/m3.best.tokens_s",
         dfl["rom"]["8192/fp8/m3"]["best"]["tokens_s"], per(lambda v: v["performance"]["dflash"]["best"]["tokens_s"])),
        ("DFlash best block", "ARCH_SPEC §9", "dflash best.block", dfl["rom"]["8192/fp8/m3"]["best"]["block"],
         per(lambda v: v["performance"]["dflash"]["best"]["block"])),
        ("energy per token, ROM AR, scenario B, mJ", "ARCH_SPEC §11.2 (88.1), atlas",
         "power_production.scenarios.B_proposed_production.rom.ar_batch1.energy_per_token_mj",
         bB["rom"]["ar_batch1"]["energy_per_token_mj"],
         per(lambda v: pw(v, "B_proposed_production", "ar_batch1", "energy_per_token_mj"))),
        ("energy per token, ROM AR, scenario A, mJ", "ARCH_SPEC §11.2 (123.0), atlas",
         "power_production.scenarios.A_measured_implementation.rom.ar_batch1.energy_per_token_mj",
         bA["rom"]["ar_batch1"]["energy_per_token_mj"],
         per(lambda v: pw(v, "A_measured_implementation", "ar_batch1", "energy_per_token_mj"))),
        ("energy per token, ROM DFlash, scenario B / A, mJ", "ARCH_SPEC §11.2 (53.6 / 108.3), atlas",
         "power_production.scenarios.*.rom.dflash_block3.energy_per_token_mj",
         [bB["rom"]["dflash_block3"]["energy_per_token_mj"], bA["rom"]["dflash_block3"]["energy_per_token_mj"]],
         per(lambda v: [pw(v, "B_proposed_production", "dflash", "energy_per_token_mj"),
                        pw(v, "A_measured_implementation", "dflash", "energy_per_token_mj")])),
        ("die power at the AR design rate, B / A, W (each die)", "ARCH_SPEC §11.2 (636.6 / 947.1), atlas",
         "power_production.scenarios.*.rom.ar_batch1.die_w",
         [bB["rom"]["ar_batch1"]["die_w"], bA["rom"]["ar_batch1"]["die_w"]],
         per(lambda v: [pw(v, "B_proposed_production", "ar_batch1", "die_w_each"),
                        pw(v, "A_measured_implementation", "ar_batch1", "die_w_each")])),
        ("die power at the DFlash design rate, B / A, W (each die)", "ARCH_SPEC §11.2 (590.0 / 1,303.7), atlas",
         "power_production.scenarios.*.rom.dflash_block3.die_w",
         [bB["rom"]["dflash_block3"]["die_w"], bA["rom"]["dflash_block3"]["die_w"]],
         per(lambda v: [pw(v, "B_proposed_production", "dflash", "die_w_each"),
                        pw(v, "A_measured_implementation", "dflash", "die_w_each")])),
        ("cooling-capped AR rate, B / A, tok/s", "ARCH_SPEC §11.2/§11.3 (7,442 / 4,689), atlas",
         "power_production.scenarios.*.rom.ar_batch1.cooling.air.capped_tokens_s",
         [bB["rom"]["ar_batch1"]["cooling"]["air"]["capped_tokens_s"],
          bA["rom"]["ar_batch1"]["cooling"]["air"]["capped_tokens_s"]],
         per(lambda v: [pw(v, "B_proposed_production", "ar_batch1", "capped_tokens_s")["air"],
                        pw(v, "A_measured_implementation", "ar_batch1", "capped_tokens_s")["air"]])),
        ("cooling-capped DFlash rate, B / A, tok/s", "ARCH_SPEC §11.2/§11.3 (11,925 / 4,731), atlas headline",
         "power_production.scenarios.*.rom.dflash_block3.cooling.air.capped_tokens_s",
         [bB["rom"]["dflash_block3"]["cooling"]["air"]["capped_tokens_s"],
          bA["rom"]["dflash_block3"]["cooling"]["air"]["capped_tokens_s"]],
         per(lambda v: [pw(v, "B_proposed_production", "dflash", "capped_tokens_s")["air"],
                        pw(v, "A_measured_implementation", "dflash", "capped_tokens_s")["air"]])),
        ("scenario-B weight MAC energy, pJ", "ARCH_SPEC §11.3 (W4A8 0.45), atlas lane rows", "mac_pj.w4a8",
         bB["mac_pj"]["w4a8"], bB["mac_pj"]["fp8"]),
    ]
    out = [dict(figure=f, where=w, record=r, old=o, new=n) for f, w, r, o, n in rows]
    hb = h8["power"]
    out += [
        dict(figure="HBM comparator, matched weight format, batch-1 rate, tok/s",
             where="ARCH_SPEC §1 (1,379), §9, atlas rate ladder 'HDC-HBM, 3.5-bit'",
             record="hbm_comparator.8192.rom_format_3.5b.tokens_s",
             old=base["hbm_comparator"]["8192"]["rom_format_3.5b"]["tokens_s"], new=h8["ar_batch1_tokens_s"]),
        dict(figure="HBM comparator, matched format, DFlash best, tok/s", where="ARCH_SPEC §9 (3,762), atlas",
             record="results/speculative/dflash_step_timing.json#hbm.rom_format_3.5b.best.tokens_s",
             old=dfl["hbm"]["rom_format_3.5b"]["best"]["tokens_s"], new=h8["dflash_best"]["tokens_s"]),
        dict(figure="HBM comparator, matched format, batch-1 energy B / A, mJ",
             where="ARCH_SPEC §11.2 (560.4 / 595.2), atlas Table 8-R1b",
             record="power_production.scenarios.*.hbm_comparator.rom35_batch1.energy_per_token_mj",
             old=[bB["hbm_comparator"]["rom35_batch1"]["energy_per_token_mj"],
                  bA["hbm_comparator"]["rom35_batch1"]["energy_per_token_mj"]],
             new=[hb["B_proposed_production"]["w8_batch1"]["energy_per_token_mj"],
                  hb["A_measured_implementation"]["w8_batch1"]["energy_per_token_mj"]]),
        dict(figure="HBM comparator, matched format, batch 16 / 128 rate, tok/s", where="ARCH_SPEC §11.2 (6,659 / 8,574)",
             record="power_production.scenarios.B_proposed_production.hbm_comparator.rom35_batch{16,128}.tokens_s",
             old=[bB["hbm_comparator"]["rom35_batch16"]["tokens_s"], bB["hbm_comparator"]["rom35_batch128"]["tokens_s"]],
             new=[hb["B_proposed_production"]["w8_batch16"]["tokens_s"],
                  hb["B_proposed_production"]["w8_batch128"]["tokens_s"]]),
        dict(figure="energy ratio HBM (matched format) / ROM, batch 1, B / A",
             where="ARCH_SPEC §11.2 (6.36x / 4.84x), atlas (6.4x)",
             record="power_production.scenarios.*.ratios_batch1.hbm_rom_format_over_rom",
             old=[bB["ratios_batch1"]["hbm_rom_format_over_rom"], bA["ratios_batch1"]["hbm_rom_format_over_rom"]],
             new=per(lambda v: [v["ratios"]["energy_ar_hbm_over_rom"]["B_proposed_production"],
                                v["ratios"]["energy_ar_hbm_over_rom"]["A_measured_implementation"]])),
        dict(figure="rate ratio ROM / HBM (matched format), AR design rates", where="atlas (6.5x), ARCH_SPEC",
             record="derived",
             old=round(base["clock_hz"] / base["power_production"]["design_point"]["ar_batch1"]["step_cycles"] /
                       base["hbm_comparator"]["8192"]["rom_format_3.5b"]["tokens_s"], 2),
             new=per(lambda v: v["ratios"]["rate_ar_rom_over_hbm"])),
        dict(figure="rate ratio ROM / HBM (matched format), both with DFlash", where="atlas (13,052 vs 3,762)",
             record="derived", old=round(dfl["rom"]["8192/fp8/m3"]["best"]["tokens_s"] /
                                         dfl["hbm"]["rom_format_3.5b"]["best"]["tokens_s"], 2),
             new=per(lambda v: v["ratios"]["rate_dflash_rom_over_hbm"])),
        dict(figure="'the deployed 3.5-bit weight format does not yet meet our quality threshold' caveats; "
                    "'Design the lane for the ROM's weight format: 4-bit weights (3.5 bits a weight with group "
                    "scales)' requirement; the S1f 3.5-bit GPU substep (1,839) and 'H200 matched format 3.5-bit' rows",
             where="atlas summary, §6.5, §8.2, rate ladder; ARCH_SPEC §11.3", record="prose",
             old="3.5-bit (HC1 INT3/INT6)",
             new="8-bit weight-only (INT8 per-channel; FP8 E4M3 block-128 alternative): the lane requirement becomes "
                 "INT8/FP8 x BF16 -> FP32 on the existing exact BF16 lane; every GPU/HBM 'matched format' row moves to "
                 "its FP8-weight figure (same bytes a weight), e.g. HDC-HBM 1,379 -> 661, B200 idealised 1,839 -> its "
                 "FP8 row"),
    ]
    return out


# -- evaluate -------------------------------------------------------------------------------------------------------
def evaluate():
    if getattr(QB, "DIES", 1) != 1:
        raise SystemExit("tools/qwen3_8bit_design.py priced the options against the single-reticle 3.5-bit baseline, "
                         "which HEAD no longer implements (O4 was adopted: tools/arch_budget_qwen3.py). The record is "
                         "frozen evidence; reproduce it at the commit that added it: git log --diff-filter=A --format=%H "
                         "-- results/arch/qwen3_8bit_design.json")
    out = QB.evaluate()                       # the baseline, recomputed (its record is held equal by its own test)
    clock = out["clock_hz"]
    QB.CLOCK[0] = clock
    inv = inventory()
    dens = density()
    QB_READ[0], QB_READ[1] = dens["anchor_8bit_rom_read_bytes_s_per_mm2"], dens["rom_read_efficiency"]
    cap = capacity(inv, dens)
    basis = json.loads(DST.BASIS.read_text())
    assert basis["clock_hz"] == clock and basis["dependency_chain"][f"{CTX}/spec"]["components"] == \
        out["dependency_chain"][f"{CTX}/spec"]["components"], "DFlash basis and the budget disagree"
    tau = DST.acceptance(json.loads(DST.ACCEPT.read_text()))
    cfgps = PS.load_cfg()
    hbm8 = hbm_comparator(out, clock, basis, tau, cap)
    h = hbm8["int8_per_channel"]
    res = dict(schema=SCHEMA, tool="tools/qwen3_8bit_design.py", status="SCENARIO -- not the baseline; nothing adopted",
               decision=dict(user="Qwen3-8B uses 8-bit weights (never 4-bit or 3.5-bit: they fail the quality bar)",
                             standing="one reticle (the user's decision); an option that is not one reticle, or "
                                      "moves weights off ROM, is the user's to choose"),
               clock_hz=clock, context=CTX, kv_format=KV_FMT, inventory={k: v for k, v in inv.items()
                                                                          if k not in ("target", "drafter")},
               density=dens, capacity=cap, configurations={}, hbm_comparator_8bit=hbm8)
    res["lane_sweep"] = {}
    for cfg in configurations():
        c = dict(cfg)
        if c["groups"] == "rom_read":
            c["groups"] = most_groups_the_rom_feeds(c, cap, clock)
        elif isinstance(c["groups"], str):
            tag = "embedding_in_hbm" if c["embed_in_hbm"] else "all_rom"
            if tag not in res["lane_sweep"]:
                res["lane_sweep"][tag] = lane_sweep(dict(c, groups=QB.GROUPS_ROM), cap, clock, basis, tau)
            c["groups"] = pick_groups(c["groups"], res["lane_sweep"][tag])
        led = ledger(c, cap)
        pf = perf(c, led, cap, clock, basis, tau)
        dp = design_point(c, led, pf, cap, clock)
        pw = price(c, dp, cfgps)
        ratios = dict(
            rate_ar_rom_over_hbm=round(pf["ar_tokens_s"] / h["ar_batch1_tokens_s"], 2),
            rate_dflash_rom_over_hbm=round(pf["dflash"]["best"]["tokens_s"] / h["dflash_best"]["tokens_s"], 2),
            energy_ar_hbm_over_rom={t: round(h["power"][t]["w8_batch1"]["energy_per_token_mj"] /
                                             pw[t]["ar_batch1"]["energy_per_token_mj"], 2) for t, _, _ in LANE_SCEN})
        res["configurations"][c["id"]] = dict(
            label=c["label"], is_option=c.get("option", True), adopted=False,
            parameters={k: c[k] for k in ("groups", "dies", "stacks_per_die", "embed_in_hbm", "lm_head_in_hbm",
                                          "drafter", "floorplan")},
            ledger=led, performance=pf, power=pw, ratios=ratios, cost=cost(c, led))
    res["o4_contiguous_cut_scenario"] = contiguous_cut(res, cap, clock, basis, tau)
    res["verdict"] = verdict(res)
    res["figure_changes"] = figure_changes(out, json.loads(DFLASH_REC.read_text()), res)
    res["checks"] = checks(res, out, cfgps)
    res["notes"] = NOTES
    return res


CUT_P = 20                        # docs/ARCH_QWEN3_O4_RTL_SPEC.md section 1.1: the best contiguous cut
CUT_RECORDED = dict(ar_tokens_s=5959.6, dflash_tokens_s=12461.0,
                    source="results/arch/qwen3_o4_rtl_gaps.json#die_split.layer_cut (O4 pair model, no scale stage)")


def contiguous_cut(res, cap, clock, basis, tau):
    """The alternative split, kept as a scenario: die A the embedding and layers 0..P-1, die B the rest, the lm_head
    and the drafter.  At batch 1 the dies take turns, so a token is one die's engine (6,144 groups, m = 5) on one
    die's 4 stacks (the KV floor doubles and binds), plus the serial handoffs: the FP32 residual A -> B and the token
    id B -> A (autoregressive); 5 slots' residuals and the drafter's BF16 taps from die A, and 5 draft tokens and the
    accepted count (DFlash block 5).  Priced by perf() on the same rules as the TP-2 point."""
    o4 = res["configurations"]["O4_two_reticles_one_package"]
    cfg = dict(configurations()[0], dies=1, stacks_per_die=4, groups=o4["ledger"]["groups_per_die"])
    led = dict(o4["ledger"], dies=1)
    pf = perf(cfg, led, cap, clock, basis, tau)
    hop, bpc = _link(clock)
    taps = [t for t in (1, 9, 17, 25, 33) if t < CUT_P]
    b = pf["dflash"]["best"]
    fwd_v = b["block"] * Q["H"] * PARTIAL_BYTES + len(taps) * b["block"] * Q["H"] * 2
    ar_x = math.ceil(hop + Q["H"] * PARTIAL_BYTES / bpc) + math.ceil(hop + 4 / bpc)
    df_x = math.ceil(hop + fwd_v / bpc) + math.ceil(hop + (b["block"] * 4 + 4) / bpc)
    ar = pf["ar_step_cycles"] + ar_x
    df = b["step_cycles"] + df_x
    return dict(P=CUT_P, die_a=f"embedding + layers 0-{CUT_P - 1}",
                die_b=f"layers {CUT_P}-35 + final norm + lm_head + drafter",
                ar_step_cycles=ar, ar_binding=pf["ar_binding"], ar_handoff_cycles=ar_x,
                ar_tokens_s=round(clock / ar, 1), dflash_block=b["block"], dflash_step_cycles=df,
                dflash_handoff_cycles=df_x, dflash_tokens_s=round(b["tokens_per_step"] * clock / df, 1),
                vs_tp2_ar=round(clock / ar / o4["performance"]["ar_tokens_s"], 3),
                vs_tp2_dflash=round(b["tokens_per_step"] * clock / df / o4["performance"]["dflash"]["best"]["tokens_s"], 3),
                recorded=CUT_RECORDED, adopted=False,
                note="a scenario, not the design point: TP-2 is the only split that reaches the O4 rates at batch 1")


def cost(c, led):
    """Relative cost drivers against the 3.5-bit single reticle (no dollar model exists in this repository)."""
    n = c["dies"]
    return dict(logic_reticles=n, logic_silicon_mm2=n * led["die_mm2"], hbm_stacks=n * c["stacks_per_die"],
                hbm_stacks_vs_baseline=round(n * c["stacks_per_die"] / QB.ROM_KV_HBM["stacks"], 3),
                rom_mask_sets=n, package=("CoWoS-L-class two-reticle interposer (~3.3 reticles, B200-class)" if n > 1
                                          else "single-reticle package with 6 stacks (H200-class)"),
                note="per-package silicon, stacks and ROM (via/metal) mask sets; both dies of a TP pair hold "
                     "different weights, so two ROM mask sets" if n > 1 else "as the baseline")


def verdict(res):
    c0 = res["configurations"]["C0_single_reticle"]
    fit = {k: v["ledger"]["fits"] for k, v in res["configurations"].items()}
    d = res["density"]
    led = c0["ledger"]
    # the cell-area multiplier at which C0 fits with no lane copy, and with the baseline's two
    budget_rom = led["target_rom_mm2"] + led["drafter_rom_mm2"] - led["deficit_mm2"]
    m_fit = d["cim_cell_area_multiplier"] * budget_rom / (led["target_rom_mm2"] + led["drafter_rom_mm2"])
    m_fit3 = d["cim_cell_area_multiplier"] * (budget_rom - 2 * led["lane_copy_mm2"]) / \
        (led["target_rom_mm2"] + led["drafter_rom_mm2"])
    return dict(single_reticle_fits=c0["ledger"]["fits"], deficit_mm2=led["deficit_mm2"],
                deficit_without_drafter_mm2=res["configurations"]["C0b_no_drafter"]["ledger"]["deficit_mm2"],
                fits_by_configuration=fit,
                density_break_even=dict(cim_cell_area_multiplier_to_fit_m1=round(m_fit, 3),
                                        cim_cell_area_multiplier_to_fit_m3=round(m_fit3, 3),
                                        assumed=d["cim_cell_area_multiplier"],
                                        note="the ROM select-cell area (x a storage-only bit) at which C0 would fit; "
                                             "an unpublished input (technology.json rom.cim_cell_area_multiplier, "
                                             "'assumed'), reported as a break-even, not proposed"),
                summary=("8-bit Qwen3-8B does NOT fit one 815 mm2 reticle at the repository's HC1-referenced ROM "
                         "density with the baseline floorplan: the target's weights need %.1f mm2 of ROM (%.1f at "
                         "3.5 bits) and the 8-bit drafter %.1f, %.1f mm2 more than the die has with no lane copy "
                         "(%.1f mm2 short even without the drafter)." % (
                             led["target_rom_mm2"], QB.RETICLE["rom_mm2"], led["drafter_rom_mm2"], led["deficit_mm2"],
                             res["configurations"]["C0b_no_drafter"]["ledger"]["deficit_mm2"])))


def checks(res, out, cfgps):
    cap = res["capacity"]
    dens = res["density"]
    b35 = cap["baseline_3p5bit"]
    rec = json.loads(BASE_REC.read_text())
    # the baseline power, priced through the same qwen_point with the new optional fields absent
    base_pt = PS.qwen_point(QB._ps_cfg(QB.qwen_design_point(out, out["clock_hz"])), "B_proposed_production",
                            "ar_batch1")
    return {
        "inventory_equals_model_config": res["inventory"]["target_params"] ==
        res["inventory"]["model_config_total_parameters"],
        "baseline_3p5bit_rom_reproduced": abs(b35["target_mm2"] - b35["record_rom_mm2"]) < 0.01,
        "baseline_3p5bit_drafter_reproduced": abs(b35["drafter_mm2"] - b35["record_drafter_rom_mm2"]) < 0.05,
        "anchor_3p5bit_rom_equals_reticle": abs(dens["anchor_35bit_rom_mm2"] - QB.RETICLE["rom_mm2"]) < 0.01,
        "anchor_8bit_elements_within_scales_of_int8": abs(
            dens["anchor_8bit_rom_mm2_required"] - (cap["int8_per_channel"]["target_total"]["mm2"])) < 1.0,
        "baseline_power_unchanged_by_8bit_fields": round(base_pt["energy_per_token_mj"], 3) ==
        rec["power_production"]["scenarios"]["B_proposed_production"]["rom"]["ar_batch1"]["energy_per_token_mj"],
        "hbm_8bit_rate_is_the_fp8_row_within_scale_bytes": abs(
            res["hbm_comparator_8bit"]["int8_per_channel"]["ar_batch1_tokens_s"] /
            out["hbm_comparator"]["8192"]["fp8"]["tokens_s"] - 1) < 0.002,
    }


NOTES = [
    "Nothing here changes a baseline record: results/arch/qwen3_budget.json, power_scenarios.json and "
    "dflash_step_timing.json stay at 3.5 bits until the user confirms a configuration.",
    "ROM density is the repository's HC1-referenced compute-in-ROM cell (4 bits a select cell, 1.6x a storage-only "
    "bit): an 8-bit weight is two cells, so the 8-bit ROM is 2 / (7/6) = 1.71x the 3.5-bit HC1-mixture ROM, not "
    "8 / 3.5 = 2.29x. A storage-only mask ROM (58.4 Mbit/mm2 at N6) would need more than the whole reticle for the "
    "target alone (capacity.storage_only_rom_mm2_target_int8).",
    "The MAC lanes consume one weight a lane a cycle whatever its width, so the ROM's weight sweep is unchanged in "
    "cycles; only the ROM read width doubles (131,072 B a cycle), which the 8-bit ROM supplies with headroom. The "
    "per-token rate therefore moves only through the lanes, the lane multiplier and the HBM bytes of each option.",
    "The DFlash step is priced by tools/dflash_step_timing.Machine on the spec chain at the option's groups (its "
    "plain token is the spec chain, as in the baseline record); the autoregressive rate by the RTL-calibrated "
    "sequencer model (tools/hdc_timing via arch_budget_qwen3.as_built), as the baseline's power design point.",
    "Without lane copies (m = 1) speculation does not pay on the ROM die: the verify's B slots each cost a weight "
    "sweep, so the best block is 1. The single-reticle options keep speculation only if they leave room for a copy.",
    "Tensor-parallel 2 (O4) is priced per die: the RTL-calibrated replay of one die's slice (16 query and 4 KV heads, "
    "half the FFN and vocabulary, H and the norms whole) at its 6,144 groups, plus 73 serial UCIe exchanges of FP32 "
    "partials (2 all-reduces a layer and the argmax gather; 10 ns hop, 19.27 cycles each, 1,407 a token) and the "
    "embedding-row handoff (~12 cycles); the verify's exchanges carry B slots' partials and the draft has its own 12. "
    "The KV of each die's half of the heads streams from its own 4 stacks. The superseded pair-as-one-engine model "
    "with BF16 partials gave 10,391.6 / 16,553.3 tok/s.",
    "Every 8-bit configuration pays the INT8 contract's per-row scale multiply after each matrix (C3): 5 cycles "
    "(ot_fp32_mul_rne_pipe's stages) x 145 matrices a token on the calibrated chain, and on each matrix stage of the "
    "specification chain.",
    "K-splits are the golden's (tools/hdc_golden.split_for, attn_splits with its power-of-two P.V split). At 6,144 "
    "groups the golden and the RTL rule agree on every target matrix and differ on the drafter's fc slice (golden "
    "S = 4,096, RTL rule 1,024): the fc is priced at the golden's split under whole-tile rounds (640 cycles, not 480).",
    "The DFlash verify runs at m = 5 on the specification chain (the shipped program has no verify slots); "
    "performance.tp.verify_calibrated_estimate re-bases it on the calibrated plain chain as a sensitivity.",
    "The embedding in HBM puts one dependent HBM row read (assumed 500 ns) on every token's chain; the lm_head in HBM "
    "adds its 622 MB to the stack stream every token (the verify and the draft each read it once a step).",
    "Tokens per step are measured in BF16 on a GPU (results/speculative/dflash_block_acceptance.json); the 8-bit "
    "target's acceptance is not measured (claude/qwen-weight-format owns the 8-bit quality study).",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    res = evaluate()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(res["verdict"]["summary"])
    print("checks", res["checks"])
    h = res["hbm_comparator_8bit"]["int8_per_channel"]
    print(f"HBM 8-bit: AR {h['ar_batch1_tokens_s']} tok/s, DFlash {h['dflash_best']['tokens_s']} "
          f"(block {h['dflash_best']['block']})")
    for k, v in res["configurations"].items():
        L, P = v["ledger"], v["performance"]
        B, A = v["power"]["B_proposed_production"], v["power"]["A_measured_implementation"]
        key = "dflash" if "dflash" in B else "ar_batch1"
        print(f"{k:40s} fits {L['fits']!s:5s} slack {L['slack_mm2'] if L['fits'] else -L['deficit_mm2']:7.1f} "
              f"m {L['lane_multiplier_m']} groups {L['groups_per_die']} | AR {P['ar_tokens_s']:8.1f} "
              f"({P['ar_binding']}) DFlash {P['dflash']['best']['tokens_s']:8.1f} b{P['dflash']['best']['block']} | "
              f"B {B['ar_batch1']['energy_per_token_mj']:.1f} mJ {B['ar_batch1']['die_w_each']:.0f} W cap "
              f"{B[key]['capped_tokens_s']['air']:.0f} | A {A['ar_batch1']['energy_per_token_mj']:.1f} mJ "
              f"{A['ar_batch1']['die_w_each']:.0f} W cap {A[key]['capped_tokens_s']['air']:.0f}")


if __name__ == "__main__":
    main()
