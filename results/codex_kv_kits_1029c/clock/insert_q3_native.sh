#!/bin/bash
set -euo pipefail
K=$1
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --cpus 8 --memory 12g --memory-swap 12g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/insert_q3_native.tcl' > "$K/native_insert_dpl.log" 2>&1
