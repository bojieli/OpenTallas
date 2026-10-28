#!/bin/bash
R=/srv/opentallas-scratch2/claude/kv-host-regen-1
cd $R
launch() { # MOD HOST MEM
  nohup ~/.local/bin/ot-run --mem $3 --threads 3 --dir $R --hosts $2 -- bash $R/bin/fp_core.sh $1 $3 > $R/logs/fp_$1.otrun.log 2>&1 &
  echo "$(date '+%F %T') $1 $2 mem=$3 pid=$!" >> $R/logs/launch.tsv
}
launch qkd_hr_core_tx     epyc2  96
launch qkd_hr_core_prompt epyc2  96
launch qkd_hr_core_rx     epyc2  64
launch qkd_hr_cdc_ch      epyc2  48
launch qkd_hr_cdc_ci      epyc2  48
launch qkd_hr_phy_pad     epyc2  48
launch qkd_hr_core_guard  epyc2  48
launch qkd_hr_core_peer   intel1 96
launch qkd_hr_core_order  intel1 64
launch qkd_hr_cdc_pc      intel1 64
launch qkd_hr_cdc_hi      intel1 48
launch qkd_hr_ingest_eng  intel1 64
launch qkd_hr_core_queue  intel1 48
launch qkd_hr_phy_adp     intel1 48
