#!/bin/bash
# hbm_die_post_grt.sh -- HBM R25GQ die, post-GRT evidence (hbmdie-v10-sta, 2026-10-12).
# Called by <run>/chain.sh after the die GRT of record (installed there as post_grt.sh); safe to re-run by hand.
# Stages (all on the relay-instanced STA case <run>/sta/case, tools/hbm_die_views.py die --case sta --relays):
#   0 prereq : clock plan + clock_plan.py balance (block insertion from views) + clock context + relay STA Tcl
#              (tools/hbm_die_sta_chain.sh STOP_BEFORE_GRT=1; resumes, kept if already built)
#   1 clkpin : relay / station clock-pin connectivity (tools/hbm_die_clock_pins.py); gate UNCLOCKED == 0
#   2 detour : GRT-of-record routed wirelength / placement HPWL (tools/hbm_die_relay_sta.py --detour-of)
#   3 sta_place : placement parasitics, TT setup / FF hold (owner option B) + OCV 0.95/1.05, wire C x1.40 / x2.44,
#              detour R,C x d, OCV + C x2.44 (run_sta_place.tcl)            -- fast bound, minutes
#   4 sta_grt : GLOBAL-ROUTE parasitics of the STA case (run_grt_sta.tcl: GRT M4-M9 -> estimate_parasitics
#              -global_routing), TT setup / FF hold / SS sensitivity + OCV 0.95/1.05, layer C x1.40 / x2.44,
#              OCV + C x2.44                                                  -- the record, hours
#   5 ir     : only when a PDN exists in the case (pdngen in run.tcl or <run>/pdn_<V>); else SKIPPED_NO_PDN
#   6 summary: <run>/sta_summary.json + <run>/results/README_row.md (copy both to results/physical/die_iter_1012/r25gq/)
# Stages 3 and 4 run concurrently (ot-heavy memory admission).  usage: [D=<run>] [SRC=<src>] [V=<preset>] hbm_die_post_grt.sh
set -u
D=${D:-/srv/opentallas-scratch/claude/hbmdie-v10}
SRC=${SRC:-$D/src_120f11b14}
V=${V:-r25gqn_v10}
B=${STA_ROOT:-$D/sta}; W=$B/case; G=${G:-$D/grt_${V}}
S=$D/sta_summary.json; R=$D/results; mkdir -p $R
MEM_PLACE=${MEM_PLACE:-64}; MEM_GRT=${MEM_GRT:-160}; CPU=${CPU:-16}
export PYTHONHASHSEED=0
say() { echo "$(date -Is) [post_grt] $*"; }
say "start V=$V src=$(cat $SRC/SOURCE_COMMIT 2>/dev/null) (GRT of record exit $(cat $G/grt.log.exit 2>/dev/null))"

# ---- 0 prereq ----
if [ ! -s $B/clock_ctx/clock_context.json ] || [ ! -s $W/run_grt_sta.tcl ]; then
  ( cd $SRC && V=$V STOP_BEFORE_GRT=1 bash tools/hbm_die_sta_chain.sh $SRC $B )
fi
[ -s $B/clock_ctx/clock_context.json ] || { say "NO CLOCK CONTEXT ($B/STATUS.log): STA skipped"; }

# ---- 1 clock-pin connectivity ----
( cd $SRC && python3 tools/hbm_die_clock_pins.py $W ) > $B/clock_pins_post.log 2>&1
CLKPIN=$(tail -1 $B/clock_pins_post.log)
say "clock pins: $(echo "$CLKPIN" | cut -c1-300)"

# ---- 2 detour factor ----
DET=0
if [ -s $G/wirelength.csv ]; then
  H=$D/hpwl
  if [ ! -s $H/hpwl.csv ]; then
    mkdir -p $H; cp $G/die.v $G/elements.lef $G/tech.lef $H/
    L=$(grep -n '^set_routing_layers' $G/run.tcl | head -1 | cut -d: -f1)
    { head -n $((L - 1)) $G/run.tcl; cat <<'EOF'
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open /work/hpwl.csv w]
set n 0
foreach net [[ord::get_db_block] getNets] {
  set st [$net getSigType]
  if {$st eq "POWER" || $st eq "GROUND"} { continue }
  set xs {}; set ys {}
  foreach it [$net getITerms] {
    set r [$it getAvgXY]
    if {[lindex $r 0]} { lappend xs [lindex $r 1]; lappend ys [lindex $r 2] } else {
      set b [[$it getInst] getBBox]; lappend xs [expr {([$b xMin] + [$b xMax]) / 2}]; lappend ys [expr {([$b yMin] + [$b yMax]) / 2}] }
  }
  foreach bt [$net getBTerms] { set b [$bt getBBox]; lappend xs [$b xMin]; lappend ys [$b yMin] }
  if {[llength $xs] < 2} { continue }
  set xs [lsort -integer $xs]; set ys [lsort -integer $ys]
  puts $f "[$net getName] [expr {double([lindex $xs end] - [lindex $xs 0] + [lindex $ys end] - [lindex $ys 0]) / $dbu}]"
  incr n
}
close $f
puts "OT_HPWL nets=$n"
EOF
    } > $H/hpwl.tcl
    ot-heavy --mem 16 -- bash $D/run_case.sh $H hpwl.tcl hpwl.log 4 16
  fi
  ( cd $SRC && python3 tools/hbm_die_relay_sta.py --detour-of $G/wirelength.csv $H/hpwl.csv ) > $B/detour.json 2>$B/detour.err
  DET=$(python3 -c "import json;print(json.load(open('$B/detour.json'))['detour_total'])" 2>/dev/null || echo 0)
  say "detour: $(cat $B/detour.json 2>/dev/null)"
