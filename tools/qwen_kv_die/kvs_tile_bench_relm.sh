#!/bin/bash
# kvs_tile_bench_relm.sh OUT TILE [MUT=0] [EDGES=2000] (KDIE5-TV 10-22): kvs_tile_bench.sh at the RELEASE KV die design
# point (kvs14r-f9b69ebb3-relm kv_flags.env, committed beside the witnesses) instead of the k1 kit point
# (kvs_kits_env.sh): the generated kit tile is then the release _n32_pj module text.  One KVS_TILE line; exit 0 only on PASS.
set -u
O=$1; T=$2; M=${3:-0}; E=${4:-2000}
mkdir -p "$O"
set -a; source results/rtl/qwen_kv_die/kdie5_tv_1022/relm_kv_flags.env; set +a
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
python3 tools/qwen_kv_die/kvs_tile_bench.py --tile "$T" --mut "$M" --edges "$E" --out "$O" --sim verilator > "$O/run.log" 2>&1
rc=$?
grep -E '^MISMATCH' "$O/run.log" | head -5
line=$(grep -E '^KVS_TILE ' "$O/run.log" | tail -1)
echo "${line:-KVS_TILE FAIL tile=$T no verdict line mut=$M }"
[ $rc -ne 0 ] && [ -z "$line" ] && tail -20 "$O/run.log"
case "$line" in "KVS_TILE PASS"*) exit 0;; *) exit 1;; esac
