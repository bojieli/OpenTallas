#!/usr/bin/env bash
# H-NETLIST A2P 2026-10-16: 2-stop COLL ring (N_Q=2, SW <-> NW) positive + reservation-fault scenarios + mutants.
#   run_pring_captured_nq2_suite.sh OUT     (Verilator 5.050; execute under ot-run)
set -euo pipefail
OUT=$(realpath -m "$1"); mkdir -p "$OUT"
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
build(){ local o=$1; shift
 "$V" --binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ --top-module tb_hgi_coll_pring_captured_static_nq2 --Mdir "$o/obj" "$@" \
  "$P/tb_hgi_coll_pring_captured_static_nq2.sv" "$P/ot_hgi_coll_pring_captured_static.sv" "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv" "$P/f32add.c" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv > "$o/build.log" 2>&1 || { tail -30 "$o/build.log"; echo "NQ2 BUILD_FAIL $o"; exit 2; }
}
S=$OUT/positive; mkdir -p "$S"; build "$S"
sha256sum "$P/tb_hgi_coll_pring_captured_static_nq2.sv" "$P/ot_hgi_coll_pring_captured_static.sv" "$S/obj/Vtb_hgi_coll_pring_captured_static_nq2" > "$OUT/sha256.txt"
"$S/obj/Vtb_hgi_coll_pring_captured_static_nq2" > "$S/run.log" 2>&1 || true
cat "$S/run.log"; grep -q '^CAPTURED_RING_NQ2 PASS ' "$S/run.log" || { echo 'NQ2 SUITE FAIL positive'; exit 1; }
for sc in 1 2 3 4 5 6 7 8 10 11 12; do
 "$S/obj/Vtb_hgi_coll_pring_captured_static_nq2" +fault=$sc > "$S/fault-$sc.log" 2>&1 || true
 grep -q '^CAPTURED_RING_NQ2 FAULT PASS ' "$S/fault-$sc.log" || { echo "NQ2 SUITE FAIL fault scenario $sc"; tail -3 "$S/fault-$sc.log"; exit 1; }
done
echo 'CAPTURED_RING_NQ2 FAULT SCENARIOS PASS 11'
rc=0; "$S/obj/Vtb_hgi_coll_pring_captured_static_nq2" +fault=9 > "$OUT/compiler-collision.log" 2>&1 || rc=$?
{ [ $rc != 0 ] && grep -q 'compiler injection collision' "$OUT/compiler-collision.log"; } || { echo 'NQ2 SUITE FAIL collision'; exit 1; }
for m in nq4:-GDUT_NQ=4:'unexpected schedule fault' carry:-GMUT_CARRY=1:'golden mismatch' wire:-GMUT_WIRE=1:'unexpected schedule fault' readlead:-GMUT_READ_LEAD=1:'unexpected schedule fault' tag:-GMUT_TAG=1:'unexpected schedule fault'; do
 n=${m%%:*}; r=${m#*:}; arg=${r%%:*}; pat=${r#*:}
 o=$OUT/mut_$n; mkdir -p "$o"; build "$o" "$arg"
 rc=0; "$o/obj/Vtb_hgi_coll_pring_captured_static_nq2" > "$o/run.log" 2>&1 || rc=$?
 if [ $rc != 0 ] && ! grep -q '^CAPTURED_RING_NQ2 PASS' "$o/run.log" && grep -q "$pat" "$o/run.log"; then
  echo "CAPTURED_RING_NQ2 MUTANT REJECTED $n: $(grep -m1 -o "$pat[^\"]*" "$o/run.log" | head -c 120)"
 else echo "NQ2 SUITE FAIL mutant $n survived or no witness (rc=$rc)"; tail -3 "$o/run.log"; exit 1; fi
 rm -rf "$o/obj"
done
echo 'CAPTURED_RING_NQ2 SUITE PASS'
