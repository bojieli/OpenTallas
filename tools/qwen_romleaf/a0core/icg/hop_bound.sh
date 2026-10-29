#!/bin/bash
# Run from the repository root, under the usual fleet admission.
# Usage: tools/qwen_romleaf/a0core/icg/hop_bound.sh OUTDIR
set -euo pipefail
out=$(mkdir -p "$1" && realpath "$1")
iverilog -g2012 -s tb_hop_bound -o "$out/hop_bound.vvp" \
  tools/qwen_romleaf/a0core/icg/tb_hop_bound.sv rtl/physical/a0_core/ot_a0_icg_hop.sv
vvp "$out/hop_bound.vvp" | tee "$out/hop_bound.log"
grep -q 'HOP_BOUND_PASS s=3 K=2 checks=32 errors=0 K3_mutant_caught=32' "$out/hop_bound.log"
