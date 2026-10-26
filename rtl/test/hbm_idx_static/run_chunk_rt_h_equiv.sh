#!/bin/bash
# HBM-P4-SPLIT: half-column core split ot_hbm_idx_chunk_rt_h vs pinned ot_hbm_idx_chunk_rt, cycle-exact lock-step.
#   run_chunk_rt_h_equiv.sh OUT MODE     MODE: pos | gap4 | mut (half seam one edge late -> must FAIL)
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); mode=${2:-pos}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
src=(rtl/test/hbm_idx_static/tb_idx_chunk_rt_h_equiv.sv rtl/hdc/v41x/ot_hbm_idx_chunk_rt_h.sv rtl/hdc/v41x/ot_hbm_idx_chunk_rt.sv
 rtl/hdc/ot_hdc_delay.sv rtl/lib/ot_rst_relay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv
 rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv)
def=(); args=(+GAPK=2)
case $mode in
 pos) ;; gap4) args=(+GAPK=4) ;; mut) def=(-DMUT=1) ;;
 *) echo "bad mode $mode"; exit 2 ;;
esac
sha256sum "${src[@]}" > "$out/sources.sha256"
"$vl" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD "${def[@]}" \
  --top-module tb_idx_chunk_rt_h_equiv --Mdir "$out/obj" "${src[@]}" > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; exit 3; }
set +e; "$out/obj/Vtb_idx_chunk_rt_h_equiv" "${args[@]}" > "$out/run.log" 2>&1; rc=$?; set -e
grep -E "CHUNK_RT_H_EQUIV|MISMATCH" "$out/run.log" | head -8
echo "CHUNK_RT_H_MODE $mode rc=$rc"
exit $rc
