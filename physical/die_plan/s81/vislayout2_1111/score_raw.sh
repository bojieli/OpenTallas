#!/bin/bash
# score_raw.sh VAR TYPES... : seed -> raw plan (no legalise) -> route_supply edge_outline (fixed tool); top regions
W=/srv/opentallas-scratch2/claude/vislayout2-s81/w; T=$W/../tools; cd $W; V=$1; shift
mkdir -p raw_$V; for t in "$@"; do python3 -I $T/seed_r0.py ready7.json $t raw_$V/seed_$t.json $V >/dev/null; done
python3 -I -c "
import json,glob;d={}
for f in glob.glob('raw_$V/seed_*.json'): d.update(json.load(open(f)))
json.dump(d,open('raw_$V/seed.json','w'),indent=1)"
python3 -I $T/apply_seed.py ready7.json raw_$V/seed.json aug4/raw_r0_$V.json
for t in "$@"; do (python3 -I ../repo/tools/die_plan/route_supply.py $W/aug4/raw_r0_$V.json --die s81 --repo ../repo --types $t --grt-halving edge_outline --out $W/rs/fx_raw_r0_${V}_$t >/dev/null 2>&1) & done; wait
for t in "$@"; do printf "%s %s\t" $V $t; tail -1 rs/fx_raw_r0_${V}_$t/route_supply_s81.tsv | cut -f3-11,12-21 | cut -c1-200; python3 -I -c "
import json;d=json.load(open('rs/fx_raw_r0_${V}_$t/route_supply_s81.json'))['rows'][0]
print('   regions', {k:(v.get('p99') if isinstance(v,dict) else v) for k,v in (d.get('regions') or {}).items()}, 'wl', d['wirelength_mm'])"; done
