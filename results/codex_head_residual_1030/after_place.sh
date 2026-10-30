#!/bin/bash
set -euo pipefail
P=/srv/opentallas-scratch2/claude/codex-head-residual-1030
V=$1
K=$P/$V
O=$K/run/results/asap7/dp_hd_tile/base/3_place.odb
G=$P/${V}_geom
while [ ! -f "$O" ]; do
 if ! docker inspect --format '{{.State.Running}}' codex-head-tile-place2 >/dev/null 2>&1; then echo 'PLACE finished without checkpoint; inspect place log'; exit 1; fi
 sleep 10
done
mkdir -p "$G"
python3 - "$O" "$G/check.json" "$V" <<'PY'
import json,sys
json.dump(dict(id='cx-head-'+sys.argv[3],odb=sys.argv[1],image='openroad/orfs:asap7lock',mem_gb=8,grt=True,rules_args=['--all-kits','--outline','708.48x1036.8','--title','HEAD existing-stage structural placement '+sys.argv[3]]),open(sys.argv[2],'w'))
PY
/home/ubuntu/.local/bin/ot-run --mem 16 --threads 4 --dir "$G" --stage "$G" --stage "$K" --stage "$P/geomtools" -- bash "$P/geomtools/geom_check.sh" "$G"
