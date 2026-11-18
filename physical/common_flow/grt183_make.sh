#!/bin/bash
# GRT183-RESUME for kit runners (FLOW-28 2026-11-04, DIE-HBM-63/FORMS hand form on fused_host_program): the runner's make
# command runs through this wrapper inside the kit's container.  Default on; OT_GRT183_RESUME=0 at the runner, or
# 'export OT_GRT183_RESUME = 0' in config.mk, opts out.
#   grt183_make.sh CMD...   CMD = make ... | bash /work/kwrs_make.sh RS make ...
# Class: full GRT reaches 0 overflow, then the incremental route inside repair_design / repair_timing dies with GRT-0183.
# In the same process neither -end_incremental nor a new full route recovers; a fresh process from the resized design does.
# grt183_resume.tcl (ROOT 10-15, unchanged, sourced before the kit's PRE_GLOBAL_ROUTE hook) saves that design and re-raises.
# Then this wrapper runs CMD exactly once more, with 4_cts.odb = the saved design; every repair runs again.  Nothing else:
#   - no saved design (GRT-0183 in the first full route, any other failure): rc as before, no re-run.  A re-run of an
#     unchanged design would repeat the same route.
#   - second GRT-0183: the hook sees the marker 5_1_grt.grt183_recovered.json and refuses; rc as before.
#   - no gate, guard, margin or repair changes.  4_cts.odb is swapped by rename only, so a stage-resume hardlink to the
#     previous attempt is never written through, and the original CTS database (mtime included) comes back afterwards.
W=${OT_GRT183_WORK:-/work}
S=${OT_GRT183_SCRIPTS:-/OpenROAD-flow-scripts/flow/scripts}/global_route.tcl
HOOK="source /work/grt183_resume.tcl"
case " $* " in *" print-"*) exec "$@";; esac
# KW-FIX-24/LEAFREP 11-06 (COORD 20:0x (5) / 20:2x (6)): clk_leaf_repeat default-on for every kit carrying
# /work/clk_leaf_repeat_default.tcl (tools/die_plan/core_flow.stage_grt183).  Disposable container copies of the ORFS
# scripts, before any opt-out below: cts.tcl sources it right before 'source_step_tcl POST CTS' (::ot_clr_default:
# skipped when the kit hooks clk_leaf_repeat.tcl itself), global_route.tcl right after the first
# 'estimate_parasitics -global_routing' (long-branch pass on GRT RC).  Opt-outs live in the Tcl (OT_CLK_LEAF_REPEAT=0,
# OT_CLK_LEAF_GRT=0 from config.mk); without the kit file nothing is patched.
SD=$(dirname "$S")
# Optional pre-CTS summaries only.  Independent cell/geometry/hold/signoff gates and stages 4+ remain intact.
# Enabled in a new kit's config, never by changing a running job or the ORFS image on the host.
if [ -f "$SD/report_metrics.tcl" ] && grep -Eq '^export OT_SKIP_PRECTS_METRICS[[:space:]]*=[[:space:]]*1[[:space:]]*$' "$W/config.mk" 2>/dev/null; then
  python3 - "$SD/report_metrics.tcl" <<'OT_PRECTS_PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
marker = '# OT_PRECTS_METRICS: summaries only, explicit gates unchanged'
if marker not in s:
    anchor = 'proc report_metrics { stage when { include_erc true } { include_clock_skew true } } {\n'
    if s.count(anchor) != 1:
        raise SystemExit('OT_PRECTS_METRICS: unsupported report_metrics signature; no patch applied')
    guard = '  # OT_PRECTS_METRICS: summaries only, explicit gates unchanged\n  if { [info exists ::env(OT_SKIP_PRECTS_METRICS)] && $::env(OT_SKIP_PRECTS_METRICS) eq "1" && $stage in {2 3} } {\n    puts "OT_PRECTS_METRICS_SKIPPED stage=$stage when=$when"\n    return\n  }\n'
    p.write_text(s.replace(anchor, anchor + guard))
OT_PRECTS_PY
  [ "$?" = 0 ] || exit 2
