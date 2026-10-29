#!/bin/bash
B=/srv/opentallas-scratch2/claude/die-head-29-ocv-base; W=/srv/opentallas-scratch2/claude/wt/die-head-29-ocv; O=$B/rep
G=/srv/opentallas-scratch2/claude/die-qc25-1028/g25; PLAN=/srv/opentallas-scratch2/claude/die-qc25-1028/plan/ev_qc25.json; PR=$G/proof
V22=/srv/opentallas-scratch2/claude/die-qc22-1028/views
for T in base new; do
  [ $T = base ] && S=$B/tools/die_plan || S=$W/tools/die_plan
  ( rm -rf $O/qcsta_$T; mkdir -p $O/qcsta_$T; cp -r /srv/opentallas-scratch2/claude/head-start-4/qc_old/sta_gate/regchar $O/qcsta_$T/; python3 $S/die_sta_related.py $PR --plan $PLAN --out $O/qcsta_$T --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice_edge --count-align $G/bind_clock.json --count-align-key region --clock-cell inv2 --core-view qfd_dv_s8x_crh=$V22/qfd_dv_s8x_crh --core-view qfd_dv_s8_crh_rp1=$V22/qfd_dv_s8_crh_rp1 --core-view qfd_dv_s8x_vmr=$V22/qfd_dv_s8x_vmr --core-view qfd_dv_s8x_prog=$V22/qfd_dv_s8x_prog --core-insertion view > $O/qcsta_$T.log 2>&1; echo QCSTA $T rc $? $(date) ) &
done
wait
