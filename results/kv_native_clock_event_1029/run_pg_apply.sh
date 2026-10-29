#!/bin/bash
set -euo pipefail
D=$(pwd)
docker run --rm --name codex-kv-native-pg-joins-$$ --cpus=4 --memory=32g --memory-swap=32g -v "$D:/work" -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -python /work/native_pg/apply_joins.py --source /work/pgkit02/psm/pdn_top_only.odb --direct-plan /work/native_pg/selected_plan.json --bridge-plan /work/native_pg/empty_bridges.json --output /work/native_pg/connected.odb --receipt /work/native_pg/connected_receipt.json > /work/native_pg/apply.log 2>&1; rc=$?; chown -R $HUID:$HGID /work/native_pg; exit $rc'
