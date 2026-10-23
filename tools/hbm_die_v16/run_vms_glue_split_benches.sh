#!/usr/bin/env bash
# STEWARD-HBMd/GLUE 2026-10-23: every lockstep case of the VM-glue split (positives vs the g7 tile and vs the contract
# ref, all 4 quadrants; mutants vs the tile), 6 in parallel, Verilator 5.050 (fleet).  One line per case in OUT/summary.txt.
#   run_vms_glue_split_benches.sh OUT
set -uo pipefail
cd "$(dirname "$0")/../.."
OUT=$(realpath -m "${1:?out}"); mkdir -p "$OUT"
cases="SW:tile:pos NW:tile:pos SE:tile:pos NE:tile:pos SW:ref:pos NW:ref:pos SE:ref:pos NE:ref:pos
SW:tile:rmut NW:tile:rmut SE:tile:g3 SW:tile:g4 NW:tile:g5 SE:tile:g7 SW:tile:split NW:tile:split SE:tile:split NE:tile:split NE:tile:sid"
run() { IFS=: read q r m <<< "$1"; bash tools/hbm_die_v16/run_vms_glue_split_equiv.sh "$q" "$r" "$m" "$OUT" > "$OUT/$q$r$m.run.log" 2>&1; echo "$q $r $m exit=$? $(grep -h VMS_GLUE_SPLIT_EQUIV "$OUT/$q$r$m.sim.log" 2>/dev/null | tail -1)"; }
export -f run; export OUT
printf '%s\n' $cases | xargs -P 6 -I{} bash -c 'run {}' | sort > "$OUT/summary.txt"
cat "$OUT/summary.txt"
