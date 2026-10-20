#!/usr/bin/env bash
# HBM-COLLQ/X x-load PRE-QUANTISED mode bench: cl2p fmt 3 (golden pre image) vs cl2 fmt 1 (FP32 image), every xw beat
# identical D = P S Es + 3 edges later.  usage: run_xload_preq.sh OUT [MUT]   (MUT 7 / 8 must FAIL)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); OUT=$(realpath -m "$1"); MUT=${2:-0}; mkdir -p "$OUT"; cd "$ROOT"
[[ -d $HOME/.local/opentallas-tools/verilator-5.050/bin ]] && export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
[[ -f "$OUT/vec/cases.txt" ]] || PYTHONPATH=tools python3 tools/hgi_sim/xload_preq_vectors_1018.py "$OUT/vec"
P=rtl/hbm_accel/generic/peers
B="$OUT/obj_m$MUT"
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -j ${JOBS:-16} -GMUT=$MUT --top-module tb_hgi_xload_preq --Mdir "$B" \
  rtl/lib/ot_rst_relay.sv $P/ot_hgi_sm_xload_static_cl2.sv $P/ot_hgi_sm_xload_static_cl2p.sv \
  rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv \
  physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_tree13.sv physical/hbm_xp_aq_tree13_1014/ot_hbm_xp_aq_scale13.sv \
  rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
  rtl/hbm_accel/generic/adapters/tb/tb_hgi_xload_preq.sv > "$OUT/build_m$MUT.log" 2>&1 || { tail -40 "$OUT/build_m$MUT.log"; exit 2; }
if [[ $MUT == 0 ]]; then "$B/Vtb_hgi_xload_preq" +DIR="$OUT/vec" +SAME=1 > "$OUT/preq_same.log" 2>&1 || true
 grep XLOAD_PREQ "$OUT/preq_same.log" | tail -3; grep -q '^XLOAD_PREQ PASS' "$OUT/preq_same.log" || { echo "XLOAD_PREQ fmt1 regression FAIL"; exit 1; }; fi
"$B/Vtb_hgi_xload_preq" +DIR="$OUT/vec" > "$OUT/preq_m$MUT.log" 2>&1 || true
grep XLOAD_PREQ "$OUT/preq_m$MUT.log" | tail -14
grep -q '^XLOAD_PREQ PASS' "$OUT/preq_m$MUT.log"
