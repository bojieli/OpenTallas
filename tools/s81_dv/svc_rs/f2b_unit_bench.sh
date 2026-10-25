#!/usr/bin/env bash
# S81/SVCG unit bench: tb_dsdv_svc_f2b (base + F2B_MUT=1), Verilator 5.050.  usage: run_unit.sh OUTDIR (repo root cwd)
set -u
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=$1; D=rtl/dsrom_sys/s81_dv/svc_rs
for V in base mut; do
  DEF=(); [ $V = mut ] && DEF=(-DF2B_MUT=1)
  mkdir -p $O/unit_$V
  "$VL" --binary --top-module tb_dsdv_svc_f2b -Mdir $O/unit_$V/obj -j 8 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -I$D "${DEF[@]}" \
    rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv $D/dsdv_svc_sx_hrow.sv $D/dsdv_svc_sx.sv \
    $D/test/tb_dsdv_svc_f2b.sv > $O/unit_$V/build.log 2>&1 || { tail -20 $O/unit_$V/build.log; continue; }
  for s in 1 2 3; do $O/unit_$V/obj/Vtb_dsdv_svc_f2b +seed=$s > $O/unit_$V/run_s$s.log 2>&1; echo "$V s$s: $(grep -E '^F2B_UNIT' $O/unit_$V/run_s$s.log | tr '\n' ' ')"; done
done
