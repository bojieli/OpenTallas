#!/bin/bash
# QC-IMPORT-2 step 1: boundary graft + bindings on the fresh native source.
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/qc-import-1
WT=$Q/wt/qc-import-2
S=$Q/codex-qc-start-native-0251/reset_wave2/synth
mkdir -p $R/bound
docker run --rm --name qci2-bind-$$ --memory=40g --memory-swap=40g --cpus=4 -v $Q:$Q -w $R openroad/orfs:asap7lock bash -c "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -python -exit $WT/results/qc_import_2_1029/boundary_bind.py --source $R/mechanics/clock_grafted.odb \
  --signal $R/mechanics/target_signal.odb --stages $S/start_stages.json --plan $R/plan/plan_qc_import1.json \
  --mapped $S/provider_mapped.json --out-odb $R/bound/source_bound.odb --out-bindings $R/bound/bindings.json \
  --report $R/bound/bind_report.json > $R/bound/bind.log 2>&1; rc=\$?; chown -R $(id -u):$(id -g) $R/bound; exit \$rc"
tail -3 $R/bound/bind.log
