#!/usr/bin/env python3
"""S81-BALANCE 10-18: a work-balanced S81 chain (same die, chain re-plan + compiler only), a balanced Qwen ROM point,
and every design compared with the A100 80GB with area = logic die + HBM stack footprint on BOTH sides.

Design study only (no RTL change, no fleet job). Every number carries a grade:
  composed  = token_path_1018 composition (mixed measured / priced terms)
  measured  = an RTL bench / closed view / real-capture statistic quoted from a committed record
  priced    = analytic price of record
  modelled  = this file's arithmetic from cited constants (formula beside the number)
  published = vendor datasheet constant
  stale     = power modelled on an older die revision (no current power figure exists)
Run: python3 results/arch/s81_balance_1018/compute.py  (writes summary.json; reads only the inputs_* files beside it)
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
F = 1.2e9
J = lambda n: json.load(open(os.path.join(HERE, n)))
STG = J("inputs_s81_stages_1009.json")          # 10-09 per-stage-group classes (ROM-MULTIUSER input, same file)
EXP = J("inputs_expert_load_holdout.json")      # measured routing statistics (expert_load.py, real captures)
HMTP = J("inputs_hbm_mtp_next.json")            # HBM-MTP D1 table (P lanes)

# ====================================================================================== HBM stack footprints (published)
HBM3E_MM2 = 11.0 * 11.0     # Micron HBM3E product brief: form factor 11 mm x 11 mm x 0.72 mm (24 GB 8H / 36 GB 12H);
#                             JSSC Jan 2023 (HBM3): max package 11 x 11 mm. Used for every one of OUR stacks (HBM3E).
HBM2E_MM2 = 10.0 * 11.0     # SK hynix, Hot Chips 2026 (ServeTheHome report): pre-HBM4 base footprint 10 x 11 mm,
#                             growing to 12.4 x 11 mm on HBM4. Used for the A100 80GB's HBM2e stacks.
A100_STACKS_ACTIVE, A100_STACK_SITES = 5, 6     # A100 80GB: 5 active HBM2e stacks (5,120-bit bus), 6 sites on the
#                                                 interposer (1 non-functional); the 6th site is a sensitivity.
INTERPOSER_NOTE = ("No sourced A100 interposer area was found (P100 = 1,200 mm2, WikiChip CoWoS page, is a different "
                   "part). Interposer area is excluded on BOTH sides; our designs also need interposers/packages.")

# ====================================================================================== S81 chain model
S81 = dict(T_ar=965378.6, T_mtp=1311215.8, tau=4.159, wave=176183.8, dies=440, die_mm2=799.2, stacks=440,
           layer_dies=388, layers=40, power_w=440 * (84.1 + 2.8))
BPC_STACK = 950e9 / F                            # 791.7 B/cycle sustained a stack (d4g 99 B/cycle/SM basis)
HOP = 1006.0                                     # stage hop class (10-09 record)
II_1018 = S81["wave"] / 5
II_1009 = STG["mtp_wavefront"]["worst_stage_busy_us"] * 1e-6 * F * (1 + 46 / 11271) + STG["mtp_wavefront"]["hop_cycles"]
K = II_1018 / II_1009                            # 10-09 -> 10-18 composition scale (as ROM-MULTIUSER)
DIES_PER_LAYER = S81["layer_dies"] / S81["layers"]   # 9.7 dies hold one layer's weights (derived)
D_CTX = 1048576
IDX_B = 68.0                                     # FP4 128-d index key + E8M0 / 32 (deepseek-v4.1-flash.json)
SCAN_BYTES = {5937.0: IDX_B * D_CTX, 2951.0: IDX_B * D_CTX / 2, 873.0: IDX_B * 16384}   # by composed idx_score
EXPERT_FIELD_SHARE = (6912 + 8960) / (448 + 8192 + 2048 + 5120 + 96 + 6912 + 8960 + 1152)  # SPEC row counts, modelled
SELECT_LOCAL = 0.8                               # share of the select class that is shard-local top-k (modelled)
MERGE_PER_DOUBLING = 150.0                       # extra top-k merge cycles per doubling of shards (modelled)
groups = [s for s in STG["stages"] if s["label"].startswith("Stage")]


def group_occ(g, shard=4, stacks_per_die=1, mtp_share=False, expert_imb=1.0, tp_extra=0, ctx=1):
    """per-position occupancy (cycles, 10-18 scale) and single-user span of one stage group.
    shard: dies whose HBM stacks hold this layer's index shard (4 = the TP4 stage today; up to ~10 = all the layer's
    own dies). stacks_per_die: 1 = p4l as specified (SCANCHK: 16 ctrl x 2 PCs = 32 PCs = 1 HBM3E stack).
    mtp_share: one index read serves the 6 verify positions (per-position HBM share /6, score MACs kept).
    expert_imb: multi-user load factor on the routed-expert share of the field (measured routing statistics).
    tp_extra: extra dies given to this group's field (TP width): field x 4/(4+e), coll x (1 + 0.25 log2((4+e)/4))."""
    c = dict(g["by_class"])
    idx = g["idx_score_cycles"]
    span_extra = 0.0
    if idx > 0:
        b = SCAN_BYTES[idx]
        scan = b / (shard * stacks_per_die * BPC_STACK)               # HBM-bound stream of the index keys
        score = idx * 4.0 / shard                                     # score MACs at the composed per-die rate
        c["hbm"] = c["hbm"] - idx + max(scan, score)
        sel = c.get("select", 0.0)
        c["select"] = sel * (1 - SELECT_LOCAL) + sel * SELECT_LOCAL * 4.0 / shard + \
            (MERGE_PER_DOUBLING * math.log2(shard / 4.0) if shard > 4 else 0.0)
        if shard > 4:
            span_extra = 2 * HOP                                      # q out to the shard stages, top-k back
        if mtp_share:
            c["hbm_mtp_step"] = (c["hbm"] - max(scan, score)) * 6 + max(scan, 6 * score)
    if tp_extra:
        c["field"] = c["field"] * 4.0 / (4 + tp_extra)
        c["coll"] = c["coll"] * (1 + 0.25 * math.log2((4 + tp_extra) / 4.0))
    span = sum(v for k, v in c.items() if k != "hbm_mtp_step") + span_extra
    # multi-user occupancy: the routed-expert part of the field is load-imbalanced across the layer's expert groups
    fe = c.get("field", 0.0) * EXPERT_FIELD_SHARE * (expert_imb - 1.0)
    occ1 = span + fe                                                  # 1 job context: the stage is held for the span
    units = dict(field=c.get("field", 0.0) + fe, su=c.get("su", 0.0), coll=c.get("coll", 0.0),
                 svc=c.get("hbm", 0.0) + c.get("select", 0.0), hop=c.get("hop", 0.0))
    occ2 = max(max(units.values()), occ1 / 2)                         # 2 job contexts (ot_dsdv_fixed_issue)
    occ = occ1 if ctx == 1 else occ2
    shared = mtp_share and "hbm_mtp_step" in c
    step1 = 6 * (occ1 - c["hbm"]) + c["hbm_mtp_step"] if shared else 6 * occ1   # one shared read a step
    svc_step = 6 * c.get("select", 0.0) + c["hbm_mtp_step"] if shared else 6 * units["svc"]
    step2 = max(6 * max(units["field"], units["su"], units["coll"], units["hop"]), svc_step, step1 / 2)
    step = step1 if ctx == 1 else step2
    return dict(span=span * K, occ=occ * K, step=step * K)