fi
if [ -f "$W/clk_leaf_repeat_default.tcl" ]; then
  CH="set ::ot_clr_default 1; source /work/clk_leaf_repeat_default.tcl; unset -nocomplain ::ot_clr_default ;# OT_CLK_LEAF_REPEAT default"
  if [ -f "$SD/cts.tcl" ] && ! grep -qF "OT_CLK_LEAF_REPEAT default" "$SD/cts.tcl"; then
    if grep -q '^ *source_step_tcl POST CTS' "$SD/cts.tcl"; then sed -i "s|^\( *\)source_step_tcl POST CTS|\1$CH\n&|" "$SD/cts.tcl"
    else echo "OT_CLK_LEAF_REPEAT default inactive: no POST CTS step in $SD/cts.tcl"; fi
  fi
  GH="set ::ot_clr_stage grt; source /work/clk_leaf_repeat_default.tcl; unset -nocomplain ::ot_clr_stage ;# OT_CLK_LEAF_REPEAT grt"
  if [ -f "$S" ] && ! grep -qF "OT_CLK_LEAF_REPEAT grt" "$S"; then
    if grep -q '^ *log_cmd estimate_parasitics -global_routing' "$S"; then
      sed -i "0,\|^\( *\)log_cmd estimate_parasitics -global_routing.*|s||&\n\1$GH|" "$S"
    else echo "OT_CLK_LEAF_REPEAT grt inactive: no estimate_parasitics -global_routing in $S"; fi
  fi
fi
# S81-COL-FLOW-1118 (COORD; S81 leaf t25_ns2 pilot + wave t51 a6 DPL-0033): repair_design / repair_timing inside the GRT stage
# legalize through the negotiation legalizer, which can leave a few overlapping buffers; nothing in the stage repaired them.
# Disposable global_route.tcl copy: right before 'source_step_tcl POST GLOBAL_ROUTE', only when check_placement fails, one diamond
# legalization inside an incremental route, then the mandatory check_placement -verbose.  A legal design is untouched (no gate,
# margin or repair change).  'export OT_GRT_POST_DPL = 0' in config.mk opts out.
if [ -f "$S" ] && ! grep -qF "OT_GRT_POST_DPL" "$S" && ! grep -Eq '^export OT_GRT_POST_DPL[[:space:]]*=[[:space:]]*0[[:space:]]*$' "$W/config.mk" 2>/dev/null; then
  if grep -q '^ *source_step_tcl POST GLOBAL_ROUTE' "$S"; then
    python3 - "$S" <<'OT_GRT_POST_DPL_PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
line = ('if {[catch {check_placement}]} { puts "OT_DPL_RESIDUAL: GRT post-repair check failed, diamond legalization in an incremental route"; '
        'global_route -start_incremental; detailed_placement -use_diamond_legalizer; global_route -end_incremental; '
        'estimate_parasitics -global_routing; check_placement -verbose } ;# OT_GRT_POST_DPL')
s = p.read_text()
s, n = re.subn(r'(?m)^( *)(source_step_tcl POST GLOBAL_ROUTE)', lambda m: m.group(1) + line + '\n' + m.group(1) + m.group(2), s, count=1)
assert n == 1
p.write_text(s)
OT_GRT_POST_DPL_PY
    [ "$?" = 0 ] || exit 2
  else echo "OT_GRT_POST_DPL inactive: no POST GLOBAL_ROUTE step in $S"; fi
fi
# OT_GRT_EST_FALLBACK begin
# WF-1 11-14 (COORD class fix, TYPE-KVHGI3 fC): the -allow_congestion GRT forms (S81 col / slice / leaf, KV hgi) ended GRT with a small
# overflow (GRT-0115, 39) and then ORFS global_route.tcl's 'estimate_parasitics -global_routing' aborted with GRT-0232 'Routing
# congestion too high' / EST-0104, so detailed route never ran.  Disposable container copy of global_route.tcl: that call is wrapped
# in catch; on failure the stage continues with placement parasitics and detailed route (which usually clears a small overflow).
if [ -f "$S" ] && ! grep -qF "OT_GRT_EST_FALLBACK" "$S"; then
  sed -i -E 's#^( *)log_cmd estimate_parasitics -global_routing(.*)$#\1if {[catch {log_cmd estimate_parasitics -global_routing\2} ot_est_e]} { puts "OT_GRT_EST_FALLBACK: estimate_parasitics -global_routing failed ($ot_est_e); placement parasitics, detailed route follows"; log_cmd estimate_parasitics -placement } ;\# OT_GRT_EST_FALLBACK#' "$S"
