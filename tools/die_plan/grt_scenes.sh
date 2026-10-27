#!/bin/bash
# GENERATED-COPY of tools/die_plan/grt_scenes.sh (FLOW-MCMM-GRT 2026-10-27): the kit's GRT timing-repair step.
#
# Bug (S81-ECO-2, CHECKED on ot_s81sl_vq e1): the FF-only GRT step (OT_VCLK_CORNER=ff make grt CORNER=BC CORNERS=bc)
# loads the FF libraries only, so repair_timing on the global-route parasitics never sees TT setup ('No setup
# violations found' at FF): vq signed off TT -64.57 / 88 EP where the r12 tc+bc GRT step had repaired 85 EP.  A
# single-mode tc+bc session is no fix either: OpenSTA's vclk source latency is per MODE, so one of TT setup / FF hold
# is timed in the other corner's IO frame (KV MCMM-GRT bug, SIGNOFF-MODES-1).
#
# Fix: a two-kit-corner kit (config.mk CORNERS = tc bc with TC_LIB_FILES / BC_LIB_FILES) repairs at GRT in TWO SCENES
# (tools/orfs_hold_mm.tcl, OpenSTA define_scene / read_sdc -mode, per-scene liberty):
#   scene tc (mode ss): TT libraries + constraint.sdc as the stage maintains it (vclk OT_VCLK_TT) -> TT SETUP
#   scene BC (mode ff): FF libraries + grt_ff_scene.sdc (vclk = OT_VCLK_FF, or for a 'rebind' kit the measured FF
#                       pin-register mean on GRT RC, the frame signoff.py times FF hold in)  -> FF HOLD
# repair_timing then repairs TT setup and FF hold together (each hold cell placed under the TT setup guard).  Only the
# 5_1_grt stage runs two-scene (env, not config.mk); every other stage and the shared die STA modes are unchanged.
# Kits that are not two-corner keep the FF-only step.
#   M="<make cmd>" bash /work/grt_scenes.sh [HOLD_MARGIN_PS]
set -uo pipefail
K=${OT_KIT_DIR:-/work}
HM=${1:-}
M=${M:?grt_scenes: M (make command) unset}
SCRIPTS=${OT_ORFS_SCRIPTS:-/OpenROAD-flow-scripts/flow/scripts}
cfgv() { sed -n "s/^[[:space:]]*\(override[[:space:]]\+\)\?export[[:space:]]\+$1[[:space:]]*[:?]\?=[[:space:]]*//p" "$K/config.mk" | tail -1; }
HMARG=""; if [ -n "$HM" ]; then HMARG="HOLD_SLACK_MARGIN=$HM"; fi
CS=$(cfgv CORNERS | tr 'A-Z' 'a-z' | xargs)
if [ "$CS" = "tc bc" ] && [ -n "$(cfgv TC_LIB_FILES)" ] && [ -n "$(cfgv BC_LIB_FILES)" ]; then
  if [ "$(cfgv OT_HOLD_MM)" = "1" ]; then
    # kit staged two-mode for every stage (kit_modes.py stage): its own session already is tc setup / BC hold
    echo "GRT_SCENES kit staged two-mode (OT_HOLD_MM=1): kit session"
    exec $M grt $HMARG
  fi
  for f in orfs_hold_mm.py orfs_hold_mm.tcl grt_ff_scene.sdc vclk_corner.tcl vclk_measured_hold.tcl vclk_ref.py; do
    if [ ! -f "$K/$f" ]; then echo "GRT_SCENES FAIL kit lacks $f (regenerate the kit with main tools)"; exit 9; fi
  done
  python3 -I "$K/orfs_hold_mm.py" "$SCRIPTS" "$K/orfs_hold_mm.tcl" > "$K/orfs_hold_mm.log" 2>&1 \
    || { cat "$K/orfs_hold_mm.log"; echo "GRT_SCENES FAIL orfs_hold_mm patch"; exit 9; }
  if [ -f "$K/kit_modes.py" ]; then
    python3 -I "$K/kit_modes.py" check "$K" --step grt --session 'tc bc' --scenes --hold-repair || exit 9
  fi
  echo "GRT_SCENES two-scene GRT repair: scene tc TT setup (vclk OT_VCLK_TT $(cfgv OT_VCLK_TT)) + scene BC FF hold (grt_ff_scene.sdc, OT_VCLK_FF $(cfgv OT_VCLK_FF)) ${HMARG:-kit HOLD_SLACK_MARGIN}"
  OT_HOLD_MM=1 OT_MM_SETUP_CORNER=tc OT_MM_FF_SDC="$K/grt_ff_scene.sdc" OT_GRT_SCENES=1 $M grt "CORNERS=tc BC" $HMARG
  rc=$?
  if [ $rc = 0 ]; then grep -h "OT_HOLD_MM sync\|OT_HOLD_MM after repair\|OT_GRT_SCENES" "$K"/run/logs/asap7/*/base/5_1_grt.log 2>/dev/null | tail -6; fi
  exit $rc
fi
echo "GRT_SCENES FF-only GRT hold repair (kit corners '${CS}', not a two-corner kit)"
if [ -f "$K/kit_modes.py" ]; then
  python3 -I "$K/kit_modes.py" check "$K" --step grt --session bc --vclk-corner ff --hold-repair || exit 9
fi
OT_VCLK_CORNER=ff $M grt CORNER=BC CORNERS=bc $HMARG
