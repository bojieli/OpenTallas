#!/bin/bash
# S-QSTN (2026-10-18): per-master bench of the qfd_c_b16_dv fabric station tiles.  From the repo root (fleet via ot-run):
#   tools/qwen_cluster/bench_stn.sh pass|mut MASTER OUTDIR [CYCLES]
# MASTER = qfd_c_stn516 | qfd_c_stn514 | qfd_c_xstn | qfd_c_xstnw.  pass builds rtl/physical/qcluster/qfd_c_stn.sv, mut
# builds rtl/test/qfd_c_stn_mut_tile.sv (one fault per master); rtl/test/tb_qfd_c_stn.sv compares every output bit every
# cycle with its own cycle model and prints STN_BENCH PASS|FAIL.  Exit 0 iff the run printed STN_BENCH PASS.
set -uo pipefail
MODE=$1; M=$2; OUT=$(mkdir -p "$3" && realpath "$3"); N=${4:-20000}
V=${VERILATOR:-verilator}
case $M in qfd_c_stn516) D=M_STN516;; qfd_c_stn514) D=M_STN514;; qfd_c_xstn) D=M_XSTN;; qfd_c_xstnw) D=M_XSTNW;;
  *) echo "STN_BENCH USAGE bad master $M"; exit 2;; esac
case $MODE in pass) STN=rtl/physical/qcluster/qfd_c_stn.sv;; mut) STN=rtl/test/qfd_c_stn_mut_tile.sv;;
  *) echo "STN_BENCH USAGE bad mode $MODE"; exit 2;; esac
SRC=("$STN" rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv rtl/hdc/ot_hdc_delay.sv rtl/test/tb_qfd_c_stn.sv)
{ sha256sum "${SRC[@]}" "$0"; "$V" --version; } > "$OUT/sources.sha256"
"$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+$D \
   --top-module tb -Mdir "$OUT/obj_${MODE}_$M" "${SRC[@]}" > "$OUT/build_${MODE}_$M.log" 2>&1 \
   || { tail -n 20 "$OUT/build_${MODE}_$M.log"; echo "STN_BENCH BUILD_FAIL $M"; exit 3; }
"$OUT/obj_${MODE}_$M/Vtb" +N=$N 2>&1 | tee "$OUT/run_${MODE}_$M.log"
rm -rf "$OUT/obj_${MODE}_$M"
grep -q "^STN_BENCH PASS $M 0 errors" "$OUT/run_${MODE}_$M.log" && ! grep -q '%Error\|%Fatal' "$OUT/run_${MODE}_$M.log"
