#!/bin/bash
set -eu
cd /srv/opentallas-scratch2/claude/codex-s81-rck-1106/am_proof
python3 prepare.py
for kind in good wrong_group wrong_xor wrong_threshold wrong_valid wrong_payload wrong_reset; do
 extra=;[ "$kind" != wrong_valid ] || extra=-DWRONG_VALID
 iverilog -g2012 -DOT_S81_KP4_AM_FACE3 $extra -s tb -o "$kind.out" tb.sv old_literal.sv reset_literal.sv face_literal.sv "$kind.sv" > "$kind.build.log" 2>&1
 if vvp "$kind.out" > "$kind.log" 2>&1; then
   [ "$kind" = good ] || { echo "MUTANT_SURVIVED $kind";exit 1; }
 else
   [ "$kind" != good ] || { cat "$kind.log";exit 1; }
 fi
 cat "$kind.log"
done
