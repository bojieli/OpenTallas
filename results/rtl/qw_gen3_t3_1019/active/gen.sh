#!/bin/bash
# QW-GEN3 10-19 = successor GEN of dv2f19g2 (claude/qw-gen3-1019): + 446 QW-DIECLK2 landings (OT_SPLIT_LAND_LIST) + R2 one hard instance per region root (OT_SPLIT_REGION_ONE_HARD, all hard<->hard direct buses landed) + DC_GRID_CENTER=1 + MU-DQ-BOOTCTX (mu_ctxrx -> tt_ctlm.ctx_x) + relay table = netlist walk vs the schedule recompiled on THIS die. STAND-INS declared in results/rtl/qw_gen3_1019/README.md. PILOT_NOT_A_GATE. (run dv2f19g3c1)
# QW-GEN2 10-19 = successor GEN of dv2f18dh2: claude/qw-gen2-1019 a5ea12ae2 (mu-die-qw2 4d2cb6301 + qw-dieclk bbe250fb5 regional die clock + recompiled d2d_cal_image_mu.svh C[8,3,1,10]/K[21,4,3,3] + cp-not-ln). Carries e0218f16e, 3c133b609, QW-DIEFIX hr/ROM-bind/last-k. STAND-INS declared in results/rtl/qw_gen2_1019/README.md. PILOT_NOT_A_GATE. (run dv2f19g3c1)
# MU-DIE-QW2 10-19 dv2f18dh2 = RELEASE MU die GEN: claude/mu-die-qw2-1019 0d4c9808f (TXDP C [8,3,1,10] 2308076af, qw-diefix, mu-qw-b1, slicekc kc[66:59], d2duser, mu-kv-ctx, MU-DQ-DHUSER observer dhobs d9bf2ed5e driving tt_ctlm.dh_user, sys_face MU=1 (57d2bf14c), d2d r9j view, 8 landh0 e1 CLOSED views, dhuser leaf k3 record). STAND-INS (labelled): tt_ctlm_dv kit (ctlm_dv clock 0ke), qfd_sys_face view (MU 0 rs3; mu1 re-close pending), slice2_e/wh (gated, not closed), native59 (n2c, multi-context MU-D2D-OVL), dhobs d1 (gated, critical). PILOT_NOT_A_GATE.
# MU-DQ-DHUSER 10-19 dv2f18dh = claude/mu-dq-dhuser-1019 (mu-die-qw2 94d5267da + dh_user observer mu_dhobs, COORD 0kg item 2): tt_ctlm.dh_user DRIVEN, no strap
# MU-DIE-QW 10-19 dv2f18mu (multi-user release die, OT_QWEN_MU_NU=4; stand-ins labelled; PILOT_NOT_A_GATE until views close) -- was Q17-PILOT dv2f17p GEN (stand-in pilot, PILOT_NOT_A_GATE)
# DIE-QWEN-GEN16 10-19 dv2f16 GEN only (the chain with the die clock build before GRT is launched separately: chain.sh)
# (base: DIE-QWEN-LEAD dv2f15r final.sh)
# src = codex/qwen-recovery-1018 104622e24 (Q-DIE15 own-grid rst_rep PDN, table loader d8b6a157e, LS 378 e1a641d23,
#   XPF 08e7c5551, reset post-tree K restrap d893466a7) + 5a789562d (clkrx gets every pll_r root: GEN bug from Q-CLK)
# LAND_PLAN = dv2f15codex/chain/land_plan.json: the PLANNED landings measured on the bi netlist with real GRT parasitics
#   (147 links, E_sta 1:92 2:43 3:3 6:3 7:6, window_fail 0, no_slack 0); dv2f15next used the stale dv2f14bg plan (129 links)
# RESET_RELEASE = source-pinned bi reset release projection (results/rtl/q_short_reset_1018/bi_root_release.json)
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f19g3c1
LP=$S/land_plan_bi_chain.json
python3 - $LP > $S/landplan_check.txt 2>&1 <<"PY" || { echo "land plan invalid (landplan_check.txt)" > $S/FINAL_LANDPLAN_INVALID; exit 5; }
import json, sys
r = json.load(open(sys.argv[1])); bad = []
for x in r["links"]:
    if x.get("E") is None: bad.append((x["bid"], "no E")); continue
    for k in ("setup_E", "hold_E"):
        miss = {"tt", "ff"} - set(x.get(k, {}))
        if miss: bad.append((x["bid"], k, "missing", sorted(miss)))
    if not x.get("window_ok"): bad.append((x["bid"], "window", x.get("hold_E")))
    if any(v < 0 for c, v in x.get("setup_E", {}).items() if c in ("tt", "ff")): bad.append((x["bid"], "setup_E<0", x["setup_E"]))
s = r["summary"]; print(json.dumps(s)); print("bad", len(bad))
for b in bad: print(b)
sys.exit(1 if bad or s.get("window_fail") or s.get("no_slack") else 0)
PY
cp $LP $S/land_plan_used.json
LAND_PLAN=$LP RESET_RELEASE=$S/src/results/rtl/q_short_reset_1018/bi_root_release.json bash $S/run.sh || { echo "GEN rc=$?" > $S/FINAL_GEN_FAIL; exit 4; }
grep CLKRX_PORTS $S/out.log > $S/clkrx_ports.txt
echo GEN_DONE > $S/GEN_DONE
