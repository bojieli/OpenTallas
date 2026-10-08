#!/bin/bash
# sync_src.sh <host> <remote dir>: pinned source snapshot of THIS worktree for route_view.sh (tools, rtl, physical and
# the result records the die generator reads), with SOURCE_COMMIT = HEAD (commit first: the snapshot is the commit).
set -e
WT=$(cd "$(dirname "$0")/../../.." && pwd); host=$1; dst=$2
cd $WT
test -z "$(git status --porcelain -- tools rtl physical)" || { echo "dirty tools/rtl/physical: commit first"; git status --porcelain -- tools rtl physical | head; exit 1; }
ssh $host "mkdir -p $dst"
rsync -a --delete --exclude .views --exclude __pycache__ tools rtl physical Makefile $host:$dst/ 
rsync -aR results/uarch/hbm_current_target_portmap_20261005 results/rtl/hbm_accel_die_floorplan_20261005 \
  results/rtl/die_top_lint_20261006 results/rtl/dshbm_matched_reference_20261005 \
  results/uarch/hbm_accel_fulldie_inputs_20261004/providers/sm_r2/routes/sm_r2/fp $host:$dst/ 2>/dev/null || true
git rev-parse HEAD | ssh $host "cat > $dst/SOURCE_COMMIT"
echo "synced $(git rev-parse --short HEAD) -> $host:$dst"
