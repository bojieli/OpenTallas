#!/bin/bash
set -euo pipefail
k=/srv/opentallas-scratch2/claude/codex-flow-ln-postff-1030/g1_109
if [[ -e "$k/ONE_G1_STARTED" ]]; then
  echo 'REFUSE: this reviewed one-G1 successor has already started; preserve it for diagnosis.' >&2
  exit 86
fi
printf 'host=%s start=%s scope=G1_ONLY source=6577522 repair=0863dd04a\n' "$(hostname)" "$(date -Is)" > "$k/ONE_G1_STARTED"
docker run --rm --name codex_ln_postff_g1_109 --cpus=8 --memory=32g --memory-swap=32g -v "$k":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place' > "$k/one_g1_native.log" 2>&1
python3 - "$k" <<'PY'
import json,sys
from pathlib import Path
k=Path(sys.argv[1]);log=(k/'one_g1_native.log').read_text()
if 'LN_POSTFF_G1_GUARD_PASS all8386FFmasters_homes_orients_clocks_and109postFFsites_exact' not in log:raise SystemExit('FAIL: missing strict native post-detail guard receipt')
(k/'ONE_G1_PLACE_GUARD_PASS.json').write_text(json.dumps(dict(scope='PLACE_ONLY_G1_GEOM_PG_LOOK_STILL_REQUIRED_NO_CTS_STA_GRT_ROUTE',all8386FFguard=True,postFF_BUF_INV=109),indent=2)+'\n')
print('ONE_G1_PLACE_GUARD_PASS; fresh actual GEOM/PG/LOOK still required; no CTS/STA/GRT/route.')
PY
