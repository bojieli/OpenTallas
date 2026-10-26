#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
root=$(cd "$(dirname "$0")/../.." && pwd)
out=$(realpath -m "$1");mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
s="$root/rtl/hbm_accel/generic/adapters/static_su/programme"
for slot in 0 1; do
 "$vl" --binary --timing -O1 -j 2 -Wno-fatal --top-module tb_su_multirate -GMUT_SLOT="$slot" \
 --Mdir "$out/obj$slot" "$s/multirate_bridge.sv" "$s/multirate_tb.sv" > "$out/build$slot.log" 2>&1
done
"$out/obj0/Vtb_su_multirate" > "$out/positive.log" 2>&1
grep -q 'SU_MULTIRATE PASS' "$out/positive.log"
for mut in SLOT RETURN PHASE; do
 bin="$out/obj0/Vtb_su_multirate";arg="+MUT_$mut"
 if [ "$mut" = SLOT ];then bin="$out/obj1/Vtb_su_multirate";arg="";fi
 set +e
 "$bin" $arg > "$out/mut_$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q 'SU_MULTIRATE FAIL' "$out/mut_$mut.log";then exit 1;fi
done
echo SU_MULTIRATE_GATE_PASS
