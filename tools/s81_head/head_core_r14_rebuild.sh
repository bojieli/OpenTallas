#!/bin/bash
# HEAD-CORE-R14 2026-10-27 (COORD RULING HEAD-CORE-R13 ASK1/ASK3): rebuild an s81_head hard core from its kit's synthesised
# netlist up to a GRT checkpoint, with the R14 flow, then STOP for render + GEOM review (no route in this script).
#   head_core_r14_rebuild.sh SRC_KIT OUT "PLAN_ARGS" [CLK_X,CLK_Y] [MEM_GB=48] [CPUS=16]      (run ON the kit host)
# SRC_KIT  a head kit (config.mk, io.tcl, netlist/, pre_cts_r5.tcl + cf/mscts_*.tcl plan-tree CTS, bind_ff_actual.tcl,
#          actual_head_sta.tcl); its run/, sign-off and LEC dirs are not copied.
# PLAN_ARGS head_tree_plan.py options for the in-core plan tree, computed on THIS build's 3_place geometry before CTS
#          (12.8a/b/d1: plan-computed, no measured input), e.g. "--entry 159.84,159.84 --fanouts 4,4,2,4,4 --l1_mirror 1".
# CLK_X,CLK_Y  optional new location of the core clock pin ft_mstrap_i (M5, 0.192 square) in io.tcl (elemA: centre).
# Flow (R14, ASK3): place -> geo dump -> plan tree -> CTS (plan-built, TritonCTS off) -> do-5_1_grt MCMM (CORNER TC,
#   CORNERS "tc bc": the R10 GRT repair ran BC-only, so TT slew was never repaired) with repair_design on UNSCALED RC
#   + 20 % slew/cap margin (head_grt_drv_unscaled.tcl) and HB4-only data hold repair (FF bound 202.5) -> read-only GRT
#   STA TT/FF (actual_head_sta.tcl, rc_cal estimate) -> STOP.  Route/ECO/sign-off/LEC follow after GEOM PASS.
# Log: OUT/r14_rebuild.log, lines R14RB_*.
set -uo pipefail
SRC=$(realpath "$1"); OUT=$2; PLAN="$3"; CLK=${4:-}; MEM=${5:-48}; CPUS=${6:-16}
HERE=$(cd "$(dirname "$0")" && pwd)
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
test ! -e "$OUT" || { echo "r14 rebuild: $OUT exists (never relaunch into a run dir)"; exit 2; }
mkdir -p "$OUT"; OUT=$(realpath "$OUT")
exec >> "$OUT/r14_rebuild.log" 2>&1
NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$SRC/config.mk" | tail -1)
echo "R14RB start $(date -Is) host $(hostname) src $SRC nick $NICK plan '$PLAN' clk '${CLK:-keep}'"
rsync -a --exclude /run --exclude '/signoff_*' --exclude '/signoff.log' --exclude '/*.log' --exclude /rc.txt --exclude '/lec*' --exclude '/actual_*.v' --exclude '/actual_sta_*.json' --exclude '/repaired_*' \
  --exclude '/if_base' --exclude '/if_mut' "$SRC"/ "$OUT"/
for f in config.mk io.tcl bind_ff_actual.tcl actual_head_sta.tcl pre_cts_r5.tcl cf/mscts_core.tcl cf/mscts_h_head.tcl; do
  test -s "$OUT/$f" || { echo "R14RB FAIL kit lacks $f"; exit 2; }; done
