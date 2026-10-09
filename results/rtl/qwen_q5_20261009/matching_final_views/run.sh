#!/bin/bash
set -euo pipefail
RUN=/srv/opentallas-scratch/claude/closure-loop/qfd_q5_landing_ecc-ab9c785e9-wc-ttalias
OUT=/srv/opentallas-scratch/codex/qwen-q5-final-views-20261009
python3 - "$RUN" "$OUT" <<'PY'
import sys,pathlib,json,hashlib,shutil,datetime
r,o=map(pathlib.Path,sys.argv[1:]); rows={}
for label,sub in [("installed","routes/qfd_q5_landing_ecc_ab9c785e9_wc_ttalias/work/orfs"),("eco","cl/eco/pass2/orfs")]:
 b=next((r/sub/"results/asap7").glob("*/base"));rows[label]={}
 for ext in ["odb","spef","sdc","v"]:
  p=b/("6_final."+ext);rows[label][ext]={"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size,"mtime_ns":p.stat().st_mtime_ns}
for ext in rows["installed"]: assert rows["installed"][ext]["sha256"]==rows["eco"][ext]["sha256"]
(o/"input_objects.json").write_text(json.dumps({"source":"ab9c785e96c41fe63522befcc3b532475bb1d260","historical_record":"7cba3f22f6ee3bbb5df44e28e24474124d0f0ce0","objects":rows,"recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2)+"\n")
shutil.copytree(r/"record/views/qfd_q5_landing_ecc",o/"views")
PY
python3 "$RUN/src/tools/tt_views/view_export.py" --orfs-dir "$RUN/routes/qfd_q5_landing_ecc_ab9c785e9_wc_ttalias/work/orfs" --name qfd_q5_landing_ecc --out "$OUT/views" --corners tt --image openroad/orfs:asap7lock > "$OUT/export_tt_stdout.log" 2>&1
printf "0\n" > "$OUT/status"
