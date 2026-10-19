#!/bin/bash
# HBM-IDXPIPE 2026-10-18: pipelined topk link die master (ot_hbm_idx_topk_link_static_p) vs the historical die master,
# fixed-latency (+5) miter + gold records + fault path (tb_idx_link_pipe.sv). Verilator 5.050 (the closure daemon's).
# Usage: run_link_pipe.sh OUT [MUT]   (no MUT: 0 must PASS, 1..4 must FAIL; with MUT: run only that one, exit = its rc)
# MUT 1 record halves, 2 flit sequence, 3 carry slots from the beat (not the ring W), 4 emit read tap one edge early.
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd);cd "$root"
out=$(realpath -m "${1:?OUT}");mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator;[ -x "$vl" ]||vl=verilator
"$vl" --version
src=(rtl/test/hbm_idx_static/tb_idx_link_pipe.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static.sv rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
sha256sum "${src[@]}" "$0" > "$out/sources.sha256"
single=${2:-}
for m in ${single:-0 1 2 3 4};do
 "$vl" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_idx_link_pipe -GMUT="$m" -GSAFE_RING="${SAFE_RING:-0}" --Mdir "$out/obj$m" "${src[@]}" > "$out/build$m.log" 2>&1 || { tail -30 "$out/build$m.log"; exit 2; }
 set +e
 (cd "$out"&&"$out/obj$m/Vtb_idx_link_pipe") > "$out/run$m.log" 2>&1
 rc=$?
 set -e
 cat "$out/run$m.log" | grep -E 'IDX_LINK_PIPE|PIPE_MITER|PIPE_RECORD|mismatch' | head -20
 if [ -n "$single" ];then exit $rc;fi
 if [ "$m" = 0 ];then [ "$rc" = 0 ];grep -q 'IDX_LINK_PIPE PASS' "$out/run$m.log"
 else [ "$rc" != 0 ];grep -q 'pipelined link exact/miter/latency mismatch' "$out/run$m.log";echo "PIPE_MUTANT $m rejected";fi
done
echo IDX_LINK_PIPE_GATE_PASS
