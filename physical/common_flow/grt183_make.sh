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
# KW-FIX-44 11-10 GRT-INCR-CONGESTED + GRT time cap (COORD rulings 11-10 (3)).  Two stops of the 5_1_grt stage, judged on
# THIS run's 5_1_grt.tmp.log (mtime >= wrapper start), measured from the end of the full global route (first GRT-0303
# 'Global routing runtime' line); the full route itself is never cut.
#  (a) congested: the full route ended with congestion (GRT-0115, only possible under -allow_congestion = KW-FIX-8
#      opt-in) and its final total overflow is >= OT_GRT_CONGESTED_FAIL_MIN (default 1000: FLOW-TIME-1 measured
#      2,594 kit logs, no form at >= 1000 overflow at iteration 20 later reached overflow 0, DRT or sign-off).  Below
#      that the KW-FIX-8 rule stands: DRT decides.  t53__clb66fa5cb a7: full route 13h46 at overflow 83,032, then the
#      incremental reroute after the leaf-repeat pass was silent 6h02 until the hub watchdog.  Stops the stage at once
#      and prints OT_GRT_CONGESTED_FAIL (autopilot: STRUCTURAL grt-overflow -> wave class ROUTING).
#      'export OT_GRT_CONGESTED_FAIL = 0' in config.mk (or env) opts out.
#  (b) time cap: everything after the full route (repair_design, incremental reroutes, hold repair) may take
#      OT_GRT_POST_MAX_S (default 21600 = 6 h).  t68 a5: full route 4h05, then post-GRT repair_design ran ~13 h (14,000
#      of 129,591 nets) before an outside kill; slw_fw_v1 cl592e3d37 a16: incremental route silent 6h06 at overflow 0
#      (neither matched the GRT-STALL rule below: last line was not the bare -end_incremental command).  The hold
#      guard alone caps hold repair at 3 h (hold_guard_grt.tcl).  Stops the stage and prints OT_GRT_TIMECAP with the
#      last hold/setup slack the log carries (autopilot: STRUCTURAL grt-timecap -> wave class TIMING).
#      'export OT_GRT_POST_MAX_S = 0' in config.mk (or env) opts out.
# Either stop: no fresh-process re-run, the stage's rc is replaced by 21.
cfg_num() { local v; v=$(sed -n "s/^export $1[[:space:]]*=[[:space:]]*\([0-9][0-9]*\)[[:space:]]*$/\1/p" "$W/config.mk" 2>/dev/null | tail -1)
  printf '%s' "${v:-$2}"; }
cong_off() { [ "${OT_GRT_CONGESTED_FAIL:-1}" = 0 ] || grep -Eq '^export OT_GRT_CONGESTED_FAIL[[:space:]]*=[[:space:]]*0[[:space:]]*$' "$W/config.mk" 2>/dev/null; }
CONG_MIN=${OT_GRT_CONGESTED_FAIL_MIN:-$(cfg_num OT_GRT_CONGESTED_FAIL_MIN 1000)}
POST_MAX=${OT_GRT_POST_MAX_S:-$(cfg_num OT_GRT_POST_MAX_S 21600)}
grt_overflow() { awk '/GRT-0096\] Final congestion report/{f=1} f && /^Total[[:space:]]/{v=$NF} END{print (v==""?"":v)}' "$1"; }
grt_slack() {   # last slack figures the log carries (hold guard chunks / start, repair_timing tables); never a new STA
  local h s
  h=$(grep -oE 'OT_HOLD_GUARD_GRT (chunk [0-9]+|start): hold ws -?[0-9.]+' "$1" | tail -1 | sed 's/.*hold ws //')
  s=$(grep -oE '(setup|Setup)[^|]*WNS[^0-9-]*-?[0-9.]+' "$1" | tail -1 | grep -oE -- '-?[0-9.]+$')
  printf 'hold_ws_ps=%s setup_wns=%s' "${h:-unmeasured}" "${s:-unmeasured}"; }
