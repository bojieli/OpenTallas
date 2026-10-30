#!/bin/bash
# DIE-KV-37: E0 (kv3_head_eighth_e0) route from FLOW-CLOCK-R6 e0_iopad 5_1_grt (R5 chunk + R6 IO hold pad at GRT), then
# do-finish + abstract/corners/signoff via run_kit_kv.sh post.  Same container steps as grt_only.sh (two-mode MM patch).
K=$(cd "$(dirname "$0")" && pwd)/e0; DRY=${1:-0}
docker run --rm --name kvcore-kv37-e0route-$$ --cpus=16 --memory=64g --memory-swap=64g -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) \
 -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
 M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16\"; rc=0; \
 python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || rc=9; \
 if [ $DRY = 1 ]; then \$M -n route | grep -oE \"(do-[0-9a-z_]+|[0-9]_[0-9a-z_]+[.](log|odb))\" | sort -u; exit 0; fi; \
 [ \$rc = 0 ] && { \$M route; rc=\$?; }; \
 [ \$rc = 0 ] && { \$M do-finish; rc=\$?; }; \
 chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_route_kv37.log" 2>&1
rc=$?; echo "E0_ROUTE rc=$rc $(date)" >> "$K/run_route_kv37.log"
[ $DRY = 1 ] && exit 0
[ $rc = 0 ] && { bash "$K/run_kit_kv.sh" "$K" post 64 16 > "$K/post_kv37.log" 2>&1; rc=$?; echo "E0_POST rc=$rc $(date)" >> "$K/run_route_kv37.log"; }
exit $rc
