#!/bin/bash
# Owned parent pilot: invoked once export callback succeeds; stops after PLACE for actual image review.
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-s81-parent-1101
W=/srv/opentallas-scratch2/claude/wt/codex-s81-parent-1101
T=col_h10_r0_p4__t1
cd "$W"
python3 "$W/physical/die_plan/s81/cores/private_overlay_qbs20_cfg7_1101/apply.py" --root "$W" --backup "$R/parent_prior_source_views" --receipt "$R/source_overlay_receipt.json"
python3 tools/die_plan/gen.py phys "$W/physical/die_plan/s81/plan_h2_2249.json" --out "$R/gen" --types "$T" --rtl-root "$W" --kit-rtl "$T=$R/rtl_canonical/kit_rtl.f" --cland-pinslot all --hold-ff-margin 10 --max-wire-um 100 > "$R/logs/gen_parent.log" 2>&1
K="$R/gen/$T"
python3 - "$K" "$W" "$R" <<'PY'
import pathlib,sys,json,hashlib
k,w,r=map(pathlib.Path,sys.argv[1:]);d=w/'physical/die_plan/s81/cores/private_overlay_qbs20_cfg7_1101';m=json.load(open(d/'manifest.json'));hits={}
for mod,spec in m['modules'].items():
 for c in ('tt','ff'):
  n=mod+'_'+c+'.lib';p=k/'macros'/n
  assert hashlib.sha256(p.read_bytes()).hexdigest()==m['files'][mod+'/'+n], 'generated macro differs from pinned actualview:'+n
  hits[str(p)]=m['files'][mod+'/'+n]
(r/'qbs20_override.json').write_text(json.dumps(dict(pinned_profile=str(d),macro_hashes=hits),indent=2)+'\n')
PY
bash "$R/gen/run_kit.sh" "$K" place 48 8 > "$R/logs/place_parent.log" 2>&1
