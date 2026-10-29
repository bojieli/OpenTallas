#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-head-lepwe
# The launched placement trial owns this exact container; wait has no polling loop.
docker wait codex-lepwe-trial6-place > "$R/trial_v6/docker_exit.txt"
test -f "$R/trial_v6/run/results/asap7/hbc_ot_s81hd_lep_pair/base/3_place.odb"
mkdir -p "$R/geom_v6"
python3 - "$R" <<'PY'
import sys,json
from pathlib import Path
r=Path(sys.argv[1]); (r/'geom_v6/check.json').write_text(json.dumps(dict(odb=str(r/'trial_v6/run/results/asap7/hbc_ot_s81hd_lep_pair/base/3_place.odb'),image='openroad/orfs:asap7lock',id='codex-lepwe-v6',mem_gb=8,grt=False,grt_max='M7',rules_args=['--all-kits','--outline','388.8x432','--title','lep_pair structural plan6'])))
PY
exec ~/.local/bin/ot-run --mem 8 --threads 2 --hosts localhost --dir "$R" -- bash /srv/opentallas-scratch2/claude/wt/codex-head-lepwe/tools/autopilot/geom_check.sh "$R/geom_v6"
