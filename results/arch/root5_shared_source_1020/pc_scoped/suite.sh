#!/bin/bash
set -eu
R=$PWD
mkdir -p pylib base cand
tar xzf pylib.tar.gz --strip-components=1 -C pylib
for side in base cand; do
 tar xf base.tar -C "$side"
 (cd "$side"; git init -q; git unpack-objects < ../objects.pack >/dev/null; git apply --binary ../main.patch)
done
(cd cand; git apply --binary ../candidate.patch)
export PYTHONPATH="$R/pylib"
for side in base cand; do
 (cd "$side/tools/ref_tile"; set +e; python3 -m pytest -p no:cacheprovider -q -rfE -o addopts='' --continue-on-collection-errors . > "$R/${side}_ref_tile.log" 2>&1; echo $? > "$R/${side}_ref_tile.rc") &
done
wait
python3 - <<'PY'
from pathlib import Path
import re,json
result={}
for side in ('base','cand'):
 t=Path(f'{side}_ref_tile.log').read_text()
 result[side]={'exit':int(Path(f'{side}_ref_tile.rc').read_text()),'summary':t.splitlines()[-1], 'failures':sorted({re.sub(r' - .*','',x) for x in t.splitlines() if x.startswith(('FAILED ','ERROR '))})}
result['new']=sorted(set(result['cand']['failures'])-set(result['base']['failures']))
result['fixed']=sorted(set(result['base']['failures'])-set(result['cand']['failures']))
Path('comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
PY