def s81_design(name, shard=None, stacks_per_die=1, mtp_share=False, expert_imb=1.0, repl=None, tp=None, ctx=1,
               composed_basis=False):
    """shard / tp: {group id: value}. repl: {group id: copies}. composed_basis: reproduce the 10-18 composition
    (it charges the 10-09 scan rate, ~4 stacks a die)."""
    shard, repl, tp = shard or {}, repl or {}, tp or {}
    occs, base_span, new_span, base_step_pos = {}, 0.0, 0.0, {}
    for g in groups:
        ref = dict(span=sum(g["by_class"].values()) * K)
        if composed_basis:
            o = dict(span=ref["span"], occ=ref["span"], step=6 * ref["span"])
            # expert imbalance still applies to occupancy in multi-user
            fe = g["by_class"].get("field", 0.0) * EXPERT_FIELD_SHARE * (expert_imb - 1.0) * K
            o["occ"] += fe
            o["step"] += 6 * fe
        else:
            o = group_occ(g, shard=shard.get(g["id"], 4), stacks_per_die=stacks_per_die, mtp_share=mtp_share,
                          expert_imb=expert_imb, tp_extra=tp.get(g["id"], 0), ctx=ctx)
        r = repl.get(g["id"], 1)
        occs[g["id"]] = dict(span=o["span"], occ=o["occ"] / r, step=o["step"] / r, label=g["label"])
        base_span += ref["span"]
        new_span += o["span"]
    II = max(v["occ"] for v in occs.values())
    STEP = max(v["step"] for v in occs.values())
    worst = max(occs, key=lambda k: occs[k]["occ"])
    # single-user: pass latency moves by the summed span change; the MTP wave term = 5 x the worst stage's own
    # single-position occupancy (unreplicated: the reserved user always uses copy A).
    dT = new_span - base_span
    own_worst = max(v["span"] for v in occs.values())
    T_ar = S81["T_ar"] + dT
    T_mtp = S81["T_mtp"] + dT + 5 * (own_worst - II_1018)
    if mtp_share:
        # with a shared read the 6 positions join at the scan stage; the step's wave term is the worst stage's
        # step occupancy minus one position (modelled)
        own_step = max(v["step"] * repl.get(k, 1) for k, v in occs.items())
        T_mtp = S81["T_mtp"] + dT + (own_step - own_worst) - 5 * II_1018
    ar = F / T_ar
    mtp = S81["tau"] * F / T_mtp
    slots_ar = math.floor(T_ar / II)
    mtp_users = max(1, math.floor(T_mtp / STEP))
    fill = max(0, math.floor((T_mtp - mtp_users * STEP) / II))
    added_dies = sum((c - 1) * round(DIES_PER_LAYER) for c in repl.values()) + sum(tp.values())
    added_stacks = added_dies * stacks_per_die + (stacks_per_die - 1) * S81["dies"]
    dies = S81["dies"] + added_dies
    stacks = S81["stacks"] + added_stacks
    die_area = dies * S81["die_mm2"]
    tot_area = die_area + stacks * HBM3E_MM2
    agg_ar = slots_ar * ar
    agg_mtp = mtp_users * mtp
    return dict(name=name, II=round(II, 1), worst=worst, worst_label=occs[worst]["label"], step=round(STEP, 1),
                T_ar=round(T_ar, 1), T_mtp=round(T_mtp, 1), single_user_ar=round(ar, 1), single_user_mtp=round(mtp, 1),
                users_ar=slots_ar, agg_ar=round(agg_ar), users_mtp=mtp_users, agg_mtp=round(agg_mtp),
                mtp_plus_ar_fillers=round(agg_mtp + fill * F / T_mtp), fillers=fill, filler_rate=round(F / T_mtp, 1),
                dies=dies, stacks=stacks, die_mm2=round(die_area), total_mm2=round(tot_area),
                agg_ar_per_mm2_die=agg_ar / die_area, agg_ar_per_mm2_total=agg_ar / tot_area,
                agg_mtp_per_mm2_total=agg_mtp / tot_area, best_floor_agg=max(agg_ar, agg_mtp),
                best_floor_per_mm2_total=max(agg_ar, agg_mtp) / tot_area,
                power_w_stale=S81["power_w"] * dies / S81["dies"],
                occ_top=sorted(((k, round(v["occ"]), v["label"]) for k, v in occs.items()), key=lambda x: -x[1])[:6],
                grade="modelled on composed stage classes (10-09 groups x K) + SCANCHK stack count")