fi
# OT_GRT_EST_FALLBACK end
# OT_GRT_ALLOW_CONG_HOOK begin
# WF-1 11-14 (COORD class fix, S81-CORES-2 / a85cd525dff: -allow_congestion in GLOBAL_ROUTE_ARGS covers only the FIRST global_route; every
# later 'global_route -end_incremental' inside repair_timing / repair_design re-parses its flags and raises GRT-0232 again, exit 2 after a
# 0-overflow main route): whenever the kit asks for allow-congestion (config.mk mentions it, or OT_GRT_ALLOW_CONGESTION=1) the stage
# keeps it on for every global_route and before each repair call, via a hook sourced ahead of the PRE GLOBAL_ROUTE step of the disposable
# global_route.tcl copy.  Nothing else changes (no gate, margin or repair setting).
if [ -f "$S" ] && ! grep -qF "OT_GRT_ALLOW_CONG_HOOK" "$S" && { grep -Eq 'allow_congestion|OT_GRT_ALLOW_CONGESTION' "$W/config.mk" 2>/dev/null || [ "${OT_GRT_ALLOW_CONGESTION:-0}" = 1 ]; }; then
  if grep -q '^ *source_step_tcl PRE GLOBAL_ROUTE' "$S"; then
    [ -f "$W/grt_allow_cong.tcl" ] || cat > "$W/grt_allow_cong.tcl" <<'OT_AC_TCL'
# S81-CORES-2 11-14 (owner: remove conservative limits). bksel_q e10 run 1 and run 2: the full GRT reaches 0 overflow,
# then the incremental reroute inside repair_timing ends at 0-1 / 1 / 39-42 overflow and raises GRT-0232. The
# -allow_congestion given in GLOBAL_ROUTE_ARGS reaches only the first full route: every later 'global_route
# -end_incremental' call re-parses its flags and clears it. This hook keeps allow-congestion on for the whole stage, so
# the small residue goes to DRT. Nothing else changes (no gate, margin or repair setting).
if {[llength [info commands ::grt::set_allow_congestion]] && ![llength [info commands ::ot_ac_gr_orig]]} {
  rename ::global_route ::ot_ac_gr_orig
  proc ::global_route {args} {
    if {[lsearch -exact $args -allow_congestion] < 0} { lappend args -allow_congestion }
    set rc [catch {uplevel 1 [list ::ot_ac_gr_orig {*}$args]} res opts]
    ::grt::set_allow_congestion 1
    return -options $opts $res
  }
  # KIT-OPS-5 11-14 (FABLE-KVOVF, measured): repair_antennas without -allow_congestion clears the router's allow-congestion state, so the
  # next estimate_parasitics -global_routing fails EST-0005.  repair_antennas joins the wrapped commands and every wrapped command
  # re-arms the state AFTER it returns too (not only before).
  foreach c {repair_timing repair_design repair_antennas} {
    if {[llength [info commands ::$c]]} {
      rename ::$c ::ot_ac_${c}_orig
      proc ::$c {args} [format {::grt::set_allow_congestion 1; set rc [catch {uplevel 1 [list ::ot_ac_%s_orig {*}$args]} res opts]; ::grt::set_allow_congestion 1; return -options $opts $res} $c]
    }
  }
  ::grt::set_allow_congestion 1
  puts "OT_GRT_ALLOW_CONGESTION hook: global_route/repair_timing/repair_design keep allow-congestion on (S81-CORES-2)"
}
OT_AC_TCL
    sed -i "s|^\( *\)source_step_tcl PRE GLOBAL_ROUTE|\1source $W/grt_allow_cong.tcl ;# OT_GRT_ALLOW_CONG_HOOK\n&|" "$S"
  else echo "OT_GRT_ALLOW_CONG_HOOK inactive: no PRE GLOBAL_ROUTE step in $S"; fi
fi
# OT_GRT_ALLOW_CONG_HOOK end
# KW-FIX-35-F2 11-08 (FLOW class F follow-up, CTS DPL-0033): CTS-stage legalization uses the kit's own 3_5 legalizer.
# ORFS erases DETAIL_PLACEMENT_ARGS outside the place stage, so stock cts.tcl (and clk_leaf_repeat) call a bare
# detailed_placement = the negotiation legalizer, which stalled with residual overlaps where 3_5's diamond pass was 100 %
# legal (QC sle_hc1__cl7d360508 a10: 1143 s, 512 left; S81 dsdv_slice_c1x_C__t3 a16: 3897 s, 306 left).  The disposable
# cts.tcl copy captures the args BEFORE the erase (::ot_kit_dpl_args, read by clk_leaf_repeat.tcl) and, only when they
# select -use_diamond_legalizer (FLOW-7 opt-in), gives a bare detailed_placement in that process the same args.  Kits
# without the opt-in: unchanged.  No gate, check or margin changes.  'export OT_CTS_DPL_ARGS = 0' in config.mk opts out.
CT=$SD/cts.tcl
if [ -f "$CT" ] && ! grep -qF "OT_CTS_DPL_ARGS" "$CT" && ! grep -Eq '^export OT_CTS_DPL_ARGS[[:space:]]*=[[:space:]]*0[[:space:]]*$' "$W/config.mk" 2>/dev/null; then
  if grep -q '^ *erase_non_stage_variables cts' "$CT"; then
    python3 - "$CT" <<'OT_CTS_DPL_PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
