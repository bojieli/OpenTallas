#!/bin/bash
# kv-die 2026-10-09: die-level evidence chain for the ROM die (r22k) and the KV die, on a remote host (memory-gated):
#   real case (legality, on-track assert, pin access) -> PDN -> full-die GRT (adjfix: M4/M5 0.30, M6-M9 0.05, signals
#   M4-M9, clock / reset nets special = CTS) -> STA TT setup / FF hold on GRT parasitics (estimate_parasitics
#   -global_routing; element views = the ASSUMED single-flop interface constants of tools/qwen_die_element_lib.py +
#   the HBM PHY abstract) -> classes.
# usage: die_chain.sh <die: kv|r22k> <run dir with case_<die>/ and libs/> <src tree>
set -u
DIE=$1; R=$(readlink -f $2); SRC=$3
H=$(dirname $(readlink -f $0))
C=$R/case_$DIE; G=$R/grt_$DIE          # unique dir names: run_case.sh / dietop_run.sh name containers after them
# die lead r9 2026-10-13: under `ot-run --mem` the whole chain is already admitted: OT_ADMIT=pass runs the stages without the
# old per-stage admission; OT_STOP=grt ends the chain after the full-die GRT (the early overflow map)
ADMIT=/srv/opentallas-scratch/admit.sh
[ "${OT_ADMIT:-}" = pass ] && ADMIT=$H/admit_pass.sh
validate_case() {
  local log=$1 stage=$2
  python3 "$H/case_status.py" --log "$C/$log" --stage "$stage" --process-exit "$(cat "$C/$log.exit" 2>/dev/null || echo 1)"
}
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
case $DIE in kv) P1=20; P2=80; P3=60; P4=40;; r22k) P1=40; P2=130; P3=160; P4=110;; *) echo bad die; exit 2;; esac
say "chain start die=$DIE src=$(cat $C/SOURCE_COMMIT 2>/dev/null) from=${OT_FROM:-case}"
# Owner no-stubs rule: audit the actual die.v against this run's real RTL at
# every launch, including preserved-case resumes. HARD_PHY still needs real ports.
if [ "$DIE" = kv ]; then
  BIND_ARGS=("$C/die.v" --split --out "$R/port_bind_launch.json" --strict)
  [ -f "$C/qkd_kv_relays.sv" ] && BIND_ARGS+=(--relay-rtl "$C/qkd_kv_relays.sv")
  [ -f "$R/expand.json" ] && BIND_ARGS+=(--expanded "$R/expand.json")
  python3 "$SRC/tools/qwen_kv_die/die_port_bind_kv.py" "${BIND_ARGS[@]}" > "$R/bind_launch.log" 2>&1 || {
    # OT_BIND_DIAGNOSTIC=1 (kvsys lead r5 2026-10-14, same convention as the S81 old-source pathfinding chains): the
    # strict audit still runs and its FAIL is stamped on every STATUS line; the run is die-timing PATHFINDING only,
    # never a die result, never a contract release, never native evidence. Default stays: refuse.
    if [ "${OT_BIND_DIAGNOSTIC:-0}" = 1 ]; then
      say "NATIVE PORT BIND FAIL ($R/bind_launch.log): DIAGNOSTIC PATHFINDING ONLY -- NOT A DIE RESULT, NOT RELEASE"
      echo "PORT_BIND_FAIL_DIAGNOSTIC_ONLY" > "$R/NOT_A_DIE_RESULT"
    else
      say "NATIVE PORT BIND FAIL ($R/bind_launch.log): no die job launched"
      exit 1
    fi
  }
fi
# OT_FROM=grt resumes on a case whose real case + PDN already passed (floorplan_pdn.odb present; logs re-checked)
if [ "${OT_FROM:-case}" = grt ]; then
  validate_case run.log run.tcl && validate_case run_pdn.log run_pdn.tcl && [ -f $C/floorplan_pdn.odb ] || { say "OT_FROM=grt: case/PDN not passed"; exit 1; }
  say "resume: $(grep -m1 OT_LEGAL $C/run.log) / $(grep -m1 'OT_PDN PASS' $C/run_pdn.log)"
else
# OT_FROM=pdn (qwen-1010/b): reuse a passed real case (floorplan.odb + run.log from an earlier run), redo the PDN
if [ "${OT_FROM:-case}" = pdn ] && validate_case run.log run.tcl && [ -s $C/floorplan.odb ]; then say "real case reused"
else
$ADMIT $P1 -- $H/run_case.sh $C run.tcl run.log 16 $((P1+40)) || { say "REAL CASE process/status failed"; exit 1; }
fi
validate_case run.log run.tcl || { say "REAL CASE FAIL ($C/run.log)"; exit 1; }
say "real case: $(grep -m4 -E 'OT_LEGAL|OT_ASSERT|OT_PA' $C/run.log | tr '\n' ' ')"
if [ "${OT_PDN:-run}" = skip ]; then
  # kvsys lead r5 2026-10-14: per-instance macro grids on the 13.4k expanded leaves insert ~15/min (~15 h): a
  # DIAGNOSTIC chain may skip the die PDN (GRT then sees no M8/M9 straps: overflow optimistic; STA unaffected)
  ln -f $C/floorplan.odb $C/floorplan_pdn.odb
  say "PDN SKIPPED (OT_PDN=skip): GRT without die straps -- DIAGNOSTIC ONLY"
