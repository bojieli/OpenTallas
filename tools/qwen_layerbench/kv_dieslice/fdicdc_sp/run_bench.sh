#!/bin/bash
# KV-FDICDC-1 lock-step bench runner: run_bench.sh WORKTREE OUTDIR
set -uo pipefail
WT=$1; O=$2; B=$(cd "$(dirname "$0")" && pwd)
mkdir -p $O; cd $O
git -C $WT show 57b15ccf22:rtl/lib/ot_async_fifo.sv | sed 's/\bmodule ot_async_fifo\b/module ot_async_fifo_old/' > old_fifo.sv
git -C $WT show 57b15ccf22:rtl/physical/ot_fdi_phy_cdc.sv | sed 's/\bmodule ot_fdi_phy_cdc\b/module ot_fdi_phy_cdc_old/; s/\bot_async_fifo #/ot_async_fifo_old #/' > old_cdc.sv
SRC="$B/tb_fdicdc_sp.sv old_fifo.sv old_cdc.sv $WT/rtl/lib/ot_async_fifo.sv $WT/rtl/physical/ot_fdi_phy_cdc.sv $WT/rtl/lib/ot_reset_sync.sv"
SC=${SC:-64}   # KV-TYPES-3 11-07: SEL_CHUNK of the SEL_PIPE 1 instance (SC=8 run_bench.sh ... = the c45 form)
run() { # tag defines W plusargs
  local t=$1 d=$2 w=$3; shift 3
  iverilog -g2012 -o sim_$t -P tb_fdicdc_sp.W=$w -P tb_fdicdc_sp.SC=$SC $d $SRC > build_$t.log 2>&1 || { echo "RUN $t BUILD_FAIL"; tail -5 build_$t.log; return; }
  timeout 1800 vvp -n sim_$t "$@" > sim_$t.log 2>&1
  echo "RUN $t $(grep -c 'error' sim_$t.log) errlines | $(grep 'FDICDC_SP' sim_$t.log | tr '\n' ' ')"
}
run nom522 "" 522 +ptx=-1 &
run nomr522 "" 522 +ptx=40 &
run nom521 "" 521 +ptx=-1 &
run txfast522 "" 522 +tc=0.833 +tp=0.151 +ptx=90 +prx=0 &
run rxfast522 "" 522 +tc=0.151 +tp=1.043 +ptx=0 +prx=90 &
wait
for m in WSEL WDATA RSEL PUB URS; do
  run mut_$m "-DOT_SP_MUT_$m" 522 +ptx=-1 &
  run mutTX_$m "-DOT_SP_MUT_$m" 522 +tc=0.833 +tp=0.151 +ptx=90 +prx=0 &
  run mutRX_$m "-DOT_SP_MUT_$m" 522 +tc=0.151 +tp=1.043 +ptx=0 +prx=90 &
done
wait
