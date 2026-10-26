#!/bin/bash
# PATH-QC-SRAMIF2 autopilot runner for the A1 F (SRAM MY) aspect kits (adapted 2026-10-25 from codex-qc-sramif-1309/btab_s8/run_s6.sh,
# the runner that routed + signed off prog_s8b).  run_kit.sh KIT [GOAL=route] [MEM_GB=24] [THREADS=8]
# Precondition: stageA.sh (CTS + GRT + per-corner bound + FF-basis GRT hold, hold_s6.sh) ended with S6_GRT_GATE PASS and no
# postcts_gate_FAIL.txt; else fail closed (FAIL_POSTCTS, exit 6) -- the autopilot never routes an unreviewed/failed snapshot.
# Then detailed route -> fill -> finish -> abstract -> so_exact/signoff.py tt,ff --ff-vclk auto (per-corner rebind from
# sdc_lint.json insertion_ps / insertion_ff_ps).  Nickname derived from config.mk (no hard-coded kit names).
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-route}; MEM=${3:-24}; THR=${4:-8}
NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$K/config.mk" | tail -1)
[ -n "$NICK" ] || { echo "run_kit: no DESIGN_NICKNAME in config.mk"; exit 2; }
grep -q 'S6_GRT_GATE PASS' "$K/s6_grt_gate.txt" 2>/dev/null || { echo "FAIL_POSTCTS stageA GRT hold gate not PASS" | tee "$K/FAIL_POSTCTS"; exit 6; }
[ -f "$K/postcts_gate_FAIL.txt" ] && { cp "$K/postcts_gate_FAIL.txt" "$K/FAIL_POSTCTS"; exit 6; }
IMAGE=openroad/orfs:asap7lock; TAG=rt6
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) tag $TAG goal $GOAL start $(date -Is)" >> "$K/image.txt"
docker run --rm --name "sramif2-$(basename "$K")-$TAG-$$" --cpus=$THR --memory=${MEM}g --memory-swap=${MEM}g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report do-generate_abstract; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$THR \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_$TAG.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $TAG $(date -Is) rc $rc" >> "$K/image.txt"
tail -3 "$K/run_$TAG.log"
[ $rc = 0 ] || exit $rc
SIGNOFF_DOCKER=docker python3 -I "$K/so_exact/signoff.py" run --base "$K/run/results/asap7/$NICK/base" --kit "$K" \
  --out "$K/signoff" --corners tt,ff --ff-vclk auto --image "$IMAGE" > "$K/signoff.log" 2>&1
src=$?; grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12; exit $src
