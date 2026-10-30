#!/bin/bash
set -euo pipefail
count_kit=$(pwd -P)
count_uid=$(id -u);count_gid=$(id -g)
count_docker=docker
docker ps >/dev/null 2>&1 || count_docker='sudo docker'
$count_docker run --rm --cpus=8 --memory=32g --memory-swap=32g -v "$count_kit":/work -e HUID="$count_uid" -e HGID="$count_gid" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /work/run_inside.py; count_rc=$?; chown -R "$HUID:$HGID" /work; exit "$count_rc"'
