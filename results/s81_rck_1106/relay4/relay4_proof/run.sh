#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81-rck-1106/relay4_proof
python3 prepare.py
for kind in good short_cohort short_reset counts_bypass valid_bypass data_bypass reset_bypass; do
 iverilog -g2012 -DOT_S81_KP4_AM_FACE3 -DOT_S81_RCK_RELAY4 -s tb -o "$kind.out" "${kind}_tb.sv" old_literal.sv reset_literal.sv face_literal.sv good.sv > "$kind.build.log" 2>&1
 if vvp "$kind.out" > "$kind.log" 2>&1; then
  [ "$kind" = good ] || { echo "MUTANT_SURVIVED $kind";exit 1; }
 else
  [ "$kind" != good ] || { cat "$kind.log";exit 1; }
 fi
 cat "$kind.log"
done
