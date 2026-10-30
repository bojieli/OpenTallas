#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-start-source-assembly-1030/attempt_833
cd "$r"
docker run --rm --memory=4g --memory-swap=4g -v "$r/kit:/work" openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; yosys -Q -T -p "read_verilog -sv /work/run/results/asap7/codex_start_source/base/1_2_yosys.v; setattr -mod -unset keep_hierarchy; setattr -unset keep_hierarchy; hierarchy -top ot_die_start_stages; flatten; write_json /work/mapped_flat.json"' >export.log 2>&1
