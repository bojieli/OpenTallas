#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../../.." && pwd)
out=$(realpath "$1")
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing -O1 -j 4 -Wno-fatal +define+OT_MEM_NO_INIT --top-module host_su_pair_tb --Mdir "$out/obj_pair" \
 "$root/rtl/hbm_accel/host_static_20261015/su_target/host_su_target.sv" \
 "$root/rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv" \
 "$root/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" \
 "$out/host_su_pair_tb.sv" > "$out/host_su_pair_build.log" 2>&1
"$out/obj_pair/Vhost_su_pair_tb" +DIR="$out" > "$out/host_su_pair_positive.log" 2>&1
grep -q HOST_SU_PAIR_PASS "$out/host_su_pair_positive.log"
set +e
"$out/obj_pair/Vhost_su_pair_tb" +DIR="$out" +MUT_EPOCH > "$out/host_su_pair_mut_epoch.log" 2>&1
rc=$?
set -e
if [[ "$rc" == 0 ]] || ! grep -q 'HOST_SU_PAIR stream exact/epoch' "$out/host_su_pair_mut_epoch.log";then exit 1;fi
echo HOST_SU_PAIR_GATE_PASS
