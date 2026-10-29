#!/bin/bash
set -euo pipefail
T=${1:?A-or-SM}
case "$T" in A|SM) ;; *) exit 2;; esac
R=/srv/opentallas-scratch2/claude/die-kv-34-1029/$T
V=/srv/opentallas-scratch2/claude/die-kv-33-1029/leaf/$T
H=/srv/opentallas-scratch2/claude/die-kv-31-1029/pgh
mkdir -p "$R/access" "$R/grt" "$R/clk/out_TT" "$R/clk/out_FF"
N=$(python3 - "$V" <<'PY'
import json,sys
from pathlib import Path
v=Path(sys.argv[1]);new=json.load(open(v/'inputs/leaf_clusters.json'))['summary']['new_cells'];p=json.load(open(v/'plan/access_plan.json'));n=sum(len(q['members']) for q in p['paths']);assert not p['failed'];assert n==75934+2*new,(n,new);print(n)
PY
)
printf 'ACTUAL_EXPECTED_CONTACTS %s\n' "$N" > "$R/access/expected_contacts.txt"
docker run --rm --name dkv34-access-$T --memory=96g --cpus=8 -v "$V:/v:ro" -v "$R:/n" -v "$H:/h:ro" openroad/orfs:latest bash -lc "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /h/src/apply_access.py --odb /v/pg_grid/native_grid.odb --plan /v/plan --grid /v/bbox/pg_rects.json --expected-contacts $N --out /n/access/access.odb > /n/access/apply.log 2>&1; chown -R 1000:1000 /n/access"
cp /srv/opentallas-scratch2/claude/die-kv-32-1029/src_phy/grt_loaded.tcl "$R/grt_loaded.tcl"
cp "$V/clk/clk.tcl" "$R/clk/clk.tcl"
( docker run --rm --name dkv34-grt-$T --memory=128g --cpus=16 -v "$R:/n" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 16 -exit /n/grt_loaded.tcl > /n/grt/grt.log 2>&1; chown -R 1000:1000 /n/grt' ) & GP=$!
for C in TT FF; do
( docker run --rm --name dkv34-clk-$T-$C --memory=32g --cpus=8 -e CORNER=$C -v "$R:/n:ro" -v "$R/clk:/w" -v "$R/clk/out_$C:/out" openroad/orfs:latest bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /w/clk.tcl > /out/clk_$CORNER.log 2>&1; chown -R 1000:1000 /out' ) &
done
wait "$GP"
wait
printf 'LEAF_CONTINUATION_DONE %s\n' "$T"
