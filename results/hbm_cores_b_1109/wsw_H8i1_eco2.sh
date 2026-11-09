#!/bin/bash
# HBM-CORES-B: ONE late ECO on wsw H8 i1 (H8 + one ECO: TT -7.19 on 1 endpoint, 1 TT + 1 FF slew, non-port hold 0).
# Authority: [COORD] OWNER RULING 17:5x (2) 2026-11-08 STANDING: small miss -> one late ECO with --owner-override,
# structural form in parallel (wsw_H10 replicated reset, same lane). Declared: this is the second ECO on the H8 form.
set -euo pipefail
K=/srv/opentallas-scratch2/claude/die-hbm-93-open/wsw_eco/i1
O=/srv/opentallas-scratch2/claude/hbm-cores-b/wsw_H8i1_eco2
S=/srv/opentallas-scratch2/claude/hbm-cores-b/tools_gd/tools/die_plan
test ! -e "$O"
python3 -I "$S/eco_loop.py" check "$K/signoff/signoff.json" || true
export OT_FLOW_TAG=flow-20261109-gd-hbm
unset OT_MARGIN_POLICY
exec python3 -I "$S/eco_loop.py" run --kit "$K" --signoff "$K/signoff/signoff.json" --out "$O" --max-iter 1 --strict-one-pass --from route --hold-margin 0 --mem 48 --cpus 16 --keep --lec --owner-override
