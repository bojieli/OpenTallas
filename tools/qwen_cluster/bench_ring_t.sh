#!/bin/bash
# QW-CB16REG (2026-10-20): bench of the hardened landing ring tiles.  From the repo root (fleet via ot-run):
#   tools/qwen_cluster/bench_ring_t.sh pass|mut MASTER OUTDIR [CYCLES]
# MASTER = qfd_c_ringx516 | qfd_c_ringx514 (each followed by its qfd_c_stn<W> output station).  mut builds a copy of qfd_c_ring_t.sv whose fixed tops read slot K = 3 (one
# edge late: a calendar slip); rtl/test/tb_qfd_c_ring_t.sv checks every output bit every cycle against its cycle model
# and the soft pair.  Exit 0 iff the run printed RING_BENCH PASS.
set -uo pipefail
MODE=$1; M=$2; OUT=$(mkdir -p "$3" && realpath "$3"); N=${4:-20000}
V=${VERILATOR:-verilator}
case $M in qfd_c_ringx516) D=M_RING516;; qfd_c_ringx514) D=M_RING514;; *) echo "RING_BENCH USAGE bad master $M"; exit 2;; esac
RING=rtl/physical/qcluster/qfd_c_ring_t.sv
case $MODE in pass) ;; mut) sed 's/\.D(4), \.K(2)) u_ring/.D(4), .K(3)) u_ring/' $RING > "$OUT/qfd_c_ring_t_mut.sv"; RING="$OUT/qfd_c_ring_t_mut.sv";;
  *) echo "RING_BENCH USAGE bad mode $MODE"; exit 2;; esac
SRC=(rtl/physical/qcluster/qfd_c_land_k.sv rtl/physical/qcluster/qfd_c_stn.sv "$RING" rtl/test/tb_qfd_c_ring_t.sv)
{ sha256sum "${SRC[@]}" "$0"; "$V" --version; } > "$OUT/sources.sha256"
"$V" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN +define+$D \
   --top-module tb -Mdir "$OUT/obj_${MODE}_$M" "${SRC[@]}" > "$OUT/build_${MODE}_$M.log" 2>&1 \
   || { tail -n 20 "$OUT/build_${MODE}_$M.log"; echo "RING_BENCH BUILD_FAIL $M"; exit 3; }
"$OUT/obj_${MODE}_$M/Vtb" +N=$N 2>&1 | tee "$OUT/run_${MODE}_$M.log"
rm -rf "$OUT/obj_${MODE}_$M"
grep -q "^RING_BENCH PASS $M 0 errors" "$OUT/run_${MODE}_$M.log" && ! grep -q '%Error\|%Fatal' "$OUT/run_${MODE}_$M.log"
