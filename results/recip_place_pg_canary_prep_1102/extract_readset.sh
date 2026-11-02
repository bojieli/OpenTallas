#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-recip-place-canary-prep-0810
SOURCE=/srv/opentallas-scratch2/claude/codex-recip-place-prep-0550
python3 - "$SOURCE" <<'PY'
from pathlib import Path
import json,hashlib,sys
r=Path(sys.argv[1]);d=json.loads((r/'PLACE_EXPECTED.json').read_text());print(d.keys())
PY
docker run --rm --name "codex-recip-place-readset-$$" --memory=1g --memory-swap=1g --cpus=1 -v "$SOURCE/kit":/work:ro -v "$R":/case -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; mkdir -p /case/unpatched /case/normal_mm; cp -a scripts /case/unpatched/; if grep -q "^override export OT_HOLD_MM = 1" /work/config.mk; then python3 -I /work/orfs_hold_mm.py scripts > /case/MM_PATCH.log; fi; cp -a scripts /case/normal_mm/; cp Makefile /case/normal_mm/; cp -a util /case/normal_mm/; make -n DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 do-3_1_place_gp_skip_io do-3_2_place_iop do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp do-3_place > /case/NORMAL_DRY.log; make -pn DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=1 do-3_1_place_gp_skip_io do-3_2_place_iop do-3_3_place_gp do-3_4_place_resized do-3_5_place_dp do-3_place | gzip > /case/MAKE_DATABASE.txt.gz'
