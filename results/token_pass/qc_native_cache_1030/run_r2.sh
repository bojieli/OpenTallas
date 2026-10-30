#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
cd "$(dirname "$0")"
for variant in 0 1 2; do
 { echo 'read_verilog -formal -sv actual_hold.sv actual_status.sv miter.sv'; echo "chparam -set MUT $variant cache_refinement"; echo 'hierarchy -top cache_refinement; setattr -mod -unset keep_hierarchy; proc; flatten'; echo 'async2sync; dffunmap; opt -noff -keepdc; select -module cache_refinement';
   printf 'sat -seq 16 -set-def-inputs -set-init-def';
   for edge in 1 2 3 4; do printf ' -set-at %s rst_n 0' "$edge"; done
   for edge in $(seq 5 16); do printf ' -set-at %s rst_n 1' "$edge"; done
   echo " -prove proof_bad 0 -show-inputs -show-outputs -dump_json r2_v${variant}.json";
 } > r2_v${variant}.ys
 yosys -Q -T -s r2_v${variant}.ys > r2_v${variant}.log 2>&1
 done
