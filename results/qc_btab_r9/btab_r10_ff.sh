#!/bin/bash
set -euo pipefail
K=$1
docker run --rm --name codex-btab-r10-ff --cpus 8 --memory 20g -v "$K":/work -e OT_RC_CAL=0.8,0.9 -e OT_MSCTS_SPEC=/work/mscts_spec_r10.tcl -e OT_MSCTS_ITERS=0 openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/btab_r10_ff.tcl' > "$K/r10_ff.log" 2>&1
grep -q BTAB_R10_FF_DONE "$K/r10_ff.log"
