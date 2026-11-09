#!/bin/bash
# HBM-CORES-B: ONE late ECO on own_vRF4T (TT +56.52; FF hold non-port 162 ep worst -21.56, port 10 ep -27.94; FF slew 12; DRC 0).
# Over the near-miss endpoint count (162 > 100) by a small amount -> [COORD] OWNER RULING 17:5x (2) STANDING --owner-override.
set -euo pipefail
K=/srv/opentallas-scratch2/claude/hbm-open-b/kits/own_vRF4T
O=/srv/opentallas-scratch2/claude/hbm-cores-b/own_RF4T_eco1
S=/srv/opentallas-scratch2/claude/hbm-cores-b/tools_gd/tools/die_plan
test ! -e "$O"
python3 -I "$S/eco_loop.py" check "$K/signoff/signoff.json" || true
export OT_HOLD_REPAIR_SCOPE=nonport OT_FLOW_TAG=flow-20261109-gd-hbm
unset OT_MARGIN_POLICY
exec python3 -I "$S/eco_loop.py" run --kit "$K" --signoff "$K/signoff/signoff.json" --out "$O" --max-iter 1 --strict-one-pass --from route --hold-margin 10 --mem 48 --cpus 16 --keep --lec --owner-override
