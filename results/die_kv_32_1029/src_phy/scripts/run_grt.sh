#!/bin/bash
# DIE-KV-32-SRC (copied from DIE-KV-31-SRC step 3): loaded die GRT0 incl clock (grt_loaded.tcl) on access/access.odb. Heavy: ot-run --mem 256 --threads 16.
set -uo pipefail
N=/srv/opentallas-scratch2/claude/die-kv-32-1029/src_phy; mkdir -p $N/grt
echo "start $(date -Is) host $(hostname)" > $N/grt/run.txt
docker run --rm --name dkv32-grt --memory=256g --memory-swap=256g --cpus=16 -v $N:/n openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 16 -exit /n/grt_loaded.tcl > /n/grt/grt.log 2>&1; rc=\$?; echo EXIT \$rc >> /n/grt/grt.log; chown -R 1000:1000 /n/grt; exit \$rc"
rc=$?; echo "end $(date -Is) exit $rc" >> $N/grt/run.txt; exit $rc
