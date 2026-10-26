#!/bin/bash
# kvs_tile_bench.sh OUT TILE [MUT=0] [EDGES=2000]: lockstep of the kit top qkd_kvs_<TILE> (OT_KV_KVS_CK1) against the
# die-bound tile of the same design point (tools/qwen_kv_die/kvs_tile_bench.py).  One KVS_TILE line; exit 0 only on
# PASS (mutants expect FAIL).  Run from the repository root (on the fleet via ot-run).
set -u
O=$1; T=$2; M=${3:-0}; E=${4:-2000}
mkdir -p "$O"
source tools/qwen_kv_die/kvs_kits_env.sh
# KV-KITS-ATTN 10-18: KVS_SIM=verilator runs on the closure daemon's pinned Verilator 5.050 (not Debian's 5.032)
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
python3 tools/qwen_kv_die/kvs_tile_bench.py --tile "$T" --mut "$M" --edges "$E" --out "$O" > "$O/run.log" 2>&1
rc=$?
grep -E '^MISMATCH' "$O/run.log" | head -5
line=$(grep -E '^KVS_TILE ' "$O/run.log" | tail -1)
echo "${line:-KVS_TILE FAIL tile=$T no verdict line mut=$M }"
[ $rc -ne 0 ] && [ -z "$line" ] && tail -20 "$O/run.log"
case "$line" in "KVS_TILE PASS"*) exit 0;; *) exit 1;; esac
