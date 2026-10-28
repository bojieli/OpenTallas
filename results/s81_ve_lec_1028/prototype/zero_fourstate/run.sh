#!/bin/bash
set -eu
B=/srv/opentallas-scratch2/claude/codex-s81-ve-lec-0359/zero_fourstate
S=/srv/opentallas-scratch2/claude/codex-s81-ve-lec-0359/zero_proto/sources.f
for mut in 0 1;do
 iverilog -g2012 -DOT_S81_VE_LOADSAFE5 -DOT_S81_VE_BF16_RING_ZERO -s tb -Ptb.MUT=$mut -o "$B/mut$mut.vvp" -f "$S" "$B/tb.sv" >"$B/build$mut.log" 2>&1
 vvp "$B/mut$mut.vvp" >"$B/run$mut.log" 2>&1
done
