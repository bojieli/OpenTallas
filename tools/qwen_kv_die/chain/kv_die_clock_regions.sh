#!/bin/bash
# KV-CLOCK 10-18: die clock trees of a KV die run on ITS OWN floorplan (never arrivals borrowed from another plan), as
# independent core REGION trees (tools/die_clock/specs/kv_regions_1018.json: c, WS, WN, ES, EN + the four HBM trees; no
# balance group), TT + FF two-corner trim, re-measured at FF; die_clock_check at TT and FF per region (families = the
# regions, so only intra-region pairs are judged against 80 ps); cross-region pairs classified by kv_landed_pairs.py
# (LANDED / RESET_ROOT / GAP) against RUN/fwd_lanes.json.
# usage: kv_die_clock_regions.sh RUN SRC_WORKTREE      (waits for the chain's real case: STATUS 'real case:' line)
set -u
R=$1; S=$2; C=$R/case_kv; D=$R/dieclk
say() { echo "$(date '+%F %T %Z') DIECLK $*" >> $R/STATUS.log; }
mkdir -p $D/tools; chmod a+rwx $D
while :; do
  grep -q 'REAL CASE' $R/STATUS.log 2>/dev/null && { say "not run: the real case failed"; exit 1; }
  grep -q ' real case: ' $R/STATUS.log 2>/dev/null && [ -s $C/floorplan.odb ] && break
  sleep 120
done
cp -r $S/tools/die_clock $S/tools/die_clock_check.py $S/tools/die_clock_geom_dump.py $D/tools/
mkdir -p $D/tools/hbm_die_v15 && cp $S/tools/hbm_die_v15/*.py $D/tools/hbm_die_v15/
cp $S/tools/die_clock/specs/kv_regions_1018.json $S/tools/die_clock/specs/kv_regions_1018_families.json $D/
# std-cell libs (TT / FF) + this run's element / ETM libs
for c in TT FF; do
  lc=$(echo $c | tr A-Z a-z)
  ls /dev/null > /dev/null
  { for f in AO INVBUF OA SIMPLE; do echo "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_${f}_RVT_${c}_nldm_2*.lib.gz"; done
    echo "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_${c}_nldm_2*.lib"
    for f in $R/libs/*_${lc}.lib; do echo /kvlibs/$(basename $f); done; } > $D/libs_${lc}.glob
done
# R per master clock pin (in-arc insertion) from this run's measured view clocks (kvsys_clocks.py clocks.json)
python3 - $R/libs/clocks.json $D/targets.json <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))
m = {k: dict(view=v['view'], source='insertion.json (kvsys clocks.json measured)',
             insertion_per_clock_pin_ps={p: [v['R_ps'].get('ss', {}).get(p, v['R_ps']['tt'][p]), v['R_ps'].get('ff', {}).get(p, v['R_ps']['tt'][p]),
                                             v['R_ps']['tt'][p]] for p in v['R_ps'].get('tt', {})}) for k, v in c['measured'].items()}
json.dump(dict(schema='opentallas.die_clock.targets.v1', masters=m), open(sys.argv[2], 'w'), indent=1)
PY
ROOTS=pll/pll_c,pll/pll_WS,pll/pll_WN,pll/pll_ES,pll/pll_EN,pll/pll_hbm_WS,pll/pll_hbm_WN,pll/pll_hbm_ES,pll/pll_hbm_EN
DK="docker run --rm --cpus=8 --memory=${DC_MEM:-90}g -v $D:/work -v $C:/case:ro -v $R/libs:/kvlibs:ro -w /work openroad/orfs:asap7lock bash -lc"
PRE='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for c in tt ff; do for g in $(cat /work/libs_$c.glob); do ls $g; done > /work/libs_$c.txt; done;'
say "start (floorplan $(stat -c %y $C/floorplan.odb | cut -c1-19))"
$DK "$PRE openroad -python -no_init -exit /work/tools/die_clock_geom_dump.py --odb /case/floorplan.odb --out /work/geom --pairs --roots $ROOTS > /work/geom.log 2>&1" \
  || { say "geom dump FAIL (dieclk/geom.log)"; exit 1; }
$DK "$PRE /usr/bin/time -v openroad -python -no_init -exit /work/tools/die_clock/build.py --odb /case/floorplan.odb --libs /work/libs_tt.txt --libs-ff /work/libs_ff.txt --spec /work/kv_regions_1018.json --targets /work/targets.json --out /work/tt --iters ${DC_ITERS:-8} --write-odb > /work/build_tt.log 2>&1" \
  || { say "CTS build FAIL (dieclk/build_tt.log)"; exit 1; }
$DK "$PRE openroad -python -no_init -exit /work/tools/die_clock/build.py --measure /work/tt/manifest.json --odb /work/tt/clock.odb --libs /work/libs_ff.txt --corner ff --out /work/ff > /work/measure_ff.log 2>&1" \
  || { say "FF measure FAIL (dieclk/measure_ff.log)"; exit 1; }
cd $D
python3 tools/die_clock/to_dump.py tt/manifest.json tt/arrivals_tt.tsv dump_tt.tsv --pairs-from geom/pairs.tsv
python3 tools/die_clock/to_dump.py tt/manifest.json $(ls ff/arrivals_ff.tsv 2>/dev/null || ls ff/*.tsv | head -1) dump_ff.tsv --pairs-from geom/pairs.tsv
python3 tools/die_clock_check.py report dump_tt.tsv --ff-dump dump_ff.tsv --targets targets.json --budget-ps 80 \
  --region-map kv_regions_1018.json --families kv_regions_1018_families.json --out die_clock_check.json > die_clock_check.txt 2>&1 \
  && say "CHECK TT+FF: $(grep -m1 'NEIGHBOUR CHECK' die_clock_check.txt)" || say "CHECK report FAIL (dieclk/die_clock_check.txt)"
python3 $S/tools/qwen_kv_die/kv_landed_pairs.py --die-v $C/die.v.prefwd --pairs geom/pairs.tsv --lanes $R/fwd_lanes.json \
  --out landed_pairs.json > landed_pairs.log 2>&1; say "$(tail -1 landed_pairs.log)"
say "done: $D/die_clock_check.txt $D/landed_pairs.json"
