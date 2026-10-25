#!/bin/bash
# KITS-SPARE/LB 2026-10-25 successor runner for the S81 split cores ve_s / ve_m (FLOW rebuild recipe on main tools):
# sdc_lint -> rtl_lint -> synth -> face_guard + reg_fanout gates -> floorplan/place (pin regs + reset entry FIRM at
# pins) -> CTS (tap_balance to bound TT, F4 leaf affinity; no CTS repair) -> FF structural hold gate (hold_gate.tcl)
# -> FF-only GRT hold repair in the FF frame (OT_VCLK_CORNER=ff, calibrated RC) -> pre-route insertion gate TT/FF
# -> [GOAL finish] route -> finish -> abstract -> corners -> signoff.py (--ff-vclk rebind via clock_binding).
# argv: KIT GOAL(grt|finish) MEM THREADS  (autopilot form).  Heavy: through ot-run only.
set -uo pipefail
K=$(cd "$1" && pwd); GOAL=${2:-finish}; MEM=${3:-32}; CPUS=${4:-16}
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
NAME=lbkit-$(basename "$K")-$$
TOP=$(sed -n "s/^export DESIGN_NAME = //p" "$K/config.mk"); SKIP=$(cat "$K/face_guard_skip.txt")
echo "image $IMAGE host $(hostname) goal $GOAL start $(date -Is)" >> "$K/image.txt"
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS\"; rc=0; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -2 /work/sdc_lint.log; \
  if [ \$rc != 0 ]; then echo FAIL_PREFLOOR sdc_lint | tee -a /work/FAIL_PREFLOOR; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1; rc=\$?; tail -2 /work/rtl_lint.log; if [ \$rc != 0 ]; then echo FAIL_PREFLOOR rtl_lint | tee -a /work/FAIL_PREFLOOR; rc=8; fi; fi; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ ! -f /work/face_guard.json ]; then python3 -I /work/face_guard_core.py \$N $TOP '$SKIP' /work/pins.json /work/face_guard.json; rc=\$?; if [ \$rc != 0 ]; then echo FAIL_PREFLOOR face_guard | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  D=\$(ls /work/run/results/asap7/*/base/1_synth.odb 2>/dev/null | tail -1); if [ \$rc = 0 ] && [ ! -f /work/face_guard_odb.json ]; then printf 'read_db %s\\nwrite_verilog /work/1_synth_odb.v\\n' \$D > /work/synth_odb_v.tcl; openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1; python3 -I /work/face_guard_core.py /work/1_synth_odb.v $TOP '$SKIP' /work/pins.json /work/face_guard_odb.json; rc=\$?; if [ \$rc != 0 ]; then echo FAIL_PREFLOOR face_guard_odb | tee -a /work/FAIL_PREFLOOR; fi; fi; \
  if [ \$rc = 0 ] && [ ! -f /work/reg_fanout.json ]; then python3 -I /work/reg_fanout_gate.py \$N --out /work/reg_fanout.json > /work/reg_fanout.log 2>&1; rc=\$?; head -6 /work/reg_fanout.log; if [ \$rc != 0 ]; then echo FAIL_PREFLOOR reg_fanout | tee -a /work/FAIL_PREFLOOR; rc=7; fi; fi; \
  if [ \$rc = 0 ]; then \$M cts; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ ! -f /work/hold_gate.log ]; then C=\$(ls /work/run/results/asap7/*/base/4_cts.odb | head -1); S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc | head -1); \
    PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n \"s/^BC_LIB_FILES *[:=] *//p\")\" ODB=\"\$C\" SDC=\"\$S\" PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
      OT_VCLK_TT=\$(sed -n \"s/^export OT_VCLK_TT = //p\" /work/config.mk) OT_VCLK_FF=\$(sed -n \"s/^export OT_VCLK_FF = //p\" /work/config.mk) \
      LAYER_PARASITICS_FILE=/work/setRC_rcx.tcl openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; rc=\$?; tail -3 /work/hold_gate.log; \
    if [ \$rc != 0 ]; then echo FAIL_POSTCTS FF structural hold gate | tee -a /work/FAIL_POSTCTS; rc=4; fi; fi; \
  if [ \$rc = 0 ] && [ ! -f /work/run/results/asap7/kr_${TOP}_k/base/5_1_grt.odb ]; then OT_VCLK_CORNER=ff \$M grt CORNER=BC CORNERS=bc; rc=\$?; \
    if [ \$rc = 0 ]; then O5=\$(ls /work/run/results/asap7/*/base/5_1_grt.odb | tail -1); rm -f /work/FAIL_POSTCTS; for c in TT FF; do OT_POSTCTS_GRT=1 OT_CORNER=\$c ODB=\$O5 openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_\$c.log 2>&1; grep -h OT_POSTCTS_GATE /work/postcts_gate_\$c.log || echo \"OT_POSTCTS_GATE \$c no result FAIL\" >> /work/postcts_gate_\$c.log; done; \
      grep -h OT_LEAF_AFF /work/run/logs/asap7/*/base/4_1_cts.log; if grep -hq \"OT_POSTCTS_GATE.*FAIL\" /work/postcts_gate_TT.log /work/postcts_gate_FF.log; then grep -h OT_POSTCTS_GATE /work/postcts_gate_*.log | sed \"s/^/FAIL_POSTCTS pre-route insertion gate: /\" > /work/FAIL_POSTCTS; rc=6; fi; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL = finish ]; then \$M route; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL = finish ]; then \$M do-finish && \$M do-generate_abstract; rc=\$?; fi; \
  O=\$(ls /work/run/results/asap7/*/base/6_final.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit.py; \
    for c in TT FF; do OT_CORNER=\$c DESIGN_NAME=$TOP ODB=\$O SPEF=\${O%.odb}.spef openroad -exit /work/corners.tcl > /work/sta_\$c.log 2>&1; done; fi; \
  chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
docker run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
echo "end $(date -Is) goal $GOAL rc $rc" >> "$K/image.txt"
tail -5 "$K/run_$GOAL.log"
if [ $rc = 0 ] && [ $GOAL = finish ]; then
  SO="$K/signoff"; [ ! -e "$SO/signoff.json" ] || SO="$K/signoff_$(date +%Y%m%d_%H%M%S)_$$"
  SIGNOFF_DOCKER=docker python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$SO" --image "$IMAGE" > "$SO.log" 2>&1
  grep -E "^SIGNOFF|^  - " "$SO.log" | head -12
fi
exit $rc
