#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-kits-1029c/astk_inputbuf_trial1/kv3_astk__190.08x181.44
DK=docker;docker ps >/dev/null 2>&1 || DK='sudo docker'
$DK run --rm --cpus 4 --memory 12g --memory-swap 12g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 4 -exit /work/astk_inputbuf_dpl.tcl' > "$K/inputbuf_dpl.log" 2>&1
