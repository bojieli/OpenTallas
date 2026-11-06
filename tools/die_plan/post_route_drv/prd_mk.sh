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
#         | t<N>: TT-only setup + DRV, no hold repair (kit without MM; KW-ECO-1)
# SO_DIR  repo checkout whose tools/ supply signoff.py bundle, clk_freeze*, orfs_hold_mm.*
# SPEF    parasitics the repair reads (default KIT's routed 6_final.spef; pass 2 = pass 1's re-extracted RCX)
# env OT_PRD_FROM=grt (default) | route  (FLOW-12 10-30, COORD 20:13 opt-in; DIE-QC-50 P6/P8eco recipe, BTAB SIGNED):
#   grt   = seed the ECO with the pre-DRT 5_1_grt.odb, ONE full detailed route afterwards (FLOW-SHARED-10 form);
#   route = seed it with the ROUTED 5_2_route.odb: the hook rips only the wires of nets whose connectivity the ECO
#           changed or whose cells it moved/re-mastered (vs that routed DB) and DRT routes those incrementally; every
#           other net (all clock nets) keeps its signed-off metal, and clk_freeze_check.sh diffs clock WIRES too.
#   final = route-keeping as route, seeded with the kit's signed 6_final.odb (fillers removed in the hook): for a kit whose
#           6_final.{odb,spef} is a post-route ECO of 5_2_route.odb (DIE-S81-50 11-03, S81 l4 hxeco_* hold ECO), where
#           the route seed does not match the SPEF (prd_hook.tcl OT_PRD STAGE_MISMATCH; eco_loop.py retries with final).
# OT_PRD_PROTECT_NETS = Tcl list of exact measured data nets to preserve during
# repair; persisted through both passes. Does not waive any signoff checks.
set -euo pipefail
KIT=$(cd "$1" && pwd -P); OUT=$2; V=$3; SO=$(cd "$4" && pwd); SPEF=${5:-}
HERE=$(cd "$(dirname "$0")" && pwd)
test ! -e "$OUT" || { echo "prd_mk: $OUT exists (never relaunch into a run dir)"; exit 2; }
RS=$(ls -d $KIT/run/results/asap7/*/base); NICK=$(basename $(dirname $RS))
test -n "$SPEF" || SPEF=$RS/6_final.spef
FROM=${OT_PRD_FROM:-grt}
case $FROM in grt) SRC=5_1_grt.odb ;; route) SRC=5_2_route.odb ;; final) SRC=6_final.odb ;;
  *) echo "prd_mk: OT_PRD_FROM=$FROM: want grt|route|final"; exit 2 ;; esac
test -f $RS/$SRC -a -f "$SPEF" || { echo "prd_mk: $RS lacks $SRC / $SPEF"; exit 2; }
# FLOW-24 11-03 (stale-seed class, before the session; with DIE-S81-50's in-hook stage check as the backstop): the
# routed SPEF and the seed must carry ONE netlist.  A kit whose 6_final.{odb,spef} were rewritten by a later post-route
# ECO keeps pre-ECO 5_1_grt/5_2_route DBs (S81 l4: 1327 hxeco_*/slweco_* cells; l0 3341, caprt 33 lweco_*).  prd_seed.py
# proves it in ~20 s from the DB/SPEF name tables, so the session is staged as OT_PRD_FROM=final (route-keeping from the
# signed 6_final.odb) at once instead of failing STAGE_MISMATCH after pin access + GRT and being retried.
SEEDCHK=
if [ -f $RS/6_final.odb ] && [ $FROM != final ] && [ "${OT_PRD_SEED_CHECK:-1}" != 0 ]; then
  src=0; SEEDCHK=$(python3 -I "$HERE/prd_seed.py" $RS/$SRC $RS/6_final.odb "$SPEF") || src=$?
  case $src in
    0) ;;
    3) echo "prd_mk: STALE SEED $RS/$SRC lacks netlist objects of $SPEF that 6_final.odb has ($SEEDCHK);" \
            "seeding the route-keeping ECO from $RS/6_final.odb (OT_PRD_FROM=final, was $FROM)"
       SRC=6_final.odb; FROM=final ;;
    *) echo "prd_mk: seed check failed rc $src: $SEEDCHK"; exit 2 ;;
  esac
