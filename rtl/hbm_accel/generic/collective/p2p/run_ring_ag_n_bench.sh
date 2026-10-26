#!/usr/bin/env bash
# ELEM-GAPS/HBMN1 native ring stop bench: (1) lockstep native vs v1 stop on dense random traffic (3 seeds),
# (2) the ring all-gather (4 native stops, F=224/112, MODE 0/1) bit-exact at the compiled edges + 8 fault traces,
# (3) r5: directed rr reduce program (+rr=1, no fault, every rr publish equal) and the rr lane-read hazard (+rr=2, native
# must fault), (4) mutants TXLEAD / CW / HZ / RRLEAD / HZRR (native) + TTL / SRC / TAG (core) must FAIL.
# single-mutant mode: `run_ring_ag_n_bench.sh OUT txlead|cw|hz|rrlead|hzrr|ttl|src|tag` exits 0 only if the mutant PASSES.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
OUT=$(realpath -m "$1"); ONE=${2:-}; mkdir -p "$OUT"; cd "$ROOT"
V=${VERILATOR:-verilator}
P=rtl/hbm_accel/generic/collective/p2p
LIB=("$P/ot_hgi_coll_ring_ag_n.sv" "$P/ot_hgi_coll_ring_ag.sv" rtl/lib/ot_rst_relay.sv "$P/ot_hgi_coll_pring_static_state_capture.sv" "$P/ot_hgi_coll_pring_static.sv" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
FL=(--binary --timing -O2 -j "${JOBS:-8}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-MULTITOP)
bring(){ "$V" "${FL[@]}" -GMUT_TTL=$2 -GMUT_SRC=$3 -GMUT_TAG=$4 -GMUT_TXLEAD=$5 -GMUT_CW=$6 -GMUT_HZ=$7 -GMUT_RRLEAD=$8 --top-module tb_hgi_coll_ring_ag_n --Mdir "$OUT/$1" "$P/tb_hgi_coll_ring_ag_n.sv" "${LIB[@]}" > "$OUT/$1.build.log" 2>&1 || { tail -30 "$OUT/$1.build.log";exit 2; }; }
block(){ "$V" "${FL[@]}" -GMUT_TXLEAD=$2 -GMUT_CW=$3 -GMUT_HZ=$4 -GMUT_RRLEAD=$5 --top-module tb_hgi_coll_ring_ag_n_lock --Mdir "$OUT/$1" "$P/tb_hgi_coll_ring_ag_n_lock.sv" "${LIB[@]}" > "$OUT/$1.build.log" 2>&1 || { tail -30 "$OUT/$1.build.log";exit 2; }; }
# a mutant PASSES only if every check passes: lockstep seed 1, rr program, rr hazard, ring MODE 0 F 224, and fault trace 8
mut_run(){ local n=$1; shift; bring ring_$n "$@"; block lock_$n $4 $5 $6 $7
  ok=1
  "$OUT/lock_$n/Vtb_hgi_coll_ring_ag_n_lock" +seed=1 > "$OUT/mut_$n.lock.log" 2>&1 || true; grep -q '^RING_AG_N LOCK PASS ' "$OUT/mut_$n.lock.log" || ok=0
  "$OUT/lock_$n/Vtb_hgi_coll_ring_ag_n_lock" +rr=1 >> "$OUT/mut_$n.lock.log" 2>&1 || true; grep -q '^RING_AG_N RR PASS ' "$OUT/mut_$n.lock.log" || ok=0
  "$OUT/lock_$n/Vtb_hgi_coll_ring_ag_n_lock" +rr=2 >> "$OUT/mut_$n.lock.log" 2>&1 || true; grep -q '^RING_AG_N RR HZ PASS ' "$OUT/mut_$n.lock.log" || ok=0
  "$OUT/ring_$n/Vtb_hgi_coll_ring_ag_n" +MODE=0 > "$OUT/mut_$n.ring.log" 2>&1 || true; grep -q '^RING_AG PASS ' "$OUT/mut_$n.ring.log" || ok=0
  "$OUT/ring_$n/Vtb_hgi_coll_ring_ag_n" +MODE=0 +fault=8 > "$OUT/mut_$n.f8.log" 2>&1 || true; grep -q '^RING_AG FAULT PASS ' "$OUT/mut_$n.f8.log" || ok=0
  # Consume all inputs: head can cause SIGPIPE before the mutant verdict.
  awk '/RING_AG/ { if (++shown <= 8) print }' "$OUT/mut_$n.lock.log" "$OUT/mut_$n.ring.log" "$OUT/mut_$n.f8.log"
  if [[ $ok == 1 ]]; then echo "RING_AG_N MUTANT $n PASSED"; return 0; else echo "RING_AG_N MUTANT $n FAILED"; return 1; fi; }
mspec(){ case $1 in txlead) echo "0 0 0 1 0 0 0";; cw) echo "0 0 0 0 1 0 0";; hz) echo "0 0 0 0 0 1 0";; rrlead) echo "0 0 0 0 0 0 1";; hzrr) echo "0 0 0 0 0 2 0";;
  ttl) echo "1 0 0 0 0 0 0";; src) echo "0 1 0 0 0 0 0";; tag) echo "0 0 1 0 0 0 0";; *) echo bad;; esac; }
