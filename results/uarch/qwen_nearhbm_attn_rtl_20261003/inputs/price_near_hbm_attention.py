#!/usr/bin/env python3
"""MODEL-ONLY pricing of near-HBM (shoreline) attention units for the Qwen3-8B ROM die (TP4).
Reads constants from the OpenTallas checkout (read-only); writes JSON next to this script."""
import json, math, hashlib, sys
from pathlib import Path

ROOT = Path("/home/ubuntu/OpenTallas")
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

R3P = "results/uarch/qwen_rom_kv_credit17_20261003/model-r3.json"
P7P = "results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json"
MACP = "physical/asap7_memory_macros/index.json"
PHYP = "physical/asap7_memory_macros/ot_hbm3e_phy/ot_hbm3e_phy.json"
r3 = json.loads((ROOT / R3P).read_text())
p7 = json.loads((ROOT / P7P).read_text())
mac = json.loads((ROOT / MACP).read_text())["macros"]
phy = json.loads((ROOT / PHYP).read_text())

import arch_budget_qwen3 as Q
import arch_budget_v41 as A
import uarch_model as U
import hdc_golden as G
UA, US = A.unit_areas()

# ---------------- shape (per die, TP4) ----------------
NH, KVH, HD, L = 8, 2, 128, 36
GROUPS = 6144                         # qwen_tp_point(4, 6144, ...) is the model-r3 baseline authority
T = 8192                              # ctx=8192 in the baseline call; KV positions per layer <= 8191
KV_B_TOKEN = r3["unified_model_join"]["modeled_source_KV_bytes_per_token"]   # 150,847,488
STACKS = 4
STACK_BPS = U.HBM_STACK_BPS           # 1.0e12 * 0.9 (arch_budget_qwen3.HBM)
F_STREAM = r3["ONE_configuration"]["stream_Hz"]   # 1.2e9
F_SERVICE = r3["ONE_configuration"]["service_Hz"]  # 1.0e9 controller clock
s_sc, s_pv = G.attn_splits(HD, GROUPS)            # golden K-splits at G=6144: (128, 512)

# ---------------- current design (model-r3) ----------------
base_cyc = r3["unified_model_join"]["baseline_cycles"]           # 128,444 (KV on core, no fill)
base_layer = r3["unified_model_join"]["baseline_layer_cycles"]   # 3,338
ATTN_STAGE = 1624   # tools/arch_budget_qwen3.as_built(...).layer_chain stage "attention: scores, softmax, P.V, 1/Z"
                    # replayed at qwen_tp_point(4,6144,'ucie_measured',1.2e9,me_lat_extra=55,ctx=8192,su_width=64)
cur_token_s = r3["calendar"]["total_conditional_s"]               # 358.6013 us
fill_Bps = 7 * 64 * F_STREAM                                       # 537.6 GB/s
fill_floor_s = KV_B_TOKEN / fill_Bps                               # 280.6 us

