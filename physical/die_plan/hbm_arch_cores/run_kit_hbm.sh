#!/bin/bash
# ELEM-HBM (gen_core_kit_hbm.py): run one HBM B2r2 core kit through ORFS in docker:
#   RTL lint (fail-closed, native macro/platform interfaces) -> sdc_lint (CP1-R10, fail-closed, vs the image liberty) -> SELRANGE (selrange_gate.py: FAIL stops, NOT RUN warns) -> synth -> face_guard / port-bind (fail closed) -> LEC (lec.py 10-24: NOT EQUIVALENT stops the kit, UNPROVEN recorded in lec/lec.json) ->
#   GOAL (finish) -> generate_abstract -> pin audit -> corners_hbm.tcl at TT / FF
#   (STA, face-flop CK spread, ETM).  Outputs chowned back to the caller.
#   run_kit_hbm.sh KITDIR [GOAL=finish] [MEM_GB=32] [CPUS=16]     (heavy: call through ot-run --mem MEM_GB)
#   GOAL=route: continue detailed route through finish and abstract generation, then sign off.
#   GOAL=post: no flow steps; pin audit + corners + signoff on the run's existing routed ODB (HBM-ELEM 10-24: the
#   corners step used to read 'make print-X' as 'X = ...' but ORFS prints 'X: ...' -> empty libs -> STA-0453 -> rc+100
#   -> signoff skipped on every finished kit).
set -uo pipefail
# HBM-CORES-R11 2026-10-27 (COORD 10:37 ruling 2, SIGNOFF-MODES-2 tools/die_plan/kit_modes.py): ONE TIMING MODE PER
# CORNER.  A kit staged two-mode (OT_HOLD_MM=1: the generator default) patches the disposable container with
# orfs_hold_mm.py before any stage; post_cts_setup.tcl repairs TT setup after the balanced tree; the GRT step repairs
# TT setup (scene tc, vclk OT_VCLK_TT) + FF hold (scene BC, vclk OT_VCLK_FF) in one two-mode session.  Unstaged kits
# keep the FF-only GRT hold repair.  kit_modes.py checks the session first: GRT fails closed (rc 9), CTS advisory.
# HBM-SM-KIDS-2 11-09: face_guard / port_bind read 1_synth.v when it exists (the old `ls a b | head -1` sorted
# its arguments and always took 1_2_yosys.v, where kept nets leave port->net BUFs); 1_2_yosys.v only as fallback.
# HBM-CORES3 10-25 (COORD KIT-CENSUS): sdc_lint / SELRANGE / port-bind / face_guard FAIL = STOP before floorplan
# (marker /work/FAIL_PREFLOOR, rc 3); post-CTS FF hold gate (hold_gate.tcl: WNS < -100 ps or > 2000 endpoints = INFO
# pre-repair screen since KIT-TRIAGE-1/G5 11-01 (COORD 11-01 05:1x / OWNER 12.28b); STOP, marker /work/FAIL_POSTCTS, rc 4,
# only below OT_HOLD_STOP_PS -200 ps reg2reg).  OT_PRE_ROUTE_FF_HOLD (GRT-estimate FF hold < 0 after repair) is INFO, not a stop.
# KW-FIX-4/BAND 11-03 (OWNER 19:12, all dies): the post-GRT per-corner insertion gate (postcts_gate.tcl TT/FF) is
# ADVISORY: a miss (band dev > tol, or no verdict) prints OT_POSTCTS_ADVISORY (postcts_advisory.log), writes no
# FAIL_POSTCTS and the kit routes on to sign-off; signoff.py records the band as signoff.json insertion_band.
# 'export OT_POSTCTS_BAND_GATE = 1' in config.mk restores the old stop (rc 6).  OT_HOLD_GATE above is unchanged.
K=$(cd "$1" && pwd -P); GOAL=${2:-finish}; MEM=${3:-32}; CPUS=${4:-16}
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
# GRT-PATCH-1 / KW-FIX-45 11-11 (COORD class bug VISLAYOUT2-HBM; OWNER edge-only halving default): K/grt_transition_mode  # GRTM
# (written at gen from the gen env OT_GRT_TRANSITION_MODE) or the host env selects the patched router image for the ORFS  # GRTM
# main run ONLY (same block as gen_phys run_kit.sh); LEC, chown and sign-off keep $IMAGE.  No mode = the stock run.  # GRTM
GIMAGE=$IMAGE; GRTD=(); GRTM=${OT_GRT_TRANSITION_MODE:-$(head -1 "$K/grt_transition_mode" 2>/dev/null)}  # GRTM
if [ -n "$GRTM" ]; then  # GRTM
  case "$GRTM" in off|edge|edge_outline) ;; *) echo "FAIL_PREFLOOR grt transition mode $GRTM (off|edge|edge_outline)" | tee -a "$K/FAIL_PREFLOOR"; exit 10;; esac  # GRTM
  GIMAGE=${OT_GRT_IMAGE:-opentallas/orfs:asap7lock-grtoff}  # GRTM
  GID=$(${OT_DOCKER:-docker} image inspect --format "{{.Id}}" "$GIMAGE" 2>/dev/null) && [ -n "$GID" ] || { echo "FAIL_PREFLOOR grt transition image $GIMAGE missing on $(hostname)" | tee -a "$K/FAIL_PREFLOOR"; exit 10; }  # GRTM
  GRTD=(-e OT_GRT_TRANSITION_MODE="$GRTM")  # GRTM
  printf '{"mode": "%s", "image": "%s", "image_id": "%s", "goal": "%s"}\n' "$GRTM" "$GIMAGE" "$GID" "$GOAL" > "$K/grt_transition.json"  # GRTM
  echo "GRTM mode $GRTM image $GIMAGE $GID"  # GRTM
