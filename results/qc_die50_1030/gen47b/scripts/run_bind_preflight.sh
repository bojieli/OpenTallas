#!/bin/bash
# DIE-QC-50/gen47b: boundary bindings (bind47b.py) -> fresh constraints export (Codex export_constraints copy) ->
# fail-closed preflight (QC-IMPORT-2 preflight.py: reset keyed on bound net)
set -euo pipefail
Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47b; G=$Q/die-qc-50/gen47; S=$G/pimp_src
W=$Q/wt/die-qc-50-gen47b/results/qc_die50_1030/gen47b/scripts
INV=$G/synthP/provider_cells.json; MAP=$G/synthP/provider_mapped.json; PL=$R/inputs/plan_qc49.json
mkdir -p $R/bound/constraints
docker run --rm --name dqc50g47b-bind-$$ --memory=32g --memory-swap=32g --cpus=4 -v $Q:$Q -w $R openroad/orfs:asap7lock bash -c "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $R/bound' EXIT
openroad -python -exit $W/bind47b.py --source $R/build/clock_native.odb --stages $G/emitP/emitted/start_stages.json \
  --ctree $G/emitP/emitted/ctree.v --plan $PL --mapped $MAP --out-odb $R/bound/source_bound.odb \
  --out-bindings $R/bound/bindings.json --report $R/bound/bind_report.json > $R/bound/bind.log 2>&1
openroad -python -exit $S/export_constraints.py --source $R/bound/source_bound.odb --inventory $INV \
  --die-plan $PL --tools $R/tools_main/tools/die_plan --out $R/bound/constraints > $R/bound/constraints/export.log 2>&1"
echo BIND_EXPORT_DONE; tail -1 $R/bound/bind.log | cut -c1-600
python3 - $R/bound/constraints/constraints.json $R/bound/source_bound.odb <<'PY'
import json,sys,hashlib
p=sys.argv[1];d=json.load(open(p));d['source_odb_sha256']=hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest()
d['partition_macros']=sorted({r[0] for r in d['actual_lower_OBS']})
json.dump(d,open(p,'w'),separators=(',',':'));print('source_odb_sha256',d['source_odb_sha256'],'partition_macros',len(d['partition_macros']),'lowerOBS',len(d['actual_lower_OBS']))
PY
docker run --rm --name dqc50g47b-pre-$$ --memory=32g --memory-swap=32g --cpus=4 -v $Q:$Q -w $R python:3.12 bash -c "
pip -q install shapely >/dev/null 2>&1
python $W/preflight.py --inventory $INV --mapped $MAP --placements $G/pimpC2/proposal/placements.json \
  --proposal-constraints $G/pimp/constraints/constraints.json --fresh-constraints $R/bound/constraints/constraints.json \
  --bindings $R/bound/bindings.json --die-plan $PL --out $R/bound/preflight.json > $R/bound/preflight.log 2>&1; chown -R 1000:1000 $R/bound; true"
python3 -c "import json;d=json.load(open('$R/bound/preflight.json'));print(d['verdict'],json.dumps(d['issues']),json.dumps(d['samples'][:5])[:1500])"
