#!/bin/bash
# QC-IMPORT-3 step 2: apply_cells (codex/provider-import-1029 apply_cells.py, copied) on the bound fresh source.
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/qc-import-1
W=$Q/wt/qc-import-3/results/qc_import_3_1029
PI=$Q/codex-provider-import-1029
S=$Q/codex-qc-start-native-0251/reset_wave2/synth
mkdir -p $R/provider
docker run --rm --name qci3-apply-$$ --memory=40g --memory-swap=40g --cpus=4 -v $Q:$Q -w $R openroad/orfs:asap7lock bash -c "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -python -exit $W/apply_cells.py --source $R/bound/source_bound.odb --inventory $S/provider_cells.json --mapped $S/provider_mapped.json \
  --placements $PI/proposal_qc_wave2_compact/placements.json --bindings $R/bound/bindings.json --preflight $R/bound/preflight.json \
  --review $R/bound/review_record.json --out $R/provider > $R/provider/apply.log 2>&1; rc=\$?; chown -R $(id -u):$(id -g) $R/provider; exit \$rc"
tail -20 $R/provider/apply.log
