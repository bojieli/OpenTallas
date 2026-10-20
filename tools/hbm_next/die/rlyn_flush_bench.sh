#!/bin/bash
# HNX-DIE 10-20: reset-flush bench of the reset-free relay (rlyn_flush_tb.sv) on the fleet Verilator 5.050, random init.
#   rlyn_flush_bench.sh REMOTE_DIR (holds rtl/hbm_accel/die_glue/{ot_hbm_rlyn,hbfd_rlyn_masters}.sv + tools/hbm_next/die/rlyn_flush_tb.sv)
# Runs pos + 2 mutants via unpinned ot-run --dir; PASS iff pos PASS and both mutants FAIL with errors > 0.
RD=$1; OTRUN=${OTRUN:-/home/ubuntu/bin/ot-run}; VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
src="rtl/hbm_accel/die_glue/ot_hbm_rlyn.sv rtl/hbm_accel/die_glue/hbfd_rlyn_masters.sv tools/hbm_next/die/rlyn_flush_tb.sv"
fail=0
for m in pos short_reset stage_mut; do
  X=; [ $m = short_reset ] && X=-DMUT_SHORT_RESET; [ $m = stage_mut ] && X=-DOT_HBM_RLYN_MUT
  $OTRUN --mem 4 --threads 2 --dir $RD -- bash -c "rm -rf vl_$m && $VL --binary --timing -Wno-fatal -Wno-lint -Wno-style --x-assign unique --x-initial unique $X --top-module tb_rlyn_flush --Mdir vl_$m -o sim $src > vl_$m.build.log 2>&1 || { tail vl_$m.build.log; exit 3; }; ./vl_$m/sim +verilator+rand+reset+2 +verilator+seed+7; rc=\$?; rm -rf vl_$m; exit \$rc" > rlyn_$m.log 2>&1
  r=$(grep RLYN_FLUSH rlyn_$m.log | tail -1); echo "$m :: $r"
  if [ $m = pos ]; then echo "$r" | grep -q "RLYN_FLUSH PASS" || fail=1; else echo "$r" | grep -Eq "RLYN_FLUSH FAIL checks=[0-9]+ errors=[1-9]" || fail=1; fi
done
[ $fail = 0 ] && echo RLYN_FLUSH_GATE PASS || { echo RLYN_FLUSH_GATE FAIL; exit 1; }
