#!/bin/bash
# usage: run_rand.sh RTLDIR OUTDIR  (verilator >= 5; RTLDIR has ot_hgi_su_unit.sv + ot_hgi_su_lgroup2_lf.sv)
R=$1; O=$2; T=$(dirname $(readlink -f $0)); mkdir -p $O
for m in 0 1 2; do for s in 1 2 3; do
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -GMUT=$m -GSEED=$s --top-module tb_rand -Mdir $O/obj_m${m}_s$s \
    $R/ot_hgi_su_unit.sv $R/ot_hgi_su_lgroup2_lf.sv $T/tb_rand.sv > $O/build_m${m}_s$s.log 2>&1 || { echo "build fail m$m"; tail -5 $O/build_m${m}_s$s.log; continue; }
  $O/obj_m${m}_s$s/Vtb_rand | grep SREG_RAND
done; done
