#!/bin/bash
# DIE-S81-85 11-09 vp SR bench: ref = main ot_s81sl_vp (SR 0), new = branch vp with -DOT_S81SL_VP_SRAMREG (SR 1).
set -uo pipefail
H=$(cd "$(dirname "$0")"; pwd); E=$H/out; mkdir -p $E
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
D0=$H/dep; Y="-f $H/deps.f"
ren(){ local f=$1 sfx=$2; for m in $(grep -oP '^\s*module\s+\K\w+' $f | sort -u); do sed -i -E "s/\b$m\b/${m}${sfx}/g" $f; done; }
run(){ local n=$1 sh=$2 hqx=$3 csd=$4 dense=$5; shift 5; local D=$E/$n; mkdir -p $D
  # flatten each side with its dependencies so the two copies can be renamed apart
  verilator -E -P $H/ref/ot_s81sl_vp.sv > $D/ref.sv 2>$D/pp_r.log || { echo "$n PP_FAIL $(head -3 $D/pp_r.log)"; return; }
  verilator -E -P "$@" $H/new/ot_s81sl_vp.sv > $D/new.sv 2>$D/pp_n.log || { echo "$n PP_FAIL"; return; }
  ren $D/ref.sv _r; ren $D/new.sv _n
  nice verilator --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-lint -Wno-style \
     -DSHIFT=$sh -DHQXV=$hqx -DCSD=$csd -DDENSE=$dense -DNCYC=${NCYC:-60000} -DGAPMIN=${GAPMIN:-24} ${XD:-} --x-initial unique --x-assign unique \
     $Y --top-module tb --Mdir $D/obj -o tb $H/tb_vp_sr.sv $D/ref.sv $D/new.sv > $D/build.log 2>&1 || { echo "$n BUILD_FAIL $(grep -m3 -i error $D/build.log)"; return; }
  for seed in ${SEEDS:-1}; do $D/obj/tb +verilator+rand+reset+0 +verilator+seed+$seed > $D/run_s$seed.log 2>&1; echo "$n seed=$seed rc=$? $(grep -hE '_RESULT' $D/run_s$seed.log | tr '\n' ' ')"; done; }
: > /summary.log
{
SEEDS="1 2 3"           run sr_legal      1 0 0 0 -DOT_S81SL_VP_SRAMREG
SEEDS="1 2 3" GAPMIN=48 run sr_legal_g48  1 0 0 0 -DOT_S81SL_VP_SRAMREG
SEEDS="1 2"   GAPMIN=48 run sr_hqx2_cs1   1 2 1 0 -DOT_S81SL_VP_SRAMREG
SEEDS="1 2"   XD=-DNOPOST run sr_dense_nopost 1 0 0 1 -DOT_S81SL_VP_SRAMREG
SEEDS="1"     run sr_dense      1 0 0 1 -DOT_S81SL_VP_SRAMREG
SEEDS="1"     run sr_mut        1 0 0 0 -DOT_S81SL_VP_SRAMREG -DOT_S81SL_VP_MUT_SRAMREG
SEEDS="1"     run sr_shift0     0 0 0 0 -DOT_S81SL_VP_SRAMREG
SEEDS="1"     run default_eq    0 0 0 1
} 2>&1 | tee -a /summary.log
