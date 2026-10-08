#!/bin/bash
# Z23* (2026-10-06, OWNER RULE margin-first): the PQ q-element with QM = 1 (ot_v41_bterm5_w10 lanes, +5 cycles), routed
# OVER-CONSTRAINED at PER (default 0.770 ns) and signed off at 0.833 ns (post_sta_qm.sh rewrites the period and the max
# input delays back): target SS >= +60 ps at 0.833.  Max input delay = PER - 0.106 ns so the internal pin -> flop budget is
# the Z22 budget (0.833 - 0.727).  FH 192.24 (owner frame).  Job root JROOT (default EPYC1 scratch).  Else as Z22:
# Z22* (2026-10-06, OWNER DECISION frame height 192.24 um): same launcher, FH=192.24, QW from the environment (bterm4 WD).
# PD (2026-10-06): GPL target density from the environment (default 0.6): the 192.24 frame spreads the lanes at 0.6 (Z22a/b post-CTS -102 / -356 ps on lane wires).
# DSROM q-element routes Z21* (2026-10-06): the PQ q-element ot_v41_rom_elem_q_qxpq_w10 (PQ = 1: banked output tags,
# op tree parity, configuration shadow by replay; QX = 10 body unchanged) on the Z20c taller-frame recipe, after the
# coordinator's PQ x q-element finding (results/rtl/dsrom_recovery_20261004/combined) and S81-DIE's request: xs_q1 / xs_e1
# move to the SOUTH face with xs_q0 / xs_e0 (S81 r8: xs_q1[151] had no access point on the north face); the PQ status
# outputs (walking, bank_free, sh_free) go north with busy / fault, go_tag south with go.  Frame height FH from the
# environment (11 S81 slots allow FH <= 185.7 um): Z21a 177.12, Z21b 181.44, Z21c 183.6.
# DSROM q-element routes Z20* (2026-10-05, OWNER DECISION: stop the frame-D timing chase; taller slot, fewer elements per die).
# QX = 10 RTL unchanged (exact, results/rtl/dsrom_qz_20261004/exact_qx10_quick.json).  Frame width 510.84 um and pin regions
# unchanged; frame height FH from the environment (frame D = 151.2 um at 77 % ORFS design-area utilisation, 58,903 um2 of
# cells + macros on 76,963 um2 of core).  Z20a FH 209.52 (~55 %), Z20b FH 192.24 (~60 %), Z20c FH 177.12 (~65 %), each a
# multiple of the S81 slot lattice (2.16 um).  Recipe kept: keepout v2, the Z18d CTS (cluster 30/50/60 + -apply_ndr full
# -balance_levels), hold repair target 25 ps, setup target 20 ps, RLA 0.22, macro hook unchanged (macros at the bottom).
# Sign-off unchanged: routed SS setup >= 0 at 60 ps, FF hold >= 0 at 25 ps, 0 DRC.
# DSROM q-element routes Z18* (2026-10-05): QX = 10 (QX = 9 + zero-cycle fixes: bterm4 NS, chain4 PD / fadd2, r_dp
# prefix differences, registered w_sf candidates) on the Z16 flow; sources add ot_v41_chain4 / ot_v41_fadd2.
# DSROM q-element routes Z16* (2026-10-05, owner structural decision): QX = 9 (segment tree ot_v41_segtree5, decide
# stage split, +1 cycle per tree level) on the Z15 flow (frame D, keepout v5, Z9s2 CTS, RLA 0.22, repair targets from
# HM / SM, optional CTSA).  Sign-off unchanged: routed SS setup >= 0 at 60 ps, FF hold >= 0 at 25 ps.
# DSROM q-element routes Z15* (2026-10-05): Z14 (below) with QX = 8 redefined: ot_v41_segtree4 XC = 4 (kept copies of x_oh per
# 8 data bits and of x_d per 20 held slots; XR = 1 measured SS -175 ps in Z14a).  Z14 header: early held
# read, zero cycles), after Z12a-c routed DRC 0 but SS -41 to -44 ps on x_oh -> held[] select -> add_a.
# DSROM q-element routes Z13* (2026-10-05, on ot-epyc2 in parallel with Z12): Z11 (below) with QX from the environment and
# an optional full CTS argument list (CTSA -> ORFS CTS_ARGS, which replaces the flow's defaults, so it repeats them:
# -sink_clustering_enable -repair_clock_nets and the Z9s2 cluster settings).  Z13a: the Z11d rerun (QX = 6, keepout v5,
# hold 30 / setup 15 ps repair targets).  Z13b: + clock NDR (-apply_ndr full) and -balance_levels (OpenROAD has no
# per-register useful skew; this is the clock-tree variation knob available).  Sign-off constraints unchanged.
# DSROM q-element route Z11 (2026-10-04): Z10 (below) with repair over-fix targets (not constraints): hold margin 20 ps
# (--hold-margin-ns ${HM:-0.02}2) and SETUP_SLACK_MARGIN 15 ps (library units), after Z10e lost ~13 ps of setup and hold
# between the global-route repair estimate and the extracted route (SS -11.9 ps, FF hold -12.8 ps); keepout v3.
# DSROM q-element routes Z10* (2026-10-04): Z9 (below) with QX from the environment (default 5) and the CTS settings of
# screen Z9s2 as defaults (CTS_CLUSTER_SIZE 30, CTS_CLUSTER_DIAMETER 50, CTS_BUF_DISTANCE 60: post-CTS SS -22.6 ps on one
# endpoint vs -43.9 ps / 400 ps TNS at the platform defaults, Z9a; Z9s1 10/20 -71.1, Z9s3 BD 30 -94.8).
# DSROM q-element routes Z9* (2026-10-04): Z7 (below; QX = 4) with keepout v2 (physical/abi3/dsrom_q_pin_keepout2.tcl,
# M5 flanks only) and optional CTS settings from the environment: CS (CTS_CLUSTER_SIZE), CD (CTS_CLUSTER_DIAMETER, um),
# BD (CTS_BUF_DISTANCE, um); unset = the platform defaults.
# DSROM q-element route Z7 (2026-10-04): Z6 (below) with QX = 4 (lane P2 shift partly moved into P1b, ot_v41_bterm4_w10,
# bit-identical, zero added cycles), after Z6 post-GRT SS -36.6 ps on p1_p -> p2_c behind ~107 ps of CTS skew.
# DSROM q-element route Z6 (2026-10-04): Z4k / Z5a (below) with QX = 3 (the x-need walker's step in one-hot form,
# zero added cycles), after Z5a / Z5b post-GRT SS -18.6 / -17.6 ps on n_c -> nA / nB.
# DSROM q-element route Z4k (2026-10-04): Z4 (below) with the edge-pin access keepout as the POST_DETAIL_PLACE hook
# (physical/abi3/dsrom_q_pin_keepout.tcl, which sources the PG check unchanged): S81 die finding, xs_q1[151] of the
# routed q abstract boxed in by the element's own route.  The abstract is written by tools/dsrom_q_abstract.tcl.
# ROUTING_LAYER_ADJUSTMENT from RLA (default 0.22, as Z2/Z3, which passed GRT; Z3b at the platform default failed
# GRT-0116 with 113 overflow gcells at the xs_q1 pin cluster, top edge x 246-276 um).  Runs Z5a (0.22), Z5b (0.20).
# DSROM q-element route Z4 (2026-10-04): Z3b (below) with QX = 2 (registered case-A walker decision, decoded x-need
# walker enables; zero added cycles), after Z3b's post-CTS SS -45.1 ps (w_j -> j + 1 < cur[k] -> select).
# DSROM q-element QX route Z3b (2026-10-04): Z3 (below) on frame D, 510.84 x 151.2 um = the per_element_envelope q
# outline of the die plan (frame C is smaller than its allotment; C at 78.5 % std-cell placement utilisation did not
# converge in detail route in Z2 / R_cap1, D_r2 routed DRC clean), hook physical/abi3/dsrom_qtiming_D_place.tcl, and the
# platform ROUTING_LAYER_ADJUSTMENT (the 0.22 override only answered frame C's GRT overflow).  Pins, SDC, budgets unchanged.
# DSROM q-element QX route Z3 (2026-10-04, after Z2's post-GRT SS -118.8 ps in the word walker):
# results/rtl/dsrom_qy_20261004/launch.sh on ot_v41_rom_elem_q_qx_w10 with QX = 1 (walker step in one-hot form, zero
# added cycles).  Every other input (frame, SDC, I/O budgets, ROUTING_LAYER_ADJUSTMENT 0.22, hold corners) is unchanged.
# DSROM q-element QY route (2026-10-04, design-owner decision after Z1): results/rtl/dsrom_qz_20261004/launch.sh on
# ot_v41_rom_elem_q_qy_w10 (QZ = 1, QY = 1: zero added data cycles, L = 2; fault port +2 cycles), the corrected FF
# output hold budget (-0.322 ns, derivation in physical/abi3/dsrom_qy_elem_io.sdc), and ROUTING_LAYER_ADJUSTMENT 0.22
# (platform default 0.25; Z1 GRT-0116 left 6 overflow gcells on M5/M7).  Die and core area unchanged.
# DSROM q-element QZ physical run (2026-10-04): results/rtl/dsrom_qpipe_20261003/launch.sh (frame C, hook, SDC,
# multicycle, PDN, I/O delays, SS WC 0.833 ns, 60 / 25 ps, ADDER_MAP off, macro track gate) on ot_v41_rom_elem_q_qz_w10
# with QZ = 1 (zero added cycles over QPIPE R_cap0, L = 2), plus multi-corner hold repair (--hold-corners WC,BC:
# repair_timing fixes hold at FF as well as SS; R_cap0 repaired hold at SS only).  No constraint is changed.
# usage: WT=<pinned worktree> RUN=<name> [STOP=cts|finish] launch.sh   (CAP is fixed at 0)
# Original header:
# DSROM q-element QPIPE physical runs (2026-10-03).  usage: WT=<pinned worktree> RUN=<name> CAP=<0|1> [STOP=cts|finish] launch.sh
# Frame C (510.84 x 126.9 um, the q-frame baseline), its track-aligned macro hook, SDC / multicycle / PDN / I/O delays
# identical to the QTIMING screens (results/rtl/dsrom_qtiming_20261003/launch_screen.sh) and the q-frame routes,
# SS (ORFS WC) 0.833 ns, 60 ps setup / 25 ps hold uncertainty, ADDER_MAP_FILE disabled (driver default), launched
# through the macro track-alignment gate (tools/run_abi3_physical_aligned.py --macro-track-gate).
# UNC / INMAX (2026-10-06, closure loop): setup uncertainty and max input delay from the environment (defaults unchanged:
# 0.06, PER - 0.106).  The closure-loop route keeps the SDC period at the 0.833 sign-off and over-constrains through the
# uncertainty instead (UNC 0.163 = 60 + 103 ps, INMAX 0.624: the Z29 route at 0.730 exactly), so 6_final.sdc is the sign-off
# clock and the post-route hold ECO and corner STA only need the sign-off post-SDC (60 ps, inputs at 0.727, outputs at the
# calibrated insertion: cl_signoff_sdc.sh).
set -e
: "${WT:?pinned worktree}" "${RUN:?run name}"
CAP=0
J=${JROOT:-/srv/opentallas-scratch/claude/dsrom-qtclose}/jobs/$RUN
mkdir -p $J
cd $WT
test -z "$(git status --porcelain)" || { echo "worktree not clean"; exit 2; }
STOP=${STOP:-finish}
SRCS=""
for s in rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv rtl/v41rom/ot_v41_elem_pq_tags.sv rtl/v41rom/ot_v41_kreg.sv \
  rtl/v41rom/ot_v41_chain3.sv rtl/v41rom/ot_v41_chain4.sv rtl/v41rom/ot_v41_fadd2.sv rtl/v41rom/ot_v41_rom_elem_w10.sv \
  rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv rtl/v41rom/ot_v41_bf16_lanes.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_cg.sv \
  rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v \
  rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv rtl/v41rom/ot_v41_chain2.sv \
  rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv rtl/v41rom/ot_v41_bterm3_w10.sv rtl/v41rom/ot_v41_bterm4_w10.sv rtl/v41rom/ot_v41_bterm5_w10.sv rtl/v41rom/ot_v41_segtree3.sv rtl/v41rom/ot_v41_segtree4.sv rtl/v41rom/ot_v41_segtree5.sv rtl/v41rom/ot_v41_segtree6.sv \
  physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v; do SRCS="$SRCS --source $s"; done