# KW-FIX-44 11-10 GRT-EARLY (COORD, owner: "fail fast is very important because many of the times you iterate on badly
# congested stuff for 12 hours or more").  (c) early: INSIDE the full global route.  The flow GRT writes congestion-<N>.rpt
# every 5 extra iterations (-congestion_report_iter_step 5); a report of THIS run whose summed 'congestion:' overflow meets
# the rule stops the stage there (FLOW-TIME-1 grt_early_stop rule 15:10000,20:1000: across 2,594 kit logs no form above it
# later reached overflow 0, DRT or sign-off).  t53__clb66fa5cb a7: congestion-15 = 23,535 at 01:13 -> stop then, instead
# of the 13h46 full route (final 83,032) plus 6h02 of incremental reroute.  -allow_congestion forms are judged too (the
# 1000 floor above already bounds KW-FIX-8).  The class line carries the H / V split and the densest 20-um tile (a
# mid-route report has no per-layer split; the GRT-0096 per-layer table exists only at the end of the route) and its top
# instance.  OT_GRT_EARLY_STOP = RULE (env or config.mk export) overrides the rule, 0 / off opts out.
early_rule() { local v=${OT_GRT_EARLY_STOP:-}
  [ -n "$v" ] || v=$(sed -n 's/^export OT_GRT_EARLY_STOP[[:space:]]*=[[:space:]]*\([0-9a-z:,]*\)[[:space:]]*$/\1/p' "$W/config.mk" 2>/dev/null | tail -1)
  case "${v:-15:10000,20:1000}" in 0|off) ;; *) printf '%s' "${v:-15:10000,20:1000}";; esac; }
