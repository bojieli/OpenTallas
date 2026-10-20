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
# Q-KV 2026-10-16: the prep's OT_KV_* flags (kvsys_prep.sh kv_flags.env) for the strict bind re-imports of kv_die
[ "$DIE" = kv ] && [ -f "$R/kv_flags.env" ] && . "$R/kv_flags.env"
say() { echo "$(date '+%F %T %Z') $*" >> $R/STATUS.log; }
# QW-DIECHAIN2 10-19 (dv2f18dh2 chain died: `ln` of the root-owned dieclk clock.odb -> grt floorplan_pdn.odb, Permission
# denied under fs.protected_hardlinks, so GRT opened no ODB): place SRC... DST hard-links when the kernel allows it and
# falls back to a copy for a root-owned / foreign-owned / cross-filesystem source.  Fails (non-zero) only if both fail.
place() {
  local n=$# s t; local d=${!n}
  for s in "${@:1:n-1}"; do
    t=$d; [ -d "$d" ] && t=$d/$(basename "$s")
    ln -f "$s" "$t" 2>/dev/null || { rm -f "$t" && cp --reflink=auto "$s" "$t"; } || return 1
  done
}
case $DIE in kv) P1=20; P2=80; P3=60; P4=40;; r22k) P1=40; P2=130; P3=160; P4=110;; *) echo bad die; exit 2;; esac
say "chain start die=$DIE src=$(cat $C/SOURCE_COMMIT 2>/dev/null) from=${OT_FROM:-case}"
# ROOT RELAY-SCHEMA 10-16: die relay stages vs the compiled schedule (OT_RELAY_SCHEDULE; SKIPPED when unset).  The KV die
# runs it after the strict bind below (QXF-SEAMK 10-18: netlist-walk export + the compiler's schedule for THIS die)
if [ "$DIE" != kv ]; then
RCL=$(bash "$SRC/tools/die_relay_chain_step.sh" "$C/relay_stages.json" "${OT_RELAY_SCHEDULE:-}" "$R/relay_check.json") && RCR=0 || RCR=$?; say "$RCL"; [ "$RCR" = 0 ] || exit 1
fi
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
  # Q-KVSYS-NETLIST 2026-10-16: the STRICT bit-level bind (tools/die_port_bind.py v2 on the BINDINGS-bound netlist:
  # unconnected / tied inputs, undriven + multi-driven net bits) is recorded at every launch beside the v1 audit
  # (RUN/port_bind_v2/port_bind_v2.json, read by tools/die_completeness.py); same diagnostic convention as above.
  bash "$SRC/tools/qwen_kv_die/kv_port_bind_v2.sh" "$C/die.v" "$R/port_bind_v2" "$C/qkd_kv_relays.sv" "$R/expand.json" \
    > "$R/port_bind_v2.log" 2>&1
  say "STRICT PORT BIND v2: $(tail -1 $R/port_bind_v2.log | cut -c1-400)"
  # QXF-SEAMK 10-18 (TOKEN-XDIE-QWEN F6: kvs14c logged 'RELAY_CHECK SKIPPED no compiled schedule' while its d2d <-> kvs_attn
  # record bundles were torn 9/11, 8/9, 6/11): the die-run table is walked from the bound GEN netlist
  # (RUN/relay_stages_netlist.json, tools/qwen_layerbench/netlist_relay_stages.py), the schedule is the calendar compiler
  # run against THIS die (tools/qwen_layerbench/layer_compile.py -> RUN/layer_compile/, the D2D calendars + TXDP + KV
  # programme the RTL loads), and tools/die_relay_check.py FAILS any stage difference AND any torn record bundle
  # (tools/die_record_bundles.py).  OT_RELAY_SCHEDULE=<table> checks against a given compiled table instead (e.g.
  # results/rtl/qwen_layer_tput_1018/compiled_L1/relay_schedule/kv_compiled.json.gz for the kvs14c netlist itself);
  # OT_RELAY_SCHEDULE=skip is the only way to skip (stamped).  A FAIL stops the chain unless OT_BIND_DIAGNOSTIC=1.
  bash "$SRC/tools/qwen_kv_die/kv_relay_check.sh" "$R" "$SRC" > "$R/relay_check.log" 2>&1 && RCR=0 || RCR=$?
  say "$(grep -E '^RELAY_CHECK ' $R/relay_check.log | tail -1 | cut -c1-600)"
  if [ "$RCR" != 0 ]; then
    if [ "${OT_BIND_DIAGNOSTIC:-0}" = 1 ]; then
      say "RELAY_CHECK FAIL ($R/relay_check.log): DIAGNOSTIC PATHFINDING ONLY -- NOT A DIE RESULT"
      echo "RELAY_CHECK_FAIL_DIAGNOSTIC_ONLY" >> "$R/NOT_A_DIE_RESULT"
    else
      say "RELAY_CHECK FAIL ($R/relay_check.log): no die job launched"; exit 1
    fi
  fi
