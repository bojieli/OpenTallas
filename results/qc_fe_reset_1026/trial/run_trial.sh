#!/bin/bash
# Diagnostic source-aligned FE reset trial: no new ELAB, no CTS/routes or freeze.
set -euo pipefail
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
W=/srv/opentallas-scratch2/claude/wt/codex-qc-fe-trial-1026
R=/srv/opentallas-scratch2/claude/codex-qc-fe-trial-1026
mkdir -p "$R/bind"
python3 - "$W" "$R" <<'PY'
import json,sys,hashlib
from pathlib import Path
w,r=map(Path,sys.argv[1:]);sys.path.insert(0,str(w/'tools/die_plan'));import fup_reset_groups as F
raw=json.loads((w/'physical/die_plan/qwen_compute/die_plan.json').read_text())
ab=json.loads((w/'physical/die_plan/qwen_compute/bind/asbuilt_meth_fixed_su.json').read_text())
raw,ab,rec=F.apply_fe_reset_overlay(raw,ab,enabled=True,overlay=F.load_fe_reset_overlay(w/'results/qc_fe_reset_1026/compose_overlay.json'))
removed={}
for k in ['land_align','land_r8','land_r8_extra','land_pad_tree','extra','param_regen']:
 if k in ab:removed[k]=True;ab.pop(k)
p=w/'physical/die_plan/qwen_compute/fe_reset_probe.json';p.write_text(json.dumps(raw,indent=1)+'\n')
a=w/'physical/die_plan/qwen_compute/bind/asbuilt_fe_reset_probe.json';a.write_text(json.dumps(ab,indent=1)+'\n')
rec.update(elab='reused profile431a17208 bind_descend/asbuilt.json; unchanged original FUP/E5/top source',scope='diagnostic FE only; no old R8/land calendars reused',removed_probe_fields=removed,plan_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(r/'profile.json').write_text(json.dumps(rec,indent=1)+'\n')
PY
P=$W/physical/die_plan/qwen_compute/fe_reset_probe.json
A=$W/physical/die_plan/qwen_compute/bind/asbuilt_fe_reset_probe.json
python3 -I "$W/tools/die_plan/bind.py" bind "$P" --asbuilt "$A" --out "$R/bind" --mem 64 > "$R/bind.log" 2>&1
python3 -I "$W/tools/die_plan/bind.py" kit-rtl "$P" --asbuilt "$A" --out "$R/bind" --type slw_fe_v1 > "$R/kit_rtl.log" 2>&1
python3 -I "$W/tools/die_plan/gen.py" phys "$P" --out "$R/gen" --types slw_fe_v1 --rtl-root "$W" --kit-rtl "slw_fe_v1=$R/bind/kit_rtl/slw_fe_v1/kit_rtl.f" --util 0.01212 --hold-ff-margin 5 > "$R/gen.log" 2>&1
# Pre-synthesis LEC is part of the generated runner. Keep its result and all port gates.
bash "$R/gen/run_kit.sh" "$R/gen/slw_fe_v1" place 32 16 > "$R/place.log" 2>&1