else
$ADMIT $P2 -- $H/run_case.sh $C run_pdn.tcl run_pdn.log 8 $((P2+60)) || { say "PDN process/status failed"; exit 1; }
validate_case run_pdn.log run_pdn.tcl || { say "PDN FAIL ($C/run_pdn.log)"; exit 1; }
say "PDN PASS $(grep -m2 OT_PGCHECK $C/run_pdn.log | tr '\n' ' ')"
fi
fi
mkdir -p $G; cp $H/grt.tcl $G/; ln -f $C/floorplan_pdn.odb $G/floorplan_pdn.odb
$ADMIT $P3 -- $H/dietop_run.sh $G grt.tcl 16 $((P3+80)) OT_ITERS=${OT_ITERS:-30} OT_TILE_UM=4.8 OT_ROUTE_RESET=${OT_ROUTE_RESET:-0}
OV=$(awk '/Final congestion report/{f=1} f && /^Total/{print $NF; exit}' $G/grt.log)
say "full-die GRT exit=$(cat $G/run.exit) overflow=${OV:-none} ($(grep -m1 'Total wirelength' $G/grt.log))"
[ "${OT_STOP:-}" = grt ] && { say "stop after GRT (OT_STOP=grt)"; exit 0; }
# qwen-1010/a: a die top without ports gets an empty *PORTS section from write_spef; OpenSTA rejects it (STA-1670)
if [ -s $G/die_grt.spef ] && head -n 30 $G/die_grt.spef | awk '/^\*PORTS$/{p=1;next} p&&NF{print;exit}' | grep -q '^\*D_NET\|^\*NAME_MAP'; then
  awk 'NR<=30 && /^\*PORTS$/ {next} {print}' $G/die_grt.spef > $G/die_grt.spef.np && mv $G/die_grt.spef.np $G/die_grt.spef
  say "SPEF: empty *PORTS section dropped (STA-1670)"
fi
sta_failed=0
corners=${OT_CORNERS-tt ff}
[ -n "${corners//[[:space:]]/}" ] || { say "STA FAIL: empty corner list"; exit 1; }
for c in $corners; do
  case "$c" in tt|ff|ss) ;; *) say "STA FAIL: unsupported corner $c"; exit 1;; esac
done
for c in $corners; do D=$R/sta_${DIE}_$c; mkdir -p $D/libs
  [ -s $G/die_grt.spef ] || { say "STA $c: no die_grt.spef (GRT parasitics), not run"; sta_failed=1; continue; }
  ln -f $G/ckpt_grt.odb $G/route.guide $G/die_grt.spef $D/
  cp $R/libs/qfd_elements_$c.lib $D/libs/; [ -f $R/libs/qfd_etm_$c.lib ] && cp $R/libs/qfd_etm_$c.lib $R/libs/views.json $D/libs/; for f in $R/libs/qfd_etm_*_$c.lib; do [ -f "$f" ] && cp "$f" $D/libs/; done; [ -f $R/libs/views.json ] && cp $R/libs/views.json $D/libs/; [ -f $R/libs/ot_hbm3e_phy_$c.lib ] && cp $R/libs/ot_hbm3e_phy_$c.lib $D/libs/
  # qwendie-1011: the die's CTS-measured clock arrivals (clock_plan.py record) when the run has one, else ideal
  CP=; [ -s $R/clock/plan.json ] && CP=$R/clock/plan.json
  python3 $H/sta_tcl.py $DIE $c $D/grt_$c.tcl $CP || { say "STA $c Tcl generation FAIL"; sta_failed=1; continue; }
  say "STA $c clock: ${OT_STA_CLOCKS:-${CP:-ideal (no clock plan)}}"
  $ADMIT $P4 -- $H/dietop_run.sh $D grt_$c.tcl 8 $((P4+60)); sta_rc=$?
  [ "$sta_rc" = 0 ] && sta_rc=$(cat "$D/run.exit" 2>/dev/null || echo 1)
  if ! python3 "$H/case_status.py" --log "$D/grt_$c.log" --stage "grt_$c.tcl" --process-exit "$sta_rc"; then
    say "STA $c FAIL process_exit=$sta_rc; see $D/grt_$c.log.status.json"
    sta_failed=1
  fi
  say "STA $c: $(grep -E '^(wns|tns|worst slack)' $D/grt_$c.log | tr '\n' ' ')"
done
[ "$sta_failed" = 0 ] || { say "chain FAIL: one or more STA corners did not complete"; exit 1; }
say "chain done"
