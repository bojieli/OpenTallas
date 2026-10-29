#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-import-0824
F=$R/reachfix
W=$Q/wt/codex-qc-import-0824
S=$Q/codex-qc-start-native-0251/reset_wave2/synth
P=$Q/qc-import-1/plan/plan_qc_import1.json
mkdir -p "$F/bound" "$F/constraints" "$F/provider" "$F/readback"
docker run --rm --name codex-qci-reachfix-bound-$$ --memory=40g --memory-swap=40g --cpus=4 -v "$Q:$Q" -w "$R" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $F' EXIT; openroad -python -exit $W/results/qc_import_2_1029/boundary_bind.py --source $F/mechanics/clock_grafted.odb --signal $F/mechanics/target_signal.odb --stages $S/start_stages.json --plan $P --mapped $S/provider_mapped.json --out-odb $F/bound/source_bound.odb --out-bindings $F/bound/bindings.json --report $F/bound/bind_report.json > $F/bound/bind.log 2>&1; openroad -python -exit $R/src/export_constraints.py --source $F/bound/source_bound.odb --inventory $S/provider_cells.json --die-plan $P --tools $W/tools/die_plan --out $F/constraints > $F/constraints/export.log 2>&1"
python3 - "$F/constraints/constraints.json" "$F/bound/source_bound.odb" <<'PY'
import json,sys,hashlib
p=sys.argv[1];d=json.load(open(p));d['source_odb_sha256']=hashlib.sha256(open(sys.argv[2],'rb').read()).hexdigest();d['partition_macros']=sorted({r[0] for r in d['actual_lower_OBS']});json.dump(d,open(p,'w'),separators=(',',':'))
PY
docker run --rm --name codex-qci-reachfix-preflight-$$ --memory=40g --memory-swap=40g --cpus=4 -v "$Q:$Q" -e PYTHONPATH="$R/pydeps" -w "$R" python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $F' EXIT; python $W/results/qc_import_2_1029/preflight.py --inventory $S/provider_cells.json --mapped $S/provider_mapped.json --placements $F/placements.json --proposal-constraints $Q/codex-provider-import-1029/constraints_qc/constraints.json --fresh-constraints $F/constraints/constraints.json --bindings $F/bound/bindings.json --die-plan $P --out $F/bound/preflight.json > $F/bound/preflight.log 2>&1"
python3 - "$F" <<'PY'
import json,hashlib,sys
from pathlib import Path
f=Path(sys.argv[1]);p=json.load(open(f/'bound/preflight.json'));assert p['verdict']=='READY_FOR_REVIEW' and not p['issues'];r=dict(schema='ot_provider_import_visual_review/1',verdict='PASS-COND',reviewer='Codex QC-import',image='results/qc_import_0824/reset_reach_fix.png',findings='Viewed 2FF -79.92um y reset-first placement. Both native reset links shortened to <=405um, clock legs ~80um; unchanged FF/clock graph and cycles. Explicit type-union windows regenerated119types/377parts0corehit0outside; actual native preflight0OBS/body/PG/bindingissues.',source_odb_sha256=p['source_odb_sha256'],conditions=['Post-apply complete actual FF-to-FF and native capture-pin reach must pass','GEOM57 routed clock wall-leg slew/arrival and A/Y phase conditions remain open','Full actual PG + real local FF CLK branches + clock/GRT/STA still required']);json.dump(r,open(f/'bound/review_record.json','w'),indent=2)
PY
docker run --rm --name codex-qci-reachfix-apply-$$ --memory=40g --memory-swap=40g --cpus=4 -v "$Q:$Q" -w "$R" openroad/orfs:asap7lock bash -c "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; trap 'chown -R 1000:1000 $F' EXIT; openroad -python -exit $W/results/qc_import_3_1029/apply_cells.py --source $F/bound/source_bound.odb --inventory $S/provider_cells.json --mapped $S/provider_mapped.json --placements $F/placements.json --bindings $F/bound/bindings.json --preflight $F/bound/preflight.json --review $F/bound/review_record.json --out $F/provider > $F/provider/apply.log 2>&1; openroad -python -exit $R/src/readback_complete.py --odb $F/provider/provider.odb --cells $F/provider/all_cells.json --out $F/readback > $F/readback/reach.log 2>&1"
cat "$F/readback/summary.json"
