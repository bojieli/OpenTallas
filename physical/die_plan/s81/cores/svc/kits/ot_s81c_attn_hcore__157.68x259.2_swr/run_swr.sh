#!/bin/bash
# PATH-S81/HCORE 10-25 runner (autopilot argv: KIT GOAL MEM THREADS; GOAL = cts | grt | finish).  Fail-closed at every step:
#   sdc_lint -> synth -> LEC (lec.py, EQUIVALENT required) -> face_guard -> CTS -> ISOLATED FF hold repair (repair_ff.tcl, a
#   NEW OpenROAD process, FF libs + FF vclk 213.14, placement RC; result replaces 4_cts.odb, the pre-repair CTS kept as
#   4_cts_preff.odb) -> independent TT setup check (833/60/25, vclk 258.53, placement RC) [GOAL=cts stops here]
#   -> GRT (SKIP_INCREMENTAL_REPAIR=1, DRV-only post hook: no mixed-corner hold session) -> post-CTS gate on 5_1_grt
#   [GOAL=grt stops here] -> route -> finish -> abstract -> pin_audit -> corners -> signoff.py; exit status = signoff's.
# Re-entrant: make skips finished stages; the FF repair runs once (ff_repair/repair_ff.tsv); LEC once (lec/lec.json).
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-finish}; MEM=${3:-48}; CPUS=${4:-16}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
NAME=swr-$(basename "$K")-$$
TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$K/config.mk")
SKIP=$(cat "$K/face_guard_skip.txt")
echo "image $IMAGE host $(hostname) start $(date -Is) goal $GOAL" >> "$K/image.txt"
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; rc=0; R=/work/run/results/asap7/hc_ot_s81c_attn_hcore_swr/base; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -2 /work/sdc_lint.log; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  N=\$R/1_2_yosys.v; \
  if [ \$rc = 0 ] && ! grep -q '\"verdict\": \"EQUIVALENT\"' /work/lec/lec.json 2>/dev/null; then python3 -I /work/lec.py /work --netlist \$N --out /work/lec > /work/lec_run.log 2>&1; lr=\$?; tail -1 /work/lec_run.log; [ \$lr = 0 ] || { echo \"PATH_S81_HCORE LEC FAIL rc \$lr\"; rc=4; }; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/count_swsel.py \$N || rc=5; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/face_guard_core.py \$N $TOP '$SKIP' /work/pins.json /work/face_guard.json; rc=\$?; fi; \
  if [ \$rc = 0 ]; then \$M cts; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ ! -f /work/ff_repair/repair_ff.tsv ]; then cp \$R/4_cts.odb \$R/4_cts_preff.odb; \
    PLIBS=\"\$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_FF_*.lib*)\" ODB=\$R/4_cts_preff.odb SDC=\$R/4_cts.sdc FF_SDC=/work/ff_vclk.sdc RCFILE=/work/setRC_rcx.tcl OUT_DIR=/work/ff_repair OT_HOLD_FF_MARGIN=5 \
      openroad -exit -no_init /work/repair_ff.tcl > /work/repair_ff.log 2>&1; rc=\$?; grep -h OT_REPAIR_FF /work/repair_ff.log | tail -3; \
    if [ \$rc = 0 ]; then cp /work/ff_repair/repair_ff.odb \$R/4_cts.odb; else echo 'PATH_S81_HCORE FF repair FAIL'; rc=6; fi; fi; \
  if [ \$rc = 0 ] && [ ! -f /work/tt_check_place.ok ]; then ODB=\$R/4_cts.odb SDC=\$R/4_cts.sdc OUT=/work/tt_check_place.rpt BASIS=placement openroad -exit -no_init /work/tt_check.tcl > /work/tt_check_place.log 2>&1; rc=\$?; grep -h OT_TT_CHECK /work/tt_check_place.log; if [ \$rc = 0 ]; then touch /work/tt_check_place.ok; else echo 'PATH_S81_HCORE TT setup FAIL at placement'; rc=7; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != cts ]; then \$M grt; rc=\$?; \
    if [ \$rc = 0 ]; then O4=\$R/5_1_grt.odb; rm -f /work/FAIL_POSTCTS; for c in TT FF; do OT_POSTCTS_GRT=1 OT_CORNER=\$c ODB=\$O4 openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_\$c.log 2>&1; grep -h OT_POSTCTS_GATE /work/postcts_gate_\$c.log || echo \"OT_POSTCTS_GATE \$c no result FAIL\" >> /work/postcts_gate_\$c.log; done; if grep -hq 'OT_POSTCTS_GATE.*FAIL' /work/postcts_gate_TT.log /work/postcts_gate_FF.log; then grep -h OT_POSTCTS_GATE /work/postcts_gate_*.log > /work/FAIL_POSTCTS; rc=3; fi; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL = finish ]; then \$M route; rc=\$?; \
    if [ \$rc = 0 ]; then \$M do-finish && \$M do-generate_abstract; rc=\$?; fi; \
    O=\$(ls \$R/6_final.odb 2>/dev/null | tail -1); \
    if [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; pr=\$?; [ \$pr = 0 ] || rc=8; \
      for c in TT FF; do OT_CORNER=\$c DESIGN_NAME=$TOP ODB=\$O SPEF=\${O%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_\$c.log 2>&1; done; fi; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
docker run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $(date -Is) rc $rc" >> "$K/image.txt"
tail -8 "$K/run_$GOAL.log"
if [ $rc = 0 ] && [ "$GOAL" = finish ]; then
  SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$K/signoff" --image "$IMAGE" > "$K/signoff.log" 2>&1
  rc=$?
  grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12
  echo "PATH_S81_HCORE signoff exit $rc"
fi
exit $rc
