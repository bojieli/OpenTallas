#!/usr/bin/env bash
# HBM-B-RTL3 ring all-gather bench: (1) ring_v5 regression suite through the adapter (AG=0 and AG=1),
# (2) all-gather F=224 and F=112 + 7 reservation-fault traces, (3) mutants TTL/SRC/TAG/AG0 must FAIL.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); ONE=${2:-}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
LIB=("$P/ot_hgi_coll_ring_ag.sv" "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
FL=(--binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP)
build(){ "$V" "${FL[@]}" -GMUT_TTL=$2 -GMUT_SRC=$3 -GMUT_TAG=$4 -GAG=$5 --top-module tb_hgi_coll_ring_ag --Mdir "$OUT/$1" "$P/tb_hgi_coll_ring_ag.sv" "${LIB[@]}" > "$OUT/$1.build.log" 2>&1 || { tail -30 "$OUT/$1.build.log";exit 2; }; }
# single-mutant mode (expect=fail bench): `run_ring_ag_bench.sh OUT ttl|src|tag|ag0` exits 0 only if the mutant PASSES
if [[ -n "$ONE" ]]; then
 case $ONE in ttl) m="1 0 0 1";; src) m="0 1 0 1";; tag) m="0 0 1 1";; ag0) m="0 0 0 0";; *) echo "unknown mutant $ONE"; exit 2;; esac
 build mut_$ONE $m; "$OUT/mut_$ONE/Vtb_hgi_coll_ring_ag" +MODE=0 > "$OUT/mut_$ONE.log" 2>&1 || true
 grep -h 'RING_AG' "$OUT/mut_$ONE.log" | head -5
 grep -q '^RING_AG PASS ' "$OUT/mut_$ONE.log"; exit $?
fi
for ag in 0 1; do
 o=$OUT/v5_ag$ag
 "$V" "${FL[@]}" +define+RING_AG=$ag --top-module tb_hgi_coll_pring_captured_static --Mdir "$o" \
  "$P/tb_hgi_coll_pring_captured_static.sv" "$P/tb_hgi_coll_ring_ag_v5_adapter.sv" "${LIB[@]}" "$P/f32add.c" > "$o.build.log" 2>&1 || { tail -30 "$o.build.log";exit 2; }
 "$o/Vtb_hgi_coll_pring_captured_static" > "$o.run.log" 2>&1; cat "$o.run.log"; grep -q '^CAPTURED_RING PASS ' "$o.run.log"
 for s in 1 2 3 4 5 6 7 8 10 11 12; do
  "$o/Vtb_hgi_coll_pring_captured_static" +fault=$s > "$o.f$s.log" 2>&1; grep -q '^CAPTURED_RING FAULT PASS ' "$o.f$s.log" || { cat "$o.f$s.log"; exit 1; }
 done
 echo "RING_V5_REGRESSION PASS ag=$ag faults=11"
done
build ag 0 0 0 1
for M in 0 1; do for F in 224 112; do "$OUT/ag/Vtb_hgi_coll_ring_ag" +MODE=$M +F=$F > "$OUT/ag.m$M.F$F.log" 2>&1; grep RING_AG "$OUT/ag.m$M.F$F.log"; grep -q '^RING_AG PASS ' "$OUT/ag.m$M.F$F.log"; done; done
for M in 0 1; do for s in 1 2 3 4 5 6 7; do "$OUT/ag/Vtb_hgi_coll_ring_ag" +MODE=$M +fault=$s > "$OUT/ag.m$M.f$s.log" 2>&1; grep -q '^RING_AG FAULT PASS ' "$OUT/ag.m$M.f$s.log" || { cat "$OUT/ag.m$M.f$s.log"; exit 1; }; done; done
echo "RING_AG FAULTS PASS 14"
nm=0
for m in "ttl 1 0 0 1" "src 0 1 0 1" "tag 0 0 1 1" "ag0 0 0 0 0"; do
 set -- $m; build mut_$1 $2 $3 $4 $5
 "$OUT/mut_$1/Vtb_hgi_coll_ring_ag" +MODE=0 > "$OUT/mut_$1.log" 2>&1 || true
 if grep -q '^RING_AG PASS ' "$OUT/mut_$1.log"; then echo "RING_AG MUTANT $1 ESCAPED"; exit 1; fi
 echo "RING_AG MUTANT $1 REJECTED: $(grep -m1 'RING_AG' "$OUT/mut_$1.log")"; nm=$((nm+1))
done
echo "RING_AG BENCH PASS mutants_rejected=$nm"
