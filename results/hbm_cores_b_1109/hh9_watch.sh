#!/bin/bash
# exits with one line at the first terminal event not listed in SKIP (space separated: count opsa1 p2gbal restj)
S=" ${SKIP:-} "
R() { ssh -n -o ControlPath=none -o ConnectTimeout=20 "$@"; }
while :; do
  if [[ $S != *" count "* ]]; then o=$(R intel2 'if pgrep -f "rtp.py --force" >/dev/null; then echo live; else echo gone; fi') && [ "$o" = gone ] && { echo "EVENT count finished"; exit 0; }; fi
  if [[ $S != *" opsa1 "* ]]; then o=$(R epyc2 'docker ps -q --filter name=hbmcore-kit_opsa1_P3_ | wc -l') && [ "$o" = 0 ] && { echo "EVENT opsa1 container ended"; exit 0; }; fi
  if [[ $S != *" p2gbal "* ]]; then o=$(R intel1 'docker ps -q --filter name=hbmcore-kit_opsa0_P2g_bal | wc -l') && [ "$o" = 0 ] && { echo "EVENT p2gbal container ended"; exit 0; }; fi
  if [[ $S != *" restj "* ]]; then o=$(R epyc6 'docker ps -q --filter id=bca409f23a19 | wc -l') && [ "$o" = 0 ] && { echo "EVENT restj container ended"; exit 0; }
    [ "$(date +%H%M)" -ge 0130 ] && [ "$(date +%H%M)" -lt 1200 ] && { echo "EVENT restj 01:30 deadline"; exit 0; }; fi
  sleep 120
done
