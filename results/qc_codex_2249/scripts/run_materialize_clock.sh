#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-2249
mkdir -p "$R/source_root" "$R/materialized_clock"
docker run --rm --name codexqc2249-clock-$$ --memory=64g --memory-swap=64g --cpus=4 -v "$Q:$Q" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $R/source_root $R/materialized_clock' EXIT; openroad -python -exit $R/src/prepare_root.py --input $R/source/provider.odb --out $R/source_root > $R/source_root/prepare.log 2>&1; openroad -exit $R/src/materialize_clock.tcl > $R/materialized_clock/run.log 2>&1"
