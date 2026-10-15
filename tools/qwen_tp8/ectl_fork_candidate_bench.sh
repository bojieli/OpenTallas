#!/usr/bin/env bash
# Small RTL-only proof; no synthesis/clock/floorplan/closure claim.
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
iverilog -g2012 -s tb_qfd_ectl_word_fork_candidate -o "$out/positive.vvp" rtl/physical/ot_qwen_ectl_word_fork_candidate.sv rtl/test/qwen_kv_die/tb_qfd_ectl_word_fork_candidate.sv
vvp "$out/positive.vvp" > "$out/positive.log"
rg '^ECTL_FORK_CANDIDATE_PASS' "$out/positive.log"
iverilog -g2012 -s tb_qfd_ectl_word_fork_candidate -Ptb_qfd_ectl_word_fork_candidate.MUT=1 -o "$out/mutant.vvp" rtl/physical/ot_qwen_ectl_word_fork_candidate.sv rtl/test/qwen_kv_die/tb_qfd_ectl_word_fork_candidate.sv
if vvp "$out/mutant.vvp" > "$out/mutant.log"; then
    echo 'ERROR: row-swap mutant survived'
    exit 1
fi
rg '^ECTL_FORK_MUTANT_DETECTED' "$out/mutant.log"