fi
# Stage policies distinguish GRT from CTS by the ORIGINAL CTS checkpoint (orfs_hold_mm.tcl ot_hold_stage: file EXISTENCE
# only, the content is never read).  Preserve it through every PRD pass.  DIE-QC-66 11-03 (class fix, tool-input): a
# routed kit whose 4_1_cts.odb was pruned (scratch reaper / resume-derived kits) still IS past CTS when its 5_1_grt.odb
# exists (that DB carries the post-CTS clock tree), so the stage identity is taken from 5_1_grt.odb and recorded in
# PRD.json ("cts_identity").  No 4_1_cts.odb and no 5_1_grt.odb -> refused (never an invalid vehicle).
CTS_ID=4_1_cts.odb
if [ ! -f "$RS/4_1_cts.odb" ]; then
  test -f "$RS/5_1_grt.odb" || { echo "prd_mk: $RS lacks original 4_1_cts.odb and 5_1_grt.odb (GRT stage identity)"; exit 2; }
  CTS_ID=5_1_grt.odb
  echo "prd_mk: $RS lacks original 4_1_cts.odb: GRT stage identity from 5_1_grt.odb (recorded in PRD.json)"
fi
HM=${V:1}; [[ "$HM" =~ ^[0-9]+$ && ${V:0:1} =~ ^[bmt]$ ]] || { echo "prd_mk: variant $V: want b<hold margin ps>, m<hold margin ps> or t<N>"; exit 2; }
mkdir -p $OUT
test -z "$SEEDCHK" || echo "$SEEDCHK" > $OUT/prd_seed.json
# Exclude the actual output subtree even for caller-selected names such as eco2.
# Otherwise creating OUT inside KIT makes rsync copy the growing pass into itself.
OUT_EXCLUDE=()
OUT_ABS=$(realpath -m -- "$OUT")
case "$OUT_ABS" in
  "$KIT"/*) OUT_REL=${OUT_ABS#"$KIT"/}; OUT_EXCLUDE=(--exclude "/${OUT_REL%%/*}/") ;;
esac
rsync -a "${OUT_EXCLUDE[@]}" --exclude .ot-run-spill-copy --exclude /run --exclude /views --exclude /signoff --exclude '/signoff_*' --exclude '/signoff*.log' \
  --exclude '/run_*.log' --exclude /rc.txt --exclude '/pass[0-9]*' --exclude '/prd_*.json' --exclude '/prd_*.log' \
  --exclude '/eco_[0-9]*' --exclude '/lec_routed_autopilot_*' $KIT/ $OUT/
B=$OUT/run/results/asap7/$NICK/base
mkdir -p $B $OUT/run/logs/asap7/$NICK/base $OUT/run/reports/asap7/$NICK/base $OUT/run/objects/asap7/$NICK/base
cp $RS/$SRC $B/4_cts.odb
cp "$RS/$CTS_ID" "$B/4_1_cts.odb"
cp "$SPEF" $B/6_final.spef
# DIE-S81-50 11-03: the logic instances the SPEF connects; prd_hook.tcl checks them against the seed (stale staging)
python3 -I "$HERE/prd_spef_insts.py" "$SPEF" $OUT/prd_spef_insts.tsv
for f in 1_2_yosys.v 1_synth.v clock_period.txt mem.json ot_face_flops.txt ot_unreg_pins.txt; do
  test -f $RS/$f && cp $RS/$f $B/; done
rsync -a $KIT/run/objects/asap7/$NICK/base/ $OUT/run/objects/asap7/$NICK/base/ 2>/dev/null || true
{ cat $OUT/constraint.sdc; echo 'set_propagated_clock [all_clocks]'; } > $B/4_cts.sdc
for f in prd_hook.tcl prd_count.tcl eco_drt_pre.tcl prd_route_keep.tcl prd_targeted.tcl prd_local_branches.tcl prd_tiesplit.tcl prd_autofo.tcl prd_spef_insts.py; do cp $HERE/$f $OUT/; done
# An explicitly selected pass hook stays pinned across subsequent passes.
if [ -n "${OT_PRD_HOOK:-}" ]; then cp "$OT_PRD_HOOK" "$OUT/prd_hook.tcl"; fi
for f in clk_freeze.tcl clk_dump_db.tcl clk_geom_diff.py clk_freeze_check.sh kit_modes_eco.tcl pg_connect.tcl; do cp "$SO/tools/die_plan/$f" $OUT/; done
MM=$(sed -n 's/^override export OT_HOLD_MM = //p; s/^export OT_HOLD_MM = //p' $OUT/config.mk | tail -n 1)
if [ "${MM:-0}" = 1 ]; then
  # two-mode session (fix 1): the kit's own patcher if staged, else the repo's
  for f in orfs_hold_mm.py orfs_hold_mm.tcl; do test -f $OUT/$f || cp "$SO/tools/$f" $OUT/; done
  [ ${V:0:1} = m ] || { echo "prd_mk: kit is two-mode (OT_HOLD_MM=1): use variant m<N>"; exit 2; }
fi
# The generated legacy core wrapper also contains a second, unbounded data
# repair. It must not run after the PRD hook has accounted for dirty routes.
python3 -I "$HERE/post_grt_chain.py" "$OUT"
# ECO hook, then the kit's own post-GRT IO / PG / reset checks.
{ echo 'source /work/kit_modes_eco.tcl'; echo 'source /work/prd_hook.tcl'; echo 'kit_modes_eco_done';
  echo 'source /work/prd_post_grt_chain.tcl'
  # PRD replaces the kit post-GRT hook, including its supply binding. Reconnect ECO-created cells before saving GRT.
  echo 'source /work/pg_connect.tcl'
  echo 'if {(![info exists ::env(OT_PG_STRICT)] || $::env(OT_PG_STRICT) ne "1") && [llength [[ord::get_db_block] getGlobalConnects]]} {ot_pg_connect_all post_route_drv}'
  echo 'ot_pg_require_bound post_route_drv'; } > $OUT/eco_post.tcl
python3 -I "$SO/tools/die_plan/signoff.py" bundle "$OUT" || exit 1
ML_TT=$(sed -n 's/^export ADDITIONAL_LIBS = //p' $OUT/config.mk | tail -n 1)
# FLOW-19 10-31 (HBM-CORES-KITS-37): kits that list their macro libs directly in TC_LIB_FILES (HBM SRAM kits:
# TC_LIB_FILES = $(TC_NLDM_LIB_FILES) /work/macros/ot_sram_..._tt.lib, no ADDITIONAL_LIBS) lost them when the line
# below re-set TC_LIB_FILES, so the SRAM was black-boxed in the repair and the post sign-off.  Without
# ADDITIONAL_LIBS, the explicit (non-$(...)) tokens of the kit's last TC_LIB_FILES line are the macro libs.
if [ -z "$(echo $ML_TT)" ]; then
  ML_TT=$(sed -n 's/^\(override \)\{0,1\}export TC_LIB_FILES *[?:+]\{0,1\}= *//p' $OUT/config.mk | tail -n 1 |
          tr ' ' '\n' | { grep -v -e '^\$(' -e '^$' || true; } | tr '\n' ' ' | sed 's/ $//')
