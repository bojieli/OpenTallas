#!/bin/bash
set -uo pipefail
source ~/.opentallas-env
SRC=/srv/opentallas/repos/peirce-topk-balanced-5ee4cde5b
JOB=/srv/opentallas-scratch/jobs/peirce-topk-balanced-gate-r1
cd "$SRC"
git rev-parse HEAD > "$JOB/source_commit.txt"
sha256sum rtl/gpu/ot_gpu_router_topk.sv rtl/gpu/ot_gpu_router_topk_ip_bal.sv rtl/gpu/ot_gpu_topk_compare_bal.sv rtl/test/hbm_topk_predicate/tb_topk_balanced.sv > "$JOB/source_hashes.txt"
iverilog -g2012 -s tb_topk_balanced -o "$JOB/gate.vvp" rtl/gpu/ot_gpu_router_topk.sv results/rtl/hbm_topk_predicate_20261005/inputs/ot_gpu_router_topk_ip_f.sv rtl/gpu/ot_gpu_router_topk_ip_bal.sv rtl/gpu/ot_gpu_topk_compare_bal.sv rtl/test/hbm_topk_predicate/tb_topk_balanced.sv > "$JOB/compile.log" 2>&1
rc=$?; echo compile_rc=$rc > "$JOB/terminal.txt"
if [ "$rc" != 0 ]; then exit "$rc"; fi
vvp "$JOB/gate.vvp" > "$JOB/runtime.log" 2>&1
rc=$?; echo runtime_rc=$rc >> "$JOB/terminal.txt"
exit "$rc"