else
  say "no $G/wirelength.csv: detour point skipped"
fi

# ---- 3 + 4 STA (placement bound and GRT record, concurrent) ----
if [ -s $B/clock_ctx/clock_context.json ]; then
  ( cd $SRC && python3 tools/hbm_die_relay_sta.py --case $W --clock-context $B/clock_ctx/clock_context.json \
      --measured results/rtl/budgets_20261006/measured_insertion.json --place-sens --detour $DET ) > $B/relay_sta_post.log 2>&1
  say "relay sta gen: $(tail -1 $B/relay_sta_post.log | cut -c1-300)"
  run_sta() {  # name tcl log mem
    ot-heavy --mem $4 -- docker run --rm --name hfd_${V}_$1 --cpus=$CPU --memory=${4}g -v $W:/work -v $W:/out \
      openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -threads $CPU -no_init -exit /work/$2 > /work/$3 2>&1; echo \$? > /work/$3.exit; chmod -R a+rwX /work"
    say "$1 exit $(cat $W/$3.exit 2>/dev/null) $(grep -E '^OT_WNS' $W/$3 | tr '\n' ' ')"
  }
  run_sta place run_sta_place.tcl sta_place.log $MEM_PLACE &
  run_sta grt run_grt_sta.tcl grt_sta.log $MEM_GRT &
  wait
fi

# ---- 5 IR ----
IR=SKIPPED_NO_PDN
grep -qiE 'pdngen|analyze_power_grid' $W/run.tcl $G/run.tcl 2>/dev/null && IR=PDN_IN_CASE_IR_NOT_WIRED
[ -d $D/pdn_$V ] && IR="PDN_CASE_PRESENT_NOT_RUN:$D/pdn_$V"
# ROOT14 10-20: the shared die IR-drop step (tools/die_safety/ir_step.sh: die-grid windows, M8+M9 straps, GRT M8 usage)
# on the GRT-of-record odb; FAIL / NOT_RUN -> OWNER_REPORT line (coordinator tells the owner) and post_grt exit 1
IR_RC=0
for O in $G/out/grt.odb $G/grt.odb $G/ckpt_grt.odb; do
  [ -s $O ] || continue
  OT_IR_DESIGN=hbm bash $SRC/tools/die_safety/ir_step.sh $O $D/ir_drop_$V $G/grt.log > $D/ir_drop_$V.log 2>&1 || IR_RC=1
  IR="$(grep -E '^DIE_IR_DROP ' $D/ir_drop_$V.log | tail -1 | cut -c1-300)"; break
done
say "ir: $IR"
[ $IR_RC = 0 ] || say "$(grep -E '^OWNER_REPORT ' $D/ir_drop_$V.log | tail -1)"