SCAN_GROUPS = [g["id"] for g in groups if g["idx_score_cycles"] > 0]
FULL_SCAN = [g["id"] for g in groups if g["idx_score_cycles"] > 2000]
imb = EXP["by_groups"]
IMB_CONT = imb["3"]["contiguous_worst_layer"]            # ~2.4 stages hold a layer's experts -> 3 expert groups
IMB_BAL = imb["3"]["balanced_holdout_worst_layer"]

designs = []
designs.append(s81_design("S81 as composed (10-18 composition; charges the 10-09 scan rate ~4 stacks/die)",
                          composed_basis=True, expert_imb=IMB_CONT))
cur = s81_design("S81 current, corrected: p4l 1 HBM3E stack a die (SCANCHK), contiguous experts", expert_imb=IMB_CONT)
designs.append(cur)
b1 = s81_design("B1: + experts spread hot/cold (LPT placement, measured holdout)", expert_imb=IMB_BAL)
designs.append(b1)
sh_all = {g: 10 for g in FULL_SCAN}
sh_all.update({g: 8 for g in SCAN_GROUPS if g not in FULL_SCAN})
b2 = s81_design("B2: + index shards over the layer's own ~10 dies' stacks (full-scan layers 10, reindex 8)",
                shard=sh_all, expert_imb=IMB_BAL)
designs.append(b2)
b3 = s81_design("B3: + MTP verify shares the index read across its 6 positions", shard=sh_all, expert_imb=IMB_BAL,
                mtp_share=True)
designs.append(b3)

# B4: replicate the worst stage groups greedily (users alternate copies), for the latency-throughput curve
heavy = sorted((g for g in groups if g["idx_score_cycles"] == 0), key=lambda g: -g["by_class"].get("field", 0))[:8]
TPW = {g["id"]: 4 for g in heavy}


def greedy(tag, tp=None, n=150, ctx=1):
    out, repl = [], {}
    for it in range(n):
        d = s81_design(f"{tag} + replicate worst groups ({sum(c - 1 for c in repl.values())} copies)", shard=sh_all,
                       expert_imb=IMB_BAL, mtp_share=True, repl=dict(repl), tp=tp, ctx=ctx)
        out.append(d)
        repl[d["worst"]] = repl.get(d["worst"], 1) + 1
    return out


curve = greedy("B4: B3")
curve_tp = greedy("B5: B3 + TP width (+4 dies on 8 field-heaviest groups)", tp=TPW)
curve_ctx2 = greedy("B6 (unmeasured 2 job contexts): B3", n=80, ctx=2)
knee = curve[10]                                  # the first 10 copies (+100 dies): the best gain per added die
best_ar = max(curve, key=lambda d: d["agg_ar_per_mm2_total"])
best_ctx2 = max(curve_ctx2, key=lambda d: d["agg_ar_per_mm2_total"])
best_mtp = max(curve, key=lambda d: d["agg_mtp_per_mm2_total"])
best_tp = max(curve_tp, key=lambda d: d["agg_ar_per_mm2_total"])
designs.append(knee)
designs.append(best_ar)
designs.append(best_tp)

