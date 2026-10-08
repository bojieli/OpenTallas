#!/bin/bash
# run_bench.sh <outdir> [iverilog defines...]: hfd_router wrapper lockstep (tb_hfd_router, 40,000 checks) under Icarus.
O=$1; shift; mkdir -p $O
V=physical/hbm_accel_die_views
iverilog -g2012 "$@" -o $O/tb.vvp -s tb_hfd_router $V/router/rtl/tb_hfd_router.sv $V/router/rtl/hfd_router.sv $V/common/ot_hfd_oreg1.sv \
  rtl/gpu/ot_gpu_router_topk_ps.sv rtl/gpu/ot_gpu_router_topk.sv rtl/common/ot_fwd_link_stage.sv > $O/build.log 2>&1 || { echo BUILD_FAILED; exit 2; }
timeout ${TMO:-7000} vvp -n $O/tb.vvp > $O/run.log 2>&1; rc=$?
grep -h "TB_hfd_router\|FAIL\|mismatch" $O/run.log | tail -3
grep -q "Fatal\|FAIL" $O/run.log && { echo TB_ROUTER_FAIL; exit 1; }
exit $rc