fi  # GRTM
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
# Optional existing XOR SAT backend; async LEC uses docker exec in this same container.
LECSOLVER=()
if [ -n "${OT_LEC_SOLVER:-}" ] && [ -d "$OT_LEC_SOLVER" ]; then
  SOLVERDIR=$(cd "$OT_LEC_SOLVER" && pwd -P)
  LECSOLVER=(-v "$SOLVERDIR:/lecsolver:ro" -e LEC_SOLVER_PATH=/lecsolver)
fi
# HBM-CORES-KITS-13 10-29: the sign-off bundle (tools/die_plan/signoff.py SIGNOFF_BUNDLE, copied by the generator) must be
# in the kit BEFORE any flow step: a hand kit copy with --exclude 'signoff*' dropped signoff.py, the ring V1/V2 flows ran
# ~1 h to 6_final and the post sign-off then died on "can't open signoff.py" (no verdict).  Fail closed up front (rc 10,
# marker FAIL_BUNDLE); restore with: python3 tools/die_plan/signoff.py bundle KITDIR.  Same file list as SIGNOFF_BUNDLE.
if [ "$GOAL" = finish ] || [ "$GOAL" = route ] || [ "$GOAL" = post ]; then
  miss=""; for f in signoff.py sdc_lint.py face_guard.py io_hold_qualification.py pair_skew.tcl clock_family.tcl kit_modes.py \
                    data_droop.py core_io_reference.py; do [ -f "$K/$f" ] || miss="$miss $f"; done
  if [ -n "$miss" ]; then echo "FAIL_BUNDLE sign-off bundle incomplete in $K:$miss (restore: signoff.py bundle $K)" | tee "$K/FAIL_BUNDLE"; exit 10; fi
  rm -f "$K/FAIL_BUNDLE"
fi
NAME=hbmcore-$(basename "$K" | tr -c 'A-Za-z0-9_.-' _ | cut -c1-60)-$$
# FLOW-21 / COORD 11-01 05:1x: the pre-route LEC runs beside place/CTS/route (tools/die_plan/lec_async.sh): NOT
# EQUIVALENT stops the route where it is and the kit waits for the LEC verdict.  OT_LEC_ASYNC=0 = the inline LEC.
LECA=
if { [ "${OT_LEC_ASYNC:-1}" != 0 ] || [ -f "$K/lec_async.on" ] || [ -f "$K/lec_async.identity" ]; } && [ -f "$K/lec_async.sh" ] && [ -f "$K/lec.py" ]; then
  LECA=1; bash "$K/lec_async.sh" start "$K" "$NAME" "$IMAGE" "$MEM" "$CPUS" "$DK" "$GOAL" || exit $?