fi
# macro libs: *_tt.lib -> *_ff.lib; explicit ASAP7 standard-cell libs (e.g. INVBUF_LVT of an LVT clock context, platform
# path or a /work copy): <group>_<VT>_TT_nldm_ -> _FF_nldm_ (same release dates in the PDK); platform paths live in the
# image, not in the kit (DIE-KV-46 10-30: the TT LVT lib was taken as a missing FF macro lib)
ML_FF=$(echo "$ML_TT" | sed -E 's/_tt\.lib/_ff.lib/g; s/(asap7sc7p5t_[A-Z]+_(RVT|LVT|SLVT))_TT_nldm_/\1_FF_nldm_/g')
for f in $ML_FF; do
  case "$f" in /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_FF_nldm_*) continue;; esac
  test -f "$OUT/${f#/work/}" || { echo "prd_mk: missing FF macro lib $f"; exit 2; }
done
if ! grep -q '^# OT_PRD post-route drive repair' $OUT/config.mk; then
cat >> $OUT/config.mk <<CFG
# OT_PRD post-route drive repair (tools/die_plan/post_route_drv, variant $V)
override export POST_GLOBAL_ROUTE_TCL = /work/eco_post.tcl
CFG
# FLOW-9 10-30: DRT of the ECO'd GRT DB clears stale special-net guides / a mixed pin-access catalog (no-op otherwise);
# a kit's own PRE_DETAIL_ROUTE hook still runs after it (OT_ECO_DRT_PRE_CHAIN).
KPRE=$(sed -n 's/^\(override \)\{0,1\}export PRE_DETAIL_ROUTE_TCL *?\{0,1\}= *//p' $OUT/config.mk | tail -n 1)
test -z "$KPRE" || echo "override export OT_ECO_DRT_PRE_CHAIN = $KPRE" >> $OUT/config.mk
cat >> $OUT/config.mk <<CFG
override export PRE_DETAIL_ROUTE_TCL = /work/eco_drt_pre.tcl
export TC_LIB_FILES = \$(TC_NLDM_LIB_FILES) $ML_TT
export BC_LIB_FILES = \$(BC_NLDM_LIB_FILES) $ML_FF
override export PWR_NETS_VOLTAGES =
override export GND_NETS_VOLTAGES =
CFG
fi
if [[ ${V:0:1} = b ]] && ! grep -q '^override export CORNERS = bc' $OUT/config.mk; then
  printf 'override export OT_HOLD_MM = 0\noverride export CORNERS = bc\n' >> $OUT/config.mk
