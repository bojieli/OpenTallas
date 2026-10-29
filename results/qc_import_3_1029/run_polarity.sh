#!/bin/bash
# QC-IMPORT-3 QC-001 clock polarity check on the bound source (diagnostic probe, docker 24g cap)
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; R=/srv/opentallas-scratch2/claude/qc-import-1; W=/srv/opentallas-scratch2/claude/wt/qc-import-3; C=/srv/opentallas-scratch2/claude/codex-qc-start-native-0251
docker run --rm --name qci3-pol-$$ --memory=24g --memory-swap=24g --cpus=2 -v $Q:$Q -w $R openroad/orfs:asap7lock bash -c "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -python -exit $W/results/qc_import_3_1029/polarity_check.py --odb $R/bound/source_bound.odb --stages $C/reset_wave2/synth/start_stages.json  --bindings $R/bound/bindings.json --bind $C/perimeter1/bind.json --mapped-v $C/reset_wave2/synth/provider_mapped.v --out $R/polarity/polarity.json; rc=\$?; chown -R 1000:1000 $R/polarity; exit \$rc"
