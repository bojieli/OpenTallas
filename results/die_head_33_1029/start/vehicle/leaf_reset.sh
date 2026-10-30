#!/bin/bash
# DIE-HEAD-33: Codex hk5_leaf2.sh steps 6-9 (local wavefront reset provider) on the src25m leaf plan; main tools.
set -euo pipefail
W=/srv/opentallas-scratch2/claude/wt/die-head-33-start
R=/srv/opentallas-scratch2/claude/die-head-33/start/leaf
python3 "$W/tools/die_plan/reset_tree.py" offsets "$R/capture/plan.json" --out "$R/reset_offsets.json" > "$R/reset_offsets.log"
python3 "$W/tools/s81_head/head_start_reset_exports.py" "$R/capture/plan.json" "$R/reset_offsets.json" "$R/stages/start_stages.json" --out "$R/exports0.json" > "$R/exports.log"
python3 - "$W" "$R" <<"PY"
import json,sys
from pathlib import Path
w,r=map(Path,sys.argv[1:]);sys.path.insert(0,str(w/"tools/s81_head"))
from head_start_reset_aliases import reuse_existing
x=reuse_existing(json.load(open(r/"exports0.json")),json.load(open(r/"reset_offsets.json")))
(r/"exports.json").write_text(json.dumps(x,indent=1)+"\n")
settle=max(74,x["summary"]["max_relative_raw_release"]+4)
(r/"settle.txt").write_text(str(settle)+"\n")
print(json.dumps(x["summary"]), "settle",settle)
PY
python3 "$W/tools/s81_head/head_start_local_reset.py" "$R/stages" "$R/exports.json" --settle "$(cat "$R/settle.txt")" --out "$R/provider" > "$R/provider.log"
echo RESET_DONE
