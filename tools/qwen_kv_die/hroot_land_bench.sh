#!/bin/bash
# hroot_land_bench.sh OUT [MUT=0] [EDGES=2000]: HKV-HROOTK2 latency lockstep of the landed stack root tile (OT_KV_HROOT_LAND=1)
# against the unlanded tile with every data input one edge late (tools/qwen_kv_die/hroot_land_bench.py).  One HROOT_LAND
# line; exit 0 only on PASS (mutants expect FAIL).  Run from the repository root (on the fleet via ot-run).
set -u
O=$1; M=${2:-0}; E=${3:-2000}
mkdir -p "$O"
source tools/qwen_kv_die/kvs_kits_env.sh
export OT_KV_HROOT_LAND=1
# the closure daemon's pinned Verilator 5.050 (not Debian's 5.032)
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin"; do [ -d "$_d" ] && export PATH="$_d:$PATH"; done
python3 tools/qwen_kv_die/hroot_land_bench.py --mut "$M" --edges "$E" --out "$O" > "$O/run.log" 2>&1
rc=$?
grep -E '^MISMATCH' "$O/run.log" | head -5
line=$(grep -E '^HROOT_LAND ' "$O/run.log" | tail -1)
echo "${line:-HROOT_LAND FAIL tile=hroot no verdict line mut=$M }"
[ $rc -ne 0 ] && [ -z "$line" ] && tail -20 "$O/run.log"
case "$line" in "HROOT_LAND PASS"*) exit 0;; *) exit 1;; esac
