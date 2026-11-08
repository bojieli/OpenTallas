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
T0=$(date +%s); stall=0
stall_off() { [ "${OT_GRT_STALL_RESUME:-1}" = 0 ] || grep -q '^export OT_GRT_STALL_RESUME = 0' "$W/config.mk" 2>/dev/null; }
watch_run() {
  stall=0
  if stall_off; then "$@"; return $?; fi
  if command -v setsid >/dev/null; then setsid "$@" & else "$@" & fi
  local pid=$! Rw Tl age last
  trap 'kill -TERM -- -$pid 2>/dev/null' TERM INT
  while kill -0 $pid 2>/dev/null; do
    local i=0; while [ $i -lt "${OT_GRT_STALL_POLL:-60}" ] && kill -0 $pid 2>/dev/null; do sleep 1; i=$((i + 1)); done   # no added latency
    kill -0 $pid 2>/dev/null || break
    Rw=$(ls -d "$W"/run/results/asap7/*/base 2>/dev/null | head -1); Tl=$(ls "$W"/run/logs/asap7/*/base/5_1_grt.tmp.log 2>/dev/null | head -1)
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
