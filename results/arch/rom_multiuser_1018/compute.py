#!/usr/bin/env python3
"""ROM-MULTIUSER 10-18: many concurrent requests on the ROM designs by pipeline interleaving (static calendar),
with one reserved latency-critical user, against the A100 80GB (8x HGX for DeepSeek, 1x for Qwen), AR and speculative.

Design study only (no RTL change, no fleet job). Every number carries a grade:
  composed  = token_path_1018 composition (mixed measured / priced terms; % split in that README)
  measured  = an RTL bench / closed-view number quoted from a committed record
  priced    = analytic price of record
  modelled  = this file's arithmetic from cited constants (formula beside the number)
  published = vendor datasheet constant
  stale     = power modelled on an older die revision (no current power figure exists)
Run: python3 results/arch/rom_multiuser_1018/compute.py   (writes summary.json beside it; reads only files beside it)
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
F = 1.2e9
STG = json.load(open(os.path.join(HERE, "inputs_s81_stages_1009.json")))

# ============================================================== S81 (DeepSeek-V4.1-Flash ROM array, p4l, 1M ctx)
S81 = dict(
    T_ar=965378.6, tok_ar=1243.0,                      # composed, token_path_1018/ds_rom.json workloads.ar
    T_mtp=1311215.8, tok_mtp=3806.2, tau=4.159,        # composed, workloads.mtp (step cycles, DSpark gamma 5)
    wave=176183.8,                                     # composed (older RTL): workloads.mtp.layers.wave = 5 x II
    dies=440, die_mm2=799.2, power_w=440 * (84.1 + 2.8),
    power_grade="stale: 84.1 W busiest saturated layer die (10-04) + 2.8 W/stack idle (as TPUT-RECHECK)",
    layer_dies=97 * 4, layers=40,
)
S81["area"] = S81["dies"] * S81["die_mm2"]
II_1018 = S81["wave"] / 5                               # 35,236.8 cycles a position at the worst stage (composed)
II_1009 = STG["mtp_wavefront"]["worst_stage_busy_us"] * 1e-6 * F * (1 + 46 / 11271) + STG["mtp_wavefront"]["hop_cycles"]
K = II_1018 / II_1009                                   # 10-09 per-stage busy -> 10-18 composition scale (modelled)
stages = [s for s in STG["stages"] if s["label"].startswith("Stage")]
DIES_PER_STAGE = round(S81["layer_dies"] / S81["layers"])   # ~10 dies hold one layer's weights (modelled, derived)

# index scan (V4.1 indexer, configs/models/candidates/deepseek-v4.1-flash.json): 32 index heads x 128 dims; each
# compressed context entry stores one FP4 key of 128 dims (64 B) + one E8M0 scale per 32 dims (4 B) = 68 B.
# Layers 2/8/14 (ratio 2) hold 512K entries at 1M ctx, layer 20 (ratio 1) 1M, reindex layers 24/28/32/36 cap 16,384.
IDX_B = 68.0
D_CTX = 1048576
SCAN_L20 = IDX_B * D_CTX                               # 71.3 MB a user a position
SCAN_TOK = IDX_B * (3 * D_CTX / 2 + D_CTX + 4 * 16384)
STACK_BPS = 950e9                                      # sustained a stack (99 B/cycle/SM basis of d4g, as TPUT-RECHECK)


def stage_occ(stacks=None, repl=None):
    """per-position occupancy (cycles) of each stage, 10-18 scale. stacks: HBM stacks a scan die (None = as composed,
    which charges the 10-09 scan rate, ~4 stacks a die). repl: {stage_id: copies} (users alternate copies)."""
    out = {}
    for s in stages:
        b = s["busy_cycles"]
        if stacks is not None and s["idx_score_cycles"] > 0:
            b += s["idx_score_cycles"] * (4.0 / stacks - 1.0)   # scan time scales with 1/bandwidth (modelled)
        b *= K
        r = (repl or {}).get(s["id"], 1)
        out[s["id"]] = (b, b / r)
    return out


def s81_point(stacks=None, repl=None):
    occ = stage_occ(stacks, repl)
    II = max(v[1] for v in occ.values())
    # single-user latency: the scan sits on each scan stage's critical path, so a stack change moves T by the summed
    # change; replication does not touch the reserved user's path (it keeps copy A and the wavefront interval of the
    # unreplicated worst stage), so its T is unchanged by construction.
    dT = sum(v[0] for v in occ.values()) - sum(v[0] for v in stage_occ().values())
    II_self = max(v[0] for v in occ.values())
    T_ar = S81["T_ar"] + dT
    T_mtp = S81["T_mtp"] + dT + 5 * (II_self - II_1018)
    slots_ar = math.floor(T_ar / II)
    fill_mtp = math.floor((T_mtp - 6 * II) / II)
    return dict(II=II, T_ar=T_ar, T_mtp=T_mtp, b1_ar=F / T_ar, b1_mtp=S81["tau"] * F / T_mtp,
                slots_ar=slots_ar, agg_all_ar=slots_ar * F / T_ar,
                mtp_users_all=math.floor(T_mtp / (6 * II)),
                agg_all_mtp=math.floor(T_mtp / (6 * II)) * S81["tau"] * F / T_mtp,
                mtp_fillers_ar=fill_mtp, agg_mtp_plus_ar=(S81["tau"] + fill_mtp) * F / T_mtp,
                cap_tok_s_ar=F / II, worst=max(occ, key=lambda k: occ[k][1]),
                occ={k: round(v[1], 1) for k, v in occ.items()})


base = s81_point()
occ0 = stage_occ()
busy = [v[0] for v in occ0.values()]
idle = dict(
    worst_stage_busy_frac_ar=max(busy) / S81["T_ar"], mean_stage_busy_frac_ar=sum(busy) / len(busy) / S81["T_ar"],
    worst_stage_idle_ar=1 - max(busy) / S81["T_ar"], mean_stage_idle_ar=1 - sum(busy) / len(busy) / S81["T_ar"],
    worst_stage_busy_frac_mtp=6 * max(busy) / S81["T_mtp"],
    mean_stage_busy_frac_mtp=6 * sum(busy) / len(busy) / S81["T_mtp"],
    n_stages=len(busy), grade="modelled from measured/composed stage busy (10-09 groups x K=%.4f)" % K,
    sorted_top=sorted(((k, round(v[0])) for k, v in occ0.items()), key=lambda x: -x[1])[:8])

# balancing options (owner/coordinator 10-18 item 2)
area0 = S81["area"]
balance = []
for st in (None, 1, 2, 4):
    p = s81_point(stacks=st)
    scan_stages = sum(1 for s in stages if s["idx_score_cycles"] > 0)
    add_stacks = 0 if st is None else (st - 1) * 4 * scan_stages
    add_mm2 = 0 if st is None else (st - 1) * 4 * scan_stages * 10.0
    balance.append(dict(option=("as composed (10-09 scan rate)" if st is None else f"{st} HBM stack(s) a scan die"),
                        added_stacks_vs_1=add_stacks, added_phy_mm2_vs_1=add_mm2, II=round(p["II"]),
                        worst=p["worst"], single_user_ar=round(p["b1_ar"], 1), single_user_mtp=round(p["b1_mtp"], 1),
                        agg_all_ar=round(p["agg_all_ar"]), agg_mtp_plus_ar=round(p["agg_mtp_plus_ar"]),
                        grade="modelled"))
L20 = "S029"
FULLSCAN = [s["id"] for s in stages if s["idx_score_cycles"] > 2000]
repl = []
for name, rp in [("none", {}), ("L20 stage x2", {L20: 2}), ("L20 stage x3", {L20: 3}), ("L20 stage x4", {L20: 4}),
                 ("4 full-scan stages x2", {k: 2 for k in FULLSCAN}),
                 ("all stages > 20k x2 (10 stages)", {k: 2 for k, v in occ0.items() if v[0] > 20000 * K})]:
    p = s81_point(repl=rp)
    added = sum(c - 1 for c in rp.values()) * DIES_PER_STAGE
    a = area0 + added * S81["die_mm2"]
    repl.append(dict(option=name, added_dies=added, added_mm2=added * S81["die_mm2"], area_mm2=a, II=round(p["II"]),
                     next_worst=p["worst"], single_user_ar=round(p["b1_ar"], 1),
                     single_user_mtp=round(p["b1_mtp"], 1), slots_ar=p["slots_ar"],
                     agg_all_ar=round(p["agg_all_ar"]), agg_mtp_plus_ar=round(p["agg_mtp_plus_ar"]),
                     agg_all_ar_per_mm2=p["agg_all_ar"] / a, grade="modelled"))

# ============================================================== Qwen3-8B ROM TP8 (8 x 841 + 8 x 272.6 mm2, 8K)
Q = dict(T=251615.0, tok=4769.2, area=8 * 841.0 + 8 * 272.6,
         power_w=8 * 527.0 * (1 + 272.6 / 841.0) + 32 * 2.8 + 603979776 * 21000 * 104.88e-12,
         power_grade="stale: 09-28 per-die envelope (mid 527 W per 841 mm2 die), as TPUT-RECHECK")
LP = 4640.0 + 2246.0                         # composed per-layer cycles (Lc die + xdie), token_path_1018/qwen_rom.json
OCC = dict(tile_field=53152.0 / 36,          # measured windows (qwen_reuse_1015: 1,432-1,476 a layer)
           kv_attention=1555.0,              # measured-old-RTL KV-die static service (qwen_attention_rate_1015)
           allreduce_if_one_in_flight=1228.0 + 956.0)   # measured windows; latency-bound (SerDes payload 1.9 % busy)
HEAD = 3048.0                                # measured-old-RTL LM head on the tile field, once a token


def qwen_point(allreduce_pipelined=True):
    occ = max(OCC["tile_field"], OCC["kv_attention"]) if allreduce_pipelined else max(OCC.values())
    n = math.floor(LP / occ)
    filler_T = Q["T"] + n * HEAD            # fillers absorb every user's head window (static bubbles; reserved user none)
    agg = Q["tok"] + (n - 1) * F / filler_T
    return dict(slot_cycles=LP / n, slots=n, filler_tok_s=F / filler_T, agg=agg, binding_occ=occ,
                cap_tok_s=F / (36 * occ + HEAD))


qp, qs = qwen_point(True), qwen_point(False)
q_idle = {k: 1 - 36 * v / Q["T"] for k, v in OCC.items()}

# ============================================================== A100 80GB (modelled roofline = A100 upper bound)
A = dict(area=826.0, bw=2.039e12, cap=80e9, w=400.0, bf16=312e12, int8=624e12,
         eff=dict(weight=0.75, kv=0.70, compute=0.45, capacity=0.90))
# Qwen3-8B 8K, W8, FP8 KV
QKV = 36 * 8 * 128 * 2 * 8192
QW = 8.19e9
QOPS = 15.14e9 + 2 * 2 * 36 * 32 * 128 * 8192
DFLASH_W = 1.05e9                            # z-lab/Qwen3-8B-DFlash-b16, 1.05 B params at 8 bit, one block pass


def a100_qwen(B, spec=False, tau=4.159, pos=6):
    e = A["eff"]
    kvB = B * QKV / (A["bw"] * e["kv"])
    if not spec:
        t = max(QW / (A["bw"] * e["weight"]) + kvB, B * QOPS / (A["int8"] * e["compute"]))
        return dict(B=B, per_user=1 / t, agg=B / t)
    t_v = max(QW / (A["bw"] * e["weight"]) + kvB, pos * B * QOPS / (A["int8"] * e["compute"]))
    t_d = DFLASH_W / (A["bw"] * e["weight"])
    t = t_v + t_d
    return dict(B=B, per_user=tau / t, agg=B * tau / t)


q_cap = int((A["cap"] * A["eff"]["capacity"] - QW - DFLASH_W) // QKV)
# DeepSeek-V4.1-Flash 1M on 8 x A100 (HGX), official precision stored, weight-only dequant
D_CKPT, D_DENSE = 510.286e9, 8.523e9
D_ROUTED = 543.58e9 * 0.53
D_EXP, D_TOPK = 256, 6
D_KVU = 890.0 * D_CTX
D_ROWS = 36 * 512 * 288.0
D_OPS = 32e9 + 2 * 32 * 128 * (3 * D_CTX / 2 + D_CTX)
N_GPU = 8
MTP_LAYER = (D_DENSE / 40 + D_ROUTED / 40)    # the DSpark/MTP block ~ one layer's weights (modelled)


def union(p):
    return D_EXP * (1 - (1 - D_TOPK / D_EXP) ** p)


def a100_ds(B, spec=False, tau=4.159, pos=6):
    e = A["eff"]
    bw = N_GPU * A["bw"]
    coll = 2 * 40 * 15e-6                     # 2 TP8 all-reduces a layer x 40 layers x ~15 us NCCL (assumed)
    tok = B * (pos if spec else 1)
    t_w = (D_DENSE + union(tok) / D_EXP * D_ROUTED) / (bw * e["weight"])
    # index keys read once a user a step (shared by its verify positions), selected rows per position
    t_kv = (B * SCAN_TOK + tok * D_ROWS) / (bw * e["kv"])
    t_c = tok * D_OPS / (N_GPU * A["bf16"] * e["compute"])
    t = max(t_w + t_kv, t_c) + coll
    if not spec:
        return dict(B=B, per_user=1 / t, agg=B / t)
    t_d = (pos - 1) * ((D_DENSE / 40 + union(B) / D_EXP * D_ROUTED / 40) / (bw * e["weight"]) + 2 * 15e-6)
    t += t_d
    return dict(B=B, per_user=tau / t, agg=B * tau / t)


d_cap = int((N_GPU * A["cap"] * A["eff"]["capacity"] - D_CKPT - MTP_LAYER) // D_KVU)


def sweep(fn, cap, **kw):
    pts = []
    for B in sorted(set([1, 2, 4, 8, 16, 32, 48, 64, 96, 128, cap])):
        if B <= cap:
            pts.append(fn(B, **kw))
    return pts


gpu = dict(
    qwen=dict(system="1 x A100 80GB, W8 + FP8 KV, 8K", area=826.0, power_w=400.0, max_users=q_cap,
              ar=sweep(a100_qwen, q_cap), spec=sweep(a100_qwen, q_cap, spec=True),
              spec_tau3=sweep(a100_qwen, q_cap, spec=True, tau=3.1445),
              spec_note="DFlash-class drafter 1.05 GB read once a step + 6 verify positions; tau 4.159 per the brief, "
                        "3.1445 (Qwen third-party tau, PROGRAM_PLAN 10-05) as sensitivity; KV read once a user a step"),
    ds=dict(system="8 x A100 80GB (HGX A100), official precision stored, 1M", area=8 * 826.0, power_w=3200.0,
            max_users=d_cap, ar=sweep(a100_ds, d_cap), spec=sweep(a100_ds, d_cap, spec=True),
            spec_note="MTP gamma 5 (6 verify positions) at tau 4.159; draft = 5 serial MTP-block passes; index keys "
                      "read once a user a step (shared by the 6 positions)"),
    grade="modelled roofline with the repo's assumed A100 efficiencies (an UPPER bound for the A100)")


def best_at(points, floor):
    ok = [p["agg"] for p in points if p["per_user"] >= floor]
    return max(ok) if ok else 0.0


# ============================================================== Pareto curves
def ours_curve_s81():
    rows = []
    r_ar = F / S81["T_ar"]
    for n in range(1, base["slots_ar"] + 1):
        rows.append(dict(mode="AR all", users=n, per_user=r_ar, agg=n * r_ar))
    r_m = S81["tau"] * F / S81["T_mtp"]
    for n in range(1, base["mtp_users_all"] + 1):
        rows.append(dict(mode="MTP all", users=n, per_user=r_m, agg=n * r_m))
    rf = F / S81["T_mtp"]
    for nf in range(0, base["mtp_fillers_ar"] + 1, 5):
        rows.append(dict(mode="1 MTP reserved + AR fillers", users=1 + nf, per_user=rf if nf else r_m,
                         reserved_user=r_m, agg=r_m + nf * rf))
    return rows


def ours_curve_qwen():
    return [dict(mode="AR, 1 reserved + fillers", users=n, per_user=(Q["tok"] if n == 1 else qp["filler_tok_s"]),
                 reserved_user=Q["tok"], agg=Q["tok"] + (n - 1) * qp["filler_tok_s"]) for n in range(1, qp["slots"] + 1)]


def norm(rows, area, power):
    for r in rows:
        r["agg_per_mm2"] = r["agg"] / area
        r["agg_per_kW"] = r["agg"] / power * 1e3
    return rows


pareto = dict(
    s81=norm(ours_curve_s81(), S81["area"], S81["power_w"]),
    qwen_rom=norm(ours_curve_qwen(), Q["area"], Q["power_w"]),
    a100_ds_ar=norm([dict(B=p["B"], per_user=p["per_user"], agg=p["agg"]) for p in gpu["ds"]["ar"]], 6608.0, 3200.0),
    a100_ds_mtp=norm([dict(B=p["B"], per_user=p["per_user"], agg=p["agg"]) for p in gpu["ds"]["spec"]], 6608.0, 3200.0),
    a100_qwen_ar=norm([dict(B=p["B"], per_user=p["per_user"], agg=p["agg"]) for p in gpu["qwen"]["ar"]], 826.0, 400.0),
    a100_qwen_spec=norm([dict(B=p["B"], per_user=p["per_user"], agg=p["agg"]) for p in gpu["qwen"]["spec"]], 826.0, 400.0),
    grade="ours modelled (calendar) on composed single-user rates; A100 modelled roofline; per-W uses STALE power for ours",
)
gpu_at_1000 = dict(
    a100_ds_ar=best_at(gpu["ds"]["ar"], 1000), a100_ds_mtp=best_at(gpu["ds"]["spec"], 1000),
    a100_qwen_ar=best_at(gpu["qwen"]["ar"], 1000), a100_qwen_spec=best_at(gpu["qwen"]["spec"], 1000),
    s81_all_ar=base["agg_all_ar"], s81_mtp_plus_ar_fillers_reserved_only=S81["tau"] * F / S81["T_mtp"],
    s81_all_mtp=base["agg_all_mtp"], qwen_rom=qp["agg"],
    note="aggregate tok/s with every user guaranteed >= 1,000 tok/s (S81 MTP+AR: only the reserved user is >=1,000; "
         "its AR fillers run at 915 tok/s, so the guaranteed->=1,000 aggregate is the all-AR or all-MTP calendar)")


def cmp(ours_agg, area, power, g, gA, gW):
    gmax = max(p["agg"] for p in g)
    return dict(ours=ours_agg, a100_max=gmax, per_system_x=ours_agg / gmax,
                per_mm2_x=(ours_agg / area) / (gmax / gA), per_W_x_stale=(ours_agg / power) / (gmax / gW))


summary_cmp = dict(
    s81_b1_ar=cmp(S81["tok_ar"], S81["area"], S81["power_w"], [gpu["ds"]["ar"][0]], 6608, 3200),
    s81_b1_mtp=cmp(S81["tok_mtp"], S81["area"], S81["power_w"], [gpu["ds"]["spec"][0]], 6608, 3200),
    s81_max_ar_vs_a100_max_ar=cmp(base["agg_all_ar"], S81["area"], S81["power_w"], gpu["ds"]["ar"], 6608, 3200),
    s81_max_mtp_plus_ar_vs_a100_max_mtp=cmp(base["agg_mtp_plus_ar"], S81["area"], S81["power_w"], gpu["ds"]["spec"], 6608, 3200),
    s81_balanced_4fullscan_x2_vs_a100_max_mtp=cmp(repl[4]["agg_all_ar"], repl[4]["area_mm2"],
                                                   S81["power_w"] * repl[4]["area_mm2"] / S81["area"], gpu["ds"]["spec"], 6608, 3200),
    qwen_b1=cmp(Q["tok"], Q["area"], Q["power_w"], [gpu["qwen"]["ar"][0]], 826, 400),
    qwen_b1_vs_a100_spec_b1=cmp(Q["tok"], Q["area"], Q["power_w"], [gpu["qwen"]["spec"][0]], 826, 400),
    qwen_max_vs_a100_max_ar=cmp(qp["agg"], Q["area"], Q["power_w"], gpu["qwen"]["ar"], 826, 400),
    qwen_max_vs_a100_max_spec=cmp(qp["agg"], Q["area"], Q["power_w"], gpu["qwen"]["spec"], 826, 400),
)

# ============================================================== buffers / area (item 2)
SRAM_MM2_PER_MB = 2 * 1 / 3.869              # 3.869 MB/mm2 array (configs/architecture/chip_design_v2.json) x2 for
#                                              ASAP7 macro periphery (modelled, conservative)
H_MSG = 40976                                 # B, the S81 stage h message (p4l README_price_land)
area = dict(
    s81=dict(
        activation_double_buffer_per_die_B=H_MSG, mm2_per_die=H_MSG / 1e6 * SRAM_MM2_PER_MB,
        user_table_per_die_B=32 * 16, draft_seed_state_B=6 * 4 * 5120 * 2,
        total_per_die_mm2=(H_MSG + 512) / 1e6 * SRAM_MM2_PER_MB,
        pct_of_die=(H_MSG + 512) / 1e6 * SRAM_MM2_PER_MB / 799.2 * 100,
        note="one extra 40,976-B landing message a rank die (receive user k+1 while computing k); no per-user "
             "on-die state: KV, index keys and the 128-entry SWA window ring live in HBM (dsdv_svc_att WB+68u), the "
             "residual (4 x 5120 mHC streams) travels in the h message; the MTP wavefront already needs the same "
             "per-position landing. Draft dies keep a seed state per MTP user (4 x 5120 BF16 = 40 KB). Grade modelled."),
    qwen=dict(
        compute_die_per_user_B=4096 * 4 + 4096 * 2, kv_die_extra_slot_B=4 * 128 * 2 + 8192 * 4 * 4,
        compute_die_mm2_4users=4 * (4096 * 6) / 1e6 * SRAM_MM2_PER_MB,
        kv_die_mm2_3extra=3 * (1024 + 131072) / 1e6 * SRAM_MM2_PER_MB,
        note="per in-flight user the compute die keeps its FP32 residual + BF16 staging (24 KB; the user is resident "
             "between layers, unlike S81); the KV die needs one more service slot per extra user (q 1 KB + score/P "
             "row 8K x 4 heads x FP32 = 128 KB, upper bound). Grade modelled."),
    sram_density=dict(mm2_per_MB=SRAM_MM2_PER_MB, src="3.869 MB/mm2 (chip_design_v2.json) x 2 periphery, modelled"),
)

# ============================================================== touched tiles, closure risk, die floorplan / GRT
# status = gaps/die_element_table.json (generated 2026-10-18 03:29; re-check before acting); fails = its route fails
T = lambda **k: k
touched = [
    T(design="S81", change="multi-user calendar (N slots, per-slot {user,pos,base} table in the job words)",
      element="compiler dv_layer_compile.py + ot_dsdv_fixed_issue program image", status="RTL (inside dsdv_seq_host, "
      "RTL-only; children sh_vc CLOSED native owed, fails 2; sh_lk gating; sh_sq RTL-only)", fails=2,
      avoid_touching="yes: the issue unit already runs a fixed program with 2 job contexts; slots are program content",
      area_mm2=0.0, risk="low", why="compiler only; collision is already a fault"),
    T(design="S81", change="user tag on the stage h message",
      element="end-slice link endpoint dsdv_slice_lep (s_0S/0N/7S/7N, RTL owed) + ot_s81ph_link_ep",
      status="RTL owed (price_land end_slice_lep rtl_owed)", fails=0,
      avoid_touching="yes if the 10-b user rides spare header bits of the existing 512-b lane; the lep is not built yet, "
                     "so add it there before it is hardened", area_mm2=0.0, risk="low", why="unbuilt leaf, no closed view"),
    T(design="S81", change="2nd landing message buffer (40,976 B) at the stage ingress",
      element="NEW leaf dsdv_mu_land (beside each end-slice lep)", status="new", fails=0,
      avoid_touching="yes: new leaf abutted to the lep; the closed dsfd_dvland_* relays are not touched",
      area_mm2=0.021, risk="low", why="SRAM + pointer, one clock region with the lep; reuse the MTP wavefront landing "
                                       "if dsfd_vm_static_landing is the same buffer (then 0 new area)"),
    T(design="S81", change="per-user window ring (WB + 68 u)", element="dsdv_svc_att (in slice cluster dsdv_svc_rs)",
      status="exists in RTL; svc_rs RTL-only, no routed version", fails=0, avoid_touching="no change needed",
      area_mm2=0.0, risk="none", why="already built"),
    T(design="S81", change="per-user index-key base and KV-row base",
      element="dsdv_svc_sx_hrow (CLOSED, native owed) / svc_sx", status="CLOSED (native owed), fails 0", fails=0,
      avoid_touching="yes, preferred: the compiler writes the absolute per-user sector base into each scan job word "
                     "(as svc_att WIN_LOAD already carries SB[29:0]); fallback: a NEW user-context leaf dsdv_mu_ctx "
                     "on the job lane at the svc entry (rsv_05 / rsv_11) adds base[u] before the job reaches svc_sx",
      area_mm2=0.004, risk="low (compiler) / medium if svc_sx itself must change", why="keep the closed hrow closed"),
    T(design="S81", change="host plane N outstanding tokens",
      element="dsdv_seq_host host leaves (dsfd_host_sd CLOSED; dsfd_host_native RTL-only NEEDS_HUMAN fails 7)",
      status="mixed", fails=10, avoid_touching="partly: the start frame already carries {user,tok,pos}; the return "
      "path needs a user field, put it in the open dsfd_host_native rather than reopening dsfd_host_sd",
      area_mm2=0.001, risk="medium", why="dsfd_host_native already has 10 fails; fold the change into its next attempt"),
    T(design="S81", change="draft seed state per MTP user (40 KB each, <= 6)", element="draft dies (no binding today)",
      status="draft dies unowned in the S81 binding", fails=0, avoid_touching="n/a (draft dies not built)",
      area_mm2=0.13, risk="low", why="unbuilt"),
    T(design="S81", change="balancing: replicate the 4 full-scan stages x2", element="die count / chain topology",
      status="layer dies unchanged; upstream stage needs a 2nd downstream link (A/B)", fails=0,
      avoid_touching="die design untouched; chain/rack re-plan + the end-slice lep must expose the 2nd tx port",
      area_mm2=40 * 799.2, risk="medium (system), none (die)", why="no die re-plan; rack and cable plan change"),
    T(design="S81", change="balancing: 2-4 HBM stacks a scan die", element="p4l die (PHY shoreline)",
      status="p4l plan 1 stack/die", fails=0, avoid_touching="no", area_mm2=30.0,
      risk="high", why="FORCES A DIE RE-PLAN: +10-30 mm2 PHY and shoreline on a 799.2 mm2 near-reticle die"),
    T(design="Qwen", change="host interface NSLOT 1 -> 4", element="qkd_host_if_pins (core ot_host_if_pb2 is already "
      "parameterised NSLOT 16 / ENG_CTX 16; the pin wrapper $fatal enforces 1)", status="host cluster (KV-HROOT lane "
      "live 10-18 19:40); qkd_host_rt NOT STARTED", fails=0,
      avoid_touching="no, but it is a parameter change on an unclosed cluster: do it now in KV-HROOT",
      area_mm2=0.01, risk="low-medium", why="pins/regs grow with SB=2 bits; cluster not closed yet"),
    T(design="Qwen", change="KV calendar user dimension + per-user KV base",
      element="kv_calendar (compiler) + qkd_kvs_ctl / qkd_kvs_hroot (RTL-only)", status="RTL-only, fails 0", fails=0,
      avoid_touching="yes for the calendar; the base can ride the job word like S81", area_mm2=0.002, risk="low",
      why="no closed view"),
    T(design="Qwen", change="KV attention: next request lands while one is in service",
      element="qkd_kvs_attn (gating) / NEW leaf at the d2d landing (q 1 KB)", status="gating, fails 0", fails=0,
      avoid_touching="yes: slot 1,721 >= service 1,555, so the service never holds 2 requests; only q of request k+1 "
                     "must land, in a 1-KB leaf beside qkd_land; capacity-1 buffer unchanged",
      area_mm2=0.001, risk="low", why="the 128-KB second score slot is NOT needed under the shift calendar"),
    T(design="Qwen", change="per-user residual on the compute die (4 x 24 KB)", element="VM (compiler regions)",
      status="VM closed blocks", fails=0, avoid_touching="yes if VM has 96 KB free (check owed); else NEW buffer leaf "
      "beside the SU spine", area_mm2=0.05, risk="low", why="addressing only"),
    T(design="Qwen", change="all-reduce engine accepts one collective a slot (1,721 cycles)",
      element="tree / SerDes collective (qfd collective windows)", status="measured latency-bound 2,184; payload 1.9% busy",
      fails=0, avoid_touching="likely (pipelined links; check the collective sequencer accepts overlapping epochs)",
      area_mm2=0.0, risk="medium", why="if it is one-in-flight, Qwen caps at 3 slots (14.0k)"),
]
die_impact = dict(
    s81_p4l=dict(placement="new leaves abut existing consumers: dsdv_mu_land beside each end-slice lep (s_0S/0N/7S/7N), "
                           "optional dsdv_mu_ctx on the job lane at the svc entries rsv_05/rsv_11; both fit the "
                           "21.4% / 171 mm2 whitespace (price_land whitespace_before) without moving neighbours",
                 added_wires="0 die-level bits if the user tag uses spare header bits; else +10 b on the 4 x 276-b "
                             "stage lanes (abutted, no new crossing)", cut="worst cut 0.5357 -> +<0.001 (10 b)",
                 long_links="none; no relay stages", area_mm2=0.03, area_pct=0.004, fits_outline=True,
                 grt_risk="low: no new long wires; die GRT headroom unknown (no S81 die run; bind FAIL 10-18 00:38)",
                 replan="none for the calendar/buffers; HBM stacks 2-4 would force a die re-plan"),
    qwen_dv2f14=dict(placement="VM regions (compiler); fallback buffer leaf beside the SU spine", added_wires="0",
                     cut="unchanged", long_links="none", area_mm2=0.05, area_pct=0.006, fits_outline=True,
                     grt_risk="low"),
    qwen_kvs14=dict(placement="1-KB q landing leaf beside qkd_land (d2d entry); host_if NSLOT inside the host cluster",
                    added_wires="+2 slot bits on the host leaf ports (local)", cut="unchanged", long_links="none",
                    area_mm2=0.01, area_pct=0.004, fits_outline=True, grt_risk="low"),
    hbm_d4g_gen2=dict(note="not touched by this study; HBM multi-user = P position lanes (HBM-MTP lane, next die)"),
    grade="modelled from the plan geometry and RTL reading; no gate run")
plan = [
    "1. Compiler only (no tile touched): S81 N-slot calendar + shift-lemma checker; Qwen kv_calendar user dimension; "
    "per-user absolute bases written into job words (svc_att SB, svc_sx scan base, KV-die base).",
    "2. Unbuilt / unclosed leaves, folded into their first hardening (no re-closure): S81 end-slice lep user tag; Qwen "
    "qkd_host_if NSLOT 4 in KV-HROOT; S81 dsfd_host_native return-path user field on its next attempt.",
    "3. New small leaves beside closed consumers: dsdv_mu_land (40 KB, at each end-slice lep), Qwen 1-KB q landing "
    "beside qkd_land; dsdv_mu_ctx only if svc_sx cannot take an absolute base.",
    "4. Bench: two-user calendar on the stage/layer benches (bit-exact per user, reference user's cycle trace "
    "identical to the single-user trace) = MU.TOK.",
    "5. Optional throughput: replicate the 4 full-scan stages (chain re-plan, no die change). Do NOT add HBM stacks "
    "unless the 1-stack scan-rate check shows p4l is scan-bound (that is a die re-plan).",
]

out = dict(
    schema="opentallas.rom_multiuser_1018.v1", lane="ROM-MULTIUSER", date="2026-10-18",
    question="good single-user tok/s AND many concurrent requests by pipeline interleaving across the ROM chain",
    s81=dict(inputs=dict(T_ar=S81["T_ar"], T_mtp=S81["T_mtp"], tau=S81["tau"], II_composed=II_1018, II_1009=II_1009,
                         K=K, area_mm2=S81["area"], power_w=S81["power_w"], power_grade=S81["power_grade"],
                         dies_per_stage=DIES_PER_STAGE, grade="composed (token_path_1018) + 10-09 stage groups"),
             base=base, idle=idle, balance_stacks=balance, balance_replicate=repl,
             index_scan=dict(bytes_per_entry=IDX_B, L20_bytes_per_position=SCAN_L20, all_layers_bytes_per_position=SCAN_TOK,
                             L20_occ_cycles_at_1_stack=SCAN_L20 / (4 * STACK_BPS) * F,
                             L20_occ_cycles_composed=5937.0 * K,
                             grade="modelled from the published indexer definition (config) + 950 GB/s a stack")),
    qwen_rom=dict(inputs=dict(T=Q["T"], tok=Q["tok"], layer_period=LP, occupancy=OCC, head=HEAD, area_mm2=Q["area"],
                              power_w=Q["power_w"], power_grade=Q["power_grade"]),
                  allreduce_pipelined=qp, allreduce_one_in_flight=qs, idle_fraction=q_idle),
    a100=gpu, pareto=pareto, gpu_at_per_user_1000=gpu_at_1000, comparisons=summary_cmp, area=area,
    touched_tiles=touched, die_impact=die_impact, reclosure_plan=plan,
    grades_legend=__doc__.split("Every number carries a grade:")[1].split("Run:")[0].strip())
json.dump(out, open(os.path.join(HERE, "summary.json"), "w"), indent=1, default=float)

if __name__ == "__main__":
    print("K", round(K, 4), "II", round(II_1018), "base", {k: (round(v) if isinstance(v, float) else v)
                                                           for k, v in base.items() if k != "occ"})
    print("idle", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in idle.items()})
    for b in balance: print("stacks", b)
    for r in repl: print("repl", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    print("qwen piped", qp, "\nqwen 1-AR", qs, "\nqwen idle", q_idle)
    print("A100 qwen cap", q_cap, "ar max", round(max(p["agg"] for p in gpu["qwen"]["ar"])),
          "spec max", round(max(p["agg"] for p in gpu["qwen"]["spec"])),
          "b1 ar", round(gpu["qwen"]["ar"][0]["per_user"]), "b1 spec", round(gpu["qwen"]["spec"][0]["per_user"]))
    print("A100 ds cap", d_cap, "ar max", round(max(p["agg"] for p in gpu["ds"]["ar"])),
          "spec max", round(max(p["agg"] for p in gpu["ds"]["spec"])),
          "b1 ar", round(gpu["ds"]["ar"][0]["per_user"]), "b1 spec", round(gpu["ds"]["spec"][0]["per_user"]))
    print("gpu@1000", {k: (round(v) if isinstance(v, float) else v) for k, v in gpu_at_1000.items()})
    for k, v in summary_cmp.items(): print(k, {kk: round(vv, 4) for kk, vv in v.items()})
    print("area", json.dumps(area)[:600])
    print("index", out["s81"]["index_scan"])
