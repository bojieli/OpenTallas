#!/bin/bash
# exits with one line at the first terminal event; SKIP = space separated subset of: opsa1 p2gbal restj
S=" ${SKIP:-} "
R() { ssh -n -o ControlPath=none -o ConnectTimeout=20 "$@"; }
L=/srv/opentallas-scratch3/claude/hbm-hard-6/kits/restj_C/ot_hgi_sfu_split3_ctl_rest_1c_vC/run/logs/asap7/hbc_ot_hgi_sfu_split3_ctl_rest_1c/base/5_2_route.tmp.log
while :; do
  if [[ $S != *" opsa1 "* ]]; then o=$(R epyc2 'docker ps -q --filter name=hbmcore-kit_opsa1_P3_ | wc -l') && [ "$o" = 0 ] && { echo "EVENT opsa1 container ended"; exit 0; }; fi
  if [[ $S != *" p2gbal "* ]]; then o=$(R intel1 'docker ps -q --filter name=hbmcore-kit_opsa0_P2g_bal | wc -l') && [ "$o" = 0 ] && { echo "EVENT p2gbal container ended"; exit 0; }; fi
  if [[ $S != *" restj "* ]]; then o=$(R epyc6 "docker ps -q --filter id=bca409f23a19 | wc -l; echo \$(( \$(date +%s) - \$(stat -c %Y $L 2>/dev/null || date +%s) ))") && { set -- $o; [ "$1" = 0 ] && { echo "EVENT restj container ended"; exit 0; }; [ "${2:-0}" -ge 14400 ] && { echo "EVENT restj log flat 4 h"; exit 0; }; }; fi
  sleep 120
done