line = ('set ::ot_kit_dpl_args [expr {[info exists ::env(DETAIL_PLACEMENT_ARGS)] ? [string trim $::env(DETAIL_PLACEMENT_ARGS)] : ""}]; '
        'if {[string first -use_diamond_legalizer $::ot_kit_dpl_args] >= 0 && [info commands ::ot_cts_dpl_orig] eq "" '
        '&& [info commands ::detailed_placement] ne ""} { rename ::detailed_placement ::ot_cts_dpl_orig; '
        'proc ::detailed_placement {args} { if {![llength $args]} { set args $::ot_kit_dpl_args }; '
        'uplevel 1 [list ::ot_cts_dpl_orig {*}$args] }; '
        'puts "OT_CTS_DPL_ARGS: CTS detailed_placement uses the kit 3_5 legalizer: $::ot_kit_dpl_args" } ;# OT_CTS_DPL_ARGS')
s = p.read_text()
s, n = re.subn(r'(?m)^( *)(erase_non_stage_variables cts)', lambda m: m.group(1) + line + '\n' + m.group(1) + m.group(2), s, count=1)
assert n == 1
p.write_text(s)
OT_CTS_DPL_PY
    [ "$?" = 0 ] || exit 2
  else echo "OT_CTS_DPL_ARGS inactive: no erase_non_stage_variables cts in $CT"; fi
fi
# KW-FIX-25/AUTORENDER 11-06 (OWNER visual check + smell list): advisory PNGs + smells.json after place, GRT and route, when the
# kit carries layout_render_hook.sh.  flow.sh (disposable container copy) gets an EXIT trap, so the hook runs right after each
# stage process, before the next stage peaks, also after a failed stage (its -failed ODB).  The stage's exit status is kept and
# the hook always returns 0, bounded by this timeout.  The hook reads ODBs only and writes under run/layout_review.
# Opt-out inside the hook: OT_LAYOUT_RENDER=0 or 'export OT_LAYOUT_RENDER = 0' in config.mk.
FS=$SD/flow.sh
if [ -f "$W/layout_render_hook.sh" ] && [ -f "$FS" ] && ! grep -qF "OT_LAYOUT_RENDER hook" "$FS"; then
  LH="trap 'ot_lr=\$?; timeout -k 10 \${OT_LAYOUT_RENDER_TOTAL_S:-1000} bash $W/layout_render_hook.sh \"\${1:-}\" \$ot_lr </dev/null || true; exit \$ot_lr' EXIT ;# OT_LAYOUT_RENDER hook"
  if grep -q '^set -euo pipefail' "$FS"; then sed -i "0,/^set -euo pipefail/s@@&\n$LH@" "$FS"
  else echo "OT_LAYOUT_RENDER inactive: no set -euo line in $FS"; fi
fi
if [ "${OT_GRT183_RESUME:-1}" = 0 ] || grep -q '^export OT_GRT183_RESUME = 0' "$W/config.mk" 2>/dev/null || [ ! -f "$W/grt183_resume.tcl" ]; then exec "$@"; fi
# disposable container copy of the ORFS script, as orfs_hold_mm.py: hook first, then the kit's own (also an 'override' one)
if ! grep -qF "$HOOK" "$S" 2>/dev/null; then
  if ! grep -q '^ *source_step_tcl PRE GLOBAL_ROUTE' "$S" 2>/dev/null; then echo "OT_GRT183_RESUME inactive: no PRE GLOBAL_ROUTE step in $S"; exec "$@"; fi
  sed -i "s|^\( *\)source_step_tcl PRE GLOBAL_ROUTE|\1$HOOK\n&|" "$S"
fi
# KW-FIX-17 11-05 GRT-STALL: grt_stall_resume.tcl (when the kit carries it) goes right before the GRT-0183 hook
SHOOK="source /work/grt_stall_resume.tcl"
if [ -f "$W/grt_stall_resume.tcl" ] && ! grep -qF "$SHOOK" "$S" 2>/dev/null; then
  sed -i "s|^\( *\)source /work/grt183_resume.tcl|\1$SHOOK\n&|" "$S"
fi
export KWRS_DONE=${KWRS_DONE:-$W/.kwrs_done.r$(cksum < "$W/resume.json" 2>/dev/null | cut -d" " -f1)}   # same key as kwrs_make.sh (KW-FIX-30: not $PPID, 1 in a container)
R=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1)
restore() { if [ -n "$R" ] && [ -f "$R/4_cts.pre_grt183.odb" ]; then mv -f "$R/4_cts.pre_grt183.odb" "$R/4_cts.odb"; fi
  [ -z "$R" ] || rm -f "$R/5_1_grt.stall_strip.shapes"; }
