#!/bin/bash
# CLAUDE S81-PH coll v4 regression (2026-10-07): all-gather at the S81 topk_merge (256 records) and cand.merge (1024)
# payloads, one message, no bit errors, lane channel 1 and 251 cycles, against the C8 reference engines.  v1..v3
# FAILED here (errs 8: the reference driver's blocking pointer race dropped the last record).  Negative controls:
# the old driver (TB_S81PH_MUT_REFRACE) and the unrelabelled gather beat (OT_S81PH_MUT_NOREORDER) must FAIL.
#   run_coll_regress.sh <out dir>        (from the repo root)  -> exit 0 iff 4 PASS and 2 FAIL as required
set -u
O=$1; B=rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh
G="-GPERF=1 -GNM=1 -GFIXM=1 -GNPT=1 -GEPER=0 -GSPEC=0"
rc=0
for w in 256 1024; do for c in "1 1" "251 12"; do set -- $c
  bash $B $O reg_ag${w}_b$1 $G -GFIXW=$w -GMAXW=$w -GCHB=$1 -GCHU=$2 || { echo "REGRESS FAIL ag$w b$1"; rc=1; }
done; done
for m in TB_S81PH_MUT_REFRACE OT_S81PH_MUT_NOREORDER; do
  if bash $B $O neg_$m $G -GFIXW=256 -GMAXW=256 -GCHB=1 -GCHU=1 -D$m; then echo "REGRESS FAIL: negative $m passed"; rc=1; fi
done
[ $rc = 0 ] && echo "COLL_REGRESS PASS" || echo "COLL_REGRESS FAIL"
exit $rc
