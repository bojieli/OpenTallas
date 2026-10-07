#!/bin/bash
# run_svc_io_bench.sh <outdir> (XDEF=+define+SVCIO_TILED: the r3 4-tile composition): Verilator build (gold + 2 mutants), 3 seeds gold, 1 seed per mutant; summary.txt
set -u
O=$(readlink -f ${1:-.}); R=$(cd $(dirname $0)/../../../.. && pwd); mkdir -p $O; cd $O
b() { t=$1; shift; d=''; for x in "$@"; do d="$d +define+$x"; done
  verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_s81ph_svc_io $d -Mdir obj_$t -o sim \
    $R/rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io.sv $R/rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io_tiles.sv $R/rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv $R/rtl/common/ot_fwd_link_stage.sv ${XDEF:-} $R/rtl/dsrom_sys/s81_ph/svc/tb_s81ph_svc_io.sv > build_$t.log 2>&1; echo "build $t rc=$?"; }
b g & b m1 S81PH_SVC_MUT_NOATOM & b m2 S81PH_SVC_MUT_SKID & wait
for s in 1 2 3; do ./obj_g/sim +SEED=$s +N=300 > run_g_$s.log 2>&1 & done
./obj_m1/sim +SEED=1 +N=300 > run_m1.log 2>&1 & ./obj_m2/sim +SEED=1 +N=300 > run_m2.log 2>&1 & wait
for f in run_*.log; do echo "$f: $(grep -h SUMMARY $f) $(grep -h RESULT $f)"; done > summary.txt; echo DONE >> summary.txt
