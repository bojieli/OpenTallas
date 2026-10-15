#!/usr/bin/env bash
# Exact bench of the static embedding return station (qkd_embedding_static_return_hop): the full 32-PC compiled
# return train through 32 real hop instances (2 edges per hop, no wait/priority).  MUT selects a negative schedule:
#   0 production (must PASS), 1 one-edge-late transfer slot of PC17, 2 missing capture valid of PC17,
#   3 overwrite of an occupied station.  Exit 0 iff PASS.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?output directory}; mut=${2:-0}; mkdir -p "$out"
d=$root/rtl/qwen_sys/static_embedding_20261014
iverilog -g2012 -s tb_static_embed_return_chain -o "$out/rc.sim" "$d/qkd_embedding_static_return_hop.sv" \
  "$d/test/tb_static_embed_return_chain.sv" > "$out/compile.log" 2>&1
vvp "$out/rc.sim" "+MUT=$mut" 2>&1 | tee "$out/mut$mut.log"
grep -q '^PASS full32PC static return chain' "$out/mut$mut.log"
