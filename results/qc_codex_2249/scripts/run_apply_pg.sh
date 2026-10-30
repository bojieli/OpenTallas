#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-2249
I=$Q/codex-qc-import-0824
mkdir -p "$R/complete_pg"
python3 -c "import json;p=json.load(open('$R/pg_full_netaware/plan/access_plan.json'));assert not p['failed'];assert sum(len(x['members']) for x in p['paths'])==198762"
docker run --rm --name codexqc2249-applypg-$$ --memory=96g --memory-swap=96g --cpus=4 -v "$Q:$Q" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $R/complete_pg' EXIT; openroad -python -exit $R/src/apply_pg.py --tools $R/snapshot/tools/die_plan --helper $I/src --source $R/materialized_clock/provider.odb --plan $R/pg_full_netaware/plan --grid $R/readback/pg_rects.json --cells $Q/die-qc38/leaf_apply/provider/all_cells.json --out $R/complete_pg > $R/complete_pg/run.log 2>&1"
