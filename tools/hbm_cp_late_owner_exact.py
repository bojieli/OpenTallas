#!/usr/bin/env python3
"""Exercise the default-off late-owner CP boundary against existing exact oracles."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'results/rtl/hbm_cp_late_owner_20261006')
out=parser.parse_args().output.resolve()
if out.exists():raise FileExistsError('Preserve prior exact evidence; supply a new --output directory')
out.mkdir(parents=True)
hashes={}
for kind in ('exact','parent'):
    command=json.loads((ROOT/f'results/rtl/hbm_cp_control_tail_20261006/exact_r1/{kind}_command.json').read_text())
    command=[v.replace('CONTROL_TAIL_CUT_TEST=1','CONTROL_TAIL_CUT_TEST=2') for v in command]
    command[command.index('-o')+1]=str(out/(kind+'.vvp'))
    for source in command:
        if source.endswith('.sv'):hashes[source]=hashlib.sha256((ROOT/source).read_bytes()).hexdigest()
    with (out/(kind+'_compile.log')).open('w') as f:subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/(kind+'.log')).open('w') as f:subprocess.run(['vvp',str(out/(kind+'.vvp'))],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    print((out/(kind+'.log')).read_text())
    (out/(kind+'.vvp')).unlink()
    (out/(kind+'_command.json')).write_text(json.dumps(command,indent=2)+'\n')
assert 'checks=8713' in (out/'exact.log').read_text()
assert 'checks=266' in (out/'parent.log').read_text()
(out/'terminal.json').write_text(json.dumps(dict(pass_exact=True,source_sha256=hashes,CONTROL_TAIL_CUT=2,added_cycles=0,added_registers=0,physical_qualified=False,adopted=False),indent=2)+'\n')