fi
# Q-COMPUTE-DIE 2026-10-15: OT_PG_OPEN_DIAG=1 lets a DIAGNOSTIC chain reach GRT/STA when pdngen PASSED and only
# check_power_grid failed (islands listed by master class); run_pdn.tcl must have written floorplan_pdn_prepg.odb.
# The PDN stays FAIL in STATUS; nothing about the PG verdict is relaxed (like OT_PDN=skip, timing-only evidence).
pg_open_diag() {
  [ "${OT_PG_OPEN_DIAG:-0}" = 1 ] && grep -q '^OT_PDN PASS' $C/run_pdn.log && [ -s $C/floorplan_pdn_prepg.odb ] || return 1
  # A killed or incomplete PG check is not a measured connectivity failure. Require both the process verdict
  # and an explicit completed check failure before taking the diagnostic continuation (Qwen recovery 10-18).
  local pg_process_rc
  pg_process_rc=$(cat "$C/run_pdn.log.process_exit" 2>/dev/null) || return 1
  case "$pg_process_rc" in 0|1) ;; *) return 1;; esac
  grep -Eq '^OT_PGCHECK (VDD|VSS) FAIL ' "$C/run_pdn.log" || return 1
  grep -E '^(OT_.*FAIL|Error:|\[ERROR)' $C/run_pdn.log | grep -v -E 'OT_PGCHECK (VDD|VSS) FAIL|PSM-0069|run_pdn.tcl, [0-9]+ PSM-0069' | grep -q . && return 1
  place $C/floorplan_pdn_prepg.odb $C/floorplan_pdn.odb || return 1
  say "PDN PG OPEN -- DIAGNOSTIC ONLY (GRT/STA continue): islands by class: $(grep PSM-0039 $C/run_pdn.log | sed -E 's/.*instance ([^ /]+)\/.*/\1/; s/(_[0-9]+)+$//' | sort | uniq -c | sort -rn | awk '{printf "%s=%s ",$2,$1}')"
}
# OT_FROM=grt resumes on a case whose real case + PDN already passed (floorplan_pdn.odb present; logs re-checked)
if [ "${OT_FROM:-case}" = grt ]; then
  validate_case run.log run.tcl && { validate_case run_pdn.log run_pdn.tcl && [ -f $C/floorplan_pdn.odb ] || pg_open_diag; } || { say "OT_FROM=grt: case/PDN not passed"; exit 1; }
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
  place $C/floorplan.odb $C/floorplan_pdn.odb || { say "PDN skip: cannot place floorplan.odb"; exit 1; }
  say "PDN SKIPPED (OT_PDN=skip): GRT without die straps -- DIAGNOSTIC ONLY"
