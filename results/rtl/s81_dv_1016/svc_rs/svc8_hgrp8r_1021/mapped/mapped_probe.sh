#!/usr/bin/env bash
# hgrp8r mapped lockstep: gold = flat mapped svc8 RTL (codex mapped_probe2 gold.v), cand = svc8_hgrp8r_bounded.v + wreg.
set -euo pipefail
R=/srv/opentallas-scratch/claude/s81-hgrp8r-1021; P=/srv/opentallas-scratch/claude/s81-svc8-1020/out_codex_mapped_probe2
O=$R/out_mapped; rm -rf "$O"; mkdir -p "$O"
cp $P/gold.v $P/cells.v $O/; cp $R/src/physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v $O/memory.v
cp $R/src/rtl/hdc/v41x/svc8_hgrp8r_bounded.v $O/cand.v; cp $R/src/rtl/hdc/v41x/ot_s81svc8_sram_wreg.v $O/wreg.v
sed 's/ot_s81svc8_hgrp_s81_bounded cand/ot_s81svc8_hgrp8r_s81_bounded cand/' $P/tb.v > $O/tb.v
grep -q 'ot_s81svc8_hgrp8r_s81_bounded cand' $O/tb.v
sha256sum $O/*.v > $O/source_identity.sha256
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; "$VL" --version
"$VL" --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 500 --x-initial unique --x-assign unique --top-module tb_svc8_mapped -Mdir "$O/obj" -o sim $O/{gold,cand,wreg,cells,memory,tb}.v > "$O/build.log" 2>&1 || { tail -20 $O/build.log; exit 2; }
f=0; for s in 1 2 3 4 5; do "$O/obj/sim" +seed=$s +verilator+rand+reset+2 +verilator+seed+$s > "$O/run_s$s.log" 2>&1 || f=1; grep -h 'SVC8_MAPPED' "$O/run_s$s.log" | tail -2; done
exit $f
