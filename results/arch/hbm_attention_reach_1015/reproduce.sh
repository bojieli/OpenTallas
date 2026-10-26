#!/bin/bash
set -euo pipefail
# Run from repository root with source-pinned physical child views present.
root=$PWD
out=${1:-/tmp/hbm-attention-reach-1015}
mkdir -p "$out"
git show 69fd7386188163d3bd44d796aa3a4bd794648828:tools/hbm_attention_direct_manifest.py > "$out/export.py"
git show 69fd7386188163d3bd44d796aa3a4bd794648828:results/arch/hbm_group_b5_1014/attention_repartition/hi.candidate.component.json > "$out/hi.component.json"
python3 "$out/export.py" "$out/hi.component.json" --root "$root" --out "$out/hi.direct.json"
python3 tools/hbm_attention_reach_repair.py "$out/hi.direct.json" results/arch/hbm_attention_reach_1015/placement.json --out "$out/receipt.json" --emit "$out/hi.repaired.direct.json"
