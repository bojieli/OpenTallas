#!/bin/bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$root"
out=$(realpath -m "${1:?OUT}")
mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vl" --version
sha256sum rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv rtl/test/hbm_idx_static/{run_link_pipe.sh,run_link_safe.sh,tb_idx_link_pipe.sv,tb_idx_control_ring.sv} > "$out/source.sha256"
"$vl" --binary --timing -j 4 -O1 -Wno-fatal --top-module tb_idx_control_ring --Mdir "$out/ring_obj" rtl/test/hbm_idx_static/tb_idx_control_ring.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv > "$out/ring_build.log" 2>&1
"$out/ring_obj/Vtb_idx_control_ring" > "$out/ring.log" 2>&1
cat "$out/ring.log"
for m in ${HIDX_MUTANTS:-0 1 2 3 4 5 6};do
 set +e
 SAFE_RING=1 SAFE_CARRY=1 EMIT_GAP=0 bash rtl/test/hbm_idx_static/run_link_pipe.sh "$out/m$m" "$m" > "$out/m$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then [ "$rc" = 0 ];grep -q 'IDX_LINK_PIPE PASS' "$out/m$m.log"
 else [ "$rc" != 0 ];grep -q 'pipelined link exact/miter/latency mismatch' "$out/m$m.log";fi
 tail -3 "$out/m$m.log"
done
echo HIDX_LINK_SAFE_SOURCE_PASS
