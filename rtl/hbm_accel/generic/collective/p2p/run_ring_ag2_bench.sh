#!/usr/bin/env bash
# HBM-B-RTL3c two-ring all-gather bench: RINGS=1 (one-ring reference) vs RINGS=2 at F=224/112, 3 ring-B fault
# traces, ring-B lane mutants ttl/src must FAIL.  Usage: run_ring_ag2_bench.sh OUT [ttl|src]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); ONE=${2:-}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
LIB=("$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_ring_ag_lane.sv" "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
FL=(--binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP)
build(){ "$V" "${FL[@]}" -GMUT_TTL=$2 -GMUT_SRC=$3 --top-module tb_hgi_coll_ring_ag2 --Mdir "$OUT/$1" "$P/tb_hgi_coll_ring_ag2.sv" "${LIB[@]}" > "$OUT/$1.build.log" 2>&1 || { tail -30 "$OUT/$1.build.log";exit 2; }; }
if [[ -n "$ONE" ]]; then
 case $ONE in ttl) m="1 0";; src) m="0 1";; *) echo "unknown mutant $ONE"; exit 2;; esac
 build mut_$ONE $m; "$OUT/mut_$ONE/Vtb_hgi_coll_ring_ag2" +RINGS=2 > "$OUT/mut_$ONE.log" 2>&1 || true
 grep -h 'RING_AG2' "$OUT/mut_$ONE.log" | head -5
 grep -q '^RING_AG2 PASS ' "$OUT/mut_$ONE.log"; exit $?
fi
build ag2 0 0
for R in 1 2; do for F in 224 112; do "$OUT/ag2/Vtb_hgi_coll_ring_ag2" +RINGS=$R +F=$F > "$OUT/ag2.r$R.F$F.log" 2>&1; grep RING_AG2 "$OUT/ag2.r$R.F$F.log"; grep -q '^RING_AG2 PASS ' "$OUT/ag2.r$R.F$F.log"; done; done
for s in 1 2 3; do "$OUT/ag2/Vtb_hgi_coll_ring_ag2" +RINGS=2 +fault=$s > "$OUT/ag2.f$s.log" 2>&1; grep -q '^RING_AG2 FAULT PASS ' "$OUT/ag2.f$s.log" || { cat "$OUT/ag2.f$s.log"; exit 1; }; done
echo "RING_AG2 FAULTS PASS 3"
nm=0
for m in "ttl 1 0" "src 0 1"; do
 set -- $m; build mut_$1 $2 $3
 "$OUT/mut_$1/Vtb_hgi_coll_ring_ag2" +RINGS=2 > "$OUT/mut_$1.log" 2>&1 || true
 if grep -q '^RING_AG2 PASS ' "$OUT/mut_$1.log"; then echo "RING_AG2 MUTANT $1 ESCAPED"; exit 1; fi
 echo "RING_AG2 MUTANT $1 REJECTED: $(grep -m1 'RING_AG2' "$OUT/mut_$1.log")"; nm=$((nm+1))
done
echo "RING_AG2 BENCH PASS mutants_rejected=$nm"
