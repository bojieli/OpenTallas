#!/usr/bin/env bash
# HBM-RTL4 ring-B die block bench (ot_hgi_coll_ring_b_stop = reset relay + command pin register + gather-only lane):
# tb_hgi_coll_ring_ag2 BLK=1 -> RINGS=1 (one-ring reference, ring B idle) vs RINGS=2 at F=224/112, bit-exact publish
# at the compiled edge; 3 ring-B fault traces; mutants ttl/src (lane) and nopipe (block without its pin register,
# commands still issued one edge early) must FAIL.  Usage: run_ring_b_stop_bench.sh OUT [ttl|src|nopipe]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); ONE=${2:-}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
LIB=("$P/ot_hgi_coll_ring_b_stop.sv" rtl/lib/ot_rst_relay.sv "$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
FL=(--binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP)
build(){ "$V" "${FL[@]}" -GBLK=1 -GMUT_TTL=$2 -GMUT_SRC=$3 -GBLK_PIPE=$4 --top-module tb_hgi_coll_ring_ag2 --Mdir "$OUT/$1" "$P/tb_hgi_coll_ring_ag2.sv" "${LIB[@]}" > "$OUT/$1.build.log" 2>&1 || { tail -30 "$OUT/$1.build.log";exit 2; }; }
mut(){ case $1 in ttl) echo "1 0 1";; src) echo "0 1 1";; nopipe) echo "0 0 0";; *) echo "unknown mutant $1" >&2; exit 2;; esac; }
if [[ -n "$ONE" ]]; then
 build mut_$ONE $(mut $ONE); "$OUT/mut_$ONE/Vtb_hgi_coll_ring_ag2" +RINGS=2 > "$OUT/mut_$ONE.log" 2>&1 || true
 grep -h 'RING_AG2' "$OUT/mut_$ONE.log" | head -5
 if grep -q '^RING_AG2 PASS ' "$OUT/mut_$ONE.log"; then echo "RING_B_STOP MUTANT $ONE ESCAPED"; exit 0; fi
 echo "RING_B_STOP FAIL mutant=$ONE: $(grep -m1 'RING_AG2' "$OUT/mut_$ONE.log")"; exit 1
fi
build blk 0 0 1
for R in 1 2; do for F in 224 112; do "$OUT/blk/Vtb_hgi_coll_ring_ag2" +RINGS=$R +F=$F > "$OUT/blk.r$R.F$F.log" 2>&1; grep RING_AG2 "$OUT/blk.r$R.F$F.log"; grep -q '^RING_AG2 PASS ' "$OUT/blk.r$R.F$F.log"; done; done
for s in 1 2 3; do "$OUT/blk/Vtb_hgi_coll_ring_ag2" +RINGS=2 +fault=$s > "$OUT/blk.f$s.log" 2>&1; grep -q '^RING_AG2 FAULT PASS ' "$OUT/blk.f$s.log" || { cat "$OUT/blk.f$s.log"; exit 1; }; done
echo "RING_B_STOP FAULTS PASS 3"
nm=0
for m in ttl src nopipe; do
 build mut_$m $(mut $m)
 "$OUT/mut_$m/Vtb_hgi_coll_ring_ag2" +RINGS=2 > "$OUT/mut_$m.log" 2>&1 || true
 if grep -q '^RING_AG2 PASS ' "$OUT/mut_$m.log"; then echo "RING_B_STOP MUTANT $m ESCAPED"; exit 1; fi
 echo "RING_B_STOP MUTANT $m REJECTED: $(grep -m1 'RING_AG2' "$OUT/mut_$m.log")"; nm=$((nm+1))
done
echo "RING_B_STOP BENCH PASS mutants_rejected=$nm"
