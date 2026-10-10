#!/bin/bash
# bf-icg 2026-10-08: RECUT=2 transaction-exact gates for QZE=1 and CG=0 (shared prepared package, built from a clean worktree)
cd /srv/opentallas-scratch/claude/bficg/wt
B=/srv/opentallas-scratch/claude/bficg
( python3 tools/s81/bf_txn_bench.py --variant recut --level 2 --prep $B/prep --work $B/qze --jobs 8 --params QZE=1 --mutant mutant_ze=QZE_MUTANT_GO --mutant mutant_z=QZ_MUTANT_Z > $B/qze.log 2>&1; echo "qze rc=$?" >> $B/STATUS ) &
( python3 tools/s81/bf_txn_bench.py --variant recut --level 2 --prep $B/prep --work $B/cg0 --jobs 8 --params CG=0 > $B/cg0.log 2>&1; echo "cg0 rc=$?" >> $B/STATUS ) &
wait; echo DONE >> $B/STATUS
