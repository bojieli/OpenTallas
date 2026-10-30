#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-2249
mkdir -p "$R/grt_trial"
python3 -c "import json;p=json.load(open('$R/complete_pg/receipt.json'));assert p['contacts']==198762 and p['non_pg_before_sha256']==p['non_pg_after_sha256'];json.dump(dict(trial=True,reason='PG_IR_NOT_RUN',congestion_iterations_requested=50,clock_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,review='results/geom_review/qc_native_2249/review.json'),open('$R/grt_trial/meta.json','w'),indent=2)"
docker run --rm --name codexqc2249-grttrial-$$ --memory=192g --memory-swap=192g --cpus=16 -v "$Q:$Q" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $R/grt_trial' EXIT; openroad -threads 16 -exit $R/src/grt_trial.tcl > $R/grt_trial/run.log 2>&1; openroad -python -exit $R/src/clock_preservation.py --tools $R/snapshot/tools/die_plan --source $R/complete_pg/provider.odb --routed $R/grt_trial/routed.odb --out $R/grt_trial/clock_preservation.json > $R/grt_trial/preserve.log 2>&1"