fi
# Read the repair margin through Make: export/override and assignment precedence must match the flow.
# An unset margin keeps the legacy no-explicit-repair path; malformed explicit values stop before GRT.
$DK run "${LECSOLVER[@]}" --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
  -e HUID=$(id -u) -e HGID=$(id -g) "${GRTD[@]}" -w /OpenROAD-flow-scripts/flow "$GIMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; \
  M='make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=$CPUS'; \
  if [ '${OT_GRT183_RESUME:-1}' != 0 ] && [ -f /work/grt183_make.sh ]; then M=\"bash /work/grt183_make.sh \$M\"; fi; \
  rc=0; if [ -f /work/orfs_hold_mm.py ] && grep -q 'def patch_intermediate_power' /work/orfs_hold_mm.py; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts --metrics-only > /work/orfs_metrics.log 2>&1 || { cat /work/orfs_metrics.log; echo 'INTERMEDIATE_POWER optimization unavailable: full power reporting retained'; }; fi; MM=\$(grep -c '^override export OT_HOLD_MM = 1' /work/config.mk); \
  if [ \$MM != 0 ]; then python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 \
    || { cat /work/orfs_hold_mm.log; echo 'KIT_MODES FAIL orfs_hold_mm patch'; chown -R \$HUID:\$HGID /work; exit 9; }; fi; \
  rc=0; if [ $GOAL != post ]; then rm -f /work/FAIL_PREFLOOR /work/FAIL_POSTCTS; \
  python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1 || { tail -3 /work/rtl_lint.log; echo 'FAIL_PREFLOOR rtl_lint (FAIL or NOT RUN)' | tee -a /work/FAIL_PREFLOOR; chown -R \$HUID:\$HGID /work; exit 8; }; \
  python3 -I /work/sdc_lint.py /work --liberty \$(ls /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*RVT_*.lib* 2>/dev/null | grep -v FAKE) > /work/sdc_lint.log 2>&1; rc=\$?; tail -2 /work/sdc_lint.log; \
  if [ \$rc != 0 ]; then echo 'FAIL_PREFLOOR sdc_lint' | tee -a /work/FAIL_PREFLOOR; fi; \
  SP=; if [ \$rc = 0 ] && [ -f /work/selrange_gate.py ]; then ( python3 -I /work/selrange_gate.py /work --out /work/selrange.json > /work/selrange.log 2>&1; echo \$? > /work/selrange.rc ) & SP=\$!; fi; \
  if [ \$rc = 0 ]; then \$M synth; rc=\$?; fi; \
  N=; for f in /work/run/results/asap7/*/base/1_synth.v /work/run/results/asap7/*/base/1_2_yosys.v; do if [ -f \$f ]; then N=\$f; break; fi; done; \
  if [ \$rc = 0 ] && [ -n \"\$N\" ]; then python3 -I /work/face_guard_core.py \$N /work > /work/face_guard.log 2>&1; fg=\$?; echo \"face_guard rc \$fg\"; \
    if [ \$fg != 0 ]; then echo 'FAIL_PREFLOOR face_guard' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; \
    python3 -I /work/port_bind_core.py \$N /work > /work/port_bind.log 2>&1; pb=\$?; cat /work/port_bind.log; \
    if [ \$pb != 0 ]; then echo 'FAIL_PREFLOOR port_bind' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; fi; \
  if [ \$rc = 0 ] && { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; }; then bash /work/lec_async.sh check-synth /work '$NAME'; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ -f /work/lec.py ] && [ -n \"\$N\" ] && { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; } && [ ! -f /work/lec_async.ready ]; then printf '1\\npython3 -I /work/lec.py /work --netlist %s --out /work/lec > /work/lec_run.log 2>&1\\n' \$N > /work/lec_async.ready; echo 'LEC_ASYNC: pre-route LEC runs beside the flow (lec_async.log)'; fi; \
  if [ \$rc = 0 ] && [ -f /work/lec.py ] && [ -n \"\$N\" ] && [ ! -f /work/lec_async.on ] && [ ! -f /work/lec_async.identity ]; then python3 -I /work/lec.py /work --netlist \$N --out /work/lec > /work/lec_run.log 2>&1; lr=\$?; tail -1 /work/lec_run.log; \
    if [ \$lr = 1 ]; then echo 'FAIL_PREFLOOR LEC NOT EQUIVALENT (lec/lec.json)' | tee -a /work/FAIL_PREFLOOR; rc=3; elif [ \$lr != 0 ]; then echo \"LEC WARNING (exit \$lr): not proved, recorded in lec/lec.json; the flow continues\"; fi; fi; \
  if [ -n \"\$SP\" ]; then wait \$SP; sr=\$(cat /work/selrange.rc 2>/dev/null); echo \"selrange rc \$sr\"; \
    if [ \"\$sr\" = 1 ]; then echo 'FAIL_PREFLOOR selrange' | tee -a /work/FAIL_PREFLOOR; rc=3; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != synth ] && [ $GOAL != floorplan ] && [ $GOAL != place ]; then \$M cts; rc=\$?; \
    C=\$(ls /work/run/results/asap7/*/base/4_cts.odb 2>/dev/null | head -1); \
    if [ \$rc = 0 ] && [ -n \"\$C\" ] && [ -f /work/hold_gate.tcl ]; then \
      S=\$(ls /work/run/results/asap7/*/base/4_cts.sdc 2>/dev/null | head -1); S=\${S:-/work/constraint.sdc}; \
      PLIBS=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n 's/^BC_LIB_FILES *[:=] *//p')\" ODB=\$C SDC=\$S PLATFORM_DIR=/OpenROAD-flow-scripts/flow/platforms/asap7 \
        OT_VCLK_TT=\$(sed -n 's/^export OT_VCLK_TT = //p' /work/config.mk) OT_VCLK_FF=\$(sed -n 's/^export OT_VCLK_FF = //p' /work/config.mk) \
        LAYER_PARASITICS_FILE=\$(sed -n 's/^export LAYER_PARASITICS_FILE = //p' /work/config.mk) \
        openroad -exit /work/hold_gate.tcl > /work/hold_gate.log 2>&1; hgrc=\$?; grep OT_HOLD_GATE /work/hold_gate.log; \
      if [ \$hgrc != 0 ] || ! grep -qE 'OT_HOLD_GATE (PASS|INFO)' /work/hold_gate.log; then grep OT_HOLD_GATE /work/hold_gate.log | sed 's/^/FAIL_POSTCTS /' | tee /work/FAIL_POSTCTS; rc=4; fi; fi; fi; \
  HM=; if [ \$rc = 0 ]; then HMR=\$(\$M print-OT_HOLD_FF_MARGIN 2> /work/hold_margin_read.log); hmr=\$?; \
    if [ \$hmr != 0 ]; then cat /work/hold_margin_read.log; echo 'FAIL_POSTCTS hold margin Make read' | tee -a /work/FAIL_POSTCTS; rc=9; \
    else HM=\$(printf '%s\\n' \"\$HMR\" | sed -nE 's/^OT_HOLD_FF_MARGIN[[:space:]]*[:=][[:space:]]*//p'); \
      if [ -n \"\$HM\" ] && ! python3 -c 'import math,re,sys; s=sys.argv[1].strip(); valid=re.fullmatch(r\"[+-]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)(?:[eE][+-]?[0-9]+)?\",s); x=float(s) if valid else float(\"nan\"); sys.exit(not math.isfinite(x))' \"\$HM\" > /work/hold_margin_value.log 2>&1; then \
        echo \"FAIL_POSTCTS invalid OT_HOLD_FF_MARGIN [\$HM]: expected a finite number\" | tee -a /work/FAIL_POSTCTS; rc=9; fi; fi; fi; \
  HSC=; if [ \$rc = 0 ] && [ -n \"\$HM\" ] && [ -f /work/hold_margin_pick.py ]; then \
    HMP=\$(python3 -I /work/hold_margin_pick.py \"\$HM\" /work/config.mk /work/native_cell_count.json 2> /work/hold_margin_pick.log); echo \"\$HMP\"; \
    case \"\$HMP\" in 'OT_HOLD_PICK hm='*' scope=reg2reg '*|'OT_HOLD_PICK hm='*' scope=nonport '*) \
      HM=\$(printf '%s\\n' \"\$HMP\" | sed -nE 's/^OT_HOLD_PICK hm=([^ ]+) .*/\\1/p'); \
      HSC=OT_HOLD_REPAIR_SCOPE=\$(printf '%s\\n' \"\$HMP\" | sed -nE 's/^OT_HOLD_PICK hm=[^ ]+ scope=([a-z0-9]+) .*/\\1/p');; esac; fi; \
  if [ \$rc = 0 ] && [ -n \"\$HM\" ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then \
    python3 -I /work/kit_modes.py check /work --step cts > /work/kit_modes_cts.log 2>&1 || echo 'KIT_MODES ADVISORY cts (QoR only)'; cat /work/kit_modes_cts.log; \
    if [ \$MM != 0 ]; then python3 -I /work/kit_modes.py check /work --step grt --session 'tc bc' --hold-repair || rc=9; \
      if [ \$rc = 0 ]; then \$M grt HOLD_SLACK_MARGIN=\$HM \$HSC; rc=\$?; fi; \
    else python3 -I /work/kit_modes.py check /work --step grt --session bc --vclk-corner ff --hold-repair || rc=9; \
      if [ \$rc = 0 ]; then OT_VCLK_CORNER=ff \$M grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=\$HM \$HSC; rc=\$?; fi; fi; \
    if [ \$rc = 9 ]; then echo 'FAIL_POSTCTS kit_modes grt (one timing mode per corner)' | tee -a /work/FAIL_POSTCTS; fi; fi; \
  if [ \$rc = 0 ] && [ -n \"\$HM\" ]; then grep -hiE \"hold buffer|RSZ-00(32|46)\" /work/run/logs/asap7/*/base/5_1_grt.log > /work/hold_census.txt 2>/dev/null; echo \"OT_HOLD_CENSUS \$(cat /work/hold_census.txt | tr \"\\n\" \" \")\"; fi; \
  if [ \$rc = 0 ] && [ -n \"\$HM\" ] && { [ $GOAL = route ] || [ $GOAL = finish ]; }; then O5=\$(ls /work/run/results/asap7/*/base/5_1_grt.odb | tail -1); \
    BG=\$(grep -c '^export OT_POSTCTS_BAND_GATE = 1' /work/config.mk); rm -f /work/postcts_advisory.log; \
    for c in TT FF; do OT_POSTCTS_BAND_GATE=\$BG OT_POSTCTS_GRT=1 OT_CORNER=\$c ODB=\$O5 openroad -exit /work/postcts_gate.tcl > /work/postcts_gate_\$c.log 2>&1; \
      grc=\$?; if [ \$grc != 0 ] || ! grep -q 'OT_POSTCTS_GATE.*PASS' /work/postcts_gate_\$c.log; then \
        if [ \$BG != 0 ]; then echo \"FAIL_POSTCTS per-corner insertion gate \$c\" | tee -a /work/FAIL_POSTCTS; rc=6; \
        else echo \"OT_POSTCTS_ADVISORY per-corner insertion gate \$c rc \$grc: \$(grep -h OT_POSTCTS_GATE /work/postcts_gate_\$c.log | tail -1) (not a stop, OWNER 11-03 19:12; band recorded in signoff.json insertion_band)\" | tee -a /work/postcts_advisory.log; fi; fi; done; \
    if grep -q '^export OT_PRE_ROUTE_FF_HOLD = 1' /work/config.mk; then \
      python3 -c 'import json,sys; d=json.load(open(\"/work/postcts_gate_ff.json\")); print(\"FF_PRE_ROUTE_HOLD\",d[\"hold_wns_est_ps\"]); sys.exit(d[\"hold_wns_est_ps\"] < 0)' > /work/pre_route_ff_hold.log 2>&1; \
      if [ \$? != 0 ]; then echo \"PRE_ROUTE_FF_HOLD INFO \$(cat /work/pre_route_ff_hold.log) (GRT estimate after repair; information only, the routed FF hold sign-off decides)\"; fi; fi; fi; \
  if [ \$rc = 0 ] && [ $GOAL != cts ] && [ $GOAL != synth ]; then \$M $GOAL; rc=\$?; fi; \
  if [ \$rc = 0 ] && [ $GOAL = route ]; then \$M do-finish; rc=\$?; fi; \
  if [ \$rc = 0 ] && { [ $GOAL = finish ] || [ $GOAL = route ]; }; then \$M do-generate_abstract; rc=\$?; fi; fi; \
  R=\$(ls -d /work/run/results/asap7/*/base | head -1); \
  O=\$(ls \$R/5_route.odb \$R/6_final.odb 2>/dev/null | tail -1); \
  if [ \$rc = 0 ] && [ -n \"\$O\" ]; then ODB=\$O PINS=/work/pins.json OUT=/work/pin_audit.json openroad -python -exit /work/pin_audit_core.py > /work/pin_audit.log 2>&1; rc=\$?; if [ \$rc != 0 ]; then echo 'FAIL_POSTROUTE pin_audit'; fi; fi; \
  if [ -f \$R/3_place.odb ]; then ODB=\$R/3_place.odb OUT=/work/placed.csv openroad -python -exit /work/dump_placed.py > /work/dump_placed.log 2>&1; cp \$R/ot_face_flops.txt /work/ 2>/dev/null; fi; \
  if [ -f \$R/6_final.odb ]; then \
    mkdir -p /work/views; \
    LIBS_TT=\$(\$M print-TC_LIB_FILES 2>/dev/null | sed -n 's/^TC_LIB_FILES *[:=] *//p' | sed 's/_SS_/_TT_/g; s/_FF_/_TT_/g; s/_ss\.lib/_tt.lib/g; s/_ff\.lib/_tt.lib/g'); \
    LEFS=\"\$(\$M print-TECH_LEF 2>/dev/null | sed -n 's/^TECH_LEF *[:=] *//p') \$(\$M print-SC_LEF 2>/dev/null | sed -n 's/^SC_LEF *[:=] *//p') \$(\$M print-ADDITIONAL_LEFS 2>/dev/null | sed -n 's/^ADDITIONAL_LEFS *[:=] *//p')\"; \
    echo \"LIBS_TT=\$LIBS_TT\" > /work/views/libs.txt; \
    for c in ff tt; do \
      case \$c in tt) L=\$LIBS_TT;; ff) L=\$(echo \$LIBS_TT | sed 's/_TT_/_FF_/g; s/_tt\.lib/_ff.lib/g');; ss) L=\$(echo \$LIBS_TT | sed 's/_TT_/_SS_/g; s/_tt\.lib/_ss.lib/g');; esac; \
      echo \"LIBS_\$c=\$L\" >> /work/views/libs.txt; \
      OT_CORNER=\$c OT_LIBS=\"\$L\" OT_LEFS=\"\$LEFS\" RES=\$R OT_MOD=\$(sed -n 's/^export DESIGN_NAME = //p' /work/config.mk) OT_OUT=/work/views OT_PER=\$(sed -n 's/^create_clock -name clk -period \([0-9.]*\).*/\1/p' /work/constraint.sdc) \
        openroad -exit /work/corners_hbm.tcl > /work/views/corner_\$c.log 2>&1 || rc=\$((rc+100)); \
    done; \
    cp \$R/*.lef /work/views/ 2>/dev/null; \
  fi; \
  if { [ -f /work/lec_async.on ] || [ -f /work/lec_async.identity ]; }; then bash /work/lec_async.sh wait /work '$NAME' '$GOAL' \$rc; fi; chown -R \$HUID:\$HGID /work; exit \$rc" > "$K/run_$GOAL.log" 2>&1