restore   # a re-run killed hard left the swap in place; its marker stays, so it does not get another one
# KW-FIX-17 11-05 GRT-STALL (COORD 17:2x (6) / 17:4x): ORFS global_route.tcl's 'global_route -end_incremental' after the
# post-GRT repair_design can spin single-threaded for hours (HBM dma_m6c 637 buffers, S81 dsdv_eng_rr_e_rfg2 1008, QC nk/nl
# a0c: log flat >2 h on that line), while ~560 finished runs took at most 77 min there.  grt_stall_resume.tcl saves the
# resized design when repair_design_helper returns.  This watch
# stops the stage (its own process group only) when 5_1_grt.tmp.log has been flat OT_GRT_STALL_S (default 5400 s) with
# '-end_incremental' as its last command and a save from THIS run exists; the stage then re-runs ONCE in a fresh process from
# that design, exactly as the GRT-0183 resume below (same marker: one fresh re-run per kit in total).  No gate, margin or
# repair change.  OT_GRT_STALL_RESUME=0 (env or config.mk export) opts out.
T0=$(date +%s); stall=0; gstop=""
stall_off() { [ "${OT_GRT_STALL_RESUME:-1}" = 0 ] || grep -q '^export OT_GRT_STALL_RESUME = 0' "$W/config.mk" 2>/dev/null; }
# Retired GRT stops: neither overflow nor elapsed repair time terminates GRT.
# OT_GRT_POST_MAX_S is only an optional diagnostic log threshold (default0).
# Zero, from config or environment, disables that diagnostic; it never enables
# a wall-time cap. Progressing pinned jobs keep their work and checkpoints.
cfg_num() { local v; v=$(sed -n "s/^export $1[[:space:]]*=[[:space:]]*\([0-9][0-9]*\)[[:space:]]*$/\1/p" "$W/config.mk" 2>/dev/null | tail -1)
  printf '%s' "${v:-$2}"; }
POST_MAX=${OT_GRT_POST_MAX_S:-$(cfg_num OT_GRT_POST_MAX_S 0)}
# S81-CONG REPAIR-NOPROGRESS 11-16 (FABLE-FIX-S81-CONG; COORD / FABLE-FLOW-0913: 8 jobs in 16 h silent to the 12 h line inside the
# post-GRT max-wire repair_design; A_t68 5.6 h between two table rows, perf 82 % single-thread incremental FastRoute).  While the
# log is inside 'OT_MAXWIRE repair_design' (grt_maxwire.tcl body started, its 'leaf instances' end line not yet printed):
#  - one OT_GRT_REPAIR_PASS line every OT_GRT_REPAIR_LOG_S (default 600 s) with the last table row and the flat time;
#  - log flat OT_GRT_REPAIR_STALL_S (default 1800 s): the stage is stopped and re-run ONCE in a fresh process with the marker
#    5_1_grt.repair_nostall.json; grt_maxwire.tcl then skips the post-GRT repair_design, so the stage keeps the
#    full route's result (the best design it has) and continues to 5_1_grt.odb.  Not a failure: rc is the re-run's rc.  0 (env or config.mk export) = off.
RSTALL=${OT_GRT_REPAIR_STALL_S:-$(cfg_num OT_GRT_REPAIR_STALL_S 1800)}; RLOG=${OT_GRT_REPAIR_LOG_S:-$(cfg_num OT_GRT_REPAIR_LOG_S 600)}
rstall=0; rlast=0
repair_check() {   # $1 = this run's 5_1_grt.tmp.log, $2 = stage pid; sets rstall and stops the stage
  local Tl=$1 pid=$2 now a b age row
  [ "$(stat -c %Y "$Tl")" -ge "$T0" ] || return 1
  a=$(grep -c '^OT_MAXWIRE repair_design' "$Tl"); b=$(grep -c '^OT_MAXWIRE leaf instances' "$Tl")
  [ "$a" -gt "$b" ] || return 1
  now=$(date +%s); age=$((now - $(stat -c %Y "$Tl")))
  row=$(grep -E '^ +[0-9]+ \|' "$Tl" | tail -1 | awk -F'|' '{gsub(/ /,""); print "nets_done=" $1 " buffers=" $4 " remaining=" $6}')
  if [ "$RLOG" -gt 0 ] && [ $((now - rlast)) -ge "$RLOG" ]; then
    echo "OT_GRT_REPAIR_PASS post-GRT repair_design ${row:-no table row yet} log_flat_s=$age $(date -u '+%F %T')"; rlast=$now
  fi
  [ "$RSTALL" -gt 0 ] && [ "$age" -ge "$RSTALL" ] || return 1
  [ -n "$Rw" ] && [ ! -f "$Rw/5_1_grt.repair_nostall.json" ] || return 1
  echo "OT_GRT_REPAIR_NO_PROGRESS 5_1_grt.tmp.log flat ${age} s inside the post-GRT repair_design (${row:-no table row}): stopping the stage (process group $pid) $(date -u '+%F %T')"
  rstall=1; kill -TERM -- -$pid 2>/dev/null || kill -TERM $pid; sleep "${OT_GRT_STALL_KILL_WAIT:-20}"; kill -KILL -- -$pid 2>/dev/null
  return 0
}
grt_slack() {   # last slack figures the log carries (hold guard chunks / start, repair_timing tables); never a new STA
  local h s
  h=$(grep -oE 'OT_HOLD_GUARD_GRT (chunk [0-9]+|start): hold ws -?[0-9.]+' "$1" | tail -1 | sed 's/.*hold ws //')
  s=$(grep -oE '(setup|Setup)[^|]*WNS[^0-9-]*-?[0-9.]+' "$1" | tail -1 | grep -oE -- '-?[0-9.]+$')
  printf 'hold_ws_ps=%s setup_wns=%s' "${h:-unmeasured}" "${s:-unmeasured}"; }
