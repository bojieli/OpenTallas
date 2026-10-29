#!/usr/bin/env bash
# HBM-CORES-REBAL-9: rebuild the m5w1 token TB with the +MUT_ADDR_EDGE opt-in (9b@e10cd90411), then run in parallel
# POS (no plusarg) and ADDR aimed at the derived first live line. Runs inside ot-run on epyc2 from the worktree.
set -uo pipefail
R=/srv/opentallas-scratch2/claude/hbm-cores-rebal-9; O=$R/tok_m5w1a
SU_TOP_MLAT=5 SU_TOP_WCOPY=1 SU_TOP_JOBS=8 /usr/bin/time -v -o $O/build.time bash tools/hbm_static/su_multirate_native_run.sh $O build || { echo TOK_ADDR_BUILD_FAIL; exit 1; }
E=$(python3 $R/mut_addr_edge.py $O/vec/serial/expected.mem); echo "MUT_ADDR_EDGE=$E"
bash $R/tok_phase.sh $O POS & MUT_ADDR_EDGE=$E bash $R/tok_phase.sh $O ADDR & wait
cat $O/phase_*.res
