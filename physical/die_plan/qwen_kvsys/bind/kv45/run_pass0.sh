#!/bin/bash
# Native v3.9/C1 metadata pass only; final C2/core-clock sources and schedule follow.
set -euo pipefail
kv45_root=${1:?usage: run_pass0.sh SCRATCH_ROOT}
cd "$kv45_root/t45"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
kv45_recipe=physical/die_plan/qwen_kvsys/bind/kv45/${2:-asbuilt_pass0.json}
kv45_output=$kv45_root/runs/${3:-pass0}
sed "s#@ASAP7_CELLS@#$kv45_root/asap7_cells#g" "$kv45_recipe" > "${kv45_recipe%.json}_runtime.json"
if [ -n "${4:-}" ]; then
    mkdir -p "$kv45_output"
    cp "$kv45_root/runs/$4/asbuilt.json" "$kv45_root/runs/$4/asbuilt_sources.json" "$kv45_output/"
else
    python3 tools/die_plan/bind.py elab physical/die_plan/qwen_kvsys/die_plan.json --asbuilt "${kv45_recipe%.json}_runtime.json" --out "$kv45_output" --mem 48
fi
python3 tools/die_plan/bind.py bind physical/die_plan/qwen_kvsys/die_plan.json --asbuilt "${kv45_recipe%.json}_runtime.json" --out "$kv45_output" --mem 48 --strict
