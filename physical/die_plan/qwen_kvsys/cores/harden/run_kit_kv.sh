#!/bin/bash
# KVG3-CORES (gen_core_kit_kv.py): run one KV core kit through ORFS in docker: synth .. finish (TC), generate_abstract,
# RTL lint (rtl_lint.py, FAIL_PREFLOOR lint rc 8) and sdc_lint gate (CP1-R10, fail-closed) before synth, the DONT_USE-honouring adder map (adder_map_dontuse.py gen, ruling 4
# 10-25) before synth and its DONT_USE netlist check after synth (fail-closed), FF-only GRT hold repair in the FF vclk frame before the goal (FLOW-FIX 10-25, core_flow.py), typed face_guard gates after synth and synth ODB export,
# LEC (lec.py, 10-24) after the synth ODB gate: NOT EQUIVALENT stops the kit, UNPROVEN is recorded in lec/lec.json,
# pin audit of the routed ODB, then corners.tcl at TT / FF (STA + write_timing_model), then signoff.py (SIGNED = closed).  Outputs chowned back.
#   GOAL: finish (full ORFS finish incl. GDS merge: needs every macro GDS) | route (route + do-finish + abstract, no GDS
#   merge: cores with SRAM macros whose GDS is missing) | place (review stop) | post (existing 6_final.odb: abstract,
#   pin audit, corners, signoff only)
#   run_kit_kv.sh KITDIR [GOAL=finish] [MEM_GB=32] [CPUS=16]     (heavy: call it through ot-run --mem MEM_GB)
set -uo pipefail
# CLOCK-RESET 10-25: `make cts` (kit corners tc+bc) BEFORE the FF-only `make grt CORNERS=bc`: make builds every missing
# prerequisite, so without it floorplan..CTS repair ran on FF libraries only and TT setup was never repaired (canary -222.85).
# FLOW-CANARY 10-25 21:10: MCMM kits (config CORNERS = tc bc) run that GRT step in the kit corners (FF vclk frame), not
# CORNERS=bc: an FF-only GRT never repairs TT setup after GRT parasitics (KV core canary c51 TT -57.66; A/B from the c51
# 4_cts checkpoint with tc+bc at GRT: TT -5.91/5 EP, FF hold -1.20/3, DRV 0). Non-MCMM kits keep CORNERS=bc.
# DIE-KV-60 ctlin 11-01: a kit staged with OT_SYNTH_KEEPDC=1 (gen --synth-keepdc / recipe synth_keepdc) patches the
# disposable container synth.tcl with synth_keepdc.py before synth (opt_dff/wreduce -keepdc; fails closed).
# KV-KITS-15 (SIGNOFF-MODES-2, HBM-CORES-R11 form): a kit staged two-mode (gen --two-mode-grt: OT_HOLD_MM=1) patches the
# disposable container with orfs_hold_mm.py first and runs the GRT hold repair in its own two-mode session (scene tc
# TT setup vclk OT_VCLK_TT / scene BC FF hold vclk OT_VCLK_FF, no OT_VCLK_CORNER), checked by kit_modes.py (rc 9).
# Unstaged kits keep the step above unchanged.
# DIE-KV-51 10-31 (default-on, COORD): a kit staged with a plan core tree (core_infra_slice.json + core_sink_census.py,
# master_slice.kit_apply) re-derives the tree's leaf sinks from ITS OWN synth netlist (1_synth_odb.v) before floorplan:
# exact -> nothing written; removed/renamed registers -> master_core_infra.tcl + plan re-compiled; mismatch -> rc 1.
K=$(cd "$1" && pwd); GOAL=${2:-finish}; MEM=${3:-32}; CPUS=${4:-16}
# KW-FIX-32 RESYNTH-GUARD (COORD 20:2x, DIE-QC-91 20:15): a kit assembled by copying stage checkpoints (cp -p keeps the
# old mtimes) re-synthesises under a make-chain goal when config.mk / sdc / rtl are newer than the restored results, so
# the proved netlist silently changes inside the same kit.  Kits that restored results and have no stage-resume plan
# (resume.json = the do-* path) refuse instead; fresh kits (no results yet) and GOAL=synth are unchanged.
if [ "$GOAL" != synth ] && [ "${OT_ALLOW_RESYNTH:-0}" != 1 ] && [ ! -f "$K/resume.json" ]; then
  RG_O=$(ls -tr "$K"/run/results/asap7/*/base/1_*.v "$K"/run/results/asap7/*/base/[2-5]_*.odb 2>/dev/null | head -1)
  if [ -n "$RG_O" ]; then
    RG_N=$(find "$K/config.mk" "$K"/*.sdc "$K/rtl" -type f -newer "$RG_O" 2>/dev/null | head -3 | tr '\n' ' ')
    if [ -n "$RG_N" ]; then
      echo "RESYNTH-GUARD: make goal $GOAL would rebuild from synth: ${RG_N}newer than the restored $(basename "$RG_O"); drive this kit with do-* targets (or OT_ALLOW_RESYNTH=1 to rebuild it)" >&2
      exit 12
    fi
  fi
fi
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
NAME=kvcore-$(basename "$K" | tr -c 'A-Za-z0-9_.-' _ | cut -c1-60)-$$
# FLOW-21 / COORD 11-01 05:1x: the pre-route LEC runs beside place/CTS/route (tools/die_plan/lec_async.sh): NOT
# EQUIVALENT stops the route where it is and the kit waits for the LEC verdict.  OT_LEC_ASYNC=0 = the inline LEC.
LECA=
if { [ "${OT_LEC_ASYNC:-1}" != 0 ] || [ -f "$K/lec_async.on" ] || [ -f "$K/lec_async.identity" ]; } && [ -f "$K/lec_async.sh" ] && [ -f "$K/lec.py" ]; then
  LECA=1; bash "$K/lec_async.sh" start "$K" "$NAME" "$IMAGE" "$MEM" "$CPUS" "$DK" "$GOAL" || exit $?
fi
# KIT-OPS-1 11-13 (COORD: two serdes kits sat >1 h in a blocking inline LEC): async LEC requested but the kit has no
# lec_async.sh = fail fast; the inline LEC runs only when asked for (OT_LEC_ASYNC=0, no lec_async.on/.identity).
if [ -z "$LECA" ] && { [ "${OT_LEC_ASYNC:-1}" != 0 ] || [ -f "$K/lec_async.on" ] || [ -f "$K/lec_async.identity" ]; } && [ -f "$K/lec.py" ] && [ ! -f "$K/lec_async.sh" ]; then
  echo "LEC_ASYNC KIT ERROR: async LEC is on (OT_LEC_ASYNC default 1) but $K/lec_async.sh is missing; refusing the blocking inline LEC after synthesis (can run for hours). Regenerate the kit or copy tools/die_plan/lec_async.sh into it; OT_LEC_ASYNC=0 runs the inline LEC on purpose." >&2
  exit 13
fi
$DK run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  if [ '${OT_GRT183_RESUME:-1}' != 0 ] && [ -f /work/grt183_make.sh ]; then M=\"bash /work/grt183_make.sh \$M\"; fi; \
  rc=0; if [ -f /work/orfs_hold_mm.py ] && grep -q 'def patch_intermediate_power' /work/orfs_hold_mm.py; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts --metrics-only > /work/orfs_metrics.log 2>&1 || { cat /work/orfs_metrics.log; echo 'INTERMEDIATE_POWER optimization unavailable: full power reporting retained'; }; fi; MM=\$(grep -c '^override export OT_HOLD_MM = 1' /work/config.mk); \
  if [ \$MM != 0 ]; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 \
    || { cat /work/orfs_hold_mm.log; echo 'KIT_MODES FAIL orfs_hold_mm patch'; rc=9; }; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && [ -f /work/rtl_lint.py ]; then python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1; rc=\$?; tail -3 /work/rtl_lint.log; if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR lint (implicit / undriven nets, missing module or port; or NOT RUN), see rtl_lint.json' | tee -a /work/FAIL_PREFLOOR; rc=8; fi; fi; \
  if [ \$rc = 0 ]; then python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -3 /work/sdc_lint.log; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then python3 -I /work/selrange_gate.py /work --out /work/selrange.json > /work/selrange.log 2>&1; src=\$?; tail -3 /work/selrange.log; if [ \$src = 1 ]; then rc=1; elif [ \$src != 0 ]; then echo \"SELRANGE NOT RUN (frontend cannot elaborate; see selrange.log)\"; fi; fi; \
  PD=/OpenROAD-flow-scripts/flow/platforms/asap7; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && grep -q '^export ADDER_MAP_FILE = /work/adder_map_dontuse.v' /work/config.mk; then python3 -I /work/adder_map_dontuse.py gen --platform-dir \$PD --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && grep -q '^override export OT_SYNTH_KEEPDC = 1' /work/config.mk; then python3 -I /work/synth_keepdc.py /OpenROAD-flow-scripts/flow/scripts/synth.tcl > /work/synth_keepdc.log 2>&1 \
    || { cat /work/synth_keepdc.log; echo 'FAIL_PREFLOOR synth_keepdc patch (unrecognised ORFS synth.tcl)'; rc=9; }; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then \$M synth; rc=\$?; fi; \
  N=\$(ls /work/run/results/asap7/*/base/1_2_yosys.v 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ $GOAL != post ] && [ -f /work/adder_map_dontuse.py ]; then python3 -I /work/adder_map_dontuse.py check --platform-dir \$PD --netlist \$N --report /work/dont_use_check.json; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && [ -f /work/replica_expect.json ]; then python3 -I /work/replica_check.py --expect /work/replica_expect.json --netlist \$N --out /work/replica_check.json > /work/replica_check.log 2>&1; rc=\$?; cat /work/replica_check.log; [ \$rc = 0 ] || echo 'REPLICA CHECK FAILED: the kit stops before floorplan (replica_check.json)'; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then python3 -I /work/core_preflight.py /work \$N --out /work/face_guard.json > /work/face_guard.log 2>&1; rc=\$?; tail -3 /work/face_guard.log; fi; \
  D=\$(ls /work/run/results/asap7/*/base/1_synth.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then \
    test -n \"\$D\" || rc=103; \
    if [ \$rc = 0 ]; then printf 'read_db %s\\nwrite_verilog /work/1_synth_odb.v\\n' \$D > /work/synth_odb_v.tcl; openroad -exit /work/synth_odb_v.tcl > /work/synth_odb_v.log 2>&1; rc=\$?; fi; \
    if [ \$rc = 0 ]; then python3 -I /work/core_preflight.py /work /work/1_synth_odb.v --out /work/face_guard_odb.json > /work/face_guard_odb.log 2>&1; rc=\$?; tail -3 /work/face_guard_odb.log; fi; \
    if [ \$rc = 0 ] && [ -f /work/replica_expect.json ]; then python3 -I /work/replica_check.py --expect /work/replica_expect.json --netlist /work/1_synth_odb.v --out /work/replica_check_odb.json > /work/replica_check_odb.log 2>&1; rc=\$?; tail -1 /work/replica_check_odb.log; fi; \
    if [ \$rc = 0 ] && [ -f /work/core_sink_census.py ] && [ -f /work/core_infra_slice.json ]; then python3 -I /work/core_sink_census.py refresh /work --slice /work/core_infra_slice.json --netlist /work/1_synth_odb.v --report /work/core_sink_census.json > /work/core_sink_census.log 2>&1; rc=\$?; tail -1 /work/core_sink_census.log; [ \$rc = 0 ] || echo 'CORE_SINK_REFRESH FAIL: the plan core tree does not match this synthesis (core_sink_census.json); the kit stops before floorplan'; fi; \
  fi; \
  if [ \$rc = 0 ] && { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; }; then bash /work/lec_async.sh check-synth /work '$NAME'; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && [ -f /work/lec.py ] && [ -n \"\$N\" ] && { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; } && [ ! -f /work/lec_async.ready ]; then printf '1\\npython3 -I /work/lec.py /work --netlist %s --out /work/lec > /work/lec_run.log 2>&1\\n' \$N > /work/lec_async.ready; echo 'LEC_ASYNC: pre-route LEC runs beside the flow (lec_async.log)'; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ] && [ -f /work/lec.py ] && [ -n \"\$N\" ] && [ ! -f /work/lec_async.on ] && [ ! -f /work/lec_async.identity ]; then python3 -I /work/lec.py /work --netlist \$N --out /work/lec > /work/lec_run.log 2>&1; lr=\$?; tail -1 /work/lec_run.log; \
    if [ \$lr = 1 ]; then echo 'LEC NOT EQUIVALENT: the kit stops (lec/lec.json)'; rc=1; elif [ \$lr != 0 ]; then echo \"LEC WARNING (exit \$lr): not proved, recorded in lec/lec.json; the flow continues\"; fi; fi; \
  HM=\$(sed -n 's/^export OT_HOLD_FF_MARGIN = //p' /work/config.mk); VF=\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk); if [ \$rc = 0 ] && [ -n \"\$HM\" ] && [ -n \"\$VF\" ] && { [ $GOAL = finish ] || [ $GOAL = route ]; }; then \$M cts; rc=\$?; if [ \$rc = 0 ] && [ \$MM != 0 ]; then echo 'GRT step: two-mode session (scene tc TT setup / scene BC FF hold)'; python3 -I /work/kit_modes.py check /work --step grt --session 'tc bc' --hold-repair || rc=9; if [ \$rc = 0 ]; then \$M grt HOLD_SLACK_MARGIN=\$HM; rc=\$?; fi; elif [ \$rc = 0 ]; then GC='CORNER=BC CORNERS=bc'; if grep -q '^export CORNERS = tc bc' /work/config.mk; then GC=''; fi; echo \"GRT step corners: \${GC:-kit MCMM tc+bc} (FF vclk frame)\"; OT_VCLK_CORNER=ff \$M grt \$GC HOLD_SLACK_MARGIN=\$HM; rc=\$?; fi; if [ \$rc != 0 ]; then echo 'GRT hold repair step (FF vclk frame) failed'; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != post ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL = route ]; then \$M do-finish; rc=\$?; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = finish ] || [ $GOAL = route ] || [ $GOAL = post ]; }; then \$M do-generate_abstract; rc=\$?; fi; \
  R=\$(ls -d /work/run/results/asap7/*/base | head -1); \
  O=\$(ls \$R/5_route.odb \$R/6_final.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit_core.py; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_POSTROUTE pin_audit'; fi; fi; \
  if [ \$rc = 0 ] && [ -f \$R/6_final.odb ]; then \
    mkdir -p /work/views; \
    LIBS_TT=\$(\$M print-LIB_FILES 2>/dev/null | sed -n 's/^LIB_FILES[:=] *//p'); \
    LEFS=\"\$(\$M print-TECH_LEF 2>/dev/null | sed -n 's/^TECH_LEF[:=] *//p') \$(\$M print-SC_LEF 2>/dev/null | sed -n 's/^SC_LEF[:=] *//p') \$(\$M print-ADDITIONAL_LEFS 2>/dev/null | sed -n 's/^ADDITIONAL_LEFS[:=] *//p')\"; \
    echo \"LIBS_TT=\$LIBS_TT\" > /work/views/libs.txt; \
    test -n \"\$LIBS_TT\" || { echo \"ERROR: empty LIB_FILES from ORFS make print helper\"; exit 102; }; \
    for c in tt ff; do \
      case \$c in tt) L=\$LIBS_TT;; ff) L=\$(echo \$LIBS_TT | sed 's/_TT_/_FF_/g; s/_tt\.lib/_ff.lib/g');; esac; \
      echo \"LIBS_\$c=\$L\" >> /work/views/libs.txt; \
      OT_CORNER=\$c OT_LIBS=\"\$L\" OT_LEFS=\"\$LEFS\" RES=\$R OT_MOD=\$(sed -n 's/^export DESIGN_NAME = //p' /work/config.mk) OT_OUT=/work/views \
        openroad -exit /work/corners.tcl > /work/views/corner_\$c.log 2>&1 || rc=\$((rc+100)); \
    done; \
    cp \$R/*.lef /work/views/ 2>/dev/null; \
  fi; \
  if { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; }; then bash /work/lec_async.sh wait /work '$NAME' '$GOAL' \$rc; fi; chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
[ -z "$LECA" ] || rc=$(bash "$K/lec_async.sh" finish "$K" "$rc" 1 "$NAME" "$GOAL")
$DK run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
tail -5 "$K/run_$GOAL.log"
# SIGNOFF (coordinator 10-24, main f942bf2f72): uniform tools/die_plan/signoff.py verdict (TT setup / FF hold with the
# standard boundary-hold overlay / DRV / unconstrained / pin-flop spread / sdc_lint / face_guard / DRC + antenna) in
# KIT/signoff/signoff.json; a core is closed only when it says SIGNED (collect_core.py reads it).
if [ $rc = 0 ] && { [ $GOAL = finish ] || [ $GOAL = route ] || [ $GOAL = post ]; } && [ -f "$K/signoff.py" ]; then
  # KW-FIX-32 11-07 (FLOW-CHILD-ETM-CONTEXT at sign-off): parent flow tag for signed child ETMs (env, else K/flow_tag)
  FT=${OT_FLOW_TAG:-$(head -1 "$K/flow_tag" 2>/dev/null)}
  SIGNOFF_DOCKER=${SIGNOFF_DOCKER:-$DK} python3 -I "$K/signoff.py" run --run-dir "$K/run" --kit "$K" \
    --out "$K/signoff" --image "$IMAGE" ${FT:+--flow-tag "$FT"} > "$K/signoff.log" 2>&1
  rc=$?
  grep -E '^SIGNOFF|^  - ' "$K/signoff.log" | head -12
fi
exit $rc
