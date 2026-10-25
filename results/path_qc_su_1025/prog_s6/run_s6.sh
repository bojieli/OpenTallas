#!/bin/bash
# PATH-QC-SU prog_s6 autopilot runner (copy of QC-CQB3 vmr_s6 run_s6.sh): run_s6.sh KIT GOAL [MEM_GB] [THREADS]  (goal route = detailed route -> finish ->
# abstract -> signoff.py tt,ff --ff-vclk auto, i.e. per-corner rebind from sdc_lint.json insertion_ps / insertion_ff_ps).
# Precondition (done by hand before the GEOM REQ, hold_s6.sh): 5_1_grt.odb + route.guide = FF-basis hold repair, gate PASS.
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-route}; MEM=${3:-24}; THR=${4:-8}
grep -q 'S6_GRT_GATE PASS' "$K/s6_grt_gate.txt" || { echo "FAIL_POSTCTS s6 GRT hold gate not PASS" | tee "$K/FAIL_POSTCTS"; exit 6; }
[ -f "$K/postcts_gate_FAIL.txt" ] && { cp "$K/postcts_gate_FAIL.txt" "$K/FAIL_POSTCTS"; exit 6; }
IMAGE=openroad/orfs:asap7lock; TAG=rt6
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) tag $TAG goal $GOAL start $(date -Is)" >> "$K/image.txt"
docker run --rm --name pqsu-prog-s6-$TAG-$$ --cpus=$THR --memory=${MEM}g --memory-swap=${MEM}g -v "$K":/work -w /OpenROAD-flow-scripts/flow $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; rc=0; for t in do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report do-generate_abstract; do make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$THR \$t || { rc=\$?; echo STAGE_FAIL \$t rc \$rc; break; }; done; exit \$rc" > "$K/run_$TAG.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $TAG $(date -Is) rc $rc" >> "$K/image.txt"
tail -3 "$K/run_$TAG.log"
[ $rc = 0 ] || exit $rc
SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --base "$K/run/results/asap7/kq_qfd_dv_s8x_prog_pd40a0/base" --kit "$K" \
  --out "$K/signoff" --corners tt,ff --ff-vclk auto --image "$IMAGE" > "$K/signoff.log" 2>&1
src=$?; grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12; exit $src
