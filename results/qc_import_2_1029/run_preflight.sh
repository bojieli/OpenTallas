#!/bin/bash
# QC-IMPORT-2: re-export actual constraints from the boundary-bound fresh source and run the fail-closed provider
# preflight (branch copy with the reset check keyed on the bound net, --die-plan = plan of record).
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/qc-import-1
WT=$Q/wt/qc-import-2
PI=$Q/codex-provider-import-1029
INV=$Q/codex-qc-start-native-0251/reset_wave2/synth/provider_cells.json
MAP=$Q/codex-qc-start-native-0251/reset_wave2/synth/provider_mapped.json
mkdir -p $R/bound/constraints
docker run --rm --name qci2-export-$$ --memory=40g --memory-swap=40g --cpus=4 -v $Q:$Q -w $R openroad/orfs:asap7lock bash -c "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -python -exit $PI/src/export_constraints.py --source $R/bound/source_bound.odb --inventory $INV \
  --die-plan $R/plan/plan_qc_import1.json --tools $WT/tools/die_plan --out $R/bound/constraints > $R/bound/constraints/export.log 2>&1
rc=\$?; chown -R $(id -u):$(id -g) $R/bound; exit \$rc"
python3 - $R/bound/constraints/constraints.json $R/bound/source_bound.odb <<'PY'
import json,sys,hashlib
p=sys.argv[1];d=json.load(open(p));d['source_odb_sha256']=hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest()
d['partition_macros']=sorted({r[0] for r in d['actual_lower_OBS']})
json.dump(d,open(p,'w'),separators=(',',':'));print('source_odb_sha256',d['source_odb_sha256'],'partition_macros',len(d['partition_macros']))
PY
docker run --rm --name qci2-preflight-$$ --memory=40g --memory-swap=40g --cpus=4 -v $Q:$Q -w $R python:3.12 bash -c "
pip -q install shapely >/dev/null 2>&1
python $WT/results/qc_import_2_1029/preflight.py --inventory $INV --mapped $MAP --placements $PI/proposal_qc_wave2_compact/placements.json \
  --proposal-constraints $PI/constraints_qc/constraints.json --fresh-constraints $R/bound/constraints/constraints.json \
  --bindings $R/bound/bindings.json --die-plan $R/plan/plan_qc_import1.json --out $R/bound/preflight.json > /dev/null; rc=\$?; chown -R $(id -u):$(id -g) $R/bound; true"
python3 -c "import json;d=json.load(open('$R/bound/preflight.json'));print(d['verdict'],json.dumps(d['issues']),json.dumps(d['samples'][:5]))"
