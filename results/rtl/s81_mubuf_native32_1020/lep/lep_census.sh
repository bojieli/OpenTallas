#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for v in a h; do
 k=s81sl_lepmu${v}_dr-20261019-224208
 p=/srv/opentallas-scratch/claude/ref_gate/$k
 n=$(find "$p/routes/gate/work/orfs/results" -name 1_2_yosys.v -print -quit)
 docker run --rm --memory=8g --memory-swap=8g -v "$PWD:/work" -v "$p:/g:ro" -w /work openroad/orfs:latest python3 tools/textbook_lint.py check --netlist "/g/${n#"$p/"}" --top ot_s81sl_lep_mu_$v --out lep_${v}_native32.json --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 reach_um=405 > lep_${v}_native32.log 2>&1
done