# ---------------- rates per stack ----------------
B_per_cycle = STACK_BPS / F_STREAM                                  # 750 B per 1.2 GHz edge
row_B = HD                                                          # one FP8 K or V row of one KV head
rows_per_cycle = B_per_cycle / row_B                                # 5.86
macs_per_row = (NH // KVH) * HD                                     # 4 q heads share a KV head: 512 MACs/row
macs_per_cycle_need = rows_per_cycle * macs_per_row                 # 3,000
row_engines = math.ceil(rows_per_cycle)                             # 6
lanes = row_engines * macs_per_row                                  # 3,072 lanes per stack
macs_per_byte = macs_per_row / row_B                                # 4 MAC / B (both phases)
pos_per_stack = math.ceil(T / STACKS)                               # 2,048 (residue-512 striping, 128 residues/stack)
K_B_layer_stack = KVH * pos_per_stack * row_B                       # 524,288 B
phase_cycles = math.ceil(K_B_layer_stack / B_per_cycle)             # 699 per phase (K or V)
scores_per_cycle = rows_per_cycle * (NH // KVH)                     # 23.4
exp_pipes = math.ceil(scores_per_cycle)                             # 24

# HBM floor
hbm_floor_s = KV_B_TOKEN / (STACKS * STACK_BPS)                     # 41.9 us
controller_cap_len1 = 32 * (1 / r3["controller"]["per_PC_accept_II_edges"]) * 32 * F_SERVICE  # 204.8 GB/s/stack
min_len_sectors = math.ceil(STACK_BPS / (32 * F_SERVICE / r3["controller"]["per_PC_accept_II_edges"]) / 32)

# ---------------- latency constants (1.2 GHz, SS where measured) ----------------
SS_REACH_UM = 504                                   # memory: SS wire reach at 1.2 GHz (261 ps + 1.135 ps/um)
gw, gh = r3["routing_cost"]["grid_w_um"], r3["routing_cost"]["grid_h_um"]
hub_to_stack_um = gh / 2 + 6000                     # ASSUMED: hub at array centre, stack centred on a 12 mm beachfront
wire_stages = math.ceil(hub_to_stack_um / SS_REACH_UM)          # 45
ADD_LAT = 7                                         # FP32_ADD_SS[7]: 1,208 MHz at SS (only stage count clearing 1.2 GHz)
LVL = ADD_LAT + 1                                   # tree level: adder + output register
MUL_LAT = 5                                         # ot_fp32_mul_rne_pipe / BF16 MAC product stages (SCALE_MUL_CYCLES)
EXP_LAT = 49                                        # ot_hdc_exp_rebalanced_mul (fmax 1,196 MHz, not closed)
RECIP_LAT = 28                                      # ot_hdc_recip_rebalanced_mul (fmax 1,223 MHz, not closed)
BUS = 512                                           # bits/cycle each way per stack link (chosen)
q_bits = NH * HD * 16
newkv_bits = 2 * KVH * HD * 8
max_bits = NH * 32
pv_bits = NH * HD * 32
z_partials_per_head = (T // 8) // 16                # 1,024 Z chunks; 16 consecutive chunks per stack-run reduce locally -> 64 partials/head die-wide
z_bits_stack = NH * (z_partials_per_head // STACKS) * 32
in_bits = q_bits + newkv_bits
out_bits = pv_bits + z_bits_stack + max_bits

score_lat = MUL_LAT + int(math.log2(s_sc)) * LVL + MUL_LAT      # product, 7-level tree, x0.25
max_roundtrip = score_lat + 4 + 2 * wire_stages + 2
assert max_roundtrip < phase_cycles / 2, "max exchange must hide under the other KV head's K stream"

def layer(bus=BUS, stream_scale=1.0, lanes_scale=1.0, prefetch=False):
    # without prefetch the phase is HBM-bound; with a full K+V prefetch buffer it is MAC-bound
    ph = math.ceil(phase_cycles / lanes_scale) if prefetch else math.ceil(phase_cycles * stream_scale)
    q_in = wire_stages + math.ceil(in_bits / bus)
    stream = 2 * ph
    tail = MUL_LAT + ADD_LAT + 8 + int(math.log2(s_pv // STACKS)) * LVL      # last accumulate + local 7-level PV tree
    out_ser = math.ceil(out_bits / bus)
    z_first = math.ceil(z_bits_stack / bus)
    hub = max(out_ser + 2 * LVL, z_first + 6 * LVL + RECIP_LAT) + MUL_LAT
    out = wire_stages + hub
    return dict(q_in=q_in, K_phase=ph, V_phase=ph, drain=tail, return_and_hub=out,
                total=q_in + stream + tail + out)

nonattn = base_cyc - L * ATTN_STAGE
cases = {}
for name, kw in dict(primary=dict(), hbm_0p7TBs=dict(stream_scale=0.9 / 0.7),
                     narrow_bus_128=dict(bus=128),
                     kv_prefetch_2x_lanes=dict(lanes_scale=2.0, prefetch=True)).items():
    lay = layer(**kw)
    cyc = nonattn + L * lay["total"]
    cases[name] = dict(per_layer_cycles=lay, token_cycles=cyc, token_us=round(cyc / F_STREAM * 1e6, 2),
                       tokens_s=round(F_STREAM / cyc, 0),
                       rate_gain_vs_358p6=round(cur_token_s / (cyc / F_STREAM) - 1, 4))

# ---------------- area (per stack, um2) ----------------
FF = p7["cells"]["ASR_area_um2"] + p7["cells"]["INV_area_um2"]   # 0.42282 um2/bit (model-r3 FF_cell_um2)
add, mul_, expa, reca = UA["fp32_add_um2"], UA["fp32_mul_um2"], UA["exp_um2"], UA["recip_um2"]
sram = mac["ot_sram_1r1w_1024x256_m2_r2c2"]
score_bits = NH * pos_per_stack * 32                                 # 524,288 bits / stack
score_macros = max(math.ceil(score_bits / sram["capacity_bits"]),
                   math.ceil(scores_per_cycle * 32 / 256))           # capacity 2, bandwidth 3 -> 4 (1r1w: separate R and W)
score_macros = 4
tree_adders = lanes // HD * (HD - 1)
area_hi = dict(lanes_MAC_UM2=lanes * Q.MAC_UM2)
area_lo = dict(lanes_LANE_COPY_plus_tree=lanes * Q.LANE_COPY_UM2 + tree_adders * (add + 32 * U.DFF_UM2))
common = dict(
    exp_pipes=exp_pipes * expa,
    s_minus_max_adders=exp_pipes * add,
    Z_chunk_adders=exp_pipes * add,
    PV_streaming_tree_stack_FF=NH * HD * int(math.log2(s_pv // STACKS)) * 32 * FF,
    score_SRAM=score_macros * sram["area_um2"],
    q_stationary_FF=lanes * 16 * FF,
    max_compare=NH * add,
    link_pipeline_FF=(2 * BUS + 32) * wire_stages * FF,
)
CTRL = 0.05   # ASSUMED address generator / sequencer / request share
stack_hi = (area_hi["lanes_MAC_UM2"] + sum(common.values())) * (1 + CTRL)
stack_lo = (area_lo["lanes_LANE_COPY_plus_tree"] + sum(common.values())) * (1 + CTRL)
hub = 32 * add + reca + NH * mul_ + STACKS * out_bits * FF
die_hi = (STACKS * stack_hi + hub) / 1e6
die_lo = (STACKS * stack_lo + hub) / 1e6

# freed
assembly_bits = r3["ONE_configuration"]["total_assembly_words"] * 787
freed_assembly_lb = assembly_bits * FF / 1e6
service_ub = r3["cells"]["total_known_service_mm2"]
kv_sram_group = U.QWEN_AREA["kv_sram_group_um2"]
freed_tile_kv_macro = GROUPS * kv_sram_group / 1e6
freed_tile_kv_packed = freed_tile_kv_macro * U.QWEN_AREA["macro_pack"]

tracks_link = 2 * BUS + 32
prefetch_bits_stack = 2 * K_B_layer_stack * 8
prefetch_macros = max(math.ceil(prefetch_bits_stack / sram["capacity_bits"]), math.ceil(2 * B_per_cycle * 8 / 256))
prefetch_extra_mm2 = STACKS * (prefetch_macros * sram["area_um2"] + lanes * Q.MAC_UM2) / 1e6
nonattn_per_layer = (base_cyc - L * ATTN_STAGE) / L
wire_new_um = STACKS * tracks_link * hub_to_stack_um

out = dict(
    schema="near-hbm-attention-pricing.v1", model_only=True, rtl=False, pnr=False, adoption=False,
    repo_head="dcba5c0ab", sources_sha256={p: sha(p) for p in (R3P, P7P, MACP, PHYP, "tools/hdc_golden.py",
        "tools/arch_budget_qwen3.py", "tools/arch_budget_v41.py", "tools/uarch_model.py", "rtl/hdc/ot_hdc_sfu.sv",
        "rtl/hdc/ot_qwen_w12_matvec.sv")},
    shape=dict(q_heads_per_die=NH, kv_heads_per_die=KVH, head_dim=HD, layers=L, ctx_positions=T - 1,
               groups_per_die=GROUPS, kv_format="FP8 E4M3 (1 B)", KV_bytes_per_token_per_die=KV_B_TOKEN,
               attention_MACs_per_token_per_die=2 * L * NH * HD * (T - 1)),
    golden_order=dict(
        source="tools/hdc_golden.py decode_token_tp / attend / matvec_il / reduce_chunked / exp / reciprocal; "
               "program check: hdc_program at G=6144 emits scores me_split=7 (128) with me_rmax, P.V me_split=9 (512)",
        attn_splits_at_G6144=[s_sc, s_pv],
        scores="s_t = fp32(tree7(bf16(q)[d]*K[t,d], d=0..127, pairwise (c0+c1)+(c2+c3)...)) * 0.25",
        max="M = max_t s_t over ALL positions (order-free) BEFORE any exp",
        exp="e_t = exp(s_t - M), golden Cody-Waite + degree-6 Horner (NOT correctly rounded; rtl/hdc/ot_hdc_sfu.sv ot_hdc_exp mirrors it)",
        Z="reduce_chunked(e): contiguous chunks of 8 positions, sequential from +0, then pairwise tree over ceil(T/8) padded to pow2 with +0 (FP32 e)",
        PV="matvec_il(V^T, bf16(e), 512): chunk c = positions t = c (mod 512) summed sequentially in increasing t from +0, then 9-level pairwise tree",
        out="PV * reciprocal(Z) (seed 0x7ef311c7 + 3 Newton steps), normalise AFTER the weighted sum",
        online_softmax_bit_exact=False,
        why_online_fails="online softmax forms exp(s - m_running) and rescales by exp(m_old - m_new): extra roundings and different exp arguments; golden uses the single global M",
        exact_streaming_scheme="two-phase per layer: stream all K (both KV heads), store FP32 scores, global max, then stream V with e from the buffer; "
            "KV striped by residue: stack = (t mod 512) div 128, so every PV chunk and every 8-position Z chunk is stack-local; "
            "PV tree levels 1-7 local, 8-9 at hub; Z tree levels 1-4 local (16 consecutive chunks per stack-run), 5-10 at hub; +0 padding is exact (e>0)",
        score_buffer_bits_per_stack=score_bits, score_buffer_bits_per_die=STACKS * score_bits,
        fragility="golden P.V split is attn_splits(hd, groups): it is tied to G=6144; any G change moves the order the unit must mirror"),
    rates_per_stack=dict(HBM_sustained_Bps=STACK_BPS, bytes_per_1p2GHz_edge=B_per_cycle, KV_rows_per_edge=round(rows_per_cycle, 3),
        MACs_per_byte=macs_per_byte, MACs_per_edge_needed=macs_per_cycle_need, MAC_lanes=lanes, row_engines=row_engines,
        scores_or_e_per_edge=round(scores_per_cycle, 2), exp_pipes=exp_pipes, K_or_V_phase_cycles=phase_cycles,
        HBM_floor_us_per_token=round(hbm_floor_s * 1e6, 2),
        controller_cap_LEN1_at_II5_Bps=controller_cap_len1, min_read_LEN_sectors_at_II5=min_len_sectors,
        required_sustained_vs_current=round(STACK_BPS / r3["physical"]["required_sustained_PHY_Bps_per_stack"][0], 2)),
    boundaries=dict(link_bus_bits_each_way=BUS, in_bits_per_layer_per_stack=in_bits, out_bits_per_layer_per_stack=out_bits,
        max_broadcast_bits=max_bits, avg_bits_per_cycle_die=round(STACKS * L * (in_bits + out_bits + max_bits) / cases["primary"]["token_cycles"], 1),
        tracks_per_stack_link=tracks_link, tracks_total=STACKS * tracks_link,
        fill_control_tracks_removed=r3["cuts"]["fill_control_bits"], corridor_capacity=r3["cuts"]["existing_fill_control_available_tracks"],
        fits_if_each_link_has_own_corridor=tracks_link <= r3["cuts"]["existing_fill_control_available_tracks"],
        narrow_fallback_bus_bits=128, narrow_tracks_total=STACKS * (2 * 128 + 32),
        wire_um_new=wire_new_um, wire_um_removed=r3["routing_cost"]["seven_fill_total_wire_um"],
        wire_reduction=round(1 - wire_new_um / r3["routing_cost"]["seven_fill_total_wire_um"], 4),
        destinations=dict(before=1536, after="4 point links to the hub; attention output re-enters the existing x-broadcast network")),
    latency=dict(constants=dict(wire_stages_hub_to_stack=wire_stages, hub_to_stack_um=hub_to_stack_um, ADD_LAT=ADD_LAT,
                     tree_level_cycles=LVL, MUL_LAT=MUL_LAT, EXP_LAT=EXP_LAT, RECIP_LAT=RECIP_LAT, score_latency=score_lat,
                     max_exchange_roundtrip=max_roundtrip, hidden_under_other_head_K_stream=phase_cycles // 2),
                 current_attention_stage_cycles=ATTN_STAGE, nonattention_cycles_per_token=nonattn,
                 baseline_KV_on_core_token_us=round(base_cyc / F_STREAM * 1e6, 2), current_token_us=round(cur_token_s * 1e6, 4),
                 current_fill_floor_us=round(fill_floor_s * 1e6, 2), cases=cases),
    area_mm2=dict(per_stack_hi=round(stack_hi / 1e6, 3), per_stack_lo=round(stack_lo / 1e6, 3),
                  components_um2=dict(**{k: round(v) for k, v in area_hi.items()}, **{k: round(v) for k, v in area_lo.items()},
                                      **{k: round(v) for k, v in common.items()}, hub_combine=round(hub)),
                  control_share_assumed=CTRL, die_added_hi=round(die_hi, 2), die_added_lo=round(die_lo, 2),
                  freed=dict(assembly_pools_lower_bound=round(freed_assembly_lb, 2), KV_service_known_upper_bound=service_ub,
                             tile_KV_macros_conditional=round(freed_tile_kv_macro, 2), tile_KV_macros_packed_conditional=round(freed_tile_kv_packed, 2)),
                  net_without_tile_KV_credit=[round(die_lo - service_ub, 2), round(die_hi - freed_assembly_lb, 2)],
                  net_with_tile_KV_credit=[round(die_lo - service_ub - freed_tile_kv_packed, 2), round(die_hi - freed_assembly_lb - freed_tile_kv_macro, 2)],
                  prefetch_2x_lanes_extra_mm2=round(prefetch_extra_mm2, 2), prefetch_macros_per_stack=prefetch_macros,
                  prefetch_refill_fits_nonattention_window=bool(2 * phase_cycles <= nonattn_per_layer),
                  slot_headroom_mm2=p7["baseline_debit_join"]["remaining_if_all_new_debits_and_PHY_outside_baseline_mm2"],
                  baseline_array_mm2=r3["physical"]["baseline_array_mm2"],
                  shoreline_strip_depth_um_per_12mm=[round(stack_lo / 12000), round(stack_hi / 12000)],
                  PHY_footprint=dict(w_um=phy["footprint"]["width_um"], h_um=phy["footprint"]["height_um"]),
                  SRAM_macro=dict(name="ot_sram_1r1w_1024x256_m2_r2c2", count_per_stack=score_macros, area_um2=sram["area_um2"],
                                  ss_fmax_mhz=sram["fmax_mhz"]["ss"], ss_clk_to_q_ps=sram["clk_to_q_ps"]["ss"])),
    unit_closure=dict(**{k: dict(area_um2=round(UA[k], 1), fmax_mhz=US[k]["fmax_mhz"], closed=US[k]["closed"])
                         for k in ("mac_bf16_um2", "fp32_add_um2", "fp32_mul_um2", "exp_um2", "recip_um2")},
                      LANE_COPY_UM2=dict(area_um2=Q.LANE_COPY_UM2, note="closed 1.2 GHz per arch_budget_qwen3 comment; corner not stated"),
                      MAC_UM2=dict(area_um2=Q.MAC_UM2, note="routed ot_hdc_matvec / 64 lanes incl. split tree"),
                      FP32_ADD_SS=U.FP32_ADD_SS),
)
(OUT / "near_hbm_attention_pricing.json").write_text(json.dumps(out, indent=1, default=str))
print(json.dumps(dict(cases=cases, area=out["area_mm2"], bnd=out["boundaries"], rates=out["rates_per_stack"],
                      lat=out["latency"]["constants"]), indent=1, default=str))
