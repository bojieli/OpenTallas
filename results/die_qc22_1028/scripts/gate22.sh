#!/bin/bash
# DIE-QC-22: rerun the die STA (gate + declared) of DIE-QC-21 g14 (trial14) with the 5 signed su_c views (export_view.py provenance) wired; plan dir resolves pins
set -u
D=/srv/opentallas-scratch2/claude/die-qc22-1028; G=/srv/opentallas-scratch2/claude/die-qc21-1028/g14; R=$D/g14v; mkdir -p $R
MT=/srv/opentallas-scratch2/claude/wt/die-qc22-1028/tools/die_plan; W=/srv/opentallas-scratch2/claude/wt/die-qc22-1028
PLAN=/srv/opentallas-scratch2/claude/die-qc20-1028/plan/ev_a0meas.json; PR=$G/proof; O=$D/views
V="--core-view qfd_dv_s8x_crh=$O/qfd_dv_s8x_crh --core-view qfd_dv_s8_crh_rp1=$O/qfd_dv_s8_crh_rp1 --core-view qfd_dv_s8x_vmr=$O/qfd_dv_s8x_vmr --core-view qfd_dv_s8x_prog=$O/qfd_dv_s8x_prog --core-view qfd_dv_s5_su8_rst3=$W/results/cores_early_1_1028/qfd_dv_s5_su8_rst3"
C="$PR --plan $PLAN --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $G/bind_clock.json --count-align-key region --clock-cell inv2 $V"
for M in view declared; do python3 $MT/die_sta_related.py $C --out $R/sta_$M --core-insertion $M > $R/sta_$M.log 2>&1 & done; wait
echo DONE $(date) >> $R/done