else
$ADMIT $P2 -- $H/run_case.sh $C run_pdn.tcl run_pdn.log 8 $((P2+60)); pdn_rc=$?
if validate_case run_pdn.log run_pdn.tcl; then say "PDN PASS $(grep -m2 OT_PGCHECK $C/run_pdn.log | tr '\n' ' ')"
elif pg_open_diag; then :
else say "PDN FAIL rc=$pdn_rc ($C/run_pdn.log)"; exit 1; fi
fi
fi
mkdir -p $G; cp $H/grt.tcl $G/; place $C/floorplan_pdn.odb $G/floorplan_pdn.odb || { say "GRT: cannot place floorplan_pdn.odb in $G"; exit 1; }
# GEN16 item 6 (10-19, OT_DIE_CLOCK_PHYS=1, Qwen compute): the PHYSICAL die clock (regional entries + forwarded spine,
# tools/qwen_split/chain_dieclk.sh) is built on the PDN floorplan BEFORE GRT; GRT routes its nets, STA takes the measured
# arrivals as source latency (dieclk_lat_<c>.tcl).  Fail closed: no complete die clock, no GRT.
if [ "${OT_DIE_CLOCK_PHYS:-0}" = 1 ]; then
  say "DIE CLOCK PHYS start (chain_dieclk.sh ${OT_DIE_CLOCK_VARIANT:-spine}: on case_${DIE}/floorplan_pdn.odb, before GRT)"
  bash $SRC/tools/qwen_split/chain_dieclk.sh $R $SRC > $R/dieclk.log 2>&1 || { say "DIE CLOCK PHYS FAIL ($R/dieclk.log, $R/dieclk/STATUS.log): $(tail -1 $R/dieclk.log | cut -c1-300)"; exit 1; }
  ln -f $R/dieclk/${OT_DIE_CLOCK_VARIANT:-spine}/tt/clock.odb $G/floorplan_pdn.odb
  say "DIE CLOCK PHYS: $(grep -h -E 'CHECK TT\+FF|QCLK_SPINE_NEIGHBOUR|QCLK_SPINE_MANIFEST|DIECLK_STA_LAT' $R/dieclk/STATUS.log | tr '\n' ' ' | cut -c1-900)"
fi
# DIE-FLOW 10-17 (owner 0cl): OT_DIE_REPAIR=1 = shared die-net repeater step before GRT (tools/die_repeaters); the
# element / ETM / PHY TT libs of this run are what the resizer sees (a master with signal pins and no liberty FAILS it)
if [ "${OT_DIE_REPAIR:-0}" = 1 ]; then
  mkdir -p $G/libs; : > $G/libs_tt.txt
  for f in $R/libs/qfd_elements_tt.lib $R/libs/qfd_etm_tt.lib $R/libs/qfd_etm_*_tt.lib $R/libs/ot_hbm3e_phy_tt.lib; do
    [ -f "$f" ] && cp "$f" $G/libs/ && echo /work/libs/$(basename $f) >> $G/libs_tt.txt; done
  [ -s $G/libs_tt.txt ] || { say "DIE_REPAIR FAIL: no TT element libs in $R/libs (the resizer would not see the element pins)"; exit 1; }
  RD=qwen_compute; [ "$DIE" = kv ] && RD=qwen_kv
  # Q-DIE12 10-18: a die with forwarded lanes (n_fck_* lane clocks) repeats them with their data (step.py *_fwd)
  grep -q 'n_fck_' $C/die.v 2>/dev/null && RD=${RD}_fwd
  RD=${OT_DIE_REPAIR_DESIGN:-$RD}; say "DIE_REPAIR design $RD"
  RS=(--skip 'n_rst_*'); [ "${OT_ROUTE_RESET:-0}" = 1 ] && RS=()   # routed registered reset hops are ordinary die nets: repeated
  python3 $SRC/tools/die_repeaters/step.py copy $G > /dev/null && \
  python3 $SRC/tools/die_repeaters/step.py tcl --design $RD --report /work/die_repeaters.json --libs-file /work/libs_tt.txt \
    --std-corner TT --legalize snap "${RS[@]}" > $G/die_rep_call.tcl || { say "DIE_REPAIR FAIL: step generation"; exit 1; }
  # Q-RLYFCLK 10-19: forwarded-lane capture payload contract (a[] + ea; landing K straps from own ties are not payload)
  if [ "${RD%_fwd}" != "$RD" ] && [ -f $SRC/tools/qwen_split/fclk_data_ports.py ]; then
    { python3 $SRC/tools/qwen_split/fclk_data_ports.py $C/die.v && cat $G/die_rep_call.tcl; } > $G/die_rep_call.tcl.new && \
      mv $G/die_rep_call.tcl.new $G/die_rep_call.tcl || { say "DIE_REPAIR FAIL: fclk data-port contract"; exit 1; }
  fi
