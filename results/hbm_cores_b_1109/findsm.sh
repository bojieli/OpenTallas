#!/bin/bash
# read-only name search for q_sm child masters; dirs named after the design, and any ODB under results/asap7/<design>
P='ot_hbm_accel_smh_*|ot_hbm_sm_pv_merge*|ot_hbm_sm_attn_*|ot_hbm_sm_kv_line*|ot_smh_static_front*|ot_hbm_sm_i8w_front*|ot_smh_*|*_smh_xs*|*smh_bdc*|*smh_tct*|*smh_tcl_gu*|*smh_pt_[we]*'
A=$(echo "$P" | sed 's/|/" -o -name "/g')
for r in /srv/opentallas-scratch /srv/opentallas-scratch2 /srv/opentallas-scratch3 /home/ubuntu/scratch-root; do
  [ -d "$r/claude" ] || continue
  eval "timeout 500 ionice -c3 nice find $r/claude -maxdepth 13 -type d \( -name \"$A\" \) -not -path '*/rtl/*' -not -path '*/.git/*' 2>/dev/null"
done