# ---- 6 summary + README row ----
python3 - "$W" "$B/detour.json" "$S" "$IR" "$G" "$CLKPIN" "$V" "$R" "$(cat $SRC/SOURCE_COMMIT 2>/dev/null)" <<'EOF'
import json, re, sys, os, time
w, det, out, ir, g, clk, v, rdir, src = sys.argv[1:]
def parse(path):
    t = open(path).read() if os.path.exists(path) else ''
    nom, sens = {}, {}
    for m in re.finditer(r'OT_WNS corner=(\w+)( pads=\w+)? ns=(\S+) tns_ns=(\S+)', t):
        nom[m[1] + (m[2] or '').replace(' pads=', '_')] = dict(wns_ns=float(m[3]), tns_ns=float(m[4]))
    for m in re.finditer(r'OT_FAIL_ENDPOINTS corner=(\w+)( pads=\w+)? n=(\d+)', t):
        nom.setdefault(m[1] + (m[2] or '').replace(' pads=', '_'), {})['fail_slack_lt_15ps'] = int(m[3])
    for m in re.finditer(r'OT_SENS case=(\S+) corner=(\w+) (.*)', t):
        kv = dict(x.split('=', 1) for x in m[3].split() if '=' in x)
        sens.setdefault(m[1], {})[m[2]] = {k: (int(x) if k == 'fail' else float(x)) for k, x in kv.items()}
    gs = re.search(r'OT_GRT_S (\d+)', t)
    tot = [l.strip() for l in t.splitlines() if l.startswith('Total')]
    return dict(log=path, exit=(open(path + '.exit').read().strip() if os.path.exists(path + '.exit') else None),
                done='OT_DONE' in t, nominal=nom, sens=sens, grt_s=gs and int(gs[1]), grt_total=tot[-1] if tot else None)
try:
    clkj = json.loads(clk)
except Exception:
    clkj = dict(raw=clk[:300])
r = dict(variant=v, src=src, when=time.strftime('%Y-%m-%d %H:%M %Z'),
         case='relay-instanced die STA case (hbm_die_views.py die --case sta --relays)',
         clock='own clock plan + clock_plan.py balance (block insertion from views) -> hbm_die_clock_context -> per-pin source latency',
         signoff='setup TT, hold FF (option B); SS setup sensitivity only',
         ocv='set_timing_derate -early 0.95 -late 1.05 (cells + nets)',
         wire_cap='C x1.40 / x2.44 (DRT/GRT net-C median / p95, results/physical/die_region_drt_1012), R x1',
         grt_of_record=dict(dir=g, exit=(open(f'{g}/grt.log.exit').read().strip() if os.path.exists(f'{g}/grt.log.exit') else None),
                            total=([l.strip() for l in open(f'{g}/grt.log') if l.startswith('Total')] or [None])[-1]
                            if os.path.exists(f'{g}/grt.log') else None),
         detour=json.load(open(det)) if os.path.exists(det) else None,
         clock_pins=clkj, sta_place=parse(f'{w}/sta_place.log'), sta_grt=parse(f'{w}/grt_sta.log'), ir=ir)
json.dump(r, open(out, 'w'), indent=1)
json.dump(r, open(f'{rdir}/sta_summary_{v}.json', 'w'), indent=1)
def f(st, c):
    x = st['nominal'].get(c)
    return f"{x['wns_ns'] * 1000:.0f}/{x['tns_ns']:.1f}/{x.get('fail_slack_lt_15ps', '?')}" if x else 'n/a'
def s(st, case):
    x = st['sens'].get(case, {})
    return ' '.join(f"{c}:{x[c]['wns_ns'] * 1000:.0f}" for c in ('tt', 'ff') if c in x) or 'n/a'
P, Q = r['sta_place'], r['sta_grt']
ocvk = next((k for k in Q['sens'] if k.startswith('ocv') and not k.endswith('2.44')), 'ocv0.05_c1.00')
row = (f"| {r['when']} | {v} @{src.split()[0] if src else '?'} | {r['grt_of_record']['total'] or 'n/a'} | "
       f"{(r['detour'] or {}).get('detour_total', 'n/a')} | TT {f(Q, 'tt')} FF {f(Q, 'ff')} SS {f(Q, 'ss')} | "
       f"TT {f(P, 'tt')} FF {f(P, 'ff')} | {s(Q, ocvk)} | {s(Q, 'c1.40')} | {s(Q, 'c2.44')} | {s(Q, ocvk.split('_')[0] + '_c2.44')} | "
       f"UNCLOCKED {clkj.get('UNCLOCKED', '?')} rly {clkj.get('by_family', {}).get('hfd_rly', '?')} fclk {clkj.get('forwarded_clock', '?')} | {ir} |")
hdr = ('| when | variant @src | GRT of record overflow | detour | GRT-parasitic WNS ps / TNS ns / fail (TT setup, FF hold, SS) | '
       'placement WNS/TNS/fail | OCV 0.95/1.05 WNS ps | C x1.40 | C x2.44 | OCV + C x2.44 | clock pins | IR |\n'
       '|---|---|---|---|---|---|---|---|---|---|---|---|\n')
open(f'{rdir}/README_row.md', 'w').write(hdr + row + '\n')
print(row)
EOF
say "summary $S ; README row $R/README_row.md (collect into results/physical/die_iter_1012/r25gq/)"
[ "${IR_RC:-0}" = 0 ] || { say "FAIL: die IR-drop check (OWNER REPORT)"; exit 1; }
