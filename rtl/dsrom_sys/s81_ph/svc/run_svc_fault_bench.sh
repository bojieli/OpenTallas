#!/bin/bash
# run_svc_fault_bench.sh <outdir>: the IO-hub fault station (s81-die-2 2026-10-08).  Builds FSTN 0, FSTN 1 and the
# FSTN 1 drop mutant; 3 seeds each.  PASS: FSTN 0 / 1 benches pass and LAT(FSTN 1) = LAT(FSTN 0) + 1 on every seed;
# the mutant must FAIL (no fault).  Verdict line: SVC_FAULT_STATION PASS|FAIL.
set -u
O=$(readlink -f ${1:-.}); R=$(cd $(dirname $0)/../../../.. && pwd); mkdir -p $O; cd $O
b() { t=$1; f=$2; shift 2; d=''; for x in "$@"; do d="$d +define+$x"; done
  verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module tb_s81ph_svc_fault -GFSTN=$f $d -Mdir obj_$t -o sim \
    $R/rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io.sv $R/rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io_tiles.sv $R/rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv \
    $R/rtl/common/ot_fwd_link_stage.sv $R/rtl/dsrom_sys/s81_ph/svc/tb_s81ph_svc_fault.sv > build_$t.log 2>&1 || { echo "BUILD FAIL $t"; tail -5 build_$t.log; exit 2; }; }
b f0 0 & b f1 1 & b mut 1 S81PH_SVC_MUT_FSTN_DROP & wait
for t in f0 f1 mut; do [ -x obj_$t/sim ] || { echo "SVC_FAULT_STATION FAIL (no build $t)"; exit 2; }; done
ok=1
for s in 1 2 3; do
  for t in f0 f1 mut; do ./obj_$t/sim +SEED=$s > run_${t}_$s.log 2>&1; grep -h SVC_FAULT_BENCH run_${t}_$s.log; done
  l0=$(grep -ho 'lat [-0-9]*' run_f0_$s.log | cut -d' ' -f2); l1=$(grep -ho 'lat [-0-9]*' run_f1_$s.log | cut -d' ' -f2)
  grep -q 'SVC_FAULT_BENCH PASS' run_f0_$s.log && grep -q 'SVC_FAULT_BENCH PASS' run_f1_$s.log && [ "$l1" = "$((l0 + 1))" ] || ok=0
  grep -q 'SVC_FAULT_BENCH FAIL' run_mut_$s.log || ok=0
done
[ $ok = 1 ] && echo "SVC_FAULT_STATION PASS (fault +1 cycle; drop mutant FAIL)" || { echo "SVC_FAULT_STATION FAIL"; exit 1; }
