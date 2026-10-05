#!/bin/bash
set -uo pipefail
source ~/.opentallas-env
cd /srv/opentallas-scratch/jobs/peirce-topk-predicate-gate-r1
sha256sum src/* > source_hashes.txt
iverilog -g2012 -s tb_topk_predicate -o gate.vvp src/ot_gpu_router_topk.sv src/ot_gpu_router_topk_ip_f.sv src/ot_gpu_router_topk_ip_pred.sv src/tb_topk_predicate.sv > compile.log 2>&1
rc=$?
echo compile_rc=$rc > terminal.txt
if [ "$rc" != 0 ]; then exit "$rc"; fi
vvp gate.vvp > runtime.log 2>&1
rc=$?
echo runtime_rc=$rc >> terminal.txt
exit "$rc"
