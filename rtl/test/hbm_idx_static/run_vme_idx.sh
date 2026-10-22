#!/usr/bin/env bash
# HBM-VMEARLY-IDX 2026-10-19: compiler early issue of the IDX.INDEX operand reads on the as-built n12 reader #(171) +
# query store (tb_idx_vme_n12.sv; Verilator 5.050 = the closure daemon's pin; run on the fleet via ot-run).
#   run_vme_idx.sh OUT CASE     one case, prints its IDX_VME_N12 line; exit 0 iff it PASSes
#   run_vme_idx.sh OUT all      ia0 + ia1 must PASS with the SAME digest (bit-exact), mut1..mut3 must FAIL
#                               -> VME_IDX_BENCH PASS|FAIL
# Cases: ia0 (ISSUE_AHEAD 0 = today), ia1 (ISSUE_AHEAD 1), ia1_g16 / ia0_g16 (use pacing G 16), mut1 (slot ignored: live
#   store cleared/overwritten), mut2 (dependent record read before its producer retired: stale rows), mut3 (ISSUE_AHEAD
#   ignored: exposure check). Extra defines via VME_DEFS (e.g. "-DLB=181 -DQL=14").
set -u
root=$(cd "$(dirname "$0")/../../.." && pwd); cd "$root"
out=$(realpath -m "${1:-/tmp/vme-idx}"); case_=${2:-all}; mkdir -p "$out"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC=(rtl/hbm_accel/index/ot_hbm_idx_vm_query_static_n12.sv rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv
     rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv rtl/hbm_accel/index/ot_hbm_idx_query_static.sv
     rtl/hbm_accel/index/ot_hbm_idx_actquant_owned_native.sv rtl/hdc/ot_hdc_delay_rf.sv
     physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v
     rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_delay.sv
     rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/lib/ot_rst_relay.sv
     physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
     rtl/test/hbm_idx_static/tb_idx_vme_n12.sv)
[ -f "$out/vec/query.hex" ] || python3 tools/hbm_vmearly_idx_vectors.py "$out/vec" 4 > /dev/null || { echo "VECTORS FAIL"; exit 2; }
sim() {  # $1 name, rest: defines
  local n=$1; shift; local d="$out/$n"; mkdir -p "$d"; cp "$out/vec/query.hex" "$out/vec/gold.hex" "$d/"
  "$VL" --version > "$d/verilator_version.txt"
  sha256sum "${SRC[@]}" tools/hbm_vmearly_idx_vectors.py tools/hdc_golden_v41.py tools/hdc_golden.py > "$d/sources.sha256"
  "$VL" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD --top-module tb_idx_vme_n12 \
     --Mdir "$d/obj" -o sim "$@" ${VME_DEFS:-} "${SRC[@]}" > "$d/build.log" 2>&1 || { echo "CASE $n BUILD FAIL"; tail -20 "$d/build.log"; return 2; }
  local r; r=$( (cd "$d" && ./obj/sim) 2>&1 | tee "$d/run.log" | grep "^IDX_VME_N12" | tr '\n' ' ')
  echo "CASE $n $r"
  case "$r" in *"IDX_VME_N12 PASS"*) return 0;; *) return 1;; esac
}
run() {
  case "$1" in
    ia0) sim ia0 -DIA=0;; ia1) sim ia1 -DIA=1;; ia0_g16) sim ia0_g16 -DIA=0 -DG=16;; ia1_g16) sim ia1_g16 -DIA=1 -DG=16;;
    mut1) sim mut1 -DIA=1 -DMUT=1;; mut2) sim mut2 -DIA=1 -DMUT=2;; mut3) sim mut3 -DIA=1 -DMUT=3;;
    *) echo "unknown case $1"; return 2;;
  esac
}
if [ "$case_" != all ]; then run "$case_"; exit $?; fi
rc=0
for c in ia0 ia1 ia0_g16 ia1_g16; do run $c || rc=1; done
dg() { grep -o "digest [0-9a-f]*" "$out/$1/run.log" | head -1; }
[ -n "$(dg ia0)" ] && [ "$(dg ia0)" = "$(dg ia1)" ] && [ "$(dg ia0_g16)" = "$(dg ia1_g16)" ] && [ "$(dg ia0)" = "$(dg ia0_g16)" ] \
  && echo "DIGEST EQUAL $(dg ia0)" || { echo "DIGEST MISMATCH ia0 '$(dg ia0)' ia1 '$(dg ia1)' g16 '$(dg ia0_g16)' '$(dg ia1_g16)'"; rc=1; }
for c in mut1 mut2 mut3; do run $c; [ $? -eq 1 ] || rc=1; done
[ $rc -eq 0 ] && echo "VME_IDX_BENCH PASS" || echo "VME_IDX_BENCH FAIL"; exit $rc