fi
# KW-ECO-1 11-01: t<N> = TT-only setup + DRV pass of a single-mode kit (no hold repair; the b<N> pass repairs FF hold)
if [[ ${V:0:1} = t ]] && ! grep -q '^override export CORNERS = tc' $OUT/config.mk; then
  printf 'override export OT_HOLD_MM = 0\noverride export CORNERS = tc\n' >> $OUT/config.mk
fi
# FLOW-CLOCK-R8: no fanout limit by default.  Sign-off limits are liberty max_transition/max_capacitance; fanout is
# WARN-only there (64) and ASAP7 liberty has no max_fanout.  The R7 KV-recipe basis 24 split bdring's 56-load bs[*]
# nets with BUFx2 fanout buffers: TT setup -22.43 -> -39.69 ps (10 -> 100 endpoints).  OT_PRD_MAX_FANOUT=<n> opts in.
FO=${OT_PRD_MAX_FANOUT:-0}; [[ "$FO" =~ ^[0-9]+$ ]] || { echo "prd_mk: OT_PRD_MAX_FANOUT=$FO: want an integer"; exit 2; }
case ${V:0:1} in
  b) printf "OT_MAX_FANOUT=$FO\nOT_SLEW_MARGIN=20\nOT_SETUP_MARGIN=\nOT_HOLD_MARGIN=$HM\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=BC CORNERS=bc'\n" ;;
  m) printf "OT_MAX_FANOUT=$FO\nOT_SLEW_MARGIN=20\nOT_SETUP_MARGIN=10\nOT_HOLD_MARGIN=$HM\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nROUTE_CORNERS='CORNER=TC CORNERS=\"tc bc\"'\n" ;;
  t) printf "OT_MAX_FANOUT=$FO\nOT_SLEW_MARGIN=20\nOT_SETUP_MARGIN=10\nOT_HOLD_MARGIN=$HM\nOT_HOLD_ALLOW_SETUP=1\nOT_HOLD_MAXBUF=40\nOT_PRD_NO_HOLD=1\nROUTE_CORNERS='CORNER=TC CORNERS=tc'\n" ;;
esac > $OUT/variant.env
# Explicit repair settings stay pinned when prd_run creates the next pass.
# Keep an explicitly empty setup margin (FF-only) distinct from an unset one.
for setting in OT_SLEW_MARGIN OT_SETUP_MARGIN OT_HOLD_ALLOW_SETUP OT_HOLD_MAXBUF; do
  if [[ -v $setting ]]; then printf '%s=%q\n' "$setting" "${!setting}" >> "$OUT/variant.env"; fi
done
[ ${V:0:1} = b ] && [ -f $OUT/vclk_corner.tcl ] && echo "OT_VCLK_CORNER=ff" >> $OUT/variant.env
[ -n "${OT_PAD_MASTERS:-}" ] && echo "OT_PAD_MASTERS='$OT_PAD_MASTERS'" >> $OUT/variant.env
[ -n "${OT_PRD_MAX_WIRE_LENGTH:-}" ] && echo "OT_PRD_MAX_WIRE_LENGTH=$OT_PRD_MAX_WIRE_LENGTH" >> $OUT/variant.env
# Shell-quote the Tcl list once so exact net names survive both shell sourcing
# and a second ECO pass. Never eval the supplied list.
[ -z "${OT_PRD_PROTECT_NETS:-}" ] || printf 'OT_PRD_PROTECT_NETS=%q\n' "$OT_PRD_PROTECT_NETS" >> $OUT/variant.env
[ -z "${OT_PRD_NARROW_PINS:-}" ] || printf 'OT_PRD_NARROW_PINS=%q\n' "$OT_PRD_NARROW_PINS" >> $OUT/variant.env
[ -z "${OT_PRD_UNFOLD_CHAINS:-}" ] || printf 'OT_PRD_UNFOLD_CHAINS=%q\n' "$OT_PRD_UNFOLD_CHAINS" >> $OUT/variant.env
[ -z "${OT_PRD_TARGETED:-}" ] || printf 'OT_PRD_TARGETED=%q\n' "$OT_PRD_TARGETED" >> $OUT/variant.env
[ -z "${OT_PRD_TARGET_SLEW_PS:-}" ] || printf 'OT_PRD_TARGET_SLEW_PS=%q\n' "$OT_PRD_TARGET_SLEW_PS" >> $OUT/variant.env
[ -z "${OT_PRD_TARGET_FANOUT:-}" ] || [ "${OT_PRD_TARGET_FANOUT}" = 0 ] || printf 'OT_PRD_TARGET_FANOUT=%q\n' "$OT_PRD_TARGET_FANOUT" >> $OUT/variant.env
[ -z "${OT_PRD_AUTO_FANOUT:-}" ] || { [[ "$OT_PRD_AUTO_FANOUT" =~ ^[0-9]+$ ]] || { echo "prd_mk: OT_PRD_AUTO_FANOUT=$OT_PRD_AUTO_FANOUT: want an integer"; exit 2; }
  echo "OT_PRD_AUTO_FANOUT=$OT_PRD_AUTO_FANOUT" >> $OUT/variant.env; }