# GRT-EARLY (inside-route overflow stop, rule 15:10000,20:1000) and GRT-INCR-CONGESTED (stop on a congested end of the full route) REMOVED 11-14, OWNER: remove conservative limits; GRT runs its full iterations.
gstop_check() {   # $1 = this run's 5_1_grt.tmp.log, $2 = stage pid; observes post-route diagnostic time; never stops GRT
  local Tl=$1 pid=$2 now last
  [ "$(stat -c %Y "$Tl")" -ge "$T0" ] || return 1
  if [ -z "$tpost" ]; then grep -q 'GRT-0303\]' "$Tl" && tpost=$(date +%s) || return 1; fi
  now=$(date +%s); last=$(grep -v '^[[:space:]]*$' "$Tl" | tail -1 | cut -c1-160)
  # WF-1 11-14 (COORD/OWNER: delete the conservative limits; kv3_sys_c b5215b6c8bc0 was killed STRUCTURAL/grt-timecap while converging):
  # the post-route time cap no longer kills GRT.  The line is logged once past OT_GRT_POST_MAX_S (default0: disabled) and the stage goes on.
  if [ -z "${tlogged:-}" ] && [ "$POST_MAX" -gt 0 ] && [ $((now - tpost)) -ge "$POST_MAX" ]; then
    echo "OT_GRT_TIMELOG stage=grt post-route repair over $((now - tpost)) s (log threshold $POST_MAX s, NO CAP: GRT continues) $(grt_slack "$Tl") last='$last' $(date -u '+%F %T')"
    tlogged=1
  fi
  [ -n "$gstop" ] || return 1
  kill -TERM -- -$pid 2>/dev/null || kill -TERM $pid; sleep "${OT_GRT_STALL_KILL_WAIT:-20}"; kill -KILL -- -$pid 2>/dev/null
  return 0
}
# FAILFAST-1 11-11 (COORD, owner fail-fast): stop on PROGRESS, not on silence.  The 2-h hung-job watchdog never fires on a build
# that keeps writing its log: DISK-1111 found six epyc4 GRTs 23-49 h in "extra iterations to remove congestion" (3-15 rounds of
# 30, GRT-0273 Disabled NDR), DRT at pass 27, hold repair that hit the buffer cap and then routed anyway.  Every poll
# /work/failfast_rules.py (kit file, copied by core_flow.stage_grt183; rules and defaults in its docstring) judges THIS run's
# logs and prints one class line: (a) [OT_GRT_NO_PROGRESS REMOVED 11-14, OWNER], (b) OT_DRT_NO_PROGRESS (from iteration 20: > 10000 violations, < 5 % per iteration over the
# last 3), (c) OT_HOLD_STRUCTURAL (buffer cap hit twice, or OT_HOLD_STALL NEEDS_RTL).  The stage stops, rc 21, no re-run; the
# autopilot classifies the line (STRUCTURAL grt-no-progress / drt-no-progress -> wave ROUTING, hold-structural -> wave TIMING).
# Opt out: OT_FAILFAST=0 (env or 'export OT_FAILFAST = 0' in config.mk), or a single rule: OT_FF_DRT / OT_FF_HOLD = 0.
FF=$W/failfast_rules.py
ff_check() {   # sets gstop, prints the class line
  local line
  [ -f "$FF" ] || return 1
  line=$(timeout 120 python3 -I "$FF" judge "$W" "$T0" "$W/run/failfast_state.json" 2>/dev/null | head -n 1)
  [ -n "$line" ] || return 1
  echo "$line"
  # WF-1 11-14 (OWNER: delete the conservative limits; gunit g2 / bksel m7 were killed with exit 21 mid-repair): a hold-structural line
  # (hold repair over N h / stalled / buffer cap) is only LOGGED now; the stage is never stopped for it.  DRT no-progress still stops.
  case "$line" in OT_DRT_NO_PROGRESS*) gstop=drt_no_progress; return 0;; esac
  [ -n "${ff_hold_logged:-}" ] || { echo "OT_HOLD_STRUCTURAL_LOGGED: not a stop (no cap, WF-1 11-14); the stage continues"; ff_hold_logged=1; }
  return 1
}
watch_run() {
  stall=0; gstop=""; tpost=""
  rm -f "$W/run/failfast_state.json" 2>/dev/null
  if stall_off && [ "$POST_MAX" -le 0 ] && [ ! -f "$FF" ] && [ "$RSTALL" -le 0 ] && [ "$RLOG" -le 0 ]; then "$@"; return $?; fi
  if command -v setsid >/dev/null; then setsid "$@" & else "$@" & fi
  local pid=$! Rw Tl age last
  trap 'kill -TERM -- -$pid 2>/dev/null' TERM INT
  while kill -0 $pid 2>/dev/null; do
    local i=0; while [ $i -lt "${OT_GRT_STALL_POLL:-60}" ] && kill -0 $pid 2>/dev/null; do sleep 1; i=$((i + 1)); done   # no added latency
    kill -0 $pid 2>/dev/null || break
    Rw=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1); Tl=$(ls "$W"/run/logs/asap7/*/base/5_1_grt.tmp.log 2>/dev/null | head -1)
    if ff_check; then kill -TERM -- -$pid 2>/dev/null || kill -TERM $pid; sleep "${OT_GRT_STALL_KILL_WAIT:-20}"; kill -KILL -- -$pid 2>/dev/null; break; fi
    if [ -n "$Tl" ] && gstop_check "$Tl" $pid; then break; fi
    if [ -n "$Tl" ] && repair_check "$Tl" $pid; then break; fi
    stall_off && continue
    [ -n "$Rw" ] && [ -n "$Tl" ] && [ -f "$Rw/5_1_grt.stall_resume.odb" ] && [ ! -f "$Rw/5_1_grt.grt183_recovered.json" ] || continue
    [ "$(stat -c %Y "$Rw/5_1_grt.stall_resume.odb")" -ge "$T0" ] || continue      # a save from this run only
    age=$(( $(date +%s) - $(stat -c %Y "$Tl") )); [ "$age" -ge "${OT_GRT_STALL_S:-5400}" ] || continue
    last=$(grep -v '^[[:space:]]*$' "$Tl" | tail -1)
    case "$last" in "global_route -end_incremental"*) ;; *) continue;; esac
    echo "OT_GRT_STALL 5_1_grt.tmp.log flat ${age} s on '$last': stopping the stage (process group $pid) $(date -u '+%F %T')"
    stall=1; kill -TERM -- -$pid 2>/dev/null || kill -TERM $pid; sleep "${OT_GRT_STALL_KILL_WAIT:-20}"; kill -KILL -- -$pid 2>/dev/null
  done
  wait $pid; local r=$?; trap - TERM INT; return $r
}
stall_clean() { local Rc; Rc=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1); [ -z "$Rc" ] || rm -f "$Rc/5_1_grt.stall_resume.odb" "$Rc/5_1_grt.stall_resume.shapes"; }
watch_run "$@"; rc=$?
if [ -n "$gstop" ]; then stall_clean; echo "OT_GRT_STOP $gstop: stage rc $rc -> 21 (no re-run)"; exit 21; fi
[ "$rc" != 0 ] || { stall_clean; exit 0; }
R=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1)
[ -n "$R" ] || exit "$rc"
L=$(ls -d "$W"/run/logs/asap7/*/base 2>/dev/null | head -1)
G=$L/5_1_grt.log
if [ "$rstall" = 1 ] && [ -f "$R/4_cts.odb" ] && [ ! -f "$R/5_1_grt.repair_nostall.json" ]; then
  stall_clean
  [ ! -f "$L/5_1_grt.tmp.log" ] || mv -f "$L/5_1_grt.tmp.log" "$L/5_1_grt.log.repair_attempt1"
  printf '{"schema": "opentallas.grt_repair_nostall.v1", "by": "grt183_make.sh", "rc_attempt1": %d, "flat_s": %d, "attempt1_log": "5_1_grt.log.repair_attempt1"}\n' "$rc" "$RSTALL" > "$R/5_1_grt.repair_nostall.json"
  [ ! -f "$KWRS_DONE" ] || sed -i '/^do-grt$/d;/^do-5_1/d' "$KWRS_DONE"
  echo "OT_GRT_REPAIR_NO_PROGRESS attempt 1 rc $rc: re-running once in a fresh process with the post-GRT max-wire repair skipped (continue, not a failure) $(date -u '+%F %T')"
  "$@"; rc=$?
  echo "OT_GRT_REPAIR_NO_PROGRESS attempt 2 rc $rc $(date -u '+%F %T')"
  exit "$rc"
