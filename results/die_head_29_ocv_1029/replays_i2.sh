#!/bin/bash
# DIE-HEAD-29 replays on intel2: HEAD plan (spice_edge, plan5 form), QC g25 plan + sta_gate; tools base (origin/main) vs new
B=/srv/opentallas-scratch2/claude/die-head-29-ocv-base; W=/srv/opentallas-scratch2/claude/wt/die-head-29-ocv
O=$B/rep; mkdir -p $O
C=/srv/opentallas-scratch2/claude/codex-head-start-0251; R3=/srv/opentallas-scratch2/claude/head-start-3; R=/srv/opentallas-scratch2/claude/head-start-4
G=/srv/opentallas-scratch2/claude/die-qc25-1028/g25; PLAN=/srv/opentallas-scratch2/claude/die-qc25-1028/plan/ev_qc25.json; PR=$G/proof
V22=/srv/opentallas-scratch2/claude/die-qc22-1028/views
for T in base new; do
  [ $T = base ] && S=$B/tools/die_plan || S=$W/tools/die_plan
  ( python3 $S/count_align_plan.py "$C/leaf_ocv2.json" --corner TT_droop-regions_corelat450,FF_droop-regions_corelat380 --sta-proof "$R3/proof_r1" --sta-plan "$R3/capture5e/plan.json" --sta-clock-cal spice_edge --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$R3/proof_r1/droop_regions.json" --sta-core-latency-ff 380 --sta-ca-ring $R/ca_ring_hd_tile_dh20.json --sta-clock-cell inv2 --start-tree clock --start-leaf-origins --start-capture-taps "$R3/capture5e/capture_taps.json" --start-clean width --start-max-hop-um 360 --start-retime-max 64 --start-prev "$C/leaf_plan4.json" --mc-chips 2000 --out $O/head_$T.json > $O/head_$T.log 2>&1; echo HEAD $T rc $? $(date) ) &
  F="--sta-proof $PR --sta-plan $PLAN --sta-clock-cal spice_edge --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
  ( python3 $S/count_align_plan.py $G/grp_spice_xing_lpo.json $F --start-tree clock --start-clean width --mc-chips 300 --out $O/qcplan_$T.json > $O/qcplan_$T.log 2>&1; echo QCPLAN $T rc $? $(date) ) &
  ( python3 $S/die_sta_related.py $PR --plan $PLAN --out $O/qcsta_$T --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice_edge --count-align $G/bind_clock.json --count-align-key region --clock-cell inv2 --core-view qfd_dv_s8x_crh=$V22/qfd_dv_s8x_crh --core-view qfd_dv_s8_crh_rp1=$V22/qfd_dv_s8_crh_rp1 --core-view qfd_dv_s8x_vmr=$V22/qfd_dv_s8x_vmr --core-view qfd_dv_s8x_prog=$V22/qfd_dv_s8x_prog --core-insertion view > $O/qcsta_$T.log 2>&1; echo QCSTA $T rc $? $(date) ) &
done
wait
