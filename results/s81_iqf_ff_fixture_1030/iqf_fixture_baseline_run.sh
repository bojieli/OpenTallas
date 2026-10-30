#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-s81types-1030/iqf_current_bind/ff_fixture
python3 - "$r" <<'PY'
from pathlib import Path
import sys
r=Path(sys.argv[1]);s=(r/'default/fixture_snapshot.tcl').read_text().replace('fixture434_postresize.tsv','fixture434_baseline.tsv')
(r/'baseline_snapshot.tcl').write_text('read_db /work/default/run/results/asap7/dp_iqf__t1/base/1_synth.odb\nset ::env(RESULTS_DIR) /work\n'+s)
PY
docker run --rm --name codex_iqf_ff_fixture_baseline1030 --cpus=1 --memory=8g --memory-swap=8g -v "$r":/work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/baseline_snapshot.tcl' > "$r/baseline.log" 2>&1
