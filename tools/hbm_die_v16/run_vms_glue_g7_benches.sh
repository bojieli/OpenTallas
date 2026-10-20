#!/usr/bin/env bash
# L2H-PGVM-G7 10-19 (VM glue g7: the g6 cases + g7 contract mutants g7 = g6 hub br landing kept, g7e = g6 eg tile relays kept): every lockstep case of the three tile masters (positives + contract mutants), 6 in parallel,
# Verilator 5.050 (fleet).  run_vms_glue_g7_benches.sh OUT ; one line per case in OUT/summary.txt (expect / exit / verdict line).
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=$(realpath -m "${1:?out}"); mkdir -p "$OUT"
cases="SW:pos NW:pos SE:pos NE:pos SW:rmut NW:rmut SE:rmut SW:land NW:land SE:land SE:sid NE:sid SW:g3 NW:g3 SE:g3 SW:g4 NW:g4 SE:g4 SW:g5 NW:g5 SE:g5 SW:g7 NW:g7 SE:g7 SW:g7e NW:g7e SE:g7e"
run() { q=${1%%:*}; m=${1##*:}; bash tools/hbm_die_v16/run_vms_glue_tile_equiv.sh "$q" "$m" "$OUT" > "$OUT/$q$m.run.log" 2>&1; echo "$q $m exit=$? $(grep -h VMS_GLUE_LT_EQUIV "$OUT/$q$m.sim.log" 2>/dev/null | tail -1)"; }
export -f run; export OUT
printf '%s\n' $cases | xargs -P 6 -I{} bash -c 'run {}' | sort > "$OUT/summary.txt"
cat "$OUT/summary.txt"
