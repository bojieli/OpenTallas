#!/bin/bash
# Q-B2r 10-16: qfd_b2_word_status exact bench. usage: run_word_status_bench.sh OUTDIR [MUT]
# MUT 0 must print PASS; MUT 1/2 (one-edge-late half valid / result) must print FAIL (exit 1).
set -u
out=$1; mut=${2:-0}
mkdir -p "$out"
F="rtl/qwen_split/qfd_b2_word_status.sv tools/qwen_b2_join/tb_b2_word_status.sv"
sha256sum $F > "$out/source.sha256"
iverilog -g2012 -s tb_b2_word_status -o "$out/sim" $F > "$out/build.log" 2>&1 || { cat "$out/build.log"; echo "FAIL build"; exit 2; }
vvp "$out/sim" +MUT=$mut > "$out/run$mut.log" 2>&1
cat "$out/run$mut.log"
grep -q '^PASS b2 word status exact' "$out/run$mut.log"
