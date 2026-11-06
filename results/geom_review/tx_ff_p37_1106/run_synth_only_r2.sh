#!/usr/bin/env bash
set -euo pipefail
base=/srv/opentallas-scratch2/claude/codex-tx-ff-p37-1106
kit=$base/generated/ot_pdie_serdes_tx_c77a41179db8-FF
mkdir -p "$base/review/context_r2"
python3 - "$base" <<'PY'
from pathlib import Path
import json,sys
b=Path(sys.argv[1]);p=Path("/srv/opentallas-scratch2/claude/codex-hbm-wave/d44v37/die_plan.json")
views=json.loads((b/"GEN_INTAKE.json").read_text())["views"]
views["plan"]=str(p)
(b/"review/views.json").write_text(json.dumps(views,indent=2)+"\n")
PY
python3 "$base/wt/physical/die_plan/hbm_arch_cores/review_core.py" --views "$base/review/views.json" --view ot_pdie_serdes_tx@c77a41179db8 --out "$base/review/context_r2"
# Mapping only: no floorplan/place/CTS/route target or asynchronous LEC launch.
sudo docker run --rm --name "txff-p37-synth-$PPID" --cpus=2 --memory=4g --memory-swap=4g \
 -v "$kit:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
 bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 synth'
sudo chown -R "$(id -u):$(id -g)" "$kit/run"
