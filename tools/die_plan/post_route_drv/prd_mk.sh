#!/bin/bash
# FLOW-CLOCK-R7 2026-10-29: make one pass dir of the shared post-route drive repair (die-agnostic, opt-in; nothing calls
# it by default).  Derived from physical/die_plan/qwen_kvsys/cores/harden/eco/mk_eco.sh OT_ECO_FROM=grt (which stays
# byte-identical for KV); differences: the kit's OWN runner/corners files are kept (no KV runner copied over a QC/S81/
# HEAD/HBM kit), the hook is prd_hook.tcl, the two-mode hold session files are staged for OT_HOLD_MM=1 kits, and the
# source parasitics can be a later pass's RCX SPEF.
#   prd_mk.sh KIT OUT VARIANT SO_DIR [SPEF]
# KIT     a ROUTED core kit (run/results/asap7/<nick>/base/5_1_grt.odb + the routed 6_final.spef), or a pass dir of this tool
# OUT     new dir (never relaunched into)
# VARIANT m<N>: tc+bc two-mode (kit OT_HOLD_MM=1), setup margin 10, hold margin N ps | b<N>: FF-only (kit without MM)
# SO_DIR  repo checkout whose tools/ supply signoff.py bundle, clk_freeze*, orfs_hold_mm.*
# SPEF    parasitics the repair reads (default KIT's routed 6_final.spef; pass 2 = pass 1's re-extracted RCX)
set -euo pipefail
KIT=$(cd "$1" && pwd); OUT=$2; V=$3; SO=$(cd "$4" && pwd); SPEF=${5:-}
HERE=$(cd "$(dirname "$0")" && pwd)
test ! -e "$OUT" || { echo "prd_mk: $OUT exists (never relaunch into a run dir)"; exit 2; }
RS=$(ls -d $KIT/run/results/asap7/*/base); NICK=$(basename $(dirname $RS))
test -n "$SPEF" || SPEF=$RS/6_final.spef
test -f $RS/5_1_grt.odb -a -f "$SPEF" || { echo "prd_mk: $RS lacks 5_1_grt.odb / $SPEF"; exit 2; }
HM=${V:1}; [[ "$HM" =~ ^[0-9]+$ && ${V:0:1} =~ ^[bm]$ ]] || { echo "prd_mk: variant $V: want b<hold margin ps> or m<hold margin ps>"; exit 2; }
mkdir -p $OUT
rsync -a --exclude /run --exclude /views --exclude /signoff --exclude '/signoff_*' --exclude '/signoff*.log' \
  --exclude '/run_*.log' --exclude /rc.txt --exclude '/pass[0-9]*' --exclude '/prd_*.json' --exclude '/prd_*.log' $KIT/ $OUT/
B=$OUT/run/results/asap7/$NICK/base
mkdir -p $B $OUT/run/logs/asap7/$NICK/base $OUT/run/reports/asap7/$NICK/base $OUT/run/objects/asap7/$NICK/base
cp $RS/5_1_grt.odb $B/4_cts.odb
cp "$SPEF" $B/6_final.spef
for f in 1_2_yosys.v 1_synth.v clock_period.txt mem.json ot_face_flops.txt ot_unreg_pins.txt; do
  test -f $RS/$f && cp $RS/$f $B/; done
rsync -a $KIT/run/objects/asap7/$NICK/base/ $OUT/run/objects/asap7/$NICK/base/ 2>/dev/null || true
{ cat $OUT/constraint.sdc; echo 'set_propagated_clock [all_clocks]'; } > $B/4_cts.sdc
for f in prd_hook.tcl prd_count.tcl; do cp $HERE/$f $OUT/; done
for f in clk_freeze.tcl clk_dump_db.tcl clk_geom_diff.py clk_freeze_check.sh kit_modes_eco.tcl; do cp "$SO/tools/die_plan/$f" $OUT/; done
MM=$(sed -n 's/^override export OT_HOLD_MM = //p; s/^export OT_HOLD_MM = //p' $OUT/config.mk | tail -n 1)
if [ "${MM:-0}" = 1 ]; then
  # two-mode session (fix 1): the kit's own patcher if staged, else the repo's
  for f in orfs_hold_mm.py orfs_hold_mm.tcl; do test -f $OUT/$f || cp "$SO/tools/$f" $OUT/; done
  [ ${V:0:1} = m ] || { echo "prd_mk: kit is two-mode (OT_HOLD_MM=1): use variant m<N>"; exit 2; }
fi
# ECO hook, then the kit's own post-GRT IO hook when it has one (as mk_eco.sh)
{ echo 'source /work/kit_modes_eco.tcl'; echo 'source /work/prd_hook.tcl'; echo 'kit_modes_eco_done';
  test -f $OUT/grt_post_core.tcl && echo 'source /work/grt_post_core.tcl'; } > $OUT/eco_post.tcl
python3 -I "$SO/tools/die_plan/signoff.py" bundle "$OUT" || exit 1
ML_TT=$(sed -n 's/^export ADDITIONAL_LIBS = //p' $OUT/config.mk | tail -n 1)
ML_FF=$(echo "$ML_TT" | sed 's/_tt\.lib/_ff.lib/g')
for f in $ML_FF; do test -f "$OUT/${f#/work/}" || { echo "prd_mk: missing FF macro lib $f"; exit 2; }; done
if ! grep -q '^# OT_PRD post-route drive repair' $OUT/config.mk; then
cat >> $OUT/config.mk <<CFG
# OT_PRD post-route drive repair (tools/die_plan/post_route_drv, variant $V)
override export POST_GLOBAL_ROUTE_TCL = /work/eco_post.tcl
export TC_LIB_FILES = \$(TC_NLDM_LIB_FILES) $ML_TT
export BC_LIB_FILES = \$(BC_NLDM_LIB_FILES) $ML_FF
override export PWR_NETS_VOLTAGES =
override export GND_NETS_VOLTAGES =
CFG
fi
if [[ ${V:0:1} = b ]] && ! grep -q '^override export CORNERS = bc' $OUT/config.mk; then
  printf 'override export OT_HOLD_MM = 0\noverride export CORNERS = bc\n' >> $OUT/config.mk
fi
case ${V:0:1} in
  b) printf "OT_MAX_FANOUT=24\nOT_SLEW_MARGIN=20\nOT_SETUP_MARGIN=\nOT_HOLD_MARGIN=$HM\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=BC CORNERS=bc'\n" ;;
  m) printf "OT_MAX_FANOUT=24\nOT_SLEW_MARGIN=20\nOT_SETUP_MARGIN=10\nOT_HOLD_MARGIN=$HM\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=TC CORNERS=\"tc bc\"'\n" ;;
esac > $OUT/variant.env
[ ${V:0:1} = b ] && [ -f $OUT/vclk_corner.tcl ] && echo "OT_VCLK_CORNER=ff" >> $OUT/variant.env
[ -n "${OT_PAD_MASTERS:-}" ] && echo "OT_PAD_MASTERS='$OT_PAD_MASTERS'" >> $OUT/variant.env
echo "OT_HOLD_MM_KIT=${MM:-0}" >> $OUT/variant.env
echo "OT_ECO_FROM=grt" >> $OUT/variant.env   # clk_freeze_check.sh --pre-unrouted (always the pre-DRT start)
printf '{"tool": "post_route_drv", "variant": "%s", "source_kit": "%s:%s", "source_grt": "%s/5_1_grt.odb", "parasitics": "%s", "signoff_tools": "%s"}\n' \
  $V "$(hostname)" $KIT $RS "$SPEF" "$SO" > $OUT/PRD.json
echo "prd pass dir ready $OUT ($(du -sh $OUT | cut -f1))"
