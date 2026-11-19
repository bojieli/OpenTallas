#!/bin/bash
# FABLE-FIX-S81-LEAF 11-19 vp CFX bench: ref = ot_s81sl_vp CFX 0, new = the same file with CFX 1, identical random inputs.
# Contract (tb_vp_cfx.sv): hc_post write-back exactly one clk later, every other output the same cycle, on legal AND dense
# (overlapping) streams; dense runs skip only the sticky fault bit (a write-back / HLOAD collision moves with the write-back).
# usage: run_vp_cfx_bench.sh [OUTDIR]
set -uo pipefail
H=$(cd "$(dirname "$0")"; pwd); R=$(cd "$H/../../../../.."; pwd); E=${1:-$H/out_cfx}; mkdir -p $E
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
VP=$R/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv
grep -v 'ot_s81sl_vp.sv' $H/leaf_bench.f | grep -E '^rtl/(lib|hdc|proto)/' | sed "s#^#$R/#" > $E/deps.f
echo "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r0c0/ot_sram_1r1w_512x128_m4_r0c0.v" >> $E/deps.f
ren(){ local f=$1 sfx=$2; for m in $(grep -oP '^\s*module\s+\K\w+' $f | sort -u); do sed -i -E "s/\b$m\b/${m}${sfx}/g" $f; done; }
run(){ local n=$1 hqx=$2 csd=$3 dense=$4 cfx=$5; shift 5; local D=$E/$n; mkdir -p $D; local X=""; [ $dense = 1 ] && X=-DDENSE_CTL
  verilator -E -P $VP > $D/ref.sv 2>$D/pp_r.log || { echo "$n PP_FAIL"; return; }
  verilator -E -P "$@" $VP > $D/new.sv 2>$D/pp_n.log || { echo "$n PP_FAIL"; return; }
  ren $D/ref.sv _r; ren $D/new.sv _n
  nice verilator --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-lint -Wno-style \
     -DSHIFT=0 -DHQXV=$hqx -DCSD=$csd -DDENSE=$dense -DCFXV=$cfx $X -DNCYC=${NCYC:-60000} -DGAPMIN=${GAPMIN:-24} --x-initial unique --x-assign unique \
     -f $E/deps.f --top-module tb --Mdir $D/obj -o tb $H/tb_vp_cfx.sv $D/ref.sv $D/new.sv > $D/build.log 2>&1 || { echo "$n BUILD_FAIL $(grep -m3 -i error $D/build.log)"; return; }
  for seed in ${SEEDS:-1}; do $D/obj/tb +verilator+rand+reset+0 +verilator+seed+$seed > $D/run_s$seed.log 2>&1; echo "$n seed=$seed rc=$? $(grep -hE '_RESULT' $D/run_s$seed.log | tr '\n' ' ')"; done; }
{
SEEDS="1 2 3"           run cfx_legal      0 0 0 1
SEEDS="1 2 3"           run cfx_dense      0 0 1 1
SEEDS="1 2"   GAPMIN=48 run cfx_hqx2_cs1   2 1 0 1
SEEDS="1"               run cfx_hqx2_dense 2 1 1 1
SEEDS="1"               run ctl_cfx0_noshift 0 0 1 0   # control: CFX 0 has no + 1 on the write-back, so this tb must FAIL (errors = write-backs)
SEEDS="1"               run ctl_mut_hq     0 0 0 1 -DOT_S81SL_VP_MUT_CFXHQ
} 2>&1 | tee $E/summary.log
