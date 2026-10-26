#!/bin/bash
# Synth stage of a TKM no-ID kit built by build_kit.py: sdc_lint -> SELRANGE -> make synth -> face_guard -> port-bind.
# Same steps/order as run_kit_hbm.sh GOAL=synth, minus the in-kit LEC (LEC runs separately with the pinned lec.py).
#   run_tkm_kit_synth.sh KIT [MEM_GB=32] [CPUS=8]       (heavy: via ot-run --mem)
set -uo pipefail
K=$(cd "$1" && pwd -P); MEM=${2:-32}; CPUS=${3:-8}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
[ -e "$K/run" ] && { echo "NOT RUN: $K/run exists"; exit 2; }
$DK run --rm --name "tkmsynth-$(basename "$K" | tr -c 'A-Za-z0-9_.-' _ | cut -c1-50)-$$" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" \
  -v "$K":/work -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -2 /work/sdc_lint.log; \
  if [ \$rc = 0 ]; then python3 -I /work/selrange_gate.py /work --out /work/selrange.json > /work/selrange.log 2>&1; sr=\$?; echo selrange rc \$sr; [ \$sr = 1 ] && rc=3; fi; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_synth.v /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | head -1); \
  if [ \$rc = 0 ] && [ -n \"\$N\" ]; then python3 -I /work/face_guard_core.py \$N /work > /work/face_guard.log 2>&1; fg=\$?; echo face_guard rc \$fg; \
    python3 -I /work/port_bind_core.py \$N /work > /work/port_bind.log 2>&1; pb=\$?; cat /work/port_bind.log; [ \$fg = 0 ] && [ \$pb = 0 ] || rc=3; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_synth.log" 2>&1
rc=$?; tail -6 "$K/run_synth.log"; echo "TKM_KIT_SYNTH rc=$rc"; exit $rc
