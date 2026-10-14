#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch/claude/hbmdie-v13
R=/tmp/claude-1000/hbmdie13/collected_clocks
L=/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock
check_owner() { python3 -c 'import json,sys;sys.exit(json.load(open(sys.argv[1]))["owner"]!="codex")' "$L"; }
say() { echo "$(date -Is) $*"; }
say 'waiting existing clock shell handles 3075392,3075393,3075394; no duplicate jobs'
ssh ot-agidock128 'tail --pid=3075392 --pid=3075393 --pid=3075394 -f /dev/null'
check_owner
say 'verifying successful terminal clocks and repaired source before STA generation'
ssh ot-agidock128 'D=/srv/opentallas-scratch/claude/hbmdie-v13; for g in trunk htop hreg; do test "$(cat "$D/sta/clock/$g/exit")" = 0 && test -s "$D/sta/clock/$g/tree_SS.txt" && test -s "$D/sta/clock/$g/tree_FF.txt" || exit 1; done'
ssh ot-epyc1tb 'D=/srv/opentallas-scratch/claude/hbmdie-v13; test "$(sha256sum "$D/src/tools/hbm_die_relay_sta.py" | cut -d" " -f1)" = 97ed441a812f6f2490a7f071ed598d9558ed58151984eeba827163a3191cee60' 
mkdir -p "$R"
for g in trunk htop hreg; do
 rsync -a "ot-agidock128:$D/sta/clock/$g/" "$R/$g/"
 rsync -a "$R/$g/" "ot-epyc1tb:$D/sta/clock/$g/"
done
check_owner
say 'recording measured clocks and corrected STA generation'
ot-run --mem 8 --threads 1 --dir "$D/sta/case" -- bash -lc 'set -e; D=/srv/opentallas-scratch/claude/hbmdie-v13; cd "$D/src"; python3 tools/budgets/clock_plan.py record --die-model "$D/sta/clock/model.json.gz" --case "$D/sta/clock/trunk" --case "$D/sta/clock/region" --case "$D/sta/clock/htop" --case "$D/sta/clock/hreg" --out "$D/sta/clock/plan.json" > "$D/sta/clock/record_codex.log" 2>&1; V=r25gqn_v13 STOP_BEFORE_GRT=1 bash tools/hbm_die_sta_chain.sh "$D/src" "$D/sta" > "$D/sta/prepare_codex.log" 2>&1'
check_owner
say 'launching placement and GRT parasitic STA independently'
ot-run --mem 64 --threads 16 --dir "$D/sta/case" -- bash -lc 'D=/srv/opentallas-scratch/claude/hbmdie-v13; W=$D/sta/case; docker run --rm --name hbmdie_v13_codex_sta_place --cpus=16 --memory=64g -v "$W:/work" openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /work/run_sta_place.tcl > /work/sta_place.log 2>&1; rc=\$?; echo \$rc > /work/sta_place.log.exit; chmod -R a+rwX /work; exit \$rc"' > /tmp/claude-1000/hbmdie13/sta_place_otrun_codex.log 2>&1 &
P=$!
check_owner
ot-run --mem 160 --threads 16 --dir "$D/sta/case" -- bash -lc 'D=/srv/opentallas-scratch/claude/hbmdie-v13; W=$D/sta/case; docker run --rm --name hbmdie_v13_codex_sta_grt --cpus=16 --memory=160g -v "$W:/work" openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads 16 -no_init -exit /work/run_grt_sta.tcl > /work/grt_sta.log 2>&1; rc=\$?; echo \$rc > /work/grt_sta.log.exit; chmod -R a+rwX /work; exit \$rc"' > /tmp/claude-1000/hbmdie13/sta_grt_otrun_codex.log 2>&1 &
Q=$!
wait "$P"; wait "$Q"
say 'STA finished; classifier by actual bound libraries'
ssh ot-epyc1tb 'D=/srv/opentallas-scratch/claude/hbmdie-v13; python3 "$D/src/tools/hbm_die_sta_classes.py" "$D/plan" "$D"/sta/case/paths_*.txt --case "$D/sta/case" --out "$D/sta_classes_codex.json" --md "$D/sta_classes_codex.md" > "$D/sta_classes_codex.log" 2>&1'
say 'COLLECT classifier complete'
