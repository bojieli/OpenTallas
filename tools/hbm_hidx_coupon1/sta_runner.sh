#!/bin/bash
set -euo pipefail
cd ..
python3 - <<'PY'
from pathlib import Path
s=Path('out/netlist.v').read_text();Path('out/sta_netlist.v').write_text(s.replace('wire signed ', 'wire '))
PY
docker run --rm --network none -v "$PWD:/work" -w /work openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit tools/hbm_hidx_coupon1/sta.tcl >out/sta3.log 2>&1
if grep -Eq '\[ERROR|^Error:' out/sta3.log; then exit 1;fi
grep -q 'data arrival time' out/sta3.log
