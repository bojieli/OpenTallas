#!/bin/bash
set -euo pipefail
cd /
R=/srv/opentallas-scratch2/claude/codex-s81-rck-0222/work
D=$R/results/s81_rck_11_reform_1108/tx_feedback
python3 -I "$R/physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py" --module ot_s81_rck_tx --recipes "$D/recipes.json" --plan "$D/plan_draft.json" --out /srv/opentallas-scratch2/claude/codex-s81-rck-0222/kits --suffix vD_region
K=/srv/opentallas-scratch2/claude/codex-s81-rck-0222/kits/ot_s81_rck_tx_vD_region
cp "$D/feedback_region.tcl" "$D/feedback_pre_gpl.tcl" "$D/feedback_pre_dpl.tcl" "$K/"
python3 -I - "$K" "$D" <<'PY'
import hashlib,json,sys
from pathlib import Path
k,d=map(Path,sys.argv[1:]);names=['feedback_region.tcl','feedback_pre_gpl.tcl','feedback_pre_dpl.tcl']
(k/'physical_form.json').write_text(json.dumps(dict(form='modeled parity-feedback placement fence',new_pin_cycles=0,region_um=[45.36,45.36,136.08,136.08],source_files={n:hashlib.sha256((d/n).read_bytes()).hexdigest() for n in names}),indent=1)+'\n')
PY
