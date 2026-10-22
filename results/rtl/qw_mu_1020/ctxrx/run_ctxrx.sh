#!/bin/bash
# QW-MU 10-20: Verilator (the closure daemon's 5.050) bench of qfd_mu_ctx_rx_die.  Run from the source root:
#   [MUT=1] bash results/rtl/qw_mu_1020/ctxrx/run_ctxrx.sh OUT [+bad=N]      (prints the TB_CTXRX verdict line)
# Files read: rtl/qwen_split/mu/qfd_mu_ctx_rx.sv, results/rtl/qw_mu_1020/ctxrx/tb_ctxrx.sv
set -u
O=$1; shift; V=${VERILATOR:-verilator}
mkdir -p $O; $V --version > $O/verilator_version.txt
$V --binary --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED --top-module tb_ctxrx -GMUT=${MUT:-0} -Mdir $O/obj \
  rtl/qwen_split/mu/qfd_mu_ctx_rx.sv results/rtl/qw_mu_1020/ctxrx/tb_ctxrx.sv > $O/build.log 2>&1 || { echo BUILD_FAIL; tail -20 $O/build.log; exit 2; }
$O/obj/Vtb_ctxrx "$@" > $O/run.out 2>&1; cat $O/verilator_version.txt; grep -E 'TB_CTXRX|ERR' $O/run.out | head -8
