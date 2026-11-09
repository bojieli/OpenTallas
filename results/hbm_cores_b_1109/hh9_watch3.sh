#!/bin/bash
# one line at the first job end. Containers: host:name substring.
W="epyc2:hbmcore-kit_opsa1_P3_ intel1:resign-rootctlE-lec epyc2:resign-h9bi2main-lec intel1:prd-n4_vRF1b_eco intel1:hbmcore-n4_local_vA_ intel1:prd-lanec_E_eco"
R() { ssh -n -o ControlPath=none -o ConnectTimeout=20 "$@"; }
L=/srv/opentallas-scratch3/claude/hbm-hard-6/kits/restj_C/ot_hgi_sfu_split3_ctl_rest_1c_vC/run/logs/asap7/hbc_ot_hgi_sfu_split3_ctl_rest_1c/base/5_2_route.tmp.log
while :; do
  for hn in $W; do h=${hn%%:*}; n=${hn#*:}
    o=$(R $h "docker ps --format '{{.Names}}' | grep -c -- '$n'") || continue
    [ "$o" = 0 ] && { echo "EVENT $n ended on $h"; exit 0; }
  done
  o=$(R epyc6 "docker ps -q --filter id=bca409f23a19 | wc -l; echo \$(( \$(date +%s) - \$(stat -c %Y $L) ))") && { set -- $o; [ "$1" = 0 ] && { echo "EVENT restj ended"; exit 0; }; [ "${2:-0}" -ge 14400 ] && { echo "EVENT restj flat 4h"; exit 0; }; }
  o=$(R intel2 'grep -c "RAN on\|NOT RUN" ~/hbm-hard-9-logs/opsa0_P2gbal_route.otrun.log') && [ "$o" != 0 ] && { echo "EVENT p2gbal route ended"; exit 0; }
  o=$(R intel1 'pgrep -f "kit_lane1p_D1/lec_h" | wc -l') && [ "$o" = 0 ] && { echo "EVENT lane1p D1 hinted LEC ended"; exit 0; }
  sleep 180
done