# 2-context sensitivity (unmeasured: overlap 2 positions inside a stage with the existing 2 job contexts)
ctx2 = s81_design("B3 with 2 job contexts a die (unmeasured sensitivity)", shard=sh_all, expert_imb=IMB_BAL,
                  mtp_share=True, ctx=2)
# stacks-per-die alternatives (die change: PHY shoreline) for comparison only
st2 = s81_design("ALT (die change): 2 HBM3E stacks a die, no sharding", stacks_per_die=2, expert_imb=IMB_BAL)
# TP-width on the compute-heaviest non-scan groups (+4 dies each), for comparison
tpw = s81_design("ALT: B3 + TP width +4 dies on the 8 field-heaviest non-scan groups", shard=sh_all,
                 expert_imb=IMB_BAL, mtp_share=True, tp={g["id"]: 4 for g in heavy})

# top-down sizing for a per-user floor: every user >= FLOOR, maximise aggregate per mm2 (die + HBM)
FLOOR = 1000.0
pts = []
for d in curve + curve_tp:
    for mode, n, rate, agg in (("AR", d["users_ar"], d["single_user_ar"], d["agg_ar"]),
                               ("MTP", d["users_mtp"], d["single_user_mtp"], d["agg_mtp"])):
        if rate >= FLOOR:
            pts.append(dict(design=d["name"], mode=mode, users=n, per_user=rate, agg=agg, dies=d["dies"],
                            stacks=d["stacks"], total_mm2=d["total_mm2"], agg_per_mm2_total=agg / d["total_mm2"]))
best_floor = max(pts, key=lambda p: p["agg_per_mm2_total"])
pareto = []
for p in sorted(pts, key=lambda p: (-p["per_user"], -p["agg"])):
    if not pareto or p["agg"] > pareto[-1]["agg"]:
        pareto.append(p)

# ====================================================================================== Qwen ROM balance
Q = dict(T=251615.0, tok=4769.2, comp_dies=8, comp_mm2=841.0, kv_dies=8, kv_mm2=377.6, kv_mm2_old=272.6,
         stacks=32, layers=36)
LP = 4640.0 + 2246.0                         # composed layer period (die + xdie), token_path_1018/qwen_rom.json
HEAD = 3048.0                                # measured-old-RTL LM head on the tile field, once a token
Q_KV_USER = 36 * 8 * 128 * 2 * 8192          # 604 MB a user a token (FP8 KV, 8K)
KV_LAYER_DIE = Q_KV_USER / 36 / 8            # 2.10 MB a KV die a layer a user
KV_PORT_BPC = 4 * 512.0                      # 4 stacks x 512 B/cycle (qwen_attention_rate_1015, PV16 design)
QOCC = dict(
    tile_field=53152.0 / 36,                 # measured windows (qwen_reuse_1015): ROM read rate, 1 MAC/lane/cycle
    kv_service=1555.0,                       # measured-old-RTL static KV-die service (one instance)
    kv_hbm=KV_LAYER_DIE / KV_PORT_BPC,       # modelled: 1,024 cycles at 512 B/cycle/stack
    allreduce_one_in_flight=1228.0 + 956.0,  # measured windows (latency-bound)
    allreduce_payload=0.019 * 2184.0,        # SerDes payload busy 1.9 % of the windows (TPUT-RECHECK) -> 41 cycles
    d2d=2 * 1024 / 64.0,                     # q 1 KB + out 1 KB a KV die a layer over a 512-b/cycle d2d lane (assumed)
    compute_su=(61285.0 / 35) - 53152.0 / 36,  # vehicle - tile field: SU/VM work on separate units (composed)
)
SERVICE_MM2 = 8.3                            # PV16 decision: KV die +8.3 mm2 for one service's P.V upgrade (proxy for
#                                              one more distributed service instance; modelled)


def qwen_point(services=1, ar_issue="one", rom_lanes=1, kv_port_scale=1.0):
    """kv_port_scale: HBM port width a stack vs today's 512 B/cycle (1.6 = 820 B/cycle, ~80 % of HBM3E 9.6 Gb/s peak)"""
    occ = dict(tile_field=QOCC["tile_field"] / rom_lanes, compute_su=QOCC["compute_su"],
               kv_service=QOCC["kv_service"] / services, kv_hbm=QOCC["kv_hbm"] / kv_port_scale,
               allreduce={"one": QOCC["allreduce_one_in_flight"], "two": QOCC["allreduce_one_in_flight"] / 2,
                          "pipelined": QOCC["allreduce_payload"] + 2 * 64}[ar_issue], d2d=QOCC["d2d"])
    # the KV service already overlaps its own HBM read: service occupancy = max(compute/services, HBM floor)
    occ["kv_service"] = max(occ["kv_service"], occ["kv_hbm"])
    order = sorted(occ.items(), key=lambda x: -x[1])
    bind, b = order[0]
    n = max(1, math.floor(LP / b))
    head_bubbles = (rom_lanes == 1)
    filler_T = Q["T"] + n * HEAD / rom_lanes if head_bubbles else Q["T"] + n * HEAD / rom_lanes
    agg = Q["tok"] + (n - 1) * F / filler_T
    sat = F / (Q["layers"] * b + HEAD / rom_lanes)          # aggregate once the binding unit saturates
    return dict(services=services, allreduce=ar_issue, rom_lanes=rom_lanes, users=n, binding=bind,
                binding_cycles=round(b, 1), next=[(k, round(v, 1), math.floor(LP / v)) for k, v in order[1:5]],
                single_user=Q["tok"], filler_rate=round(F / filler_T, 1), agg=round(agg),
                saturated_agg_if_users_grow=round(sat),
                users_supported_by=dict((k, math.floor(LP / v)) for k, v in occ.items()))


