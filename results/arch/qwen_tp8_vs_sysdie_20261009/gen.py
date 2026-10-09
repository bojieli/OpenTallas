#!/usr/bin/env python3
"""Qwen3-8B ROM, 8K AR: re-price TP8 against the companion system die (owner stream qwen-tp8-vs-sysdie, 2026-10-09).

Adds no model of its own beyond the stated per-node scaling rules.  Inputs (all committed):
  * the token path results/arch/token_path_20261008/qwen_rom.json (218,472 cycles, 5,492.7 tok/s; per-node windows);
  * the engine tiling rule tools/hdc_qwen_fullshape_placement_w12.py (rtl_split, run at TP 4 and TP 8);
  * the r17b die geometry site/chip_explorer/inputs/geo.json (block areas);
  * the r21b area sheet area_sheet_7f423a133.json (codex/qwen-system-resume-20261009 @ 791a681f5, sha below);
  * configs/hardware/technology.json links (UCIe, board SerDes) and HBM;
  * the collective RTL rtl/rom/ot_rom_oneshot_allreduce.sv (fold latency 2 + (N-1) x ADD_LAT, LAT 339 board).

    python3 results/arch/qwen_tp8_vs_sysdie_20261009/gen.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLK = 1.2e9
TP_PATH = ROOT / "results/arch/token_path_20261008/qwen_rom.json"
GEO = ROOT / "site/chip_explorer/inputs/geo.json"
TECH = ROOT / "configs/hardware/technology.json"
STEP = ROOT / "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_step_stream4.json"
AREA_SHEET = dict(path="results/arch/qwen_system_20261009/area_sheet_7f423a133.json",
                  commit="791a681f5 (branch codex/qwen-system-resume-20261009, not on main)",
                  sha256="73cc3ecd4aed0826fc2fe44e0672e660d43cffa9424ddfa20eb4f380bc33f79f",
                  r21b_outline_mm2=846.792, no_reuse_known_total_mm2=882.774, budget_mm2=858.0,
                  scale_rom_macros_mm2=3.679, native128pc_frames_mm2=11.771, embedding_stations_mm2=2.42)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def placement(tp, groups):
    code = ("import json,hdc_qwen_fullshape_placement_w12 as P,hdc_isa as I;r=P.placement();"
            "print(json.dumps(dict(lanes=I.W_LANES,il=I.INTERLEAVE,words=r['matrix_code_words_per_die'],"
            "m={m['name'].split('.')[-1]:dict(rows=m['rows'],k=m['columns'],split=m['split'],kc=m['k_per_split'],"
            "rounds=m['rounds'],stream=m['words'],util=round(m['rows']*m['columns']/(m['words']*I.W_LANES*P.GROUPS),4))"
            " for m in r['matrices_per_die'][:4]+r['matrices_per_die'][-1:]})))")
    env = dict(os.environ, QWEN_O4_TP=str(tp), QWEN_O4_GROUPS=str(groups))
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "tools", env=env, capture_output=True, text=True,
                         check=True).stdout
    return json.loads(out.strip().splitlines()[-1])


def geo_areas():
    q = json.loads(GEO.read_text())["qwen_rom"]
    a, names = {}, {}
    for k, x, y, w, h, n in q["rects"]:
        kind = q["kinds"][k]
        a[kind] = a.get(kind, 0.0) + w * h / 1e6
        if kind == "io":
            names[n] = w * h / 1e6
    return {k: round(v, 2) for k, v in a.items()}, {k: round(v, 2) for k, v in names.items()}


def main():
    tp = json.loads(TP_PATH.read_text())
    tech = json.loads(TECH.read_text())
    nodes = {n["id"]: n for n in tp["nodes"]}
    L1 = {n["id"].split(".", 1)[1]: n for n in tp["nodes"] if n["group"] == "L1"}
    groups = {g["id"]: g for g in tp["groups"]}
    base_tok = tp["totals"]["cycles"]
    steady = groups["L1"]["cycles"]
    l0_extra = groups["L0"]["cycles"] - steady
    head = nodes["head.lm_head"]
    n_handoff = int(round(base_tok - (7 + groups["L0"]["cycles"] + 35 * steady + head["cycles"])))
    assert n_handoff == 36, n_handoff

    p4, p8, p8h = placement(4, 6144), placement(8, 6144), placement(8, 3072)
    area_kind, io = geo_areas()

    # ---------------- per-node scaling rules ----------------
    me_ops = ["qkv", "o_proj", "gate_up", "down"]
    pm = {"qkv": "qkv", "o_proj": "o", "gate_up": "gu", "down": "down"}
    adder = lambda n: n["cycles"] - n["base_cycles"]           # priced adders stay per op (relays, MUL_LAT, band)
    attn_stream_tp4 = 2 * 8192 * 128 * 2 // 4096                # 4 MiB a layer a die over 128 PC landings x 32 B = 1,024
    attn_fixed = L1["attn_kv"]["base_cycles"] - attn_stream_tp4  # 131

    def layer(tp8_variant, su_per_head_scale=0.5, attn_mode="central", ar_extra=0, relay_board=False):
        """steady-layer cycles under a TP8 variant ('A' 4 stacks/die, 'B' 2 stacks/die, 'H' half die G 3,072)"""
        rows = {}
        for op in me_ops:
            n = L1[op]
            s4 = p4["m"][pm[op]]["stream"]
            s8 = (p8 if tp8_variant in "AB" else p8h)["m"][pm[op]]["stream"]
            rows[op] = n["base_cycles"] - s4 + s8 + adder(n)
        a = L1["attn_kv"]
        if tp8_variant == "A":   # 1 KV head over the same 128 PC landings / 24 row engines: stream halves
            st = {"central": attn_stream_tp4 / 2, "best": attn_stream_tp4 / 2 - attn_fixed / 2,
                  "worst": attn_stream_tp4 / 2 + attn_fixed}[attn_mode]
            rows["attn_kv"] = a["base_cycles"] - attn_stream_tp4 + st + adder(a)
        else:                    # half the PC landings / row engines (B) or half the die (H): unchanged
            rows["attn_kv"] = a["cycles"]
        for op in ("rmsnorm1", "attn_tail", "rmsnorm2", "residual"):
            rows[op] = L1[op]["cycles"]                           # full-vector, replicated on every die
        for op in ("qknorm_rope", "softmax_norm"):
            rows[op] = L1[op]["cycles"] * su_per_head_scale       # per-head work: 8q+2kv -> 4q+1kv heads a die
        fold = (8 - 1) * 5 - (4 - 1) * 5                          # 2 + (N-1) x ADD_LAT: 37 vs 17 cycles
        board = 339 + 4 if relay_board else 0                     # 2x2 board mesh: diagonal relayed (2 crossings)
        for op in ("allreduce1", "allreduce2"):
            rows[op] = L1[op]["cycles"] + fold + ar_extra + board
        return rows

    def token(rows, variant):
        lay = sum(rows.values())
        if variant == "A":
            l0 = (l0_extra - 222) / 2 + 222      # cold KV fill halves (4 stacks, half the bytes); 222 = KV constants
        else:
            l0 = l0_extra
        hs = (p8 if variant in "AB" else p8h)["m"]["lm_head"]["stream"]
        hd = head["cycles"] - p4["m"]["lm_head"]["stream"] + hs + 10   # + 8-way argmax gather (4 more beats + fold)
        tot = 7 + (lay + l0) + 35 * lay + hd + 36
        return dict(layer_cycles=round(lay, 1), l0_extra=round(l0, 1), head_cycles=round(hd, 1),
                    token_cycles=round(tot, 1), tok_s=round(CLK / tot, 1),
                    vs_tp4=round(base_tok / tot - 1, 4),
                    link_cycles=round(36 * (rows["allreduce1"] + rows["allreduce2"]), 1),
                    link_share=round(36 * (rows["allreduce1"] + rows["allreduce2"]) / tot, 4),
                    rows={k: round(v, 1) for k, v in rows.items()})

    tp4 = dict(layer_cycles=steady, token_cycles=base_tok, tok_s=round(CLK / base_tok, 1),
               link_cycles=tp["totals"]["by_class"][1]["cycles"],
               link_share=round(tp["totals"]["by_class"][1]["cycles"] / base_tok, 4),
               rows={k: v["cycles"] for k, v in L1.items() if k != "kv_prefetch"})
    tp8 = {}
    for v in ("A", "B", "H"):
        tp8[v] = dict(central=token(layer(v), v),
                      best=token(layer(v, su_per_head_scale=0.5, attn_mode="best"), v),
                      worst=token(layer(v, su_per_head_scale=1.0, attn_mode="worst"), v),
                      board_2x2_relay=token(layer(v, relay_board=True), v))

    # ---------------- option 1: companion system die ----------------
    ucie = tech["links"]["rom_package_ucie"]["hop_latency_s"]
    x_lat = dict(central=round(ucie["value"] * CLK) + 2, low=11 + 2, high=round(ucie["range_high"] * CLK) + 2)
    # crossings a token: attention q out + attention result back, every layer (row engines move with the KV);
    # embedding row in; token out to the host (loop turnaround); collectives: 2 crossings an all-reduce if moved
    cross = dict(attention=2 * 36, embed=1, host_loop=2, collective_if_moved=2 * 72)
    sysdie = {}
    for k, lat in x_lat.items():
        a = (cross["attention"] + cross["embed"] + cross["host_loop"]) * lat
        b = a + cross["collective_if_moved"] * lat
        sysdie[k] = dict(crossing_cycles=lat,
                         collective_stays=dict(added=a, token_cycles=base_tok + a, tok_s=round(CLK / (base_tok + a), 1),
                                               vs_tp4=round(base_tok / (base_tok + a) - 1, 4)),
                         collective_moved=dict(added=b, token_cycles=base_tok + b, tok_s=round(CLK / (base_tok + b), 1),
                                               vs_tp4=round(base_tok / (base_tok + b) - 1, 4)))
    # alternative split: KV landing moved, row engines stay -> 4 MiB a layer a die crosses UCIe (prefetch hides it)
    kv_bytes_layer = 2 * 8192 * 128 * 2
    ucie_bw = tech["links"]["rom_package_ucie"]["bytes_s"]["value"]
    fill_ucie_cyc = kv_bytes_layer / ucie_bw * CLK

    # ---------------- area ----------------
    AS = AREA_SHEET
    rom_tp4_lin = 229.3                     # tools/uarch_model.qwen_rom_need_mm2(4, 6144) rom_mm2 (75 Mbit/mm2 basis)
    code_banks_tp4, code_banks_tp8 = 5, -(-p8["words"] // 4096)
    rom_save_lin = rom_tp4_lin / 2
    rom_save_quant = rom_tp4_lin * (code_banks_tp4 - code_banks_tp8) / code_banks_tp4
    serdes_add = 2 * io["io_serdes"]        # 3x off-package destinations (6 vs 2): 3x lanes
    coll_add = round(io["io_collective"] * (7 / 3 - 1), 2)  # 7 receive FIFOs + 8-input fold vs 3
    kv_half = round(area_kind["phy"] / 2 + area_kind["hbm_ctrl"] / 2 + area_kind["cdc"] / 2 + area_kind["row_engine"] / 2
                    + AS["native128pc_frames_mm2"] / 2, 2)
    die_tp4 = AS["no_reuse_known_total_mm2"]
    tp8A = dict(central=round(die_tp4 - rom_save_quant - AS["scale_rom_macros_mm2"] / 2 + serdes_add + coll_add, 1),
                linear=round(die_tp4 - rom_save_lin - AS["scale_rom_macros_mm2"] / 2 + serdes_add + coll_add, 1))
    tp8B = {k: round(v - kv_half, 1) for k, v in tp8A.items()}
    moved = dict(hbm_phy=area_kind["phy"], hbm_ctrl=area_kind["hbm_ctrl"], cdc=area_kind["cdc"],
                 row_engines=area_kind["row_engine"], native128pc_frames=AS["native128pc_frames_mm2"],
                 io_embedding_rom=io["io_embedding_rom"], embedding_stations=AS["embedding_stations_mm2"])
    moved_coll = dict(io_serdes=io["io_serdes"], io_collective=io["io_collective"])
    ucie_new = 2 * 5.0                      # two narrow UCIe-A modules to the system dies (modelled: q/out vectors only)
    sys_regain_stay = round(sum(moved.values()) - ucie_new, 1)
    sys_regain_moved = round(sys_regain_stay + sum(moved_coll.values()), 1)
    sys_die = dict(collective_stays=round(sum(moved.values()) + ucie_new + 12.0, 1),   # + host/PLL/CSR 12 (modelled)
                   collective_moved=round(sum(moved.values()) + sum(moved_coll.values()) + io["io_ucie"]
                                          + ucie_new + 12.0, 1))

    def margin(a):
        return dict(die_mm2=a, margin_mm2=round(AS["budget_mm2"] - a, 1),
                    margin_pct=round((AS["budget_mm2"] - a) / AS["budget_mm2"] * 100, 1))

    # ---------------- throughput (aggregate) ----------------
    kv_tok = 36 * 8 * 8192 * 128 * 2                      # FP8 K+V bytes a token at 8K, whole model
    stack_bw = 4.0e12 / 4                                  # compose_P8191: 4-stack peak 4.000 TB/s a die
    eff = 0.96                                             # measured L1 fill at 96.0% of peak
    stack_cap = tech["hbm"]["hbm3e"]["stack_capacity_bytes"]["value"]

    def agg(stacks, tile_occ, tok_cycles, dies, logic_mm2):
        kv_bound = stacks * stack_bw * eff / kv_tok
        tile_bound = CLK / tile_occ
        a = min(kv_bound, tile_bound)
        return dict(stacks=stacks, kv_bound_tok_s=round(kv_bound), tile_window_bound_tok_s=round(tile_bound),
                    aggregate_tok_s=round(a), binding="KV stream" if kv_bound < tile_bound else "tile windows",
                    users_to_saturate=round(a * tok_cycles / CLK, 1),
                    kv_capacity_users=int(stacks * stack_cap // kv_tok),
                    per_die=round(a / dies), per_logic_mm2=round(a / logic_mm2, 2),
                    per_total_silicon_mm2=round(a / (logic_mm2 + stacks * 1150.0), 3))

    occ4 = 36 * sum(L1[o]["base_cycles"] for o in me_ops) + head["base_cycles"]
    def occ8(v):
        pp = p8 if v in "AB" else p8h
        return (36 * sum(L1[o]["base_cycles"] - p4["m"][pm[o]]["stream"] + pp["m"][pm[o]]["stream"] for o in me_ops)
                + head["base_cycles"] - p4["m"]["lm_head"]["stream"] + pp["m"]["lm_head"]["stream"])

    logic4 = 4 * die_tp4
    rows = []
    rows.append(dict(id="TP4", label="TP4 today (r21b, 2 x 2-die packages, 16 stacks)", dies=4, packages=2,
                     per_user_tok_s=tp4["tok_s"], token_cycles=base_tok, link_share=tp4["link_share"],
                     area_per_die=margin(round(die_tp4, 1)), logic_mm2_per_instance=round(logic4, 1),
                     aggregate=agg(16, occ4, base_tok, 4, logic4), grade="priced candidate (token_path_20261008)"))
    for v, lab, st, dies_area in (("A", "TP8-A: 8 dies, 4 stacks/die (4 x B200-class packages, 32 stacks)", 32, tp8A),
                                  ("B", "TP8-B: 8 dies, 2 stacks/die (16 stacks)", 16, tp8B)):
        c = tp8[v]["central"]
        lg = 8 * dies_area["central"]
        rows.append(dict(id=f"TP8-{v}", label=lab, dies=8, packages=4, per_user_tok_s=c["tok_s"],
                         per_user_range=[tp8[v]["worst"]["tok_s"], tp8[v]["best"]["tok_s"]],
                         per_user_if_board_2x2_mesh=tp8[v]["board_2x2_relay"]["tok_s"],
                         token_cycles=c["token_cycles"], link_share=c["link_share"],
                         area_per_die=margin(dies_area["central"]), area_per_die_linear_rom=dies_area["linear"],
                         logic_mm2_per_instance=round(lg, 1),
                         aggregate=agg(st, occ8(v), c["token_cycles"], 8, lg), grade="modelled on measured windows"))
    for k, lab in (("collective_stays", "Option 1a: system die, collective IO stays on the ROM die"),
                   ("collective_moved", "Option 1b: system die, collective IO moved too")):
        reg = sys_regain_stay if k == "collective_stays" else sys_regain_moved
        d = round(die_tp4 - reg, 1)
        lg = 4 * d + 4 * sys_die[k]
        t = sysdie["central"][k]
        rows.append(dict(id="SYS-1a" if k == "collective_stays" else "SYS-1b", label=lab, dies=8, packages=2,
                         per_user_tok_s=t["tok_s"],
                         per_user_range=[sysdie["high"][k]["tok_s"], sysdie["low"][k]["tok_s"]],
                         token_cycles=t["token_cycles"],
                         link_share=round((tp4["link_cycles"] + (144 * x_lat["central"] if k == "collective_moved"
                                                                  else 0)) / t["token_cycles"], 4),
                         area_per_die=margin(d), system_die_mm2=sys_die[k], logic_mm2_per_instance=round(lg, 1),
                         aggregate=agg(16, occ4, t["token_cycles"], 4, lg),
                         grade="modelled crossings on the priced TP4 token"))

    problems = dict(
        divisibility="none: 32 Q / 8 KV heads -> 4 Q + 1 KV per die (GQA groups whole); FFN 12,288/8 = 1,536; "
                     "vocab 151,936/8 = 18,992; the engine tiling keeps lane utilisation (qkv/gu 1.0, o/down 0.889, "
                     "head 0.989 vs 0.999) at G 6,144 -- the matvec stream halves, no lanes idle",
        tp8_is_the_kv_limit="TP8 is the largest legal split: 1 KV head a die; TP16 would replicate KV heads",
        compute_halves_only_on_stream="the measured ME windows are mostly fixed latency (x broadcast, tree, relays "
                                      "95/op, band +7): halving the weight stream saves only 256 cycles a layer "
                                      "(512 -> 256 stream); the big compute saving is attention (KV per die halves) "
                                      "and only if each die keeps 4 stacks and 24 row engines",
        collective_does_not_shrink="the all-reduce payload is the full hidden vector (4,096 FP32) on every die at any "
                                   "TP; the one-shot fold grows 17 -> 37 cycles; the board crossing LAT 339 is "
                                   "unchanged only on a fully connected 4-package board (K4)",
        collective_share="link share of the token rises from 34.6% (TP4) to 42.3% (TP8-A) / 38.3% (TP8-B)",
        board_topology="4 packages must be fully connected (3 board neighbours each); on a 2x2 board mesh the "
                       "diagonal pair is relayed (+343 cycles an all-reduce) and TP8-A falls to +5.6%",
        serdes="off-package destinations per die 2 -> 6: per-package egress 307 -> 922 GB/s (77% of the 1.19 TB/s "
               "90-lane 2-die-package SerDes budget, 307 of 397 GB/s per K4 neighbour), all with RS(544,514) FEC; "
               "3x SerDes lanes per die",
        unclosed_path="the TP4 collective path (qfd_io_collective TT -341, qfd_io_xfifo TT -772, qfd_link_rx128 "
                      "TT -696) is not closed today; TP8 widens it (7 receive FIFOs, 8-input fold)",
        critical_path_imbalance="none: every die runs the same schedule in lockstep (identical geometry per die)",
    )

    # decision
    A, B = rows[1], rows[2]
    tp8_better_user = A["per_user_tok_s"] > rows[0]["per_user_tok_s"]
    tp8_better_agg = A["aggregate"]["aggregate_tok_s"] > rows[0]["aggregate"]["aggregate_tok_s"]
    decision = dict(
        rule="owner: adopt TP8 if it gives better total decode throughput and per-user rate after all communication "
             "overhead, without compute/communication problems; otherwise adopt the companion system die (option 1)",
        tp8_better_per_user=tp8_better_user, tp8_better_aggregate_per_instance=tp8_better_agg,
        compute_problems="none found (heads, FFN and vocab divide by 8; lane utilisation unchanged; lockstep dies)",
        communication_problems="none blocking: the all-reduce grows only +20 cycles (+40 a layer, +0.7% of the "
                               "token) and fits the SerDes budget at 77%; it does not shrink, so its share rises "
                               "34.6% -> 42.3%. Two hard requirements: a fully connected 4-package board (K4) and "
                               "3x off-package SerDes lanes a die",
        verdict="ADOPT TP8 (variant A: 8 dies, 4 HBM stacks a die, 4 B200-class 2-die packages, K4 board)",
        why=[f"per user {A['per_user_tok_s']:,} vs {rows[0]['per_user_tok_s']:,} tok/s "
             f"({A['per_user_tok_s'] / rows[0]['per_user_tok_s'] - 1:+.1%} central; range "
             f"{A['per_user_range'][0]:,}-{A['per_user_range'][1]:,}, worst case still +11.6%) after the larger "
             "collective", 
             f"aggregate per instance {A['aggregate']['aggregate_tok_s']:,} vs "
             f"{rows[0]['aggregate']['aggregate_tok_s']:,} tok/s (modelled ceiling)",
             "the die drops to ~802 mm2 (6.5% reticle margin; 9.2% if ROM area scales linearly) from 882.8 mm2 "
             "(-2.9%), with the same tile count and shorter tiles; option 1 regains a similar margin (7.3%) "
             "but loses 0.5-1.4% per user and needs a new die and a larger interposer",
             "TP8-A uses the existing package class (2 dies + 8 stacks, B200-type); option 1 does not"],
        conditions=["the 4 packages must be fully connected on the board; on a 2x2 board mesh TP8-A falls to "
                    "+5.6% and TP8-B to -3.2%",
                    "each die keeps 4 stacks and the 24 near-HBM row engines: with 2 stacks a die (TP8-B, 16 "
                    "stacks) per-user gain is +8.7% and the KV-bound aggregate is unchanged (+0.3%), which does "
                    "not meet the 'better total throughput' leg",
                    "the attention halving (1 KV head spread over all 128 PC landings) is modelled, not measured: "
                    "a TP8 L1 at P8191 on the STREAM4 vehicle (KV_NH=1) is the confirming run"],
        costs_flagged=["2x logic dies (8 vs 4) and 2x HBM stacks (32 vs 16) per instance: aggregate per die "
                       "-37%, per logic mm2 -30%, per total silicon (stacks at 1,150 mm2) -36%; the iso-area "
                       "Qwen headline against GPUs gets worse",
                       "collective share of the token 34.6% -> 42.3%; the TP4 collective path is still not closed "
                       "and TP8 widens it (7 receive FIFOs, 8-input fold)",
                       "3x SerDes lanes a die with RS FEC: always-on lane power (~0.73 W a lane) unpriced"],
        alternative="if the owner weighs per-die / iso-silicon efficiency over per-instance speed, option 1a "
                    "(system die, collective stays on the ROM die) keeps per-die throughput and loses 0.5% per user",
    )

    out = dict(
        schema="opentallas.qwen-tp8-vs-sysdie.v1",
        stream="qwen-tp8-vs-sysdie", date="2026-10-09",
        clock_hz=CLK, position=8191, mode="AR (DSpark off), INT8 weights, FP8 KV in HBM",
        basis=dict(token_path=dict(path=str(TP_PATH.relative_to(ROOT)), sha256_16=sha(TP_PATH),
                                   token_cycles=base_tok, tok_s=tp["totals"]["tok_s_published"],
                                   steady_layer=steady, l0_extra=l0_extra, head=head["cycles"],
                                   status=tp["headline"]["status"]),
                   area_sheet=AS, geo=dict(path=str(GEO.relative_to(ROOT)), sha256_16=sha(GEO),
                                           die="r17b snapshot", block_mm2=area_kind, io_mm2=io),
                   technology=dict(path=str(TECH.relative_to(ROOT)), sha256_16=sha(TECH),
                                   ucie_hop_s=ucie, ucie_bytes_s=ucie_bw,
                                   board_serdes_hop_s=tech["links"]["rom_board_serdes"]["hop_latency_s"]["value"],
                                   board_link_LAT_cycles=339,
                                   board_link_LAT_source="tools/qwen_rom_rt_token_stream4_w12.py --coll-lat 339 "
                                                         "(the measured TP4 token's collective LAT)"),
                   measured_attention=dict(path=str(STEP.relative_to(ROOT)), sha256_16=sha(STEP),
                                           note="KV_IDEAL L0 5,283 = chained 5,282: attention is engine-bound, the "
                                                "KV fill (1,311 cycles at 96% of 4.0 TB/s) is hidden by prefetch")),
        engine_tiling=dict(tool="tools/hdc_qwen_fullshape_placement_w12.py (rtl_split)",
                           TP4_G6144=p4, TP8_G6144=p8, TP8_G3072=p8h,
                           finding="at G 6,144 TP8 halves every stream (qkv 64->32, o 48->24, gu 256->128, down "
                                   "144->72, head 1,584->800) at the same utilisation; ROM depth 20,016 -> 10,016 "
                                   "words (5 -> 3 code banks). A half-size TP8 die (G 3,072) keeps the TP4 stream "
                                   "times exactly, so it only adds communication"),
        scaling_rules=dict(
            me_ops="window - TP4 stream + TP8 stream; priced adders (relays 95, MUL_LAT, band +7) kept per op "
                   "(conservative: a shorter TP8 die has fewer relay stations)",
            attention=f"TP8-A: stream {attn_stream_tp4} -> {attn_stream_tp4 // 2} (4 MiB -> 2 MiB a die over 128 PC "
                      f"landings), fixed {attn_fixed} kept (central); best halves the fixed part too, worst keeps the "
                      "full fixed part plus no halving of its tail; TP8-B/H: unchanged (half the landings/engines)",
            su="rmsnorm/residual/attn_tail replicated (unchanged); qknorm_rope and softmax_norm scale with heads a "
               "die: 0.5 central/best, 1.0 worst",
            allreduce="+20 cycles (fold 2 + 7 x 5 vs 2 + 3 x 5); board LAT 339 per crossing unchanged on a K4 "
                      "4-package board; serialisation 256 words unchanged (one word a cycle to all destinations)",
            head="lm_head stream 1,584 -> 800, + 10 cycles for the 8-way argmax gather",
            l0="TP8-A: cold KV fill halves (the 222-cycle KV constants kept); B/H unchanged"),
        tp4=tp4, tp8=tp8,
        system_die=dict(crossing_cycles=x_lat, crossings_per_token=cross, by_latency=sysdie,
                        partition="row engines (near-HBM attention) move with the HBM PHYs, controllers, CDC and "
                                  "landing frames: only q (<= 1,280 values) and the attention result cross UCIe, "
                                  "twice a layer; the 4 MiB KV stream never crosses",
                        kv_landing_only_alternative=dict(
                            note="move only PHY/controller/landing, keep row engines: 4 MiB a layer a die crosses "
                                 "UCIe-A at 4.2 TB/s",
                            fill_cycles_over_ucie=round(fill_ucie_cyc), hidden_by_prefetch=True,
                            energy_mJ_per_token_per_die=round(36 * kv_bytes_layer * 8 * 0.5e-12 * 1e3, 2),
                            verdict="worse: same latency, ~0.6 mJ/token/die more, 7 mm more UCIe shoreline"),
                        area_moved_off_rom_die_mm2=moved, collective_io_mm2=moved_coll, new_ucie_on_rom_die_mm2=ucie_new,
                        rom_die_regain_mm2=dict(collective_stays=sys_regain_stay, collective_moved=sys_regain_moved),
                        system_die_mm2_per_rom_die=sys_die,
                        packaging="per package: 2 ROM dies + 2 system dies (or 4 half-size, one per stack pair) + "
                                  "8 stacks; the stacks move from the ROM-die E/W edges to the system dies, so the "
                                  "interposer grows to ~3.5-4 reticles (B200 is ~3.3): roadmap CoWoS-L class, not "
                                  "B200-identical"),
        area=dict(rom_tp4_linear_mm2=rom_tp4_lin, rom_save_linear_mm2=round(rom_save_lin, 1),
                  rom_save_bank_quantised_mm2=round(rom_save_quant, 1), code_banks=[code_banks_tp4, code_banks_tp8],
                  tp8_serdes_add_mm2=serdes_add, tp8_collective_add_mm2=coll_add, tp8B_kv_half_mm2=kv_half,
                  tp8A_die=tp8A, tp8B_die=tp8B),
        side_by_side=rows,
        problems_tp8=problems,
        closure_risk=dict(
            TP4="r21b at 882.8 mm2 known, 24.8 mm2 over the reticle; tile, spine and collective not closed",
            TP8="die ~802 mm2 (6.5% margin, 9.2% at linear ROM); tiles lose 2 of 5 code banks (shorter tile, "
                "smaller ROM fanout: plausibly easier, unproven); collective path widened to N 8 (7 receive "
                "FIFOs, 8-input fold) on a path already failing TT; 3x SerDes; 8 ROM images; K4 board",
            SYS="ROM die ~795.5 mm2 (7.3% margin; 787.9 mm2, 8.2%, with the collective IO moved) with the same tile/spine/collective closure as today; a new system "
                "die (HBM PHY/ctrl/row engines/host/PLL, small, edge-bound) and two UCIe interfaces; larger "
                "interposer"),
        decision=decision,
        unvalidated=["every TP8 and system-die number is modelled from measured TP4 windows; no TP8 or system-die "
                     "RTL was run",
                     "the r21c embedding fetch (+248 typical / +567 worst a token) is uncharged in every option, as "
                     "in the 218,472 basis",
                     "the TP4 aggregate is a modelled ceiling (KV stream at 96% of 4.0 TB/s a die vs tile windows); "
                     "no batched run exists",
                     "SerDes always-on lane power (0.73 W a lane) for 3x lanes is not in any rate",
                     "system-die host/PLL/CSR 12 mm2 and UCIe module 5 mm2 are modelled"],
    )
    (HERE / "result.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps([dict(id=r["id"], user=r["per_user_tok_s"], rng=r.get("per_user_range"),
                           agg=r["aggregate"]["aggregate_tok_s"], die=r["area_per_die"], share=r["link_share"],
                           logic=r["logic_mm2_per_instance"], bind=r["aggregate"]["binding"],
                           users=r["aggregate"]["users_to_saturate"], pd=r["aggregate"]["per_die"],
                           pmm=r["aggregate"]["per_logic_mm2"], pts=r["aggregate"]["per_total_silicon_mm2"])
                      for r in rows], indent=0))
    print({v: {k: (tp8[v][k]["tok_s"], tp8[v][k]["vs_tp4"]) for k in tp8[v]} for v in tp8})
    print(sysdie)


if __name__ == "__main__":
    main()
