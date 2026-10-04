#!/bin/bash
# Run a parent near-HBM bench build script with the hub source swapped for the timing successor:
#   hubp_swap.sh <build script> <its arguments...>
# The pinned script and benches are untouched.  A copy of the script (next to it, so its relative paths
# resolve) lists rtl/test/nearhbm/ot_qwen_nearhbm_attn_hub_shim_p.sv + rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv
# in place of rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub.sv.
set -e
S=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); shift
T=$(mktemp "$(dirname "$S")/.hubp_XXXXXX.sh")
trap 'rm -f "$T"' EXIT
sed 's#\$W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub\.sv#$W/test/nearhbm/ot_qwen_nearhbm_attn_hub_shim_p.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv#' "$S" > "$T"
grep -q ot_qwen_nearhbm_attn_hub_p.sv "$T" || { echo "hubp_swap: hub source not found in $S" >&2; exit 2; }
bash "$T" "$@"
