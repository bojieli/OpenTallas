#!/usr/bin/env bash
set -euo pipefail
R=/srv/opentallas-scratch/claude/closure-loop/hcoll_ring_ag_ctln_1018-r5c-4c84aa2ed
D=/srv/opentallas-scratch/claude/ringag-recovery-1019
# Only replay existing binaries produced by the pinned source, never pretend to compile.
source <(sed '/^if \[\[ -n "\$ONE"/,$d' "$D/rtl/hbm_accel/generic/collective/p2p/run_ring_ag_n_bench.sh") "$R/bench/ring_ag_n"
bring(){ test -x "$OUT/$1/Vtb_hgi_coll_ring_ag_n"; }
block(){ test -x "$OUT/$1/Vtb_hgi_coll_ring_ag_n_lock"; }
for s in 1 2 3; do "$OUT/lock/Vtb_hgi_coll_ring_ag_n_lock" +seed=$s > "$D/lock.$s.log"; grep '^RING_AG_N LOCK PASS ' "$D/lock.$s.log"; done
for m in 0 1; do for f in 224 112; do "$OUT/ring/Vtb_hgi_coll_ring_ag_n" +MODE=$m +F=$f > "$D/ring.$m.$f.log"; grep '^RING_AG PASS ' "$D/ring.$m.$f.log"; done; done
for n in txlead cw hz rrlead hzrr ttl src tag; do
 set +e
 (set -e; mut_run "$n" $(mspec "$n")) > "$D/mut_$n.log" 2>&1
 rc=$?
 set -e
 test "$rc" = 1
 grep "^RING_AG_N MUTANT $n FAILED$" "$D/mut_$n.log"
 # Preserve actual semantic mismatch, never qualify an infrastructure error.
 grep -E 'RING_AG_N LOCK mismatch|RING_AG FAIL|RING_AG_N RR (FAIL|mismatch)|RING_AG_N RR HZ FAIL|Assertion failed.*RING_AG' "$OUT/mut_$n.lock.log" "$OUT/mut_$n.ring.log" "$OUT/mut_$n.f8.log" > "$D/assertion_$n.log"
done
echo 'RING_AG_N REPLAY PASS positive_configurations=7 mutants_rejected=8 source=4c84aa2ed'
