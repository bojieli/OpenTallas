#!/bin/bash
# QW-GEN3 10-19 = successor GEN of dv2f19g2 (claude/qw-gen3-1019): + 446 QW-DIECLK2 landings (OT_SPLIT_LAND_LIST) + R2 one hard instance per region root (OT_SPLIT_REGION_ONE_HARD, all hard<->hard direct buses landed) + DC_GRID_CENTER=1 + MU-DQ-BOOTCTX (mu_ctxrx -> tt_ctlm.ctx_x) + relay table = netlist walk vs the schedule recompiled on THIS die. STAND-INS declared in results/rtl/qw_gen3_1019/README.md. PILOT_NOT_A_GATE. (run dv2f19g3r)
# QW-GEN2 10-19 = successor GEN of dv2f18dh2: claude/qw-gen2-1019 a5ea12ae2 (mu-die-qw2 4d2cb6301 + qw-dieclk bbe250fb5 regional die clock + recompiled d2d_cal_image_mu.svh C[8,3,1,10]/K[21,4,3,3] + cp-not-ln). Carries e0218f16e, 3c133b609, QW-DIEFIX hr/ROM-bind/last-k. STAND-INS declared in results/rtl/qw_gen2_1019/README.md. PILOT_NOT_A_GATE. (run dv2f19g3r)
# MU-DIE-QW2 10-19 dv2f18dh2 = RELEASE MU die GEN: claude/mu-die-qw2-1019 0d4c9808f (TXDP C [8,3,1,10] 2308076af, qw-diefix, mu-qw-b1, slicekc kc[66:59], d2duser, mu-kv-ctx, MU-DQ-DHUSER observer dhobs d9bf2ed5e driving tt_ctlm.dh_user, sys_face MU=1 (57d2bf14c), d2d r9j view, 8 landh0 e1 CLOSED views, dhuser leaf k3 record). STAND-INS (labelled): tt_ctlm_dv kit (ctlm_dv clock 0ke), qfd_sys_face view (MU 0 rs3; mu1 re-close pending), slice2_e/wh (gated, not closed), native59 (n2c, multi-context MU-D2D-OVL), dhobs d1 (gated, critical). PILOT_NOT_A_GATE.
# MU-DQ-DHUSER 10-19 dv2f18dh = claude/mu-dq-dhuser-1019 (mu-die-qw2 94d5267da + dh_user observer mu_dhobs, COORD 0kg item 2): tt_ctlm.dh_user DRIVEN, no strap
# MU-DIE-QW 10-19 dv2f18mu (multi-user release die, OT_QWEN_MU_NU=4; stand-ins labelled; PILOT_NOT_A_GATE until views close) -- was Q17-PILOT dv2f17p chain (stand-in pilot, PILOT_NOT_A_GATE): + OT_BIND_FWD_RLYH0=1
# dv2f16 chain (DIE-QWEN-GEN16): strict bind -> real case -> PDN r8 (own-grid rst_rep, OT_RST_REP_VIEW=closed) -> repeaters -> GRT -> STA tt/ff/ss
# -> die clock check + land plan + hold budget (same flags as dv2f14bi chain.sh)
S=/srv/opentallas-scratch/claude/qwen-split-compute/dv2f19g3r
cd $S/src || exit 9
grep -q "^rc=0" $S/out.log || { echo "GEN not rc=0" > $S/CHAIN_SKIPPED; exit 7; }
OT_RELAY_SCHEDULE=${OT_RELAY_SCHEDULE:?compiled schedule of THIS die} DC_GRID_CENTER=${DC_GRID_CENTER:-1} OT_BIND_FWD_RLYH0=1 OT_DIE_CLOCK_PHYS=${OT_DIE_CLOCK_PHYS:-1} OT_DIE_CLOCK_MODE=${OT_DIE_CLOCK_MODE:-regional} OT_DIE_CLOCK_VARIANT=${OT_DIE_CLOCK_VARIANT:-rA} DC_MEM=${DC_MEM:-85} OT_RST_REP_VIEW=closed OT_PORT_BIND_STRAPS=$S/src/results/arch/qwen_split_compute_1014/q_slice_1017/straps_dv2f18mu.json OT_DIE_REPAIR=1 OT_PDN_RELAY_GRIDS=1 \
  OT_HOLD_BUDGET=die OT_SPLIT_PHY_NFACE=1 OT_SPLIT_PHY_TALL=1 OT_ASSUMED_PHY_PG_ACCESS=1 bash tools/qwen_split/chain_after_build.sh dv2f19g3r > $S/chain.log 2>&1
rc=$?
echo "chain rc=$rc" >> $S/chain.log
echo "$(date "+%F %T %Z") STA-0201 (missing master pins) in real case: $(grep -c STA-0201 $S/chain/case_r22k/run.log 2>/dev/null)" >> $S/chain/STATUS.log
exit $rc
