#!/usr/bin/env python3
"""TPUT-RECHECK 10-18: single-stream and multi-request throughput of the CURRENT designs against the A100 80GB.

Owner question (10-18): the 09-23 iso-area / iso-power studies looked good for total throughput under many
concurrent requests. Does that still hold after all the iterations?

Analysis only (no RTL). Every number carries a grade:
  composed  = token_path_1018 composition (mixed measured / priced terms, see that README for the % split)
  priced    = analytic price of record
  modelled  = this file's bound model from cited constants (formula in the row)
  published = vendor datasheet constant
  stale     = modelled on an older die revision, kept only because no current figure exists
Run: python3 results/arch/tput_recheck_1018/compute.py  (writes summary.json beside it)
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
F = 1.2e9                                   # streaming clock of every current design

# ---------------------------------------------------------------- A100 80GB SXM (the only comparator; owner 10-18)
A100 = dict(area_mm2=826.0, hbm_Bps=2.039e12, hbm_bytes=80e9, stacks=5, power_w=400.0,
            bf16_flops=312e12, int8_ops=624e12, nvlink_one_way_Bps=300e9,
            src="configs/hardware/technology.json reference_parts.a100_sxm_80gb (NVIDIA A100 datasheet); "
                "INT8 624 TOPS dense from the same datasheet",
            eff=dict(weight=0.75, kv=0.70, compute=0.45, capacity=0.90,
                     src="configs/hardware/technology_inputs.json runtime_and_cost_assumptions.a100 (assumed)"))
A100_MEASURED_NOTE = ("No measured A100 decode trace exists in the repo (results/DECISION.md:96 lists it Open). "
                      "Public anchor, short context only: TensorRT-LLM Llama-3-8B ~4,500 output tok/s on one A100 40GB "
                      "(Modal example, https://modal.com/docs/examples/trtllm_llama). The A100 rows below are a "
                      "roofline with the repo's assumed efficiencies, i.e. an UPPER bound for the A100.")

# ---------------------------------------------------------------- models
# Qwen3-8B: 36 layers, 8 KV heads x 128, FP8 KV (owner baseline) -> 73,728 B/token; 8K context
Q_KV_TOK = 36 * 8 * 128 * 2 * 1                 # bytes per context token (FP8 K+V)
Q_CTX = 8192
Q_KV_USER = Q_KV_TOK * Q_CTX                    # 603,979,776 B = results/arch/qwen3_8bit_design.json kv_bytes_per_token
Q_W8 = 8.19e9                                   # 8-bit weights (16.38 GB BF16 checkpoint / 2)
Q_OPS = 15.14e9 + 2 * 2 * 36 * 32 * 128 * Q_CTX  # matmul ops + QK/PV at 8K

# DeepSeek-V4.1-Flash: configs/models/candidates/deepseek-v4.1-flash.json
D_CKPT = 510.286e9                              # stored bytes at official precision (FP4 experts, FP8 dense, engram)
D_DENSE = 8.523e9                               # dense weight bytes (all read every token)
D_ROUTED_TOTAL = 543.58e9 * 0.53                # routed params at FP4 + UE8M0 scales ~0.53 B/param -> ~288 GB
D_EXPERTS, D_TOPK = 256, 6
D_ROUTED_TOKEN = D_ROUTED_TOTAL * D_TOPK / D_EXPERTS
D_CTX = 1048576
D_KV_USER = 890.0 * D_CTX                       # global KV 890 B/token (published, model card 2.4.4) -> 0.93 GB
# index scan per token per user: layers 2/8/14 ratio 2 (512K entries), layer 20 ratio 1 (1M), 4 reindex x 16,384; 68 B
D_SCAN_L20 = 68.0 * D_CTX
D_SCAN_TOKEN = 68.0 * (3 * D_CTX / 2 + D_CTX + 4 * 16384)
D_ROWS_TOKEN = 36 * 512 * 288.0                 # top-512 selected latent rows per attention layer
D_KV_TOKEN = D_SCAN_TOKEN + D_ROWS_TOKEN        # ~0.19 GB a token a user
D_OPS = 32e9 + 2 * 32 * 128 * (3 * D_CTX / 2 + D_CTX)   # 2 x 16B active + index-score MACs


def union(p):                                   # expected distinct experts per layer for p independent tokens
    return D_EXPERTS * (1 - (1 - D_TOPK / D_EXPERTS) ** p)


# ---------------------------------------------------------------- A100 baselines (modelled roofline)
def a100_qwen(B, kv_bytes=Q_KV_USER, w=Q_W8):
    e = A100["eff"]
    t_w = w / (A100["hbm_Bps"] * e["weight"])
    t_kv = B * kv_bytes / (A100["hbm_Bps"] * e["kv"])
    t_c = B * Q_OPS / (A100["int8_ops"] * e["compute"])
    t = max(t_w + t_kv, t_c)
    return dict(batch=B, step_s=t, per_user_tok_s=1 / t, aggregate_tok_s=B / t,
                bound="KV read" if t_kv > t_w else "weight read")


def a100_qwen_cap(kv_bytes=Q_KV_USER, w=Q_W8):
    return int((A100["hbm_bytes"] * A100["eff"]["capacity"] - w) // kv_bytes)


N_A100_DS = math.ceil(D_CKPT / (A100["hbm_bytes"] * A100["eff"]["capacity"]))   # 8 = one HGX A100


def a100_ds(B, n=N_A100_DS):
    e = A100["eff"]
    bw = n * A100["hbm_Bps"]
    t_w = (D_DENSE + min(B * D_ROUTED_TOKEN, union(B) / D_EXPERTS * D_ROUTED_TOTAL)) / (bw * e["weight"])
    t_kv = B * D_KV_TOKEN / (bw * e["kv"])
    t_c = B * D_OPS / (n * A100["bf16_flops"] * e["compute"])
    t_coll = 2 * 40 * 15e-6                     # 2 TP8 all-reduces a layer at ~15 us NCCL small-message latency (assumed)
    t = max(t_w + t_kv, t_c) + t_coll
    return dict(batch=B, gpus=n, step_s=t, per_user_tok_s=1 / t, aggregate_tok_s=B / t,
                bound="expert-weight read" if t_w > t_kv else "KV/index read")


def a100_ds_cap(n=N_A100_DS):
    return int((n * A100["hbm_bytes"] * A100["eff"]["capacity"] - D_CKPT) // D_KV_USER)


# ---------------------------------------------------------------- our designs (current revisions)
TP = "results/arch/token_path_1018/{}.json workloads.{}.tok_s"
designs = {}

# 1. S81 p4l DeepSeek ROM array -----------------------------------------------------------------------------------
s81_dies = 97 * 4 + 52                          # 97 stages x 4 rank dies + head/table/draft dies carried from rm5
s81 = dict(
    name="DS ROM array S81 p4l", model="DeepSeek-V4.1-Flash", context=D_CTX,
    dies=s81_dies, die_mm2=799.2, area_mm2=s81_dies * 799.2, stacks=s81_dies,
    area_src="results/arch/s81_dv_1016/p4l/plan.json (799.2 mm2), price_land.json stages_from_slots 97; 4 rank dies a "
             "stage + 52 non-layer dies (dsrom_s81_rack_20261006/rack.json, rm5 HANDOFF); 1 HBM3E stack a die "
             "(s81_dv_1016/SPEC.md 0b-p4g). Die count derived, grade derived.",
    power_w=s81_dies * 84.1 + s81_dies * 2.8,
    power_src="STALE modelled: 84.1 W busiest saturated layer die (10-04) + 2.8 W/stack idle "
              "(dsrom_s81_rack_20261006/rack.json die_w; technology.json). No p4l power exists.",
    b1_ar=1243.0, b1_ar_src=TP.format("ds_rom", "ar"), b1_mtp=3806.2, b1_mtp_src=TP.format("ds_rom", "mtp"),
    b1_grade="composed: 10.3% current RTL, 61.4% older RTL, 17.9% modelled PHY, 10.4% priced (AR)",
)
T_ds = 965378.6                                 # AR token cycles
die_cycles_total = 615525.0                     # by_kind.layer
stage_mean = die_cycles_total / 97
stage_peak = stage_mean * 25329.0 / 15388.0     # imbalance: busiest layer (L20) / mean layer die cycles
scan_dies = 4                                   # one stage of rank dies holds layer 20's index (conservative)
stack_Bps = 99 * 16 * F / 2                     # 950 GB/s a stack sustained (d4g basis 99 B/cycle/SM)
s81_scan_bound = scan_dies * stack_Bps / D_SCAN_L20
s81_stage_bound = F / stage_peak
s81_cap_users = int(22.5e9 // (356 * D_CTX / 4))  # busiest owner die: (288+68) B x 1M / 4 dies in one 22.5 GB stack
s81_agg = min(s81_scan_bound, s81_stage_bound)
s81.update(
    supported_inflight_today=1,
    supported_note="RTL: user/pos/tok tags on start frames, per-user window-ring addressing (dsdv_svc_att), "
                   "2 job contexts a die (ot_dsdv_fixed_issue). Missing: a multi-user compiled calendar "
                   "(dv_layer_compile.py is one token), user-tagged/buffered activation hand-off, per-user index-key "
                   "base in svc_sx, HBM sizing for N users on p4l.",
    agg_bounds=dict(
        stage_occupancy=dict(tok_s=s81_stage_bound, inflight=T_ds / stage_peak,
                             formula="1.2 GHz / busiest stage busy cycles; stage = 615,525 layer-die cycles / 97 x "
                                     "1.65 imbalance (L20 25,329 / mean 15,388)", grade="modelled"),
        index_scan_hbm=dict(tok_s=s81_scan_bound,
                            formula="4 scan dies x 1 stack x 950 GB/s / (68 B x 1M layer-20 index keys a user a token)",
                            grade="modelled", sensitivity_4_stacks_per_scan_die=4 * s81_scan_bound),
        kv_capacity_users=dict(users=s81_cap_users, grade="modelled",
                               formula="22.5 GB stack / ((288+68) B x 1M / 4 dies) on the busiest owner die"),
    ),
    agg_tok_s=1243.0, agg_modelled_tok_s=s81_agg, agg_inflight=s81_agg * T_ds / F, agg_bound="layer-20 index scan (HBM BW per user, no sharing)",
    agg_grade="modelled (needs the missing multi-user calendar)",
)
designs["s81"] = s81

# 2. Qwen ROM TP8 compute + KV dies --------------------------------------------------------------------------------
q = dict(
    name="Qwen ROM TP8 (dv2f14 + kvs14)", model="Qwen3-8B", context=Q_CTX,
    dies=16, area_mm2=8 * 841.0 + 8 * 272.6, stacks=32,
    area_src="841 mm2 compute die (official, HANDOFF 1672/1707; 522-575 target not closed) x 8 + kvs13i KV die "
             "272.6 mm2 x 8 (qwen_kv_die_audit_1016/KV_AUDIT_1016.txt); 4 HBM3E stacks a KV die (tools/qwen_kv_die)",
    power_w=8 * 527.0 * (1 + 272.6 / 841.0) + 32 * 2.8 + Q_KV_USER * 21000 * 104.88e-12,
    power_src="STALE modelled: 09-28 per-die envelope 435-619 W (power_scenarios.json, mid 527 W) on the 841 mm2 die, "
              "KV die scaled by area, + 2.8 W/stack idle + KV traffic at 104.88 pJ/B (A100-measured, technology.json)",
    b1_ar=4769.2, b1_ar_src=TP.format("qwen_rom", "ar"), b1_mtp=None, b1_mtp_src="AR only (owner 10-05 AR_MODE)",
    b1_grade="composed: 0.7% current RTL, 98.5% older RTL (TP4 10-13 vehicle + 10-15 KV service), 0.8% priced/PHY",
)
T_q = 251615.0
q_bounds = dict(
    kv_die_attention=dict(tok_s=F / (1555.0 * 36), formula="1.2 GHz / (1,555-cycle KV-die service x 36 layers); "
                          "the service buffer holds one request (tools/qwen_static_schedule/attention.py)",
                          grade="modelled from measured service (10-15)"),
    matvec_windows=dict(tok_s=F / 53152.0, formula="1.2 GHz / 53,152 matvec-window cycles a token "
                        "(qwen_reuse_1015/reuse.json: weights re-streamed per user, 1 MAC/lane/cycle)",
                        grade="modelled from measured windows"),
    kv_hbm=dict(tok_s=32 * 1.0e12 / Q_KV_USER, formula="32 stacks x 1.0 TB/s / 604 MB a user a token at 8K",
                grade="modelled"),
    kv_capacity_users=dict(users=int(32 * 22.5e9 // Q_KV_USER), grade="modelled"),
)
q_agg = min(v["tok_s"] for k, v in q_bounds.items() if "tok_s" in v)
q.update(
    supported_inflight_today=1,
    supported_note="qkd_host_if_pins.sv:104 $fatal unless NSLOT==1 && ENG_CTX==1; KV attention static buffer of "
                   "capacity 1; kv_calendar has no user dimension; ot_qwen_activation_handoff (user tags) is TB-only.",
    agg_bounds=q_bounds, agg_tok_s=4769.2, agg_modelled_tok_s=q_agg, agg_inflight=q_agg * T_q / F,
    agg_bound="KV-die attention service (one request at a time, 56k cycles a token)",
    agg_grade="modelled (needs multi-slot host leaf, KV calendar user dimension, compiler interleave)",
    cross_check="TP4 10-09 pricing gave 25,362 tok/s tile-window bound at 4.6 users (qwen_tp8_vs_sysdie_20261009); "
                "10-15 model gave 7,168 at batch 2 (qwen_reuse_1015)",
)
designs["qwen_rom"] = q

# 3/4. HBM d4g ------------------------------------------------------------------------------------------------------
die_Bps = 99 * 16 * F                            # 1.90 TB/s a die sustained (99 B/cycle/SM x 16 SM)
for key, model, n, b1, b1src, b1g, T in [
    ("hbm_ds", "DeepSeek-V4.1-Flash", 192, 1993.8, TP.format("hbm_gen_ds", "ar"),
     "composed: 9.6% current RTL, 8.2% modelled PHY, 82.2% priced (price5 1,905.4)", 601855.9),
    ("hbm_qwen", "Qwen3-8B", 8, 930.9, TP.format("hbm_gen_qwen", "ar"),
     "composed: 6.9% current RTL, 93.0% priced (price5 946.2)", 1289007.9)]:
    d = dict(name=f"HBM d4g ({model})", model=model, context=D_CTX if key == "hbm_ds" else Q_CTX,
             dies=n, die_mm2=641.83, area_mm2=n * 641.83, stacks=2 * n,
             area_src="results/arch/hbm_die_d4g/plan/plan_geometry.json 641.83 mm2 (630.66 + 11.2 SM frame), 16 SMs, "
                      "2 HBM3E stacks/45 GB a die; DS TP-192 (hgi_sim/d4g_price5_1018.py), Qwen TP-8 (TOKEN-PASS-HBMQ)",
             b1_ar=b1, b1_ar_src=b1src, b1_grade=b1g,
             b1_mtp=3258.7 if key == "hbm_ds" else None,
             b1_mtp_src="price5 summary (priced; HBM MTP parked by owner)" if key == "hbm_ds" else None,
             supported_inflight_today=1,
             supported_note="ot_hbm_token_loop.sv takes one job {job,tok,pos} with no user field or KV base; "
                            "ISA/compiler records are single-row. P position lanes (lane HBM-MTP) are a study with no "
                            "committed result.")
    bw = n * die_Bps
    if key == "hbm_ds":
        d["power_w"] = 12544.0
        d["power_src"] = "STALE modelled: HBM DS system 12,544 W AR (energy_silicon_measured, 10-07, older geometry)"
        rows = []
        for P in (1, 8, 32, 128):
            t_lat = T / F                                       # today's AR token latency, unchanged per step (assumed)
            t_bw = (D_DENSE + union(P) / D_EXPERTS * D_ROUTED_TOTAL + P * D_KV_TOKEN) / bw
            t = max(t_lat, t_bw)
            rows.append(dict(P=P, step_us=t * 1e6, aggregate_tok_s=P / t,
                             bound="token latency" if t_lat >= t_bw else "HBM bandwidth",
                             experts_touched_per_layer=union(P)))
        d["agg_tok_s"] = d["b1_ar"]
        d["agg_bound"] = "time-share: one job at a time, so aggregate = single-stream rate"
        d["p_lane_potential"] = dict(rows=rows, grade="modelled, UNBUILT (needs P x MACs a weight word, row-count ISA, "
                                     "multi-query attention, expert-union compiler)",
                                     formula="step = max(today's token latency, (dense + union(P) experts + P x 0.19 GB "
                                             "KV/index) / (192 x 1.90 TB/s))",
                                     kv_capacity_users=int((n * 45e9 - D_CKPT) // D_KV_USER),
                                     older_model="MICROARCH_MODEL.md:450: V4.1 HBM AR 21,792 tok/s at 32 users (old rev)")
    else:
        d["power_w"] = n * 641.83 * 0.5 + 2 * n * 2.8
        d["power_src"] = "modelled ROUGH: 0.5 W/mm2 (A100 TDP density, technology.json roofline note) + 2.8 W/stack"
        rows = []
        for P in (1, 8, 16, 64):
            t_lat = T / F
            t_bw = (Q_W8 + P * Q_KV_USER) / bw
            t = max(t_lat, t_bw)
            rows.append(dict(P=P, step_us=t * 1e6, aggregate_tok_s=P / t,
                             bound="token latency" if t_lat >= t_bw else "HBM bandwidth (KV)"))
        d["agg_tok_s"] = d["b1_ar"]
        d["agg_bound"] = "time-share: one job at a time, so aggregate = single-stream rate"
        d["p_lane_potential"] = dict(rows=rows, grade="modelled, UNBUILT", kv_bound_tok_s=bw / Q_KV_USER,
                                     formula="step = max(today's token latency, (8.19 GB weights + P x 604 MB KV) / "
                                             "(8 x 1.90 TB/s))",
                                     kv_capacity_users=int((n * 45e9 - Q_W8) // Q_KV_USER),
                                     older_model="MICROARCH_MODEL.md:450: Qwen HBM 6,684 tok/s at 16 users (old rev)")
    designs[key] = d

# ---------------------------------------------------------------- comparisons
a1_q = a100_qwen(1)
capq = a100_qwen_cap()
aq = a100_qwen(capq)
capq_bf16 = a100_qwen_cap(kv_bytes=2 * Q_KV_USER)
aq_bf16 = a100_qwen(capq_bf16, kv_bytes=2 * Q_KV_USER)
a1_d = a100_ds(1)
capd = a100_ds_cap()
ad = a100_ds(capd)
gpu = dict(
    qwen_8k=dict(system="1 x A100 80GB, W8 weights + 8-bit KV (matched precision)", area_mm2=826.0, stacks=5,
                 power_w=400.0, b1=a1_q, max_users=capq, at_max=aq,
                 bf16_kv_sensitivity=dict(max_users=capq_bf16, at_max=aq_bf16)),
    ds_1m=dict(system=f"{N_A100_DS} x A100 80GB (HGX A100), official-precision weights stored, weight-only dequant",
               area_mm2=N_A100_DS * 826.0, stacks=5 * N_A100_DS, power_w=N_A100_DS * 400.0, b1=a1_d,
               max_users=capd, at_max=ad),
    grade="modelled roofline, A100 upper bound", constants=A100, measured_note=A100_MEASURED_NOTE)


def ratios(d, g):
    o = {}
    o["b1_per_device_x"] = d["b1_ar"] / g["b1"]["per_user_tok_s"]
    o["b1_per_mm2_x"] = (d["b1_ar"] / d["area_mm2"]) / (g["b1"]["aggregate_tok_s"] / g["area_mm2"])
    o["b1_per_W_x"] = (d["b1_ar"] / d["power_w"]) / (g["b1"]["aggregate_tok_s"] / g["power_w"])
    o["agg_today_per_mm2_x"] = (d["agg_tok_s"] / d["area_mm2"]) / (g["at_max"]["aggregate_tok_s"] / g["area_mm2"])
    o["agg_today_per_W_x"] = (d["agg_tok_s"] / d["power_w"]) / (g["at_max"]["aggregate_tok_s"] / g["power_w"])
    o["agg_today_per_stack_x"] = (d["agg_tok_s"] / d["stacks"]) / (g["at_max"]["aggregate_tok_s"] / g["stacks"])
    o["iso_area_a100_count"] = d["area_mm2"] / 826.0
    return o


cmp = {}
for k, d in designs.items():
    g = gpu["qwen_8k"] if d["model"] == "Qwen3-8B" else gpu["ds_1m"]
    r = ratios(d, g)
    if "p_lane_potential" in d:
        # potential = P 8 (the lane width HBM-MTP studies); larger P rows are a ceiling only (per-step latency held
        # constant, SM/SU/attention work growing with P is not priced)
        best = [x for x in d["p_lane_potential"]["rows"] if x["P"] == 8][0]
        r["agg_ceiling_tok_s"] = max(x["aggregate_tok_s"] for x in d["p_lane_potential"]["rows"])
        d["agg_modelled_tok_s"] = best["aggregate_tok_s"]
        r["agg_potential_tok_s"] = best["aggregate_tok_s"]
        r["agg_potential_P"] = best["P"]
        r["agg_potential_per_mm2_x"] = (best["aggregate_tok_s"] / d["area_mm2"]) / (g["at_max"]["aggregate_tok_s"] / g["area_mm2"])
        r["agg_potential_per_W_x"] = (best["aggregate_tok_s"] / d["power_w"]) / (g["at_max"]["aggregate_tok_s"] / g["power_w"])
    m = d["agg_modelled_tok_s"]
    r["agg_modelled_per_mm2_x"] = (m / d["area_mm2"]) / (g["at_max"]["aggregate_tok_s"] / g["area_mm2"])
    r["agg_modelled_per_W_x"] = (m / d["power_w"]) / (g["at_max"]["aggregate_tok_s"] / g["power_w"])
    r["agg_modelled_per_stack_x"] = (m / d["stacks"]) / (g["at_max"]["aggregate_tok_s"] / g["stacks"])
    r["iso_area_a100_aggregate_tok_s"] = g["at_max"]["aggregate_tok_s"] * d["area_mm2"] / g["area_mm2"]
    cmp[k] = r

prior = dict(
    qwen_q4_inside_a100=dict(b1_x=14.37, b256_x=0.327, crossover_batch=16,
                             src="results/derived/rom_iso_area_inside_a100_die.json answer (09-23)",
                             basis="one 826 mm2 die, q4p25 weights in 596 mm2 ROM, 81 mm2 compute, NO KV term on "
                                   "either side (A100 by_batch goes compute-bound at 20,612 tok/s from b=64 with no "
                                   "KV read or capacity limit)"),
    ds_array_vs_gpu=dict(best_x="12.9-15.8", worst_x="0.9-1.75",
                         src="results/derived/rom_iso_area_against_gpu.json shipped_geometries "
                             "DSV4-Flash/ROM-N5-native-HBMKV-array-pipeline-x62..x84",
                         basis="DSV4-Flash (not V4.1), 50,530-68,460 mm2 analytical arrays, against a B200 cluster "
                               "modelled as link-latency-bound tensor parallel (its own caveat), roofline both sides"),
    wafer_vs_array=dict(src="docs/WAFER_VS_ARRAY_ISO_AREA.md (09-26)",
                        basis="array b4096 aggregate 113k-1.35M tok/s at 2-12 wafer-equivalents, analytical"),
)

out = dict(schema="opentallas.tput_recheck_1018.v1", lane="TPUT-RECHECK", date="2026-10-18",
           comparator="A100 80GB SXM only (owner 10-18 correction: same 7 nm class as ASAP7, same as 09-23 studies)",
           designs=designs, a100=gpu, ratios=cmp, prior_0923=prior,
           grades_legend=__doc__.split("Every number carries a grade:")[1].split("Run:")[0].strip())
with open(os.path.join(HERE, "summary.json"), "w") as fh:
    json.dump(out, fh, indent=1, default=float)

# console table
print(f"{'design':32s} {'b1':>6s} {'A100b1':>6s} {'b1/dev':>6s} {'b1/mm2':>6s} {'b1/W':>5s} | {'agg today':>9s} "
      f"{'x/mm2':>6s} | {'agg model':>9s} {'A100agg':>7s} {'x/mm2':>6s} {'x/W':>5s} {'x/stk':>5s} {'iso-area A100':>13s}")
for k, d in designs.items():
    g = gpu["qwen_8k"] if d["model"] == "Qwen3-8B" else gpu["ds_1m"]
    r = cmp[k]
    print(f"{d['name'][:32]:32s} {d['b1_ar']:6.0f} {g['b1']['per_user_tok_s']:6.0f} {r['b1_per_device_x']:6.2f} "
          f"{r['b1_per_mm2_x']:6.3f} {r['b1_per_W_x']:5.2f} | {d['agg_tok_s']:9.0f} {r['agg_today_per_mm2_x']:6.3f} | "
          f"{d['agg_modelled_tok_s']:9.0f} {g['at_max']['aggregate_tok_s']:7.0f} {r['agg_modelled_per_mm2_x']:6.3f} "
          f"{r['agg_modelled_per_W_x']:5.2f} {r['agg_modelled_per_stack_x']:5.2f} {r['iso_area_a100_aggregate_tok_s']:13.0f}")
print("A100 qwen cap users", capq, "agg", round(aq["aggregate_tok_s"]), "bf16kv", capq_bf16, round(aq_bf16["aggregate_tok_s"]))
print("A100 ds gpus", N_A100_DS, "cap users", capd, "agg", round(ad["aggregate_tok_s"]), "b1", round(a1_d["per_user_tok_s"]))
print("S81 bounds", {k: round(v.get("tok_s", v.get("users", 0))) for k, v in s81["agg_bounds"].items()},
      "inflight", round(s81["agg_inflight"]))
print("Qwen bounds", {k: round(v.get("tok_s", v.get("users", 0))) for k, v in q_bounds.items()},
      "inflight", round(q["agg_inflight"], 1))
for k in ("hbm_ds", "hbm_qwen"):
    print(k, [(r["P"], round(r["aggregate_tok_s"]), r["bound"]) for r in designs[k]["p_lane_potential"]["rows"]])
for k, d in designs.items():
    print(k, "area", round(d["area_mm2"]), "power", round(d["power_w"]))
