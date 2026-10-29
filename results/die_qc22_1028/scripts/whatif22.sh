#!/bin/bash
# DIE-QC-22 task 3 estimate: kit-contract intra window WHAT-IF (--intra-window-ps) on g14 declared + 5 su_c views
D=/srv/opentallas-scratch2/claude/die-qc22-1028; G=/srv/opentallas-scratch2/claude/die-qc21-1028/g14; R=$D/g14w
MT=/srv/opentallas-scratch2/claude/wt/die-qc22-1028/tools/die_plan; W=/srv/opentallas-scratch2/claude/wt/die-qc22-1028
PLAN=/srv/opentallas-scratch2/claude/die-qc20-1028/plan/ev_a0meas.json; PR=$G/proof; O=$D/views
V="--core-view qfd_dv_s8x_crh=$O/qfd_dv_s8x_crh --core-view qfd_dv_s8_crh_rp1=$O/qfd_dv_s8_crh_rp1 --core-view qfd_dv_s8x_vmr=$O/qfd_dv_s8x_vmr --core-view qfd_dv_s8x_prog=$O/qfd_dv_s8x_prog --core-view qfd_dv_s5_su8_rst3=$W/results/cores_early_1_1028/qfd_dv_s5_su8_rst3"
C="$PR --plan $PLAN --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $G/bind_clock.json --count-align-key region --clock-cell inv2 $V --core-insertion declared"
mkdir -p $R
for WW in 150 180 208; do python3 $MT/die_sta_related.py $C --out $R/w$WW --intra-window-ps $WW > $R/w$WW.log 2>&1 & done; wait
echo DONE $(date) >> $R/done
