#!/bin/bash
# S81-CORES-R 11-16: u_mq 128x23 ring + FF tail lockstep bench (EL 140 depth 139, EL 124 depth 123) vs the 1024-deep form
set -euo pipefail
R=$(cd "$(dirname "$0")/../../../.." && pwd); T=$(mktemp -d)
python3 -I $R/tools/die_plan/s81_svc_idx_fit.py $R/physical/die_plan/s81/bind/source_modules/portfix178/dsdv_idx_rg3_nq_native.sv $T/fit.sv
python3 -I $R/results/rtl/s81_svc_idx_fit_1103/mq_tail_1116/mk_bench.py $T/fit.sv $T/tb.sv
iverilog -g2012 -o $T/tb $T/tb.sv $R/results/rtl/s81_svc_idx_fit_1103/dsdv_idx_fit_mem.sv $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x23_m1_r0c0/ot_sram_1r1w_128x23_m1_r0c0.v
vvp -n $T/tb | grep MQBENCH | tee $T/out
grep -q "EL140_vs_ref_mismatch=0 EL124_vs_ref_mismatch=0 EL140_depth139_mismatch=0 first_match_lag=139 tail_stages=12" $T/out