if [[ -n "$ONE" ]]; then m=$(mspec $ONE); [[ $m == bad ]] && { echo "unknown mutant $ONE"; exit 2; }; mut_run $ONE $m; exit $?; fi
block lock 0 0 0 0
for s in 1 2 3; do "$OUT/lock/Vtb_hgi_coll_ring_ag_n_lock" +seed=$s > "$OUT/lock.s$s.log" 2>&1; cat "$OUT/lock.s$s.log" | grep RING_AG_N; grep -q '^RING_AG_N LOCK PASS ' "$OUT/lock.s$s.log"; done
"$OUT/lock/Vtb_hgi_coll_ring_ag_n_lock" +rr=1 > "$OUT/lock.rr1.log" 2>&1; grep RING_AG_N "$OUT/lock.rr1.log"; grep -q '^RING_AG_N RR PASS ' "$OUT/lock.rr1.log"
"$OUT/lock/Vtb_hgi_coll_ring_ag_n_lock" +rr=2 > "$OUT/lock.rr2.log" 2>&1; grep RING_AG_N "$OUT/lock.rr2.log"; grep -q '^RING_AG_N RR HZ PASS ' "$OUT/lock.rr2.log"
bring ring 0 0 0 0 0 0 0
for M in 0 1; do for F in 224 112; do "$OUT/ring/Vtb_hgi_coll_ring_ag_n" +MODE=$M +F=$F > "$OUT/ring.m$M.F$F.log" 2>&1; grep RING_AG "$OUT/ring.m$M.F$F.log"; grep -q '^RING_AG PASS ' "$OUT/ring.m$M.F$F.log"; done; done
for M in 0 1; do for s in 1 2 3 4 5 6 7 8; do "$OUT/ring/Vtb_hgi_coll_ring_ag_n" +MODE=$M +fault=$s > "$OUT/ring.m$M.f$s.log" 2>&1; grep -q '^RING_AG FAULT PASS ' "$OUT/ring.m$M.f$s.log" || { cat "$OUT/ring.m$M.f$s.log"; exit 1; }; done; done
echo "RING_AG_N FAULTS PASS 16"
nm=0
for n in txlead cw hz rrlead hzrr ttl src tag; do
 if mut_run $n $(mspec $n) > "$OUT/mut_$n.log" 2>&1; then cat "$OUT/mut_$n.log"; echo "RING_AG_N MUTANT $n ESCAPED"; exit 1; fi
 echo "RING_AG_N MUTANT $n REJECTED: $(grep -m1 'RING_AG' "$OUT/mut_$n.log")"; nm=$((nm+1))
done
echo "RING_AG_N BENCH PASS mutants_rejected=$nm"
