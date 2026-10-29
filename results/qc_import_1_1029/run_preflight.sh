#!/bin/bash
# QC-IMPORT-1: export actual constraints from the fresh native source and run the fail-closed provider preflight
# (Codex results/provider_import_1029 tools, unchanged). Bindings are still empty -> expected HOLD on boundary ports;
# the point is the fresh-source OBS/body checks.
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/qc-import-1
WT=$Q/wt/qc-import-1
PI=$Q/codex-provider-import-1029
INV=$Q/codex-qc-start-native-0251/reset_wave2/synth/provider_cells.json
MAP=$Q/codex-qc-start-native-0251/reset_wave2/synth/provider_mapped.json
mkdir -p $R/constraints $R/preflight
docker run --rm --name qcimp1-export-$$ --memory=40g --memory-swap=40g --cpus=4 -v $Q:$Q -w $R openroad/orfs:asap7lock bash -c "
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
openroad -python -exit $PI/src/export_constraints.py --source $R/mechanics/clock_grafted.odb --inventory $INV \
  --die-plan $R/plan/plan_qc_import1.json --tools $WT/tools/die_plan --out $R/constraints > $R/constraints/export.log 2>&1
rc=\$?; chown -R $(id -u):$(id -g) $R/constraints; exit \$rc"
tail -12 $R/constraints/export.log
python3 - $R/constraints/constraints.json $R/mechanics/clock_grafted.odb <<'PY'
import json,sys,hashlib
p=sys.argv[1];d=json.load(open(p));d['source_odb_sha256']=hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest()
d['partition_macros']=sorted({r[0] for r in d['actual_lower_OBS']})
json.dump(d,open(p,'w'),separators=(',',':'));print('source_odb_sha256',d['source_odb_sha256'],'partition_macros',len(d['partition_macros']))
PY
echo '{"schema":"ot_provider_boundary_bindings/1","source_odb_sha256":null,"ports":{}}' > $R/preflight/bindings_empty.json
docker run --rm --name qcimp1-preflight-$$ --memory=40g --memory-swap=40g --cpus=4 -v $Q:$Q -w $R python:3.12 bash -c "
pip -q install shapely >/dev/null 2>&1
python $PI/src/preflight.py --inventory $INV --mapped $MAP --placements $PI/proposal_qc_wave2_compact/placements.json \
  --proposal-constraints $PI/constraints_qc/constraints.json --fresh-constraints $R/constraints/constraints.json \
  --bindings $R/preflight/bindings_empty.json --out $R/preflight/preflight_nobind.json; chown -R $(id -u):$(id -g) $R/preflight; true"
python3 -c "import json;d=json.load(open('$R/preflight/preflight_nobind.json'));print(d['verdict'],json.dumps(d['issues']))"
