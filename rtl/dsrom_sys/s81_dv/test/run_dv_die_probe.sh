#!/bin/bash
# run_dv_die_probe.sh <kit dir> <out dir> : TOKEN-PASS-S81 (10-18) full-RTL Verilator build + idle-run cost probe of the
# current S81 die dv_die (p4l bind9).  Kit = die_probe.f (die_port_bind --elab-out closure + tb_dv_die_probe.sv), paths
# relative to the kit.  Records: build wall / max RSS (build.time), run wall / RSS for NCYC 2,000 and 20,000 idle cycles
# after reset (run_<n>.time, DV_DIE_PROBE_T0/T1 stamps -> simulated cycles per wall second), verdict TB_DV_DIE_PROBE.
set -u
K=$1; OUT=$2; VL=${VL:-verilator}; J=${J:-32}
mkdir -p $OUT; cd $K
$VL --version > $OUT/verilator.version 2>&1
( sha256sum $(grep -v '^+' die_probe.f) ) > $OUT/sources.sha256
/usr/bin/time -v -o $OUT/build.time $VL --binary --timing -j $J -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN \
  -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE --unroll-count 4 -fno-dfg -CFLAGS -O1 --top-module tb_dv_die_probe \
  -f die_probe.f --Mdir $OUT/obj -o sim > $OUT/build.log 2>&1
echo "build rc $?" > $OUT/status
for n in 2000 20000; do
  [ -x $OUT/obj/sim ] || break
  /usr/bin/time -v -o $OUT/run_$n.time $OUT/obj/sim +NCYC=$n > $OUT/run_$n.log 2>&1; echo "run $n rc $?" >> $OUT/status
done
for n in 2000 20000; do
  t0=$(grep -h DV_DIE_PROBE_T0 $OUT/run_$n.log 2>/dev/null | cut -d= -f2); t1=$(grep -h DV_DIE_PROBE_T1 $OUT/run_$n.log 2>/dev/null | cut -d= -f2)
  [ -n "$t0" ] && [ -n "$t1" ] && echo "rate $n $(python3 -c "print(round($n/($t1-$t0),1))") cyc/s" >> $OUT/status
done
grep -h "Elapsed\|Maximum resident" $OUT/build.time $OUT/run_*.time >> $OUT/status 2>/dev/null
grep -h "TB_DV_DIE_PROBE\|DV_DIE_PROBE cycles" $OUT/run_*.log >> $OUT/status 2>/dev/null
cat $OUT/status
