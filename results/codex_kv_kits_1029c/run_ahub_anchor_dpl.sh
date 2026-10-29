#!/bin/bash
set -euo pipefail
K=$1
DK=docker; docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --cpus 4 --memory 24g --memory-swap 24g -v "$K":/work -e HUID="$(id -u)" -e HGID="$(id -g)" -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /work/anchor_dpl.tcl > /work/anchor_dpl.log 2>&1; rc=$?; chown -R "$HUID:$HGID" /work; exit $rc'
