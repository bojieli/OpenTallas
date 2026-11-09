#!/bin/bash
# HBM-CORES-B: ONE late ECO on opsb_PS2f (TT +50.28, DRV 0, DRC 0, LEC EQ; FF hold: 937 port-start ends (NEEDS_PARENT),
# 24 non-port ends at -6.96). Near miss inside the COORD 05:37 numbers; first ECO on this routed form; non-port scope.
set -euo pipefail
K=/srv/opentallas-scratch2/claude/hbm-open-b/kits/opsb_PS2f
O=/srv/opentallas-scratch2/claude/hbm-cores-b/opsb_PS2f_eco1
S=/srv/opentallas-scratch2/claude/hbm-cores-b/tools_gd/tools/die_plan
test ! -e "$O"
python3 -I "$S/eco_loop.py" check "$K/signoff/signoff.json" || true
export OT_HOLD_REPAIR_SCOPE=nonport OT_FLOW_TAG=flow-20261109-gd-hbm
unset OT_MARGIN_POLICY
exec python3 -I "$S/eco_loop.py" run --kit "$K" --signoff "$K/signoff/signoff.json" --out "$O" --max-iter 1 --strict-one-pass --from route --hold-margin 10 --mem 32 --cpus 16 --keep --lec
