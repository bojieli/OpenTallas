#!/bin/bash
# DIE-KV-31-SRC step 2: refresh native OBS/PG pins (export_overlay.py) from the rebuilt src_phy native_grid.odb onto the
# codex-kv-pg-0834 grid3_bbox export (after compare_grid.py proves the top grid is identical), plan std-cell PG access
# (plan_access.py --native-overlay), per-net census, render. Tools = read-only copies of codex-kv-pg-0834/src (pgh/src).
# Stages: overlay | plan | apply
set -euo pipefail
N=/srv/opentallas-scratch2/claude/die-kv-31-1029/src_phy
H=/srv/opentallas-scratch2/claude/die-kv-31-1029/pgh
C=/srv/opentallas-scratch2/claude/codex-kv-pg-0834
V=/srv/opentallas-scratch2/claude/die-kv-31-1029/venv/bin/python
NONPG=cce6226e17592e0d3fde4fa9808970c28dfda5ee15e99794de7fd2354344d4ee
A=$N/access; mkdir -p $A
case ${1:?overlay|plan|apply} in
overlay)
docker run --rm --name dkv31-overlay --memory=60g --cpus=2 -v $N:/n -v $H:/h:ro -v $C:/c:ro openroad/orfs:latest bash -lc "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /n/compare_grid.py --odb /n/pg_grid/native_grid.odb --pg-rects /c/grid3_bbox/pg_rects.json --out /n/access/compare_grid.json > /n/access/compare_grid.log 2>&1; openroad -python -no_init -exit /h/src/export_overlay.py --odb /n/pg_grid/native_grid.odb --old-native /c/native_export/geometry.json --terms /c/grid3_bbox/power_terms.json --reservations /c/grid/source_pg_reservations.json --non-pg-sha $NONPG --out /n/access/overlay.json > /n/access/overlay.log 2>&1; chown -R 1000:1000 /n/access"
python3 -c "import json,sys;r=json.load(open('$A/compare_grid.json'));sys.exit(0 if r['identical'] else 'TOP GRID DIFFERS: export not reusable')"
;;
plan)
/usr/bin/time -v $V $H/src/plan_access.py --input $C/grid3_bbox --out $A/plan --clock-seed $C/grid3_bbox/clock_seed.json --native-overlay $A/overlay.json > $A/plan.log 2> $A/plan.time
$V $N/census_access.py --plan $A/plan --out $A/census.json
MPLBACKEND=Agg $V $H/src/render_access.py --source $C/grid3_bbox --plan $A/plan --out $A/access_render.png
;;
apply)
docker run --rm --name dkv31-apply --memory=96g --cpus=2 -v $N:/n -v $H:/h:ro -v $C:/c:ro openroad/orfs:latest bash -lc "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /h/src/apply_access.py --odb /n/pg_grid/native_grid.odb --plan /n/access/plan --grid /c/grid3_bbox/pg_rects.json --out /n/access/access.odb > /n/access/apply.log 2>&1; chown -R 1000:1000 /n/access"
;;
esac
echo STAGE_DONE $1 $(date -Is)
