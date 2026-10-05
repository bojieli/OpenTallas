#!/bin/bash
# Run a parent near-HBM bench build script with sources swapped for the timing successors:
#   [NHB_SWAP=hub|stack|hub,stack] hubp_swap.sh <build script> <its arguments...>      (default NHB_SWAP=hub)
# The pinned scripts and benches are untouched.  A copy of the script (next to it, so its relative paths resolve)
# lists, in place of the parent source:
#   hub    rtl/test/nearhbm/ot_qwen_nearhbm_attn_hub_shim_p.sv   + rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv
#   stack  rtl/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_p.sv + rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv
set -e
S=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); shift
T=$(mktemp "$(dirname "$S")/.hubp_XXXXXX.sh")
trap 'rm -f "$T"' EXIT
cp "$S" "$T"
SW=${NHB_SWAP:-hub}
for x in ${SW//,/ }; do
  case $x in
    hub)   sed -i 's#\$W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub\.sv#$W/test/nearhbm/ot_qwen_nearhbm_attn_hub_shim_p.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv#' "$T"
           grep -q ot_qwen_nearhbm_attn_hub_p.sv "$T" || { echo "hubp_swap: hub source not found in $S" >&2; exit 2; } ;;
    stack) sed -i 's#\$W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack\.sv#$W/test/nearhbm/ot_qwen_nearhbm_attn_stack_shim_p.sv $W/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_p.sv#' "$T"
           grep -q ot_qwen_nearhbm_attn_stack_p.sv "$T" || { echo "hubp_swap: stack source not found in $S" >&2; exit 2; } ;;
    *) echo "hubp_swap: unknown NHB_SWAP item $x" >&2; exit 2 ;;
  esac
done
bash "$T" "$@"