EARLY_RULE=$(early_rule)
early_check() {   # judge each congestion-<N>.rpt of this run once, when it is complete (20 s old); sets gstop=congested
  local Rd f n
  [ -n "$EARLY_RULE" ] || return 1
  Rd=$(ls -d "$W"/run/reports/asap7/*/base 2>/dev/null | head -1); [ -n "$Rd" ] || return 1
  for f in "$Rd"/congestion-[0-9]*.rpt; do
    [ -f "$f" ] || continue
    n=${f##*/congestion-}; n=${n%.rpt}
    case " $early_done " in *" $n "*) continue;; esac
    [ "$(stat -c %Y "$f")" -ge "$T0" ] || { early_done="$early_done $n"; continue; }
    [ $(( $(date +%s) - $(stat -c %Y "$f") )) -ge "${OT_GRT_EARLY_SETTLE_S:-20}" ] || continue
    early_done="$early_done $n"
    line=$(python3 -I - "$f" "$n" "$EARLY_RULE" <<'OT_GRT_EARLY_PY'
import collections, re, sys, time
f, n, rule = sys.argv[1], int(sys.argv[2]), sys.argv[3]
thr = {}
for part in rule.split(","):
    m = re.fullmatch(r"\s*(\d+)\s*:\s*(\d+)\s*", part)
    if not m:
        sys.exit(0)                                   # a malformed rule never stops a run
    thr[int(m[1])] = int(m[2])
if n not in thr:
    sys.exit(0)
tot, hv, tiles, insts = 0, collections.Counter(), collections.Counter(), {}
kind = srcs = None
TILE = 20.0
for ln in open(f, errors="replace"):
    if ln.startswith("violation type:"):
        kind = "H" if "Horizontal" in ln else "V" if "Vertical" in ln else "?"
    elif ln.lstrip().startswith("srcs:"):
        srcs = ln.split()[1:]
    else:
        m = re.search(r"congestion:(\d+)", ln)
        if m:
            c = int(m[1]); tot += c; hv[kind] += c; cur = c
            continue
        m = re.search(r"bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\)", ln)
        if m and kind:
            x, y = (float(m[1]) + float(m[3])) / 2, (float(m[2]) + float(m[4])) / 2
            t = (int(x // TILE), int(y // TILE)); tiles[t] += cur
            for s in srcs or []:
                h = re.sub(r"^net:", "", s).split("/")[0]
                insts.setdefault(t, collections.Counter())[h] += 1
if tot < thr[n]:
    sys.exit(0)
hot = ""
if tiles:
    (tx, ty), tc = tiles.most_common(1)[0]
    top = insts.get((tx, ty), collections.Counter()).most_common(1)
    hot = (f" hotspot ({tx * TILE:g},{ty * TILE:g})-({(tx + 1) * TILE:g},{(ty + 1) * TILE:g}) overflow {tc} of {tot}"
           + (f" top {top[0][0]}" if top else ""))
print(f"OT_GRT_CONGESTED_FAIL stage=grt early: congestion-{n} overflow {tot} >= {thr[n]} (rule {rule}) "
      f"H {hv['H']} / V {hv['V']}{hot}; stopping inside the full global route (KW-FIX-44 GRT-EARLY) "
      + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
OT_GRT_EARLY_PY
)
    if [ -n "$line" ]; then echo "$line"; gstop=congested; return 0; fi
  done
  return 1
}
gstop_check() {   # $1 = this run's 5_1_grt.tmp.log, $2 = stage pid; sets gstop and stops the stage
  local Tl=$1 pid=$2 now ov last
  [ "$(stat -c %Y "$Tl")" -ge "$T0" ] || return 1
  if [ -z "$tpost" ] && early_check; then
    kill -TERM -- -$pid 2>/dev/null || kill -TERM $pid; sleep "${OT_GRT_STALL_KILL_WAIT:-20}"; kill -KILL -- -$pid 2>/dev/null
    return 0
  fi
  if [ -z "$tpost" ]; then grep -q 'GRT-0303\]' "$Tl" && tpost=$(date +%s) || return 1; fi
  now=$(date +%s); last=$(grep -v '^[[:space:]]*$' "$Tl" | tail -1 | cut -c1-160)
  if [ "$cong_seen" = 0 ]; then
    cong_seen=1
    if ! cong_off && grep -q 'GRT-0115\]' "$Tl"; then
      ov=$(grt_overflow "$Tl")
      if [ -n "$ov" ] && [ "$ov" -ge "$CONG_MIN" ]; then
        echo "OT_GRT_CONGESTED_FAIL stage=grt full global route ended with congestion: total overflow $ov >= $CONG_MIN; stopping before repair/incremental reroute (KW-FIX-44 GRT-INCR-CONGESTED) $(date -u '+%F %T')"
        gstop=congested
      fi
    fi
  fi
  if [ -z "$gstop" ] && [ "$POST_MAX" -gt 0 ] && [ $((now - tpost)) -ge "$POST_MAX" ]; then
    echo "OT_GRT_TIMECAP stage=grt post-route repair over $((now - tpost)) s (cap $POST_MAX s) $(grt_slack "$Tl") last='$last' (KW-FIX-44) $(date -u '+%F %T')"
    gstop=timecap
  fi
  [ -n "$gstop" ] || return 1
  kill -TERM -- -$pid 2>/dev/null || kill -TERM $pid; sleep "${OT_GRT_STALL_KILL_WAIT:-20}"; kill -KILL -- -$pid 2>/dev/null
  return 0
}
watch_run() {
  stall=0; gstop=""; tpost=""; cong_seen=0; early_done=""
  if stall_off && cong_off && [ "$POST_MAX" -le 0 ] && [ -z "$EARLY_RULE" ]; then "$@"; return $?; fi
  if command -v setsid >/dev/null; then setsid "$@" & else "$@" & fi
  local pid=$! Rw Tl age last
  trap 'kill -TERM -- -$pid 2>/dev/null' TERM INT
  while kill -0 $pid 2>/dev/null; do
    local i=0; while [ $i -lt "${OT_GRT_STALL_POLL:-60}" ] && kill -0 $pid 2>/dev/null; do sleep 1; i=$((i + 1)); done   # no added latency
    kill -0 $pid 2>/dev/null || break
    Rw=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1); Tl=$(ls "$W"/run/logs/asap7/*/base/5_1_grt.tmp.log 2>/dev/null | head -1)
    if [ -n "$Tl" ] && gstop_check "$Tl" $pid; then break; fi
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
