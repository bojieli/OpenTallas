#!/bin/bash
# BIND-SUBTYPE-2 (DO_NOT_COUNT): repository LEC (tools/die_plan/lec.py) on the subtype kits, pos then neg.
D=/srv/opentallas-scratch2/claude/bind-subtype-2-1111/lec
cd "$D/tools" || exit 9
for k in kit_q_b110 kit_q_b110_neg; do
  echo "LEC_START $k $(date -u +%T)"
  python3 -I die_plan/lec.py "$D/$k" --netlist "$D/$k/gate/new_q_b110.v" --mem 32 > "$D/$k.lec.log" 2>&1
  echo "LEC_RC $k $?"
  tail -3 "$D/$k.lec.log" | cut -c1-300
done
