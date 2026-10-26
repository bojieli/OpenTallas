#!/bin/bash
set -u
R=$PWD
mkdir -p base cand pylib
tar xzf pylib.tar.gz --strip-components=1 -C pylib
tar xf base.tar -C base
tar xf cand.tar -C cand
export PYTHONPATH="$R/pylib"
for side in base cand; do
 for cohort in closure_loop ref_tile; do
  (cd "$side/tools/$cohort"; python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' --continue-on-collection-errors . > "$R/${side}_${cohort}.log" 2>&1; echo $? > "$R/${side}_${cohort}.rc") &
 done
done
wait
python3 - <<'ENDPY'
from pathlib import Path
import json
out={}
for c in ('closure_loop','ref_tile'):
 out[c]={}
 for s in ('base','cand'):
  lines=Path(f'{s}_{c}.log').read_text().splitlines()
  out[c][s]={'summary':lines[-1], 'fails':sorted(set(x.split(' - ')[0] for x in lines if x.startswith(('FAILED ','ERROR '))))}
 out[c]['new']=sorted(set(out[c]['cand']['fails'])-set(out[c]['base']['fails']))
Path('comparison.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
ENDPY
