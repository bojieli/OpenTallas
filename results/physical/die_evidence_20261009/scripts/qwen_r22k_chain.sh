#!/bin/bash
# die-evidence-2 2026-10-09 (Claude): Qwen3-8B ROM die r22k (ROM die of the ROM die + KV die pair) die-level chain.
#   A. tools/qwen_kv_die/chain/die_chain.sh r22k (kv-die's chain, fixed here: GRT writes die_grt.spef in the routing
#      session, STA reads it (GRT-0008), ETM-bound libs read first): real case -> PDN r5 -> full-die GRT -> STA TT / FF
#   B. clock plan: extract_die --die qwen_rom --qwen-recipe r22k -> clock-only CTS htop / hreg -> record   [parallel]
#   C. IR: the prep's windowed PSM cases (PDN r5, 200 um guard), judged with ir_judge.py                 [parallel]
#   D. after GRT: guided representative-region DRTs (col / io / spine / vmsu) on the GRT checkpoint
# usage: qwen_r22k_chain.sh <src> <run dir (case_r22k/, libs/, ir/ from qwen_r22k_prep.sh)>
set -u
SRC=$(readlink -f $1); R=$(readlink -f $2); C=$R/case_r22k; G=$R/grt_r22k
PY=/srv/opentallas-scratch/claude/die-evidence-2/venv/bin/python     # scipy (the generator / extract_die need it)
Q3=/srv/opentallas-scratch/claude/qwen-die-r20
ADMIT=/srv/opentallas-scratch/admit.sh; H=$SRC/tools/qwen_kv_die/chain
say() { echo "$(date '+%F %T %Z') $*" >> $R/EVIDENCE.log; }
say "start src=$SRC ($(cat $SRC/SOURCE_COMMIT))"
# B. clock plan
( CK=$R/clock; mkdir -p $CK; cd $SRC
  $ADMIT 40 -- $PY tools/budgets/extract_die.py --src $SRC --die qwen_rom --qwen-recipe r22k --out $CK/model.json.gz > $CK/extract.log 2>&1 || { say "CLOCK extract FAIL ($(tail -1 $CK/extract.log))"; exit 1; }
  say "clock model: $(tail -1 $CK/extract.log | cut -c1-300)"
  for g in htop hreg; do
    $PY tools/budgets/clock_plan.py emit --die-model $CK/model.json.gz --group $g --name qwen_r22k_$g --out $CK/$g > $CK/emit_$g.log 2>&1 || { say "clock emit $g FAIL"; continue; }
    ( cd $CK/$g && $ADMIT 24 -- bash run.sh > run.out 2>&1 ) &
  done; wait
  $PY tools/budgets/clock_plan.py record --die-model $CK/model.json.gz $(for g in htop hreg; do [ -f $CK/$g/tree_SS.txt ] && echo --case $CK/$g; done) --out $CK/plan.json > $CK/record.log 2>&1
  gzip -kf $CK/plan.json 2>/dev/null; say "CLOCK PLAN: $(tail -1 $CK/record.log | cut -c1-400)" ) &
# C. IR
( cp $Q3/ir22/ir_judge.py $R/ir/ 2>/dev/null
  # unique case names (run_case.sh names containers after the dir; the r21b chain on this host uses ir_<window>)
  for d in $R/ir/ir_*/; do [ -d "$d" ] && mv ${d%/} $R/ir/ir22k_$(basename $d | sed 's/^ir_//'); done
  for d in $R/ir/ir22k_*/; do [ -f $d/run.tcl ] || continue
    ( $ADMIT 40 -- $H/run_case.sh $d run.tcl run.log 8 60 ) &
    sleep 30
  done; wait
  ( cd $R/ir && python3 ir_judge.py ir22k_* > judged.txt 2>&1 ); say "IR: $(tail -6 $R/ir/judged.txt | tr '\n' ' ' | cut -c1-600)" ) &
# A. case -> PDN -> GRT -> STA
bash $H/die_chain.sh r22k $R $SRC
say "die_chain: $(tail -3 $R/STATUS.log | tr '\n' ' ' | cut -c1-600)"
[ -f $G/ckpt_grt.odb ] || { say "NO GRT CHECKPOINT: regions skipped"; wait; exit 1; }
# D. regions: windows from the placed DEF (tile column, IO edge at the host SerDes, tree top, SU + VM stack)
$PY - $C/floorplan_placed.def > $R/windows.txt <<'PY'
import re, sys
t = open(sys.argv[1]).read(); u = float(re.search(r'UNITS DISTANCE MICRONS (\d+)', t).group(1))
W = [float(x) / u for x in re.search(r'DIEAREA \( (\S+) (\S+) \) \( (\S+) (\S+) \)', t).groups()]
def bb(pat):
    return [(float(m.group(3)) / u, float(m.group(4)) / u) for m in re.finditer(r'- (\S+) (\S+) \+ \S+ \( (\S+) (\S+) \)', t)
            if re.fullmatch(pat, m.group(1)) or re.fullmatch(pat, m.group(2))]
c = lambda v, lo, hi: max(lo, min(hi, v))
tl = sorted(bb(r'qfd_tile\S*'))
if tl:
    xs = sorted({round(x) for x, _ in tl}); x = xs[len(xs) // 4]; ys = sorted(y for xx, y in tl if round(xx) == x)
    y = ys[len(ys) // 2]; print(f'col {x - 40:.0f} {y - 3200:.0f} {x + 600:.0f} {y + 3200:.0f}')
io = bb(r'io_serdes\S*'); tt = bb(r'sp_tree_top\S*'); vm = bb(r'sp_vector_memory\S*'); uc = bb(r'ucie_kv|ot_qkvd_ucie\S*')
if io: x, y = io[0]; print(f'io {c(x-1700,0,W[2]-3500):.0f} {W[3]-2900:.0f} {c(x-1700,0,W[2]-3500)+3480:.0f} {W[3]:.0f}')
if tt: x, y = tt[0]; print(f'spine {x-300:.0f} {y:.0f} {x+1100:.0f} {y+4100:.0f}')
if vm: x, y = vm[0]; print(f'vmsu {x-300:.0f} {y-1500:.0f} {x+1900:.0f} {y+2500:.0f}')
if uc: x, y = uc[0]; print(f'ucie {c(x-800,0,W[2]-2400):.0f} 0 {c(x-800,0,W[2]-2400)+2400:.0f} 2400')
PY
say "region windows: $(tr '\n' ';' < $R/windows.txt)"
mkdir -p $R/regions
while read n x0 y0 x1 y1; do
  O=$R/regions/gw22k_$n
  ( cd $SRC && $PY tools/qwen_die_region_guided.py stage --ckpt $G/ckpt_grt.odb --out $O --win $x0,$y0,$x1,$y1 --threads 24 --mem 250 ) > $R/regions/$n.stage.log 2>&1 || { say "region $n stage FAIL"; continue; }
  mkdir -p $O/libs; cp $R/libs/*.lib $R/libs/views.json $O/libs/ 2>/dev/null
  cp -n $H/run_case.sh $SRC/tools/qwen_die_region_guided.py $O/ 2>/dev/null
  ( $ADMIT 150 -- $O/start_region.sh > $O/start.out 2>&1; say "region $n: $(tail -1 $O/STATUS.log 2>/dev/null)" ) &
  sleep 600
done < $R/windows.txt
wait
say "chain done: regions in $R/regions/gw22k_*/"
