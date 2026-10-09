#!/bin/bash
# die-evidence-2 2026-10-09 (Claude): Qwen KV die evidence on top of the kv-die stream's chain (EPYC1 kv-die/die_kv:
# real case -> PDN -> full-die GRT -> its own STA).  kv-die owns the KV-die recipe and GRT; this adds:
#   B. own clock plan (extract_die --die qwen_kv -> clock-only CTS htop / hreg -> record)               [now]
#   A. STA TT / FF on the GRT SPEF (the GRT-0008 fix: kv-die's own STA reads guides = no wire RC)       [after GRT]
#   D. guided representative-region DRTs: stack aggregator + row engines (the 16.5 k-bit abutment), the N-edge
#      UCIe / d2d / seq column, the centre attention hub                                                  [after GRT]
# usage: qwen_kv_extras.sh <src> <kv-die run dir (die_kv)> <out dir>
set -u
SRC=$(readlink -f $1); K=$(readlink -f $2); E=$3; mkdir -p $E; E=$(readlink -f $E); G=$K/grt_kv; C=$K/case_kv
PY=/srv/opentallas-scratch/claude/die-evidence-2/venv/bin/python
ADMIT=/srv/opentallas-scratch/admit.sh; H=$SRC/tools/qwen_kv_die/chain
say() { echo "$(date '+%F %T %Z') $*" >> $E/STATUS.log; }
say "start src=$SRC ($(cat $SRC/SOURCE_COMMIT)) kv-die run=$K"
( CK=$E/clock; mkdir -p $CK; cd $SRC; [ -f $CK/extract.log ] && exit 0   # a clock run already started (re-launch)
  $ADMIT 20 -- $PY tools/budgets/extract_die.py --src $SRC --die qwen_kv --out $CK/model.json.gz > $CK/extract.log 2>&1 || { say "CLOCK extract FAIL ($(tail -1 $CK/extract.log | cut -c1-300))"; exit 1; }
  say "clock model: $(tail -1 $CK/extract.log | cut -c1-300)"
  for g in htop hreg; do
    $PY tools/budgets/clock_plan.py emit --die-model $CK/model.json.gz --group $g --name qwen_kv_$g --out $CK/$g > $CK/emit_$g.log 2>&1 || { say "clock emit $g FAIL"; continue; }
    ( cd $CK/$g && $ADMIT 16 -- bash run.sh > run.out 2>&1 ) &
  done; wait
  $PY tools/budgets/clock_plan.py record --die-model $CK/model.json.gz $(for g in htop hreg; do [ -f $CK/$g/tree_SS.txt ] && echo --case $CK/$g; done) --out $CK/plan.json > $CK/record.log 2>&1
  say "CLOCK PLAN: $(tail -1 $CK/record.log | cut -c1-400)" ) &
say "waiting for the kv-die GRT (grt_kv/run.exit + die_grt.spef)"
until [ -f $G/run.exit ] || grep -qE "PDN FAIL|REAL CASE FAIL|chain done" $K/STATUS.log 2>/dev/null; do sleep 300; done
[ -f $G/die_grt.spef ] && [ -f $G/ckpt_grt.odb ] || { say "no GRT SPEF/checkpoint ($(tail -1 $K/STATUS.log))"; wait; exit 1; }
say "GRT landed: $(grep 'full-die GRT' $K/STATUS.log | tail -1)"
for c in tt ff; do D=$E/sta_kv_$c; mkdir -p $D/libs
  ln -f $G/ckpt_grt.odb $G/die_grt.spef $D/ 2>/dev/null || cp $G/ckpt_grt.odb $G/die_grt.spef $D/
  cp $K/libs/qfd_elements_$c.lib $D/libs/; [ -f $K/libs/ot_hbm3e_phy_$c.lib ] && cp $K/libs/ot_hbm3e_phy_$c.lib $D/libs/
  python3 $H/sta_tcl.py kv $c $D/grt_$c.tcl
  ( $ADMIT 40 -- $H/dietop_run.sh $D grt_$c.tcl 8 100; say "STA $c (GRT SPEF): $(grep -E '^(wns|tns|worst slack)' $D/grt_$c.log | tr '\n' ' ')" ) &
done
$PY - $C/floorplan_placed.def > $E/windows.txt <<'PY'
import re, sys
t = open(sys.argv[1]).read(); u = float(re.search(r'UNITS DISTANCE MICRONS (\d+)', t).group(1))
W = [float(x) / u for x in re.search(r'DIEAREA \( (\S+) (\S+) \) \( (\S+) (\S+) \)', t).groups()]
pos = {m.group(1): (float(m.group(3)) / u, float(m.group(4)) / u) for m in re.finditer(r'- (\S+) (\S+) \+ \S+ \( (\S+) (\S+) \)', t)}
def first(p):
    k = sorted(n for n in pos if re.fullmatch(p, n)); return pos[k[0]] if k else None
c = lambda v, lo, hi: max(lo, min(hi, v))
a = first(r'astk_WS\S*') or first(r'astk\S*')
if a: x, y = a; print(f'astk {c(x-700,0,W[2]-2200):.0f} {c(y+500,0,W[3]-2200):.0f} {c(x-700,0,W[2]-2200)+2200:.0f} {c(y+500,0,W[3]-2200)+2200:.0f}')
u_ = first(r'ucie\S*|d2d\S*')
if u_: x, y = u_; print(f'ncol {c(x-600,0,W[2]-2000):.0f} {c(y-1600,0,W[3]-2000):.0f} {c(x-600,0,W[2]-2000)+2000:.0f} {c(y-1600,0,W[3]-2000)+2000:.0f}')
h = first(r'ahub\S*')
if h: x, y = h; print(f'ahub {c(x-700,0,W[2]-2000):.0f} {c(y-700,0,W[3]-2000):.0f} {c(x-700,0,W[2]-2000)+2000:.0f} {c(y-700,0,W[3]-2000)+2000:.0f}')
PY
say "region windows: $(tr '\n' ';' < $E/windows.txt)"
mkdir -p $E/regions
while read n x0 y0 x1 y1; do
  O=$E/regions/gwkv_$n
  ( cd $SRC && $PY tools/qwen_die_region_guided.py stage --ckpt $G/ckpt_grt.odb --out $O --win $x0,$y0,$x1,$y1 --threads 16 --mem 120 ) > $E/regions/$n.stage.log 2>&1 || { say "region $n stage FAIL"; continue; }
  mkdir -p $O/libs; cp $K/libs/*.lib $O/libs/ 2>/dev/null
  cp -n $H/run_case.sh $SRC/tools/qwen_die_region_guided.py $O/ 2>/dev/null
  ( $ADMIT 80 -- $O/start_region.sh > $O/start.out 2>&1; say "region $n: $(tail -1 $O/STATUS.log 2>/dev/null)" ) &
  sleep 300
done < $E/windows.txt
wait
say "done"
