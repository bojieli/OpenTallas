#!/bin/bash
set -euo pipefail
D=$(pwd)
docker run --rm --name codex-kv-native-audit-$$ --cpus=4 --memory=32g --memory-swap=32g -v "$D:/work" -w /work -e HUID=$(id -u) -e HGID=$(id -g) openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -python /work/audit_native_source.py > /work/native_source/audit.log 2>&1; rc=$?; chown -R $HUID:$HGID /work/native_source; exit $rc'
