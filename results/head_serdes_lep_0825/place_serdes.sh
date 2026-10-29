#!/bin/bash
set -euo pipefail
RUN=/srv/opentallas-scratch2/claude/codex-head-serdes-lep-0825
KIT="$RUN/quarter_keep"
python3 - "$KIT" <<'PY'
import json,sys
from pathlib import Path
k=Path(sys.argv[1]); d=json.loads((k/'lec/lec.json').read_text())
assert d['verdict']=='EQUIVALENT', d['verdict']
assert not (k/'FAIL_PREFLOOR').exists(), 'Inherited pre-floor gate failed'
for f in ('face_guard.json','port_bind.json','rtl_lint.json','sdc_lint.json'):
    assert (k/f).exists(), f
PY
docker run --rm --name codex-head-serdes-qkeep-place-0825 --cpus=8 --memory=32g --memory-swap=32g \
    -v "$KIT":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock \
    bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place' \
    > "$RUN/place.log" 2>&1
