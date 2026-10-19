#!/bin/bash
# Q-CLK 10-18: PHYSICAL die clock of a Qwen compute die GEN under the landed-regions standard, on ITS OWN placed
# floorplan (chain case_r22k/floorplan.odb), TT + FF.  Same method as tools/qwen_kv_die/chain/kv_die_clock_regions.sh.
#   qwen_compute_dieclk.sh prep  D CASE LIBS        (clk_rx port completion, geometry + pairs, spec / targets / families)
#   qwen_compute_dieclk.sh spine D VARIANT          (GEN16: spine spec from spec.json, then build)
#   qwen_compute_dieclk.sh build D VARIANT          (VARIANT v0 = independent region trees;
#                                                    v1 = + neighbour-relative trim of every cross-region data pair
#                                                    without a landing, budget 60 ps, judged as one family)
# D holds tools/ (die_clock, die_clock_check.py, die_clock_geom_dump.py).  Results: D/<VARIANT>/STATUS, check_*.txt,
# landed_pairs.json, png/.
set -u
MODE=$1; D=$2; TL=${DC_TOOLS:-tools}   # tools dir under D (a variant may bring its own copy)
say() { echo "$(date '+%F %T %Z') QCLK $*" | tee -a $D/STATUS.log; }
IMG=openroad/orfs:asap7lock
if [ "$MODE" = prep ]; then
  C=$3; L=$4
  mkdir -p $D/libs && cp $L/*_tt.lib $L/*_ff.lib $L/clocks_*.tcl $L/views.json $D/libs/ && cp $C/die.v $C/fwd_lanes.json $D/
  for c in TT FF; do
    lc=$(echo $c | tr A-Z a-z)
    { for f in AO INVBUF OA SIMPLE; do echo "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_${f}_RVT_${c}_nldm_2*.lib.gz"; done
      echo "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_${c}_nldm_2*.lib"
      for f in $D/libs/*_${lc}.lib; do echo /work/libs/$(basename $f); done; } > $D/libs_${lc}.glob
  done
  DK="docker run --rm --cpus=4 --memory=${DC_MEM:-48}g -v $D:/work -v $C:/case:ro -w /work $IMG bash -lc"
  $DK "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /work/$TL/die_clock/qwen_clkrx_ports.py --odb /case/${DC_FLOORPLAN:-floorplan.odb} --die-v /work/die.v --out /work/floorplan_ck.odb > /work/clkrx_ports.log 2>&1" \
    || { say "clk_rx port completion FAIL (clkrx_ports.log)"; exit 1; }
  say "$(grep -h 'QCLK_CLKRX' $D/clkrx_ports.log | tr '\n' ' ' | cut -c1-600)"
  ROOTS=$(grep -o 'qfd_clkrx clk_rx (.*' $D/die.v | grep -o '\.pll_[a-z0-9_]*' | tr -d . | grep -v pll_fwd | sed 's#^#clk_rx/#' | paste -sd,)
  $DK "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -no_init -exit /work/$TL/die_clock_geom_dump.py --odb /work/floorplan_ck.odb --out /work/geom --pairs --roots $ROOTS > /work/geom.log 2>&1" \
    || { say "geom dump FAIL"; exit 1; }
  say "geom: $(grep -c ROOT_MISSING $D/geom.log) roots missing, $(wc -l < $D/geom/clknets.tsv) entry pins, $(grep GEOM_DUMP_PAIRS $D/geom.log)"
  python3 $D/$TL/die_clock/qwen_compute_dieclk_prep.py --geom $D/geom --clocks-dir $D/libs --out $D --die "$(basename $C)" | tee -a $D/STATUS.log
  python3 $D/$TL/die_clock/qwen_landed_pairs.py --geom $D/geom --lanes $D/fwd_lanes.json --out $D/landed_pairs_pre.json | tee -a $D/STATUS.log
  # v1: neighbour pairs = every cross-region data pair the standard leaves unlanded (GAP), as tree names
  python3 - $D <<'PY'
import json, sys, collections
D = sys.argv[1]
sp = json.load(open(f'{D}/spec.json'))
name = {t['root']: t['name'] for t in sp['trees']}
roots = collections.defaultdict(set)
for ln in open(f'{D}/geom/clknets.tsv'):
    r, ld = ln.split('\t')[:2]; roots[ld.split('/')[0]].add(r)
lp = json.load(open(f'{D}/landed_pairs_pre.json'))
nb = set()
gp = lp.get('gap_root_pairs', [])
for ra, rb in gp:
    if ra in name and rb in name:
        nb.add(tuple(sorted((name[ra], name[rb]))))
sp['neighbours'] = sorted(map(list, nb)); sp['neighbour_budget_ps'] = 60.0
sp['note'] += ' v1: + neighbour-relative trim (60 ps) of every unlanded cross-region data pair (GAP root pairs).'
json.dump(sp, open(f'{D}/spec_v1.json', 'w'), indent=1)
# families: v0 one per tree; v1 connected components of the neighbour graph
par = {t['name']: t['name'] for t in sp['trees']}
def f(x):
    while par[x] != x:
        x = par[x]
    return x
for a, b in nb:
    par[f(a)] = f(b)
fam = collections.defaultdict(list)
for t in sp['trees']:
    fam[f(t['name'])].append(t['root'])
json.dump(fam, open(f'{D}/families_v1.json', 'w'), indent=1)
print('QCLK v1 neighbours', len(nb), 'families', len(fam))
PY
  cp $D/spec.json $D/spec_v0.json; cp $D/families.json $D/families_v0.json
  say "prep done"
  exit 0
fi
if [ "$MODE" = spine ]; then
  # GEN16 10-19: spine variant spec (regional entries at the sink medians fed by ONE buffered DME spine; families =
  # all spine members, NEIGHBOUR pairs recorded); DC_SPINE_SOURCE overrides the source pin, DC_SPINE_TRIM=1 trims them
  python3 $D/$TL/die_clock/qwen_spine_spec.py --spec $D/spec.json --pairs $D/landed_pairs_pre.json --out-spec $D/spec_$3.json \
    --out-families $D/families_$3.json ${DC_SPINE_SOURCE:+--source $DC_SPINE_SOURCE} $([ "${DC_SPINE_TRIM:-0}" = 1 ] && echo --neighbours) \
    | tee -a $D/STATUS.log || exit 1
  MODE=build
fi
V=$3; O=$D/$V; mkdir -p $O/ff; chmod a+rwx $O $O/ff   # measure_only does not create its --out dir
DK="docker run --rm --cpus=${DC_CPUS:-8} --memory=${DC_MEM:-90}g -v $D:/work -w /work $IMG bash -lc"
PRE='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for c in tt ff; do for g in $(cat /work/libs_$c.glob); do ls $g; done > /work/libs_$c.txt; done;'
say "$V build start"
if [ "${DC_REUSE_TT:-0}" = 1 ] && [ -s $O/tt/clock.odb ] && [ -s $O/tt/manifest.json ]; then say "$V reuse TT build ($O/tt)"; else
$DK "$PRE /usr/bin/time -v openroad -python -no_init -exit /work/$TL/die_clock/build.py --odb /work/floorplan_ck.odb --libs /work/libs_tt.txt --libs-ff /work/libs_ff.txt --spec /work/spec_$V.json --targets /work/targets.json --out /work/$V/tt --iters ${DC_ITERS:-8} --write-odb > /work/$V/build_tt.log 2>&1" \
  || { say "$V CTS build FAIL ($V/build_tt.log)"; exit 1; }
fi
$DK "$PRE openroad -python -no_init -exit /work/$TL/die_clock/build.py --measure /work/$V/tt/manifest.json --odb /work/$V/tt/clock.odb --libs /work/libs_ff.txt --corner ff --out /work/$V/ff > /work/$V/measure_ff.log 2>&1" \
  || { say "$V FF measure FAIL ($V/measure_ff.log)"; exit 1; }
cd $O
AT=tt/arrivals_tt.tsv; AF=$(ls ff/arrivals_ff.tsv 2>/dev/null || ls ff/*.tsv | head -1)
python3 $D/$TL/die_clock/to_dump.py tt/manifest.json $AT dump_tt.tsv --pairs-from $D/geom/pairs.tsv
python3 $D/$TL/die_clock/to_dump.py tt/manifest.json $AF dump_ff.tsv --pairs-from $D/geom/pairs.tsv
python3 $D/$TL/die_clock_check.py report dump_tt.tsv --ff-dump dump_ff.tsv --targets $D/targets.json --budget-ps 80 \
  --region-map $D/spec_$V.json --families $D/families_$V.json --out die_clock_check.json > die_clock_check.txt 2>&1 \
  && say "$V CHECK TT+FF: $(grep -m1 'NEIGHBOUR CHECK' die_clock_check.txt)" || say "$V CHECK report FAIL ($V/die_clock_check.txt)"
python3 $D/$TL/die_clock/qwen_landed_pairs.py --geom $D/geom --lanes $D/fwd_lanes.json --arr-tt $AT --arr-ff $AF \
  --out landed_pairs.json > landed_pairs.log 2>&1; say "$V $(tail -1 landed_pairs.log | cut -c1-500)"
grep -q '"spine"' $D/spec_$V.json && { python3 $D/$TL/die_clock/spine_neighbour_report.py die_clock_check.json $D/spec_$V.json \
  --out spine_neighbour.json > spine_neighbour.log 2>&1; say "$V $(tail -1 spine_neighbour.log | cut -c1-600)"
  python3 - tt/manifest.json >> spine_neighbour.log 2>&1 <<'PY'
import json, sys
m = json.load(open(sys.argv[1])); s = m.get('spine', {})
print('QCLK_SPINE_MANIFEST cells', s.get('cells'), 'levels', s.get('levels'), 'members', len(s.get('members', [])),
      'model', json.dumps(s.get('model')), 'generator pins without loads', len(s.get('generator_pins_without_loads', [])))
PY
  say "$V $(tail -1 spine_neighbour.log | cut -c1-300)"; }
mkdir -p png
python3 $D/$TL/die_clock/plot.py tt/manifest.json $AT $D/geom/blocks.tsv png/die_tt.png --title "Q-CLK $V TT" > png/plot.log 2>&1
python3 $D/$TL/die_clock/plot.py tt/manifest.json $AF $D/geom/blocks.tsv png/die_ff.png --title "Q-CLK $V FF" >> png/plot.log 2>&1
grep -h 'cells\|iter' build_tt.log | tail -4 >> $D/STATUS.log
say "$V done: $O/die_clock_check.txt $O/landed_pairs.json $O/png"
