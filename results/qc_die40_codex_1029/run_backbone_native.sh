#!/bin/bash
set -euo pipefail
Q=/srv/opentallas-scratch2/claude
R=$Q/codex-qc-1847
M=$Q/codex-qc-mesh5-1029
python3 - <<'PYNATIVE'
import json
from pathlib import Path
q=Path('/srv/opentallas-scratch2/claude')
e=json.load(open(q/'codex-qc-import-0824/reachfix/mechanics/endpoints.json'));e=e.get('endpoints',e)
stubs={r['port']:r for r in json.load(open(q/'die-qc30/b1/phy_stub_plan.json'))['stubs']}
r=[[v['net'],'M7',*(stubs[k]['m7_stub_um'] if k in stubs else v['rect_um'])] for k,v in e.items()]
json.dump(r,open(q/'codex-qc-1847/native_m7_reserved.json','w'))
PYNATIVE
docker run --rm --name codexqc1847-backbone-$$ --memory=64g --memory-swap=64g --cpus=2 -v "$Q:$Q" -w "$R" python:3.12 bash -c "set -e; trap 'chown -R 1000:1000 $R/backbone_native' EXIT; pip -q install shapely numpy pyyaml >/dev/null 2>&1; cd $M/src/results/qc_clock_physical_1029; python $R/backbone_native.py --jog-src $M/src/results/qc_clock_physical_1029 --fixed-wires $Q/die-qc36/prebuild_e1_resite_noaccess/fixed_wires.json --cell-windows $Q/codex-qc-1029/baseline26/islands119_cellmap/cell_windows.json --geometry $M/census119_h800/geometry.json --clock-base-resited $Q/die-qc36/backbone_bb1/clock_base_resite_v2.json --reserved-metal $Q/codex-qc-macropg-1029/bridges_v1/reserved_bridges.json --reserved-metal $R/native_m7_reserved.json --max-jog 1.5 --riser-island off --column-select track --riser-max 9.0 --tags RN1,RN1c --out $R/backbone_native > $R/backbone_native.log 2>&1"
