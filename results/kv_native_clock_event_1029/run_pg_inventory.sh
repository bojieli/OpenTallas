#!/bin/bash
set -euo pipefail
D=$(pwd)
docker run --rm --name codex-kv-pg-inventory-$$ --cpus=4 --memory=32g --memory-swap=32g -v "$D:/work" -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -python /work/native_pg/inventory.py --odb /work/pgkit02/psm/pdn_top_only.odb --out /work/native_pg/inventory.json > /work/native_pg/inventory.log 2>&1; rc=$?; chown -R $HUID:$HGID /work/native_pg; exit $rc'