EXTRA=(); [ -n "${CTSA:-}" ] && EXTRA=(--orfs-var "CTS_ARGS=$CTSA")
exec python3 tools/run_abi3_physical_aligned.py --macro-track-gate --macro-track-gate-record $J/macro_gate.json \
 --persistent-workdir $J/work --launch-receipt $J/receipt.json \
 --view asap7 --top ot_v41_rom_elem_q_qxpq_w10 $SRCS \
 --clock-period-ns ${PER:-0.770} --clock-uncertainty-ns ${UNC:-0.06} --io-delay-fraction 0.2 --stages pnr \
 --die-area 0 0 510.84 ${FH:?frame height} --core-area 0 0.27 510.84 $(python3 -c "print(round(${FH}-0.27,3))") --place-density ${PD:-0.6} --macro-place-halo 2 2 \
 --pin-region "^(p|busy|fault|walking|bank_free|sh_free).*=top:136.08-374.76" --pin-region "^(clk|rst|cfg|go|xs_v|xs_p|xs_b|xs_sv|xs_q0|xs_e0|xs_q1|xs_e1).*=bottom:${XLO:-136.08}-${XHI:-374.76}" \
 --max-transition-ns 0.32 --slew-margin-percent 40 --hold-margin-ns ${HM:-0.02} \
 --step-tcl POST_MACRO_PLACE=physical/abi3/dsrom_qtiming_D_place.tcl --step-tcl POST_DETAIL_PLACE=${PDH:-physical/abi3/dsrom_q_pin_keepout2.tcl} \
 --orfs-var PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7_ir.tcl --nickname-tag dsrom_qx10qm_${RUN}_20261006 \
 --output $J/out --sdc-append physical/abi3/dsrom_qy_elem_io.sdc \
 --macro-view ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8 \
 --param MTP=1 --param EARLY=1 --param NB=2 --param FAST=1 --param PP=1 --param QTIMING_FIX=1 \
 --param QPIPE=1 --param QP_XS=1 --param QP_CAP=$CAP --param QP_P1=1 --param QP_CSAM=10 \
 --param QZ=1 --param QZ_NS=8 --param QZ_NE=4 --param QY=1 --param QX=${QX:-5} --param PQ=${PQ:-1} --param QW=${QW:-0} --param QM=${QM:-1} --param QS=${QS:-0} --orfs-var ROUTING_LAYER_ADJUSTMENT=${RLA:-0.22} --orfs-var SETUP_SLACK_MARGIN=${SM:-15} --orfs-var CTS_CLUSTER_SIZE=${CS:-30} --orfs-var CTS_CLUSTER_DIAMETER=${CD:-50} --orfs-var CTS_BUF_DISTANCE=${BD:-60} --hold-corners WC,BC \
 --pnr-stop-after $STOP --orfs-corner WC --clock-uncertainty-hold-ns 0.025 \
 --core-input-delay-min-ns 0.36 --core-input-delay-max-ns ${INMAX:-$(python3 -c "print(round(${PER:-0.770}-0.106,3))")} --output-delay-min-ns -0.322 --output-delay-max-ns -0.193 "${EXTRA[@]}" > $J/launch.log 2>&1
