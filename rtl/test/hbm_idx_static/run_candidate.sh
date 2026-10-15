#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:-/tmp/hbm-idx-static-candidate-proof}")
mkdir -p "$out"
python3 tools/hbm_idx_static_candidate_vectors.py "$out"
for m in 0 1;do
 iverilog -g2012 -s tb_candidate_static -Ptb_candidate_static.MUT="$m" -o "$out/c$m.vvp" rtl/hbm_accel/index/ot_hbm_idx_candidate_static.sv rtl/test/hbm_idx_static/tb_candidate_static.sv > "$out/cbuild$m.log" 2>&1
 set +e
 (cd "$out"&&vvp "c$m.vvp") > "$out/crun$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/crun$m.log"
 if [ "$m" = 0 ];then test "$rc" = 0;else test "$rc" != 0;fi
done
