#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?output};mut=${2:-0};mode=${3:-normal}
mkdir -p "$out"
python3 tools/hbm_coll_static/native_programme_pair.py --out "$out/images" > "$out/compiler.log"
v=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
p=rtl/hbm_accel/host_static_20261015/transport
"$v" --binary --timing -O2 -j 4 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ +define+OT_MEM_NO_INIT --top-module tb_host_sm_pair_fleet -GMUT="$mut" --Mdir "$out/obj$mut" "$p/ot_hbm_host_sm_pair_install.sv" "$p/ot_hbm_host_sm_pair_fleet.sv" "$p/tb_host_sm_pair_fleet.sv" rtl/hbm_accel/sm/static/native_pair_1417/ot_smh_calendar_pair_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v > "$out/build$mut.log" 2>&1 || { tail -40 "$out/build$mut.log";exit 2; }
exe="$out/obj$mut/Vtb_host_sm_pair_fleet"
if [[ "$mut" != 0 ]];then
 scenario=0;[[ "$mut" != 2 ]] || scenario=1
 if "$exe" +IMAGES="$out/images" +case="$scenario" > "$out/run$mut.log" 2>&1;then echo "HOST_SM_PAIR MUTANT SURVIVED $mut";exit 1;fi
 grep -q 'HOST_SM_PAIR_FAIL' "$out/run$mut.log"
 echo "HOST_SM_PAIR MUTANT REJECTED $mut";cat "$out/run$mut.log";exit 0
fi
"$exe" +IMAGES="$out/images" > "$out/run0.log" 2>&1 || { cat "$out/run0.log";exit 1; }
cat "$out/run0.log"
for scenario in {1..6};do
 "$exe" +IMAGES="$out/images" +case="$scenario" > "$out/case-$scenario.log" 2>&1 || { cat "$out/case-$scenario.log";exit 1; }
 grep -q '^HOST_SM_PAIR_NEGATIVE_PASS' "$out/case-$scenario.log";cat "$out/case-$scenario.log"
done