q_opts = []
for sv, ar, rl, ks, why in [
        (1, "one", 1, 1.0, "today's units (one KV service, one all-reduce in flight)"),
        (1, "pipelined", 1, 1.0, "all-reduce accepts one collective a slot (compiler + collective sequencer)"),
        (2, "one", 1, 1.0, "2 KV services a die, all-reduce unchanged"),
        (2, "pipelined", 1, 1.0, "2 distributed KV services + pipelined all-reduce"),
        (4, "pipelined", 1, 1.0, "4 distributed KV services (one per HBM stack) + pipelined all-reduce"),
        (2, "pipelined", 2, 1.0, "+ ROM 2-user lanes on the compute die (weights read once for 2 users; DIE CHANGE)"),
        (4, "pipelined", 2, 1.6, "+ 4 services, wider KV HBM ports (820 B/cycle/stack), ROM 2-user lanes (DIE CHANGE)"),
        (4, "pipelined", 4, 1.6, "+ 4 services, wider KV HBM ports, ROM 4-user lanes (DIE CHANGE)")]:
    p = qwen_point(sv, ar, rl, ks)
    p["option"] = why
    kv_add = (sv - 1) * SERVICE_MM2 * Q["kv_dies"]
    p["added_kv_die_mm2_system"] = kv_add
    p["area_die_mm2"] = Q["comp_dies"] * Q["comp_mm2"] + Q["kv_dies"] * Q["kv_mm2"] + kv_add
    p["area_total_mm2"] = p["area_die_mm2"] + Q["stacks"] * HBM3E_MM2
    p["rom_lanes_area"] = "UNPRICED die change on the 841 mm2 compute die (P accumulators a MAC lane + P x-slot " \
                          "stores; HBM-MTP measured ~33 mm2/lane on a 642 mm2 HBM die as an analogue)" if rl > 1 else "0"
    p["agg_per_mm2_total"] = p["agg"] / p["area_total_mm2"]
    p["single_user_unchanged"] = True
    q_opts.append(p)
q_bal = q_opts[1]          # balanced point without die change: pipelined all-reduce, 1 service (KV die not binding)

# ====================================================================================== A100 80GB (modelled roofline)
A = dict(area=826.0, bw=2.039e12, cap=80e9, w=400.0, bf16=312e12, int8=624e12,
         eff=dict(weight=0.75, kv=0.70, compute=0.45, capacity=0.90))
QKV = Q_KV_USER
QW = 8.19e9
QOPS = 15.14e9 + 2 * 2 * 36 * 32 * 128 * 8192
DFLASH_W = 1.05e9


def a100_qwen(B, spec=False, tau=4.159, pos=6):
    e = A["eff"]
    kvB = B * QKV / (A["bw"] * e["kv"])
    if not spec:
        t = max(QW / (A["bw"] * e["weight"]) + kvB, B * QOPS / (A["int8"] * e["compute"]))
        return dict(B=B, per_user=1 / t, agg=B / t)
    t = max(QW / (A["bw"] * e["weight"]) + kvB, pos * B * QOPS / (A["int8"] * e["compute"])) + \
        DFLASH_W / (A["bw"] * e["weight"])
    return dict(B=B, per_user=tau / t, agg=B * tau / t)


D_CKPT, D_DENSE, D_ROUTED = 510.286e9, 8.523e9, 543.58e9 * 0.53
D_EXP, D_TOPK = 384, 6
D_KVU = 890.0 * D_CTX
D_ROWS = 36 * 512 * 288.0
SCAN_TOK = IDX_B * (3 * D_CTX / 2 + D_CTX + 4 * 16384)
D_OPS = 32e9 + 2 * 32 * 128 * (3 * D_CTX / 2 + D_CTX)
NG = 8


def union(p):
    return D_EXP * (1 - (1 - D_TOPK / D_EXP) ** p)


def a100_ds(B, spec=False, tau=4.159, pos=6):
    e = A["eff"]
    bw = NG * A["bw"]
    coll = 2 * 40 * 15e-6
    tok = B * (pos if spec else 1)
    t_w = (D_DENSE + union(tok) / D_EXP * D_ROUTED) / (bw * e["weight"])
    t_kv = (B * SCAN_TOK + tok * D_ROWS) / (bw * e["kv"])
    t_c = tok * D_OPS / (NG * A["bf16"] * e["compute"])
    t = max(t_w + t_kv, t_c) + coll
    if not spec:
        return dict(B=B, per_user=1 / t, agg=B / t)
    t += (pos - 1) * ((D_DENSE / 40 + union(B) / D_EXP * D_ROUTED / 40) / (bw * e["weight"]) + 2 * 15e-6)
    return dict(B=B, per_user=tau / t, agg=B * tau / t)


