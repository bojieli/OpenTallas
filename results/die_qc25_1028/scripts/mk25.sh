#!/bin/bash
# DIE-QC-25: derive trial25 chain scripts from DIE-QC-24's (ev_qc25 plan, trial24-refit stage cal, --rep-on-leg + guard 50)
S=/srv/opentallas-scratch2/claude/die-qc24-1028; O=/srv/opentallas-scratch2/claude/die-qc25-1028
for f in chain24.sh run_clock24.sh kit24.sh overlay24.py gate24.sh; do
  n=${f/24/25}
  sed -e 's#wt/die-qc24-1028/results/die_qc21_1028/inv2_stage_cal_trial13b.json#wt/die-qc25-1028/results/die_qc25_1028/inv2_stage_cal_trial24.json#g' \
      -e 's#\$D/\.\./die-qc23-1028/plan/ev_qc23pg.json#$D/plan/ev_qc25.json#g' \
      -e 's#die-qc23-1028/plan/ev_qc23pg.json#die-qc25-1028/plan/ev_qc25.json#g' \
      -e 's#die-qc24-1028#die-qc25-1028#g' \
      -e 's#trial24#trial25#g; s#c24_#c25_#g; s#/c24 #/c25 #g; s#\$D/c24#$D/c25#g; s#c24/#c25/#g; s# g24# g25#g; s#bays24#bays25#g; s#overlay24#overlay25#g; s#kit24#kit25#g; s#grt24#grt25#g' \
      -e 's#snake_len24#snake_len25#g; s#snake24#snake25#g; s#eval_trial24#eval_trial25#g; s#eval24#eval25#g; s#val24#val25#g; s#chain24#chain25#g; s#run_clock24#run_clock25#g; s#gate24#gate25#g; s#qc24-clock24#qc25-clock25#g; s#DIE-QC-24#DIE-QC-25#g' \
      -e 's#^t24) #t25) #' \
      -e 's#--rep-off-leg-max 50 \$COMMON#--rep-off-leg-max 50 --rep-on-leg $COMMON#' \
      $S/$f > $O/$n
done
