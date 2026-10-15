#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../../.." && pwd)
out=$(realpath "$1")
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src=("$root/rtl/hbm_accel/host_static_20261015/su_target/host_su_target.sv" "$root/rtl/hbm_accel/generic/adapters/static_su/programme/ot_hbm_su_programme.sv" "$root/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v" "$out/host_su_tb.sv")
"$vl" --binary --timing -O1 -j 4 -Wno-fatal +define+OT_MEM_NO_INIT --top-module host_su_tb --Mdir "$out/obj" "${src[@]}" > "$out/host_su_build.log" 2>&1
"$out/obj/Vhost_su_tb" +DIR="$out" > "$out/host_su_positive.log" 2>&1
grep -q HOST_SU_PASS "$out/host_su_positive.log"
for mut in DATA ADDR PHASE;do
 set +e
 "$out/obj/Vhost_su_tb" +DIR="$out" +MUT_$mut > "$out/host_su_mut_$mut.log" 2>&1
 rc=$?
 set -e
 if [[ "$rc" == 0 ]] || ! grep -q 'HOST_SU exact mismatch' "$out/host_su_mut_$mut.log";then exit 1;fi
done
"$vl" --binary --timing -O1 -j 4 -Wno-fatal +define+OT_MEM_NO_INIT --top-module host_su_tb -GMUT_READY=1 --Mdir "$out/obj_ready" "${src[@]}" > "$out/host_su_build_ready.log" 2>&1
set +e
"$out/obj_ready/Vhost_su_tb" +DIR="$out" > "$out/host_su_mut_ready.log" 2>&1
rc=$?
set -e
if [[ "$rc" == 0 ]] || ! grep -q 'HOST_SU missing row falsely ready' "$out/host_su_mut_ready.log";then exit 1;fi
echo HOST_SU_GATE_PASS