fi
if [ "$stall" = 1 ] && [ -f "$R/5_1_grt.stall_resume.odb" ] && [ -f "$R/4_cts.odb" ] && [ ! -f "$R/5_1_grt.grt183_recovered.json" ]; then
  [ ! -f "$L/5_1_grt.tmp.log" ] || mv -f "$L/5_1_grt.tmp.log" "$L/5_1_grt.log.stall_attempt1"
  python3 -I - "$R" "$L/5_1_grt.log.stall_attempt1" "$rc" > "$R/5_1_grt.grt183_recovered.json" <<'PY'
import hashlib, json, os, sys
R, G, rc = sys.argv[1:]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()
last = [l.rstrip() for l in open(G, errors="replace") if l.strip()][-1:] if os.path.exists(G) else []
print(json.dumps({"schema": "opentallas.grt183_resume.v1", "kind": "grt_stall", "by": "grt183_make.sh", "rc_attempt1": int(rc),
                  "attempt1_log": "5_1_grt.log.stall_attempt1", "attempt1_lines": last,
                  "cts_odb_sha256": sha(R + "/4_cts.odb"), "resume_odb_sha256": sha(R + "/5_1_grt.stall_resume.odb")}, indent=1))
PY
  mv "$R/4_cts.odb" "$R/4_cts.pre_grt183.odb" && mv "$R/5_1_grt.stall_resume.odb" "$R/4_cts.odb" || { restore; exit "$rc"; }
  [ ! -f "$R/5_1_grt.stall_resume.shapes" ] || mv -f "$R/5_1_grt.stall_resume.shapes" "$R/5_1_grt.stall_strip.shapes"
  trap restore EXIT
  [ ! -f "$KWRS_DONE" ] || sed -i '/^do-grt$/d;/^do-5_1/d' "$KWRS_DONE"
  echo "OT_GRT_STALL_RESUME attempt 1 rc $rc: re-running once in a fresh process from the resized design $(date -u '+%F %T')"
  "$@"; rc=$?
  echo "OT_GRT_STALL_RESUME attempt 2 rc $rc $(date -u '+%F %T')"
  exit "$rc"
