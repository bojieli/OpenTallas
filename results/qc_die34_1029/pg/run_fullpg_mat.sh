#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; R=/srv/opentallas-scratch2/claude/die-qc34
docker run --rm --name dqc34-fullpg-mat-$$ --memory=56g --memory-swap=56g --cpus=4 -v "$Q:$Q" -w "$R" -e PYTHONPATH="$R/pydeps310" openroad/orfs:asap7lock bash -c "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap \"chown -R 1000:1000 $R/fullpg_mat\" EXIT; openroad -python -exit $R/src/materialize_full.py > $R/fullpg_mat/run.log 2>&1"
tail -30 $R/fullpg_mat/run.log