grep -q hold_pad_hb4.tcl "$OUT/bind_ff_actual.tcl" || { echo "R14RB FAIL bind_ff_actual.tcl lacks the HB4-only wrapper"; exit 2; }
if [ -n "$CLK" ]; then
  X=${CLK%,*}; Y=${CLK#*,}
  grep -q '^place_pin -pin_name {ft_mstrap_i} ' "$OUT/io.tcl" || { echo "R14RB FAIL io.tcl has no ft_mstrap_i pin"; exit 2; }
  sed -i "s|^place_pin -pin_name {ft_mstrap_i} .*|place_pin -pin_name {ft_mstrap_i} -layer M5 -location {$X $Y} -pin_size {0.1920 0.1920}|" "$OUT/io.tcl"
  echo "R14RB clock pin ft_mstrap_i -> ($X,$Y): $(grep '{ft_mstrap_i}' "$OUT/io.tcl")"
fi
cp "$HERE/head_grt_drv_unscaled.tcl" "$HERE/head_tree_plan.py" "$OUT/"
{ cat "$OUT/bind_ff_actual.tcl"; echo 'source /work/head_grt_drv_unscaled.tcl'; } > "$OUT/bind_ff_r14.tcl"
cat >> "$OUT/config.mk" <<'CFG'

# ---- HEAD-CORE-R14 rebuild (tools/s81_head/head_core_r14_rebuild.sh; COORD RULING HEAD-CORE-R13 ASK1/ASK3) ----
# plan tree computed on this build's 3_place geometry (head_tree_plan.py) before CTS; GRT repair_design on unscaled RC
# (head_grt_drv_unscaled.tcl, >= 20 % slew/cap margin), HB4-only data hold (bind_ff_actual.tcl wrappers), MCMM GRT.
override export OT_MSCTS_SPEC = /work/mscts_spec_r14.tcl
override export PRE_GLOBAL_ROUTE_TCL = /work/bind_ff_r14.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/noop.tcl
override export SKIP_INCREMENTAL_REPAIR = 0
export OT_GRT_DRV_MARGIN = 20
CFG
DK() { docker run --rm --name "hd-r14-$NICK-$$-$1" --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$CPUS" -v "$OUT":/work \
  -e CPUS="$CPUS" -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "set -euo pipefail; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $2"; }
M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=\$CPUS CORNER=TC CORNERS='tc bc'"
B=$OUT/run/results/asap7/$NICK/base
# a placeholder spec so the PRE_CTS file exists during place (not read before CTS)
echo "# R14 placeholder: replaced by the plan computed on 3_place before CTS" > "$OUT/mscts_spec_r14.tcl"
if [ "${OT_R14_FROM_PLACE:-0}" = 1 ]; then
  # warm start (elemA): the kit's own 3_place (12.2a1 pushdown-patched 1_synth.odb + island cells + its reset restore,
  # steps that live in Codex/R5 helper scripts outside the ORFS make flow); only the clock pin box is moved, std-cell
  # placement unchanged (the root island cell u_isl_root is fixed and the pin moves a few um inside the island hole).
  SB=$SRC/run/results/asap7/$NICK/base; mkdir -p "$B" "$OUT/run/logs/asap7/$NICK/base" "$OUT/run/reports/asap7/$NICK/base"
  for f in 1_2_yosys.v 1_2_yosys.sdc 1_synth.odb 1_synth.sdc 2_floorplan.odb 2_floorplan.sdc 3_place.odb 3_place.sdc clock_period.txt ot_face_flops.txt ot_unreg_pins.txt; do
    test -f "$SB/$f" && cp -p "$SB/$f" "$B/"; done
  rsync -a "$SRC/run/objects/" "$OUT/run/objects/" 2>/dev/null || true
  test -s "$B/3_place.odb" || { echo "R14RB FAIL no 3_place.odb in $SB"; exit 3; }
  if [ -n "$CLK" ]; then
    cat > "$OUT/r14_move_pin.tcl" <<TCL
read_db /work/run/results/asap7/$NICK/base/3_place.odb
set b [ord::get_db_block]; set u [\$b getDbUnitsPerMicron]; set bt [\$b findBTerm ft_mstrap_i]
if {\$bt eq "NULL"} { error "R14RB no ft_mstrap_i" }
foreach bp [\$bt getBPins] { foreach bx [\$bp getBoxes] { puts "R14RB_PIN old [\$bx xMin] [\$bx yMin] [\$bx xMax] [\$bx yMax] dbu" }; odb::dbBPin_destroy \$bp }
set bp [odb::dbBPin_create \$bt]; set l [[ord::get_db_tech] findLayer M5]; set h [expr {round(0.096 * \$u)}]
set cx [expr {round($X * \$u)}]; set cy [expr {round($Y * \$u)}]
odb::dbBox_create \$bp \$l [expr {\$cx - \$h}] [expr {\$cy - \$h}] [expr {\$cx + \$h}] [expr {\$cy + \$h}]
\$bp setPlacementStatus FIRM
puts "R14RB_PIN new ft_mstrap_i M5 centre $X $Y"
write_db /work/run/results/asap7/$NICK/base/3_place.odb
exit
TCL
    DK pin "openroad -no_init -exit /work/r14_move_pin.tcl" > "$OUT/r14_pin.log" 2>&1
    grep R14RB_PIN "$OUT/r14_pin.log" || { echo "R14RB FAIL pin move"; exit 3; }
  fi
  echo "R14RB warm start from the kit 3_place $(date -Is)"
  CTS_T=do-cts
elif [ "${OT_R14_PATCH_SYNTH:-0}" = 1 ]; then
  # cold rebuild from RTL (elemB, place.sh recipe): orfs_hold_mm patch -> synth -> face_guard_core on the Yosys netlist
  # (fail-closed) -> 12.2a1 pushdown netlist patch (patch_synth.tcl: clk -> ft_* island ports) + post-patch SDC -> place
  TOP=$(sed -n 's/^export DESIGN_NAME = //p' "$OUT/config.mk" | tail -1); SKIP=$(cat "$OUT/face_guard_skip.txt")
  # the guard runs on the PRE-patch Yosys netlist, whose clock port is still clk (patch_synth turns it into ft_*):
  # add clk to the kit skip set (the kit set ^(ft_.*|rst_n)$ was written for the patched form).
  SKIP="^(clk|${SKIP#^(}"
  # the kit wrapper face_guard_core.py reads G.MAX_CHAIN, which main face_guard.py (49e28f506, unbounded chain trace
  # with cycle detection) no longer defines; it only bounds the report-only self-loop classification.
  sed -i 's/G\.MAX_CHAIN + 2/getattr(G, "MAX_CHAIN", 64) + 2/' "$OUT/face_guard_core.py"
  R=/work/run/results/asap7/$NICK/base
  DK place "rc=0; python3 -I /work/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts /work/orfs_hold_mm.tcl > /work/orfs_hold_mm.log 2>&1 || rc=\$?; grep -q 'status.: .patched.' /work/orfs_hold_mm.log || rc=3; echo HOLD_MM rc \$rc; [ \$rc = 0 ] || exit \$rc; \
    $M synth; python3 -I /work/face_guard_core.py $R/1_2_yosys.v $TOP '$SKIP' /work/pins.json /work/face_guard.json; echo FACE_GUARD rc \$?; \
    ODB_IN=$R/1_synth.odb openroad -exit /work/patch_synth.tcl; cp /work/constraint_pd.sdc $R/1_synth.sdc; touch $R/1_synth.odb $R/1_synth.sdc; \
    $M place" > "$OUT/r14_place.log" 2>&1; rc=$?
  grep -h '^HOLD_MM\|^FACE_GUARD\|^PS ' "$OUT/r14_place.log"
  grep -q '^FACE_GUARD rc 0' "$OUT/r14_place.log" || { echo "R14RB FAIL face_guard"; exit 3; }
  echo "R14RB synth+patch+place rc=$rc $(date -Is)"; [ $rc = 0 ] || exit 3
  CTS_T=cts
else
  DK place "$M place" > "$OUT/r14_place.log" 2>&1; rc=$?
  echo "R14RB place rc=$rc $(date -Is)"; [ $rc = 0 ] || exit 3
  CTS_T=cts
fi
cat > "$OUT/dump_geo_r14.tcl" <<'TCL'
read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
proc um {v} { return [format %.3f [expr {$v / double($::u)}]] }
set d [$b getDieArea]; puts $f "DIE [um [$d xMin]] [um [$d yMin]] [um [$d xMax]] [um [$d yMax]]"
set c [$b getCoreArea]; puts $f "CORE [um [$c xMin]] [um [$c yMin]] [um [$c xMax]] [um [$c yMax]]"
set ns 0; set nm 0
foreach i [$b getInsts] {
  set m [$i getMaster]
  foreach it [$i getITerms] {
    set mt [$it getMTerm]; set pn [$mt getName]
    if {[$m isBlock]} {
      if {![regexp -nocase {^(clk|ck|clock)$} $pn]} continue
      set r [$i getBBox]; set ib [$it getBBox]; set n [$it getNet]; set nn [expr {$n eq "NULL" ? "-" : [$n getName]}]
      puts $f "MACRO [$i getName] [$m getName] [um [$r xMin]] [um [$r yMin]] [um [$r xMax]] [um [$r yMax]] $pn [um [expr {([$ib xMin]+[$ib xMax])/2}]] [um [expr {([$ib yMin]+[$ib yMax])/2}]] $nn"; incr nm; continue
    }
    if {[$mt getSigType] ne "CLOCK" && $pn ne "CLK"} continue
    if {![string match "*DFF*" [$m getName]] && ![string match "*SDF*" [$m getName]] && ![string match "*ICG*" [$m getName]]} continue
    set ib [$it getBBox]; set n [$it getNet]; set nn [expr {$n eq "NULL" ? "-" : [$n getName]}]
    puts $f "SINK [um [expr {([$ib xMin]+[$ib xMax])/2}]] [um [expr {([$ib yMin]+[$ib yMax])/2}]] [$m getName] [$i getName] $pn $nn"; incr ns
  }
}
close $f
puts "R14RB_GEO sinks $ns macros $nm"
exit
TCL
DK geo "ODB=/work/run/results/asap7/$NICK/base/3_place.odb OUT=/work/r14.geo openroad -no_init -exit /work/dump_geo_r14.tcl" > "$OUT/r14_geo.log" 2>&1
grep R14RB_GEO "$OUT/r14_geo.log" || { echo "R14RB FAIL geo dump"; exit 3; }
# shellcheck disable=SC2086
python3 -I "$OUT/head_tree_plan.py" "$OUT/r14.geo" "$OUT/r14plan" $PLAN > "$OUT/r14_plan.log" 2>&1; rc=$?
grep -E '^(L1MIRROR|EQ|PLAN|GPGATE)' "$OUT/r14_plan.log" | cut -c1-600
[ $rc = 0 ] && [ -s "$OUT/r14plan.tcl" ] || { echo "R14RB FAIL plan rc=$rc"; exit 3; }
cp "$OUT/r14plan.tcl" "$OUT/mscts_spec_r14.tcl"
echo "R14RB plan sha256 $(sha256sum "$OUT/mscts_spec_r14.tcl" | cut -c1-16) $(date -Is)"
DK cts "$M $CTS_T" > "$OUT/r14_cts.log" 2>&1; rc=$?
echo "R14RB cts rc=$rc $(date -Is)"; [ $rc = 0 ] || exit 3
DK grt "$M do-5_1_grt" > "$OUT/r14_grt.log" 2>&1; rc=$?
echo "R14RB grt rc=$rc $(date -Is)"
grep -h 'HD_GRT_DRV\|R10_HOLD_DONE\|OT_HB4PAD: after\|GRT-0' "$OUT/run/logs/asap7/$NICK/base/5_1_grt.log" 2>/dev/null | tail -n 12
[ $rc = 0 ] || exit 3
DK sta "for C in TT FF; do OT_HEAD_NICK=$NICK OT_CORNER=\$C openroad -threads 4 -exit /work/actual_head_sta.tcl > /work/r14_sta_\$C.log 2>&1; done"
grep -h ACTUAL_HEAD_STA "$OUT"/r14_sta_*.log
docker run --rm -v "$OUT":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work >/dev/null 2>&1
echo "R14RB done (STOP before route: render + GEOM REQ) $(date -Is)"