fi
$ADMIT $P3 -- $H/dietop_run.sh $G grt.tcl 16 $((P3+80)) OT_ITERS=${OT_ITERS:-30} OT_TILE_UM=4.8 OT_ROUTE_RESET=${OT_ROUTE_RESET:-0} OT_DIE_REPAIR=${OT_DIE_REPAIR:-0}
if [ "${OT_DIE_REPAIR:-0}" = 1 ]; then
  say "$(python3 $SRC/tools/die_repeaters/step.py check $G/die_repeaters.json)" || true
  python3 $SRC/tools/die_repeaters/step.py check $G/die_repeaters.json > /dev/null || { say "DIE_REPAIR FAIL: no GRT result is a die result"; exit 1; }
fi
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
  place $G/ckpt_grt.odb $G/route.guide $G/die_grt.spef $D/ || { say "STA $c: cannot place GRT outputs in $D"; sta_failed=1; continue; }
  cp $R/libs/qfd_elements_$c.lib $D/libs/; [ -f $R/libs/qfd_etm_$c.lib ] && cp $R/libs/qfd_etm_$c.lib $R/libs/views.json $D/libs/; for f in $R/libs/qfd_etm_*_$c.lib; do [ -f "$f" ] && cp "$f" $D/libs/; done; [ -f $R/libs/views.json ] && cp $R/libs/views.json $D/libs/; [ -f $R/libs/ot_hbm3e_phy_$c.lib ] && cp $R/libs/ot_hbm3e_phy_$c.lib $D/libs/
  # qwendie-1011: the die's CTS-measured clock arrivals (clock_plan.py record) when the run has one, else ideal
  CP=; [ -s $R/clock/plan.json ] && CP=$R/clock/plan.json
  python3 $H/sta_tcl.py $DIE $c $D/grt_$c.tcl $CP || { say "STA $c Tcl generation FAIL"; sta_failed=1; continue; }
  say "STA $c clock: ${OT_STA_CLOCKS:-${CP:-ideal (no clock plan)}}"
  if [ "${OT_DIE_CLOCK_PHYS:-0}" = 1 ]; then
    # GEN16 item 6: measured die-clock arrivals as source latency after the compensated clocks (SS: no measured corner)
    if [ -s $R/dieclk/dieclk_lat_$c.tcl ] && grep -q OT_COMPENSATED_CLOCK $D/grt_$c.tcl; then
      sed -i "/OT_COMPENSATED_CLOCK/r $R/dieclk/dieclk_lat_$c.tcl" $D/grt_$c.tcl; say "STA $c: physical die clock arrivals ($(head -2 $R/dieclk/dieclk_lat_$c.tcl | tail -1 | cut -c1-160))"
    elif [ "$c" = ss ]; then say "STA ss: die clock NOT measured at SS (sensitivity corner; ideal die clock)"
    else say "STA $c: DIE CLOCK PHYS latency file missing or no compensated clock block"; sta_failed=1; continue; fi
  fi
  # ROOT 2026-10-16 (coordinator, owner-approved): shared die clock check on every die trial (tools/die_clock_check.*);
  # dumped inside the STA session after the reports, corners in OT_DCC_CORNERS (default tt)
  DCC=0; case " ${OT_DCC_CORNERS:-tt} " in *" $c "*) DCC=1;; esac
  if [ "$DCC" = 1 ] && [ -f "$SRC/tools/die_clock_check.tcl" ]; then
    cp "$SRC/tools/die_clock_check.tcl" $D/die_clock_check.tcl
    printf '%s\n' 'if {[catch {set ::env(OT_DCC_OUT) /work/die_clock_dump.tsv; source /work/die_clock_check.tcl} err]} { puts "OT_DCC_FAIL $err" } else { puts OT_DCC_DONE }' >> $D/grt_$c.tcl
  fi
  # Q-DIE12 10-18: forwarded-lane landing slacks per lane (tools/qwen_split/fwd_land_plan.py tcl) in every corner, so one
  # chain yields the land plan (E per link) for the next GEN (OT_SPLIT_LAND_PLAN) without a second STA session
  if [ -s $C/fwd_lanes.json ] && [ "${OT_FWD_LAND_DUMP:-1}" = 1 ]; then
    python3 $SRC/tools/qwen_split/fwd_land_plan.py tcl --lanes $C/fwd_lanes.json --corner $c --out $D/land_$c.tcl > /dev/null && \
      printf 'if {[catch {source /work/land_%s.tcl} err]} { puts "OT_LAND_FAIL $err" }\n' $c >> $D/grt_$c.tcl
  fi
  # KV-LANDSLOT 10-18: reset release window of the cross-tree reset root hops (OT_RST_WINDOW_HOPS = kv_rst_window.py
  # hops json): MCP setup E_r / hold E_r-1 per hop, worst path per hop net -> rst_window_<c>.tsv (after the reports)
  if [ -n "${OT_RST_WINDOW_HOPS:-}" ] && [ -s "$OT_RST_WINDOW_HOPS" ]; then
    python3 "$SRC/tools/qwen_kv_die/kv_rst_window.py" tcl --hops "$OT_RST_WINDOW_HOPS" --corner $c --out $D/rst_window.tcl \
      && printf '%s\n' 'if {[catch {source /work/rst_window.tcl} err]} { puts "OT_RST_WINDOW_FAIL $err" }' >> $D/grt_$c.tcl \
      || say "RST WINDOW $c: Tcl generation FAIL"
  fi
  # DIE-FLOW 10-17: post-GRT slew/cap audit of the repeated die nets (TT session; GRT detours are invisible pre-GRT)
  if [ "${OT_DIE_REPAIR:-0}" = 1 ] && [ "$c" = tt ] && [ -f $G/die_repeaters.tcl ]; then
    cp $G/die_repeaters.tcl $G/die_repeaters.skip_nets.txt $D/ 2>/dev/null
    printf '%s\n' 'if {[catch {source /work/die_repeaters.tcl; ot_die_rep_post_grt_audit /work/die_repeaters.post_grt.json /work/die_repeaters.skip_nets.txt} err]} { puts "OT_DIE_REP_POST_GRT_FAIL $err" }' >> $D/grt_$c.tcl
  fi
  $ADMIT $P4 -- $H/dietop_run.sh $D grt_$c.tcl 8 $((P4+60)); sta_rc=$?
  [ "$sta_rc" = 0 ] && sta_rc=$(cat "$D/run.exit" 2>/dev/null || echo 1)
  if ! python3 "$H/case_status.py" --log "$D/grt_$c.log" --stage "grt_$c.tcl" --process-exit "$sta_rc"; then
    say "STA $c FAIL process_exit=$sta_rc; see $D/grt_$c.log.status.json"
    sta_failed=1
  fi
  say "STA $c: $(grep -E '^(wns|tns|worst slack)' $D/grt_$c.log | tr '\n' ' ')"
  if [ "$DCC" = 1 ] && [ -s $D/die_clock_dump.tsv ]; then
    python3 "$SRC/tools/die_clock_check.py" report $D/die_clock_dump.tsv --out $D/die_clock_check.json > $D/die_clock_check.txt 2>&1 \
      && say "DIE CLOCK CHECK $c: $D/die_clock_check.txt" || say "DIE CLOCK CHECK $c report FAIL (see $D/die_clock_check.txt)"
  elif [ "$DCC" = 1 ]; then say "DIE CLOCK CHECK $c: no dump ($(grep -m1 OT_DCC_FAIL $D/grt_$c.log))"; fi