q_cap = int((A["cap"] * A["eff"]["capacity"] - QW - DFLASH_W) // QKV)
d_cap = int((NG * A["cap"] * A["eff"]["capacity"] - D_CKPT - (D_DENSE + D_ROUTED) / 40) // D_KVU)
sw = lambda fn, cap, **kw: [fn(B, **kw) for B in sorted(set([1, 2, 4, 8, 16, 32, 48, 64, 96, 128, cap])) if B <= cap]
gpu = dict(ds_ar=sw(a100_ds, d_cap), ds_mtp=sw(a100_ds, d_cap, spec=True), q_ar=sw(a100_qwen, q_cap),
           q_spec=sw(a100_qwen, q_cap, spec=True))
A_AREA = dict(ds=dict(die=NG * 826.0, total=NG * (826.0 + A100_STACKS_ACTIVE * HBM2E_MM2),
                      total_6sites=NG * (826.0 + A100_STACK_SITES * HBM2E_MM2), stacks=NG * 5, power_w=NG * 400.0),
              qwen=dict(die=826.0, total=826.0 + A100_STACKS_ACTIVE * HBM2E_MM2,
                        total_6sites=826.0 + A100_STACK_SITES * HBM2E_MM2, stacks=5, power_w=400.0))
best = lambda pts, floor=0.0: max([p["agg"] for p in pts if p["per_user"] >= floor] or [0.0])

# ====================================================================================== the comparison table
HBM_DIE = 641.83
hm = {r["P"]: r for r in HMTP["table"]}
systems = [
    # name, model, dies, die_mm2_each(or total), stacks, b1_ar, b1_spec, agg_ar(all users >= floor), agg_spec, power, grade
    dict(name="S81 current (corrected 1 stack/die), 1 user (today)", model="ds", die_mm2=cur["die_mm2"],
         stacks=cur["stacks"], b1_ar=cur["single_user_ar"], b1_spec=cur["single_user_mtp"],
         multi_ar=cur["single_user_ar"], multi_spec=cur["single_user_mtp"], power=cur["power_w_stale"],
         grade="modelled (composed classes + SCANCHK)"),
    dict(name="S81 current + multi-user calendar (ROM-MULTIUSER, corrected)", model="ds", die_mm2=cur["die_mm2"],
         stacks=cur["stacks"], b1_ar=cur["single_user_ar"], b1_spec=cur["single_user_mtp"], multi_ar=cur["agg_ar"],
         multi_spec=cur["agg_mtp"], power=cur["power_w_stale"], grade="modelled"),
    dict(name="S81 balanced B3 (no added dies)", model="ds", die_mm2=b3["die_mm2"], stacks=b3["stacks"],
         b1_ar=b3["single_user_ar"], b1_spec=b3["single_user_mtp"], multi_ar=b3["agg_ar"], multi_spec=b3["agg_mtp"],
         power=b3["power_w_stale"], grade="modelled"),
    dict(name=f"S81 balanced B4 knee ({knee['dies']} dies: the 10 heaviest groups x2)", model="ds",
         die_mm2=knee["die_mm2"], stacks=knee["stacks"], b1_ar=knee["single_user_ar"],
         b1_spec=knee["single_user_mtp"], multi_ar=knee["agg_ar"], multi_spec=knee["agg_mtp"],
         power=knee["power_w_stale"], grade="modelled"),
    dict(name=f"S81 balanced B4 best per mm2 ({best_ar['dies']} dies)", model="ds", die_mm2=best_ar["die_mm2"],
         stacks=best_ar["stacks"], b1_ar=best_ar["single_user_ar"], b1_spec=best_ar["single_user_mtp"],
         multi_ar=best_ar["agg_ar"], multi_spec=best_ar["agg_mtp"], power=best_ar["power_w_stale"], grade="modelled"),
    dict(name="Qwen ROM TP8 today (1 user)", model="qwen", die_mm2=q_opts[0]["area_die_mm2"], stacks=Q["stacks"],
         b1_ar=Q["tok"], b1_spec=None, multi_ar=Q["tok"], multi_spec=None, power=8 * 527.0 * (1 + Q["kv_mm2"] / 841.0),
         grade="composed"),
    dict(name="Qwen ROM balanced (pipelined all-reduce, 4 users)", model="qwen", die_mm2=q_bal["area_die_mm2"],
         stacks=Q["stacks"], b1_ar=Q["tok"], b1_spec=None, multi_ar=q_bal["agg"], multi_spec=None,
         power=8 * 527.0 * (1 + Q["kv_mm2"] / 841.0), grade="modelled"),
    dict(name="HBM d4g DS (192 dies, 1 job in flight)", model="ds", die_mm2=192 * HBM_DIE, stacks=384, b1_ar=1993.8,
         b1_spec=3258.7, multi_ar=1993.8, multi_spec=3258.7, power=12544.0,
         grade="composed AR / priced MTP (price5)"),
    dict(name="HBM d4g Qwen (8 dies)", model="qwen", die_mm2=8 * HBM_DIE, stacks=16, b1_ar=930.9, b1_spec=None,
         multi_ar=930.9, multi_spec=None, power=8 * HBM_DIE * 0.5 + 16 * 2.8, grade="composed"),
    dict(name="HBM next die P=2 DS (192 x 676.4 mm2)", model="ds", die_mm2=192 * hm[2]["die_mm2"], stacks=384,
         b1_ar=hm[2]["ds_ar"], b1_spec=hm[2]["ds_mtp"], multi_ar=hm[2]["ds_users_agg"], multi_spec=hm[2]["ds_mtp"],
         power=12544.0 * hm[2]["die_mm2"] / HBM_DIE, grade="modelled (HBM-MTP D1; P=2 users = 2 AR users)"),
    dict(name="HBM next die P=2 Qwen (8 x 676.4 mm2)", model="qwen", die_mm2=8 * hm[2]["die_mm2"], stacks=16,
         b1_ar=hm[2]["qwen_ar"], b1_spec=hm[2]["qwen_dflash16_pub"], multi_ar=hm[2]["qwen_users_agg"],
         multi_spec=hm[2]["qwen_dflash16_pub"], power=8 * hm[2]["die_mm2"] * 0.5 + 16 * 2.8,
         grade="modelled (HBM-MTP D1; Qwen DFlash rows under HBM-MTP-QCHK)"),
]
cmp_rows = []
for s in systems:
    g = "ds" if s["model"] == "ds" else "qwen"
    ga, gs = (gpu["ds_ar"], gpu["ds_mtp"]) if g == "ds" else (gpu["q_ar"], gpu["q_spec"])
    tot = s["die_mm2"] + s["stacks"] * HBM3E_MM2
    aa = A_AREA[g]
    row = dict(system=s["name"], grade=s["grade"], die_mm2=round(s["die_mm2"]), stacks=s["stacks"],
               hbm_mm2=round(s["stacks"] * HBM3E_MM2), total_mm2=round(tot), a100_die_mm2=aa["die"],
               a100_total_mm2=aa["total"])
    for tag, ours, gpts, floor in (("b1_ar", s["b1_ar"], ga[:1], 0), ("b1_spec", s["b1_spec"], gs[:1], 0),
                                   ("max_ar", s["multi_ar"], ga, 0), ("max_spec", s["multi_spec"], gs, 0),
                                   ("floor1000_ar", s["multi_ar"] if s["b1_ar"] >= FLOOR else 0.0, ga, FLOOR),
                                   ("floor1000_spec", (s["multi_spec"] or 0.0) if (s["b1_spec"] or 0) >= FLOOR else 0.0,
                                    gs, FLOOR)):
        if ours is None or (tag == "floor1000_spec" and s["b1_spec"] is None):
            continue
        gv = best(gpts, floor)
        row[tag] = dict(ours=round(ours), a100=round(gv),
                        per_system=(ours / gv if gv else None),
                        per_mm2_die=((ours / s["die_mm2"]) / (gv / aa["die"]) if gv else None),
                        per_mm2_die_hbm=((ours / tot) / (gv / aa["total"]) if gv else None),
                        per_mm2_die_hbm_6sites=((ours / tot) / (gv / aa["total_6sites"]) if gv else None),
                        per_W_stale=((ours / s["power"]) / (gv / aa["power_w"]) if gv else None),
                        a100_note=("A100 has no point at >= 1,000 tok/s per user" if floor and not gv else ""))
    cmp_rows.append(row)


def rnd(x):
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: rnd(v) for k, v in x.items()}
    if isinstance(x, list):
        return [rnd(v) for v in x]
    return x


summary = dict(
    schema="opentallas.s81_balance_1018.v1", lane="S81-BALANCE", date="2026-10-18",
    grades="composed / measured / priced / modelled / published / stale (see compute.py header)",
    hbm_footprint=dict(hbm3e_mm2=HBM3E_MM2, hbm3e_src="Micron HBM3E product brief: 11 x 11 x 0.72 mm (24/36 GB); "
                       "JSSC Jan 2023 HBM3: max package 11 x 11 mm", hbm2e_mm2=HBM2E_MM2,
                       hbm2e_src="SK hynix at Hot Chips 2026 (ServeTheHome): pre-HBM4 base 10 x 11 mm; HBM4 12.4 x 11",
                       a100_stacks=A100_STACKS_ACTIVE, a100_sites=A100_STACK_SITES, interposer=INTERPOSER_NOTE,
                       grade="published"),
    scanchk=dict(finding="p4l has ONE HBM3E stack a die: 16 regional controllers dsfd_ctrl_rg2 x 2 pseudo-channels = "
                         "32 PCs = one HBM3/3E stack, one PHY with an 8.5 mm north face (s81_dv_1016/SPEC.md 0b-p4g); "
                         "tput_recheck counts 440 stacks for 440 dies",
                 composed_scan_rate="the 10-18 composition charges the 10-09 L20 scan, 5,987 cycles for 71.3 MB on "
                                    "4 dies = 3.76 stacks a die",
                 corrected=dict(ar=cur["single_user_ar"], mtp=cur["single_user_mtp"]),
                 note="lane S81-SCANCHK had not reported when this study ran; this is this lane's own check"),
    expert_load=dict(EXP, applied=dict(groups_per_layer=3, contiguous_worst=IMB_CONT, balanced_worst=IMB_BAL,
                                       expert_field_share=EXPERT_FIELD_SHARE,
                                       note="S81 row-shards every matrix over all frames of a TP4 stage (SPEC: rows/128 "
                                            "a frame), so routing cannot unbalance dies INSIDE a stage; only the split "
                                            "of a layer's 384 experts over its ~2.4 stages matters (3 groups)")),
    s81=dict(designs=rnd(designs), curve=rnd([{k: d[k] for k in ("name", "dies", "stacks", "total_mm2", "II", "users_ar",
                                                               "agg_ar", "users_mtp", "agg_mtp", "single_user_ar",
                                                               "single_user_mtp", "agg_ar_per_mm2_total",
                                                               "agg_mtp_per_mm2_total")} for d in curve]),
             curve_tp=rnd([{k: d[k] for k in ("name", "dies", "stacks", "total_mm2", "II", "users_ar", "agg_ar",
                                              "users_mtp", "agg_mtp", "single_user_ar", "single_user_mtp",
                                              "agg_ar_per_mm2_total", "agg_mtp_per_mm2_total")} for d in curve_tp]),
             best_tp_per_mm2=rnd(best_tp), knee=rnd(knee), best_ctx2=rnd(best_ctx2),
             curve_ctx2=rnd([{k: d[k] for k in ("name", "dies", "total_mm2", "II", "users_ar", "agg_ar", "users_mtp",
                                                "agg_mtp", "agg_ar_per_mm2_total")} for d in curve_ctx2]), best_ar_per_mm2=rnd(best_ar), best_mtp_per_mm2=rnd(best_mtp), ctx2_sensitivity=rnd(ctx2),
             alt_two_stacks_die_change=rnd(st2), alt_tp_width=rnd(tpw),
             floor=dict(per_user_floor=FLOOR, best=rnd(best_floor), pareto=rnd(pareto)),
             constants=dict(K=K, dies_per_layer=DIES_PER_LAYER, stack_B_per_cycle=BPC_STACK, hop=HOP,
                            select_local=SELECT_LOCAL, merge_per_doubling=MERGE_PER_DOUBLING)),
    qwen=dict(occupancy_per_layer=rnd(QOCC), layer_period=LP, options=rnd(q_opts), balanced=rnd(q_bal),
              kv_die_mm2=Q["kv_mm2"], kv_die_src="kvs14c place kit 377.6 mm2 (HANDOFF KV-CLOCK 10-18 06:55)"),
    a100=dict(ds_cap_users=d_cap, qwen_cap_users=q_cap, area=A_AREA, b1=dict(ds_ar=gpu["ds_ar"][0],
              ds_mtp=gpu["ds_mtp"][0], q_ar=gpu["q_ar"][0], q_spec=gpu["q_spec"][0]),
              max=dict(ds_ar=best(gpu["ds_ar"]), ds_mtp=best(gpu["ds_mtp"]), q_ar=best(gpu["q_ar"]),
                       q_spec=best(gpu["q_spec"])),
              grade="modelled roofline (repo efficiencies) = A100 UPPER bound; 384 routed experts (corrected from 256 "
                    "in ROM-MULTIUSER)"),
    comparison=rnd(cmp_rows),
)
json.dump(summary, open(os.path.join(HERE, "summary.json"), "w"), indent=1)
if __name__ == "__main__":
    for d in designs + [ctx2, st2, tpw]:
        print(f"{d['name'][:70]:70s} II {d['II']:8.0f} AR {d['single_user_ar']:7.1f} MTP {d['single_user_mtp']:7.1f} "
              f"uAR {d['users_ar']:3d} agg {d['agg_ar']:6d} uMTP {d['users_mtp']:2d} aggM {d['agg_mtp']:6d} dies "
              f"{d['dies']} mm2 {d['total_mm2']} /mm2 {d['agg_ar_per_mm2_total']:.4f} {d['worst_label']}")
    print("best floor", best_floor)
    for p in q_opts:
        print(p["option"][:60], p["users"], p["binding"], p["binding_cycles"], p["agg"], p["next"][:3])
    for r in cmp_rows:
        print(r["system"][:50], {k: (v["ours"], v["a100"], v["per_mm2_die_hbm"] and round(v["per_mm2_die_hbm"], 3))
                                 for k, v in r.items() if isinstance(v, dict)})
