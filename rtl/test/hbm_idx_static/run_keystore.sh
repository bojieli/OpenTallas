#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-keystore-proof}")
mkdir -p "$out"
for m in 0 1 2;do
 iverilog -g2012 -s tb_keystore_static -Ptb_keystore_static.MUT="$m" -o "$out/w$m.vvp" rtl/hbm_accel/index/ot_hbm_idx_keystore_static.sv rtl/test/hbm_idx_static/tb_keystore_static.sv > "$out/wbuild$m.log" 2>&1
 set +e
 vvp "$out/w$m.vvp" > "$out/wrun$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/wrun$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
done
