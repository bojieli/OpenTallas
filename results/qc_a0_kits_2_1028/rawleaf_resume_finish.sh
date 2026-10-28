#!/usr/bin/env bash
# QC-A0-KITS-2 2026-10-28: route + sign-off continuation of the GEOM-PASS rawleaf rst145 placement (CODEX-PV 10-27 14:58).
# Same steps as the kit run_kit.sh after LEC (CTS -> FF-only GRT hold repair -> route -> finish -> abstract -> pin audit
# -> corners -> signoff.py), with make -o on the reviewed 3_place.odb/.sdc so the placement is never redone.
# Pre-synth gates (rtl_lint/sdc_lint/selrange/face_guard/LEC) were run on the base kit 23a47eb989 (base_lec/lec.json EQ).
#   resume_finish.sh KITDIR [GOAL=finish] [MEM_GB=24] [CPUS=8]
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-finish}; MEM=${3:-24}; CPUS=${4:-8}
case "$GOAL" in cts|grt|route|finish) ;; *) echo "resume_finish: goal $GOAL not allowed" >&2; exit 2;; esac
python3 - "$K" <<'PY' || exit 2
import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);m=json.load(open(k/'RAWLEAF_RESUME.json'))
for n,e in [(m['placement'],m['placement_sha256']),(m['placement'].replace('.odb','.sdc'),m['sdc_sha256'])]:
    if hashlib.sha256((k/n).read_bytes()).hexdigest()!=e: raise SystemExit('reviewed placement/SDC changed: '+n)
for n,e in m['static_inputs_sha256'].items():
    if hashlib.sha256((k/n).read_bytes()).hexdigest()!=e: raise SystemExit('static input changed: '+n)
print('resume_finish: reviewed placement + static inputs hash-checked')
PY
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}; DOCKER=${OT_DOCKER:-docker}; NAME=kqc-rawleaf-rst145-$GOAL-$$
TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$K/config.mk")
B=/work/run/results/asap7/kq_ot_qwen_tile_lsl_rawfault_m3_a0k/base
echo "image $IMAGE $($DOCKER image inspect --format '{{.Id}}' $IMAGE) host $(hostname) start $(date -Is) runner resume_finish.sh" > "$K/image.txt"
$DOCKER run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS -o $B/3_place.odb -o $B/3_place.sdc'; rc=0; \
  HM=\$(sed -n 's/^export OT_HOLD_FF_MARGIN = //p' /work/config.mk); VF=\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk); \
  \$M cts; rc=\$?; if [ \$rc != 0 ]; then echo 'CTS (kit corners) failed'; fi; \
  if [ \$rc = 0 ] && [ -n \"\$HM\" ] && [ -n \"\$VF\" ] && [ $GOAL != cts ]; then OT_VCLK_CORNER=ff \$M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=\$HM; rc=\$?; if [ \$rc != 0 ]; then echo 'FF-only GRT hold repair (FF vclk frame) failed'; fi; fi; \
  if [ \$rc = 0 ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then \$M do-finish && \$M do-generate_abstract; rc=\$?; fi; \
  O=\$(ls $B/5_route.odb $B/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; fi; \
  F=\$(ls $B/6_final.odb 2>/dev/null | tail -1); \
  if [ -n \"\$F\" ]; then for c in TT FF; do OT_CORNER=\$c DESIGN_NAME=$TOP ODB=\$F SPEF=\${F%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_\$c.log 2>&1; done; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
$DOCKER run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $(date -Is) rc $rc" >> "$K/image.txt"
tail -5 "$K/run_$GOAL.log"
if [ $rc = 0 ] && { [ $GOAL = route ] || [ $GOAL = finish ]; } && [ -f "$K/signoff.py" ]; then
  SIGNOFF_DOCKER="$DOCKER" python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff \
    --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1
  grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12
fi
exit $rc