rc=$?
if [ -n "$GRTM" ] && [ $rc = 0 ] && [ "$GOAL" != post ]; then GL=$(ls "$K"/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | tail -1)  # GRTM
  if [ -n "$GL" ] && ! grep -q "GRT-9103\] OT transition-layer mode $GRTM " "$GL"; then echo "FAIL_GRT_MODE $GRTM: $GL has no matching GRT-9103 (mode not applied)" | tee -a "$K/FAIL_GRT_MODE"; rc=1; fi  # GRTM
fi  # GRTM
[ -z "$LECA" ] || rc=$(bash "$K/lec_async.sh" finish "$K" "$rc" 3 "$NAME" "$GOAL")
$DK run --rm -v "$K":/work "$IMAGE" chown -R $(id -u):$(id -g) /work >/dev/null 2>&1
tail -5 "$K/run_$GOAL.log"
# signoff whenever the flow itself finished (a corners/ETM error is rc >= 100 and must not hide the verdict)
if { [ "$GOAL" = finish ] || [ "$GOAL" = route ] || [ "$GOAL" = post ]; } && [ $((rc % 100)) = 0 ] && ls "$K"/run/results/asap7/*/base/6_final.odb >/dev/null 2>&1; then
  SO="$K/signoff"
  [ ! -e "$SO/signoff.json" ] || SO="$K/signoff_$(date +%Y%m%d_%H%M%S)"
  # KW-FIX-32 11-07 (FLOW-CHILD-ETM-CONTEXT at sign-off): parent flow tag for signed child ETMs (env, else K/flow_tag)
  FT=${OT_FLOW_TAG:-$(head -1 "$K/flow_tag" 2>/dev/null)}
  python3 "$K/signoff.py" run --run-dir "$K/run" --kit "$K" --corners tt,ff --out "$SO" --docker "$DK" ${FT:+--flow-tag "$FT"} || rc=1
  # ROUTE-HOLD-PASS (DIE-HBM-97 11-10, COORD vecd-clkroot-r2): opt-in in-flow FF hold repair on the ROUTED RCX parasitics,
  # one pass (tools/die_plan/route_hold_pass.py; generator --route-hold-pass on writes OT_ROUTE_HOLD_PASS = 1 and
  # OT_ROUTE_HOLD_TOOLS).  Runs only when this sign-off's hold_ff FAILs on core-owned endpoints; the pass dir signs off
  # with this runner's GOAL=post (never re-enters here).  Gates unchanged; a kit without the key: unchanged.
  if { [ "$GOAL" = finish ] || [ "$GOAL" = route ]; } && [ -f "$SO/signoff.json" ] && \
     grep -qE '^[[:space:]]*(override[[:space:]]+)?export[[:space:]]+OT_ROUTE_HOLD_PASS[[:space:]]*=[[:space:]]*1[[:space:]]*$' "$K/config.mk"; then
    RHT=$(sed -nE 's/^[[:space:]]*(override[[:space:]]+)?export[[:space:]]+OT_ROUTE_HOLD_TOOLS[[:space:]]*=[[:space:]]*(.*[^[:space:]])[[:space:]]*$/\2/p' "$K/config.mk" | tail -1)
    if [ -f "$RHT/route_hold_pass.py" ]; then
      python3 -I "$RHT/route_hold_pass.py" run "$K" "$SO/signoff.json" --mem "$MEM" --cpus "$CPUS" --lec || rc=1
    else
      echo "ROUTE_HOLD_PASS ERROR: OT_ROUTE_HOLD_TOOLS='$RHT' has no route_hold_pass.py"; rc=1
    fi
  fi
fi
exit $rc