done
if [ -n "${OT_RST_WINDOW_HOPS:-}" ] && [ -s "$OT_RST_WINDOW_HOPS" ]; then
  RWD=$R/dieclk; say "$(python3 "$SRC/tools/qwen_kv_die/kv_rst_window.py" report --hops "$OT_RST_WINDOW_HOPS" \
    --tt $R/sta_${DIE}_tt/rst_window_tt.tsv --ff $R/sta_${DIE}_ff/rst_window_ff.tsv \
    $( [ -s $RWD/dump_tt.tsv ] && echo --dump-tt $RWD/dump_tt.tsv ) $( [ -s $RWD/dump_ff.tsv ] && echo --dump-ff $RWD/dump_ff.tsv ) \
    --out $R/rst_window.json 2>&1 | tail -1)"
fi
[ "$sta_failed" = 0 ] || { say "chain FAIL: one or more STA corners did not complete"; exit 1; }
if [ -s $C/fwd_lanes.json ] && [ "${OT_FWD_LAND_DUMP:-1}" = 1 ]; then
  LG=(); for c in tt ff; do [ -s $R/sta_${DIE}_$c/grt_$c.log ] && LG+=($R/sta_${DIE}_$c/grt_$c.log); done
  [ ${#LG[@]} -gt 0 ] && say "LAND PLAN: $(python3 $SRC/tools/qwen_split/fwd_land_plan.py plan --lanes $C/fwd_lanes.json --logs "${LG[@]}" --out $R/land_plan.json 2>&1 | tail -1)"
fi
# DIE-FLOW 2026-10-17 (FLOW-HOLD D1-D3, OT_HOLD_BUDGET=die: die_sta_libs.py U 25 + sta_tcl.py FF hold dump): per-link
# classifier -- launch-min from the bound ETMs, delta <= 80, ASSUMED single-flop masters = hold DIAGNOSTIC links
if [ "${OT_HOLD_BUDGET:-tile}" = die ]; then
  HD=$R/sta_${DIE}_ff
  if [ -s $HD/hold_links_ff.rpt ] && [ -f "$SRC/tools/die_hold_budget.py" ]; then
    QV=; [ -f $R/libs/views.json ] && QV="--qwen-views $R/libs/views.json"
    say "HOLD BUDGET: $(python3 "$SRC/tools/die_hold_budget.py" classify --report $HD/hold_links_ff.rpt $QV \
        --paths-cap ${OT_HOLD_DUMP_PATHS:-200000} --design qwen_$DIE --out $R/hold_budget.json 2>&1 | tail -1)"
  else
    say "HOLD BUDGET: no FF hold dump or no tools/die_hold_budget.py in $SRC -- not classified"
  fi
fi
# Every completed KV die trial carries its endpoint cause table and actual GRT
# congestion/pin/channel readout. The enclosing ot-run scope admits this work;
# standalone callers retain the normal stage admission rather than running a
# memory-heavy endpoint/guide walk outside the resource book.
if [ "$DIE" = kv ]; then
  if $ADMIT 8 -- python3 "$SRC/tools/qwen_kv_die/kvsys_classify.py" --run "$R" --out "$R/classify.json" > "$R/classify.log" 2>&1 &&
     $ADMIT 8 -- python3 "$SRC/tools/qwen_kv_die/kv_readout.py" --run "$R" --classify "$R/classify.json" --out "$R/readout" > "$R/readout.log" 2>&1; then
    say "KV READOUT: $R/classify.json $R/readout/readout.md"
  else
    say "KV READOUT FAIL: see $R/classify.log and $R/readout.log (physical/STA logs preserved)"
    exit 1
  fi
fi
say "chain done"