fi
stall_clean
if [ -f "$R/5_1_grt.grt183_recovered.json" ] || [ ! -f "$R/5_1_grt.grt183_resume.odb" ] || [ ! -f "$R/4_cts.odb" ] \
  || ! grep -q OT_GRT183_RESUME_SAVED "$G" 2>/dev/null || ! grep -q GRT-0183 "$G"; then exit "$rc"; fi
cp -p "$G" "$G.grt183_attempt1"
python3 -I - "$R" "$G" "$rc" > "$R/5_1_grt.grt183_recovered.json" <<'PY'
import hashlib, json, sys
R, G, rc = sys.argv[1:]
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()
lines = [l.rstrip() for l in open(G, errors="replace") if "GRT-0183" in l or "OT_GRT183_RESUME_SAVED" in l][:6]
print(json.dumps({"schema": "opentallas.grt183_resume.v1", "by": "grt183_make.sh", "rc_attempt1": int(rc),
                  "attempt1_log": "5_1_grt.log.grt183_attempt1", "attempt1_lines": lines,
                  "cts_odb_sha256": sha(R + "/4_cts.odb"), "resume_odb_sha256": sha(R + "/5_1_grt.grt183_resume.odb")}, indent=1))
PY
mv "$R/4_cts.odb" "$R/4_cts.pre_grt183.odb" && mv "$R/5_1_grt.grt183_resume.odb" "$R/4_cts.odb" || { restore; exit "$rc"; }
trap restore EXIT
[ ! -f "$KWRS_DONE" ] || sed -i '/^do-grt$/d;/^do-5_1/d' "$KWRS_DONE"
echo "OT_GRT183_RESUME attempt 1 rc $rc: re-running once in a fresh process from the resized design $(date -u '+%F %T')"
"$@"; rc=$?
echo "OT_GRT183_RESUME attempt 2 rc $rc $(date -u '+%F %T')"
exit "$rc"
