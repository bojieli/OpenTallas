#!/bin/sh
# HOLD-REPAIR 10-26: QC seam hold-cell estimate (plan model, UNCHECKED). Inputs = claude/qc-mp-region2-1026@32fa41d13d
# results/qc_mp_region2/{seam_landing,region_summary}.json (copied to in/).
set -e
D=$(cd "$(dirname "$0")" && pwd); H="$D/../../tools/die_plan/hold_demand.py"
for s in "region_flat --derate flat" "region_aocv_draft --derate aocv_draft" \
         "mesh20_flat --derate flat --mesh-skew-ps 20" "mesh20_aocv_draft --derate aocv_draft --mesh-skew-ps 20" \
         "mesh80_flat --derate flat --mesh-skew-ps 80" "mesh80_aocv_draft --derate aocv_draft --mesh-skew-ps 80"; do
  set -- $s; o=$1; shift
  python3 -I "$H" --seam-landing "$D/in/seam_landing.json" --region-summary "$D/in/region_summary.json" "$@" --out "$D/$o" > /dev/null
done
python3 -I - "$D" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); out = {}
for o in ("region_flat", "region_aocv_draft", "mesh20_flat", "mesh20_aocv_draft", "mesh80_flat", "mesh80_aocv_draft"):
    r = json.loads((d / o / "hold_demand.json").read_text())
    out[o] = dict(derate=r["derate"], mesh_skew_ps=r["mesh_skew_ps"], windows_ps=r["windows_ps"], **r["summary"]["DIE"])
(d / "scenario_summary.json").write_text(json.dumps(dict(label="UNCHECKED plan-model estimate, QC die seams", cell="HB4xp67",
                                                         scenarios=out), indent=1) + "\n")
PY
