#!/bin/bash
set -eu
P=/srv/opentallas-scratch/claude/qwen-clock-phase-1019/baseline_measure
C=/srv/opentallas-scratch/claude/codex-qwen-dieclk2-1019
mkdir -p "$P/exact_geometry"
docker run --rm --cpus=2 --memory=24g -v "$C:/work:ro" -v "$P:/phase" -w /phase openroad/orfs:asap7lock bash -lc '
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 openroad -python -no_init -exit /phase/tools/die_clock/build.py --odb /work/floorplan_ck.odb --libs /work/libs_tt.txt --spec /phase/spec_exact_geometry.json --targets /work/targets.json --out /phase/exact_geometry --geometry-only --write-odb > /phase/exact_geometry/replay.log 2>&1
'
