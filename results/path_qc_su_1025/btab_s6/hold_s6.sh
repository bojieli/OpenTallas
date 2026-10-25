#!/bin/bash
# PATH-QC-SU btab_s6 (from QC-CQB3 vmr_s6 hold_s6.sh; no pass-1 RCX corr): FF-basis GRT hold step (hold_grt_s6.tcl) + main FLOW pre-route insertion gate (cf/main/postcts_gate.tcl,
# TT/FF pin-reg I on 5_1_grt within +-20 of the bound OT_VCLK_TT/FF; basis = main setRC_rcx_asap7.tcl, the FLOW default;
# kit-basis rc_cal 0.8/0.9 measurement recorded as info).  Logs run_hold6.log, postcts_gate_{TT,FF}[_kit].log.
set -uo pipefail
K=$(cd "$(dirname "$0")" && pwd); IMAGE=openroad/orfs:asap7lock
B=/work/run/results/asap7/kq_qfd_dv_s8x_btab_adj0/base
TT=$(sed -n 's/^export OT_VCLK_TT = //p' "$K/config.mk"); FF=$(sed -n 's/^export OT_VCLK_FF = //p' "$K/config.mk")
echo "image $IMAGE $(docker image inspect --format '{{.Id}}' $IMAGE) host $(hostname) hold6 start $(date -Is) vclk TT $TT FF $FF" >> "$K/image.txt"
docker run --rm --name pqsu-btab-s6-hold-$$ --cpus=8 --memory=20g --memory-swap=20g -v "$K":/work -w /work \
  -e RESULTS_DIR=$B -e OT_RC_CAL=0.8,0.9 -e OT_MSCTS_SPEC=/work/mscts_spec.tcl \
  -e OT_VCLK_TT=$TT -e OT_VCLK_FF=$FF -e OT_S6_MAXBUF=100 -e OT_S6_HOLD_MARGIN=${OT_S6_HOLD_MARGIN:-15} $IMAGE \
  bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 8 -exit /work/hold_grt_s6.tcl > /work/run_hold6.log 2>&1 || exit 1; \
    for c in TT FF; do \
      OT_POSTCTS_GRT=1 OT_CORNER=\$c ODB=$B/5_1_grt.odb LAYER_PARASITICS_FILE=/work/cf/main/setRC_rcx_asap7.tcl openroad -exit /work/cf/main/postcts_gate.tcl > /work/postcts_gate_\$c.log 2>&1; \
      grep -h OT_POSTCTS_GATE /work/postcts_gate_\$c.log || echo \"OT_POSTCTS_GATE \$c no result FAIL\"; \
      cp /work/postcts_gate_\$(echo \$c | tr A-Z a-z).json /work/postcts_gate_\$(echo \$c | tr A-Z a-z)_main.json 2>/dev/null; \
      OT_POSTCTS_GRT=1 OT_CORNER=\$c ODB=$B/5_1_grt.odb LAYER_PARASITICS_FILE=/work/cf/rc_cal.tcl openroad -exit /work/cf/main/postcts_gate.tcl > /work/postcts_gate_\${c}_kit.log 2>&1; \
      grep -h OT_POSTCTS_GATE /work/postcts_gate_\${c}_kit.log | sed 's/^/INFO kit-basis /'; \
      mv /work/postcts_gate_\$(echo \$c | tr A-Z a-z).json /work/postcts_gate_\$(echo \$c | tr A-Z a-z)_kit.json 2>/dev/null; \
      mv /work/postcts_gate_\$(echo \$c | tr A-Z a-z)_main.json /work/postcts_gate_\$(echo \$c | tr A-Z a-z).json 2>/dev/null; done" > "$K/run_hold6_gate.log" 2>&1
rc=$?
docker run --rm -v "$K":/work $IMAGE chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
grep -h 'S6_\|OT_MSCTS_WINDOW' "$K/run_hold6.log" | tail -12; cat "$K/run_hold6_gate.log"
if [ $rc = 0 ] && grep -q '^OT_POSTCTS_GATE.*FAIL' "$K/run_hold6_gate.log"; then
  grep -h '^OT_POSTCTS_GATE' "$K/run_hold6_gate.log" | sed 's/^/FAIL_POSTCTS pre-route insertion gate: /' > "$K/postcts_gate_FAIL.txt"; rc=6; fi
if [ $rc = 0 ] && ! grep -q 'S6_GRT_GATE PASS' "$K/s6_grt_gate.txt"; then rc=4; fi
echo "end hold6 $(date -Is) rc $rc" >> "$K/image.txt"; exit $rc