[ -z "${OT_PRD_TIE_SPLIT:-}" ] || printf 'OT_PRD_TIE_SPLIT=%q\n' "$OT_PRD_TIE_SPLIT" >> $OUT/variant.env
# DIE-S81-48 11-02: OT_PRD_REPAIR_RC=placement = repair on placement estimates for ECO nets (FlexPA SIG11 class)
# FLOW-25 11-03: unset = the hook decides (a seed with routed data wires repairs on placement, RSZ-0074 class); grt = A/B
case "${OT_PRD_REPAIR_RC:-}" in '') ;; placement|grt) echo "OT_PRD_REPAIR_RC=$OT_PRD_REPAIR_RC" >> $OUT/variant.env ;;
  *) echo "prd_mk: OT_PRD_REPAIR_RC=$OT_PRD_REPAIR_RC: want placement|grt"; exit 2 ;; esac
# DIE-S81-49 11-02: OT_PRD_BUFFER_REMOVAL=1 re-enables setup-repair buffer removal (default off: removed-buffer class)
case "${OT_PRD_BUFFER_REMOVAL:-}" in ''|0) ;; 1) echo "OT_PRD_BUFFER_REMOVAL=1" >> $OUT/variant.env ;;
  *) echo "prd_mk: OT_PRD_BUFFER_REMOVAL=$OT_PRD_BUFFER_REMOVAL: want 0|1"; exit 2 ;; esac
echo "OT_HOLD_MM_KIT=${MM:-0}" >> $OUT/variant.env
# clk_freeze_check.sh: grt -> --pre-unrouted (clock routed once by the ECO DRT); route -> clock wires must be unchanged
echo "OT_ECO_FROM=$FROM" >> $OUT/variant.env
if [ $FROM = grt ]; then   # default: files byte-identical to the pre-opt-in form
printf '{"tool": "post_route_drv", "variant": "%s", "source_kit": "%s:%s", "source_grt": "%s/5_1_grt.odb", "parasitics": "%s", "signoff_tools": "%s"}\n' \
  $V "$(hostname)" $KIT $RS "$SPEF" "$SO" > $OUT/PRD.json
else
echo "OT_PRD_FROM=$FROM" >> $OUT/variant.env
if [ -n "${OT_PRD_LOCAL_BRANCHES:-}" ]; then
  test -f "$OT_PRD_LOCAL_BRANCHES" || { echo "prd_mk: missing exact local-branch manifest"; exit 2; }
  cp "$OT_PRD_LOCAL_BRANCHES" "$OUT/prd_local_branches_targets.tsv"
  echo "OT_PRD_LOCAL_BRANCHES=/work/prd_local_branches_targets.tsv" >> $OUT/variant.env
  [ -z "${OT_PRD_LOCAL_MACRO_HALO_UM:-}" ] || printf 'OT_PRD_LOCAL_MACRO_HALO_UM=%q\n' "$OT_PRD_LOCAL_MACRO_HALO_UM" >> $OUT/variant.env
fi
printf '{"tool": "post_route_drv", "variant": "%s", "from": "%s", "source_kit": "%s:%s", "source_route": "%s/%s", "parasitics": "%s", "signoff_tools": "%s"}\n' \
  $V $FROM "$(hostname)" $KIT $RS $SRC "$SPEF" "$SO" > $OUT/PRD.json
fi
if [ $CTS_ID != 4_1_cts.odb ]; then
  python3 -I -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["cts_identity"]=sys.argv[2]; open(p,"w").write(json.dumps(d)+"\n")' \
    $OUT/PRD.json "$RS/$CTS_ID (original 4_1_cts.odb absent)"
fi
echo "prd pass dir ready $OUT ($(du -sh $OUT | cut -f1))"
