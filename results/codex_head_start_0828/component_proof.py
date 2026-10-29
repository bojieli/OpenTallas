"""HEAD START measured proof decomposition for the existing GRT vehicle.

Each local BUFx8 output is observed at its downstream FF CLK pins (T/F rows),
so the BUFx8 component includes its final short wire. This telescopes with
measured native tree N/M nodes and keeps the real source-edge polarity.
"""
import json, re, shutil, sys
from pathlib import Path
repo, old, run, physical, out = map(Path, sys.argv[1:])
sys.path.insert(0, str(repo/'tools/die_plan'))
import clock_components as C
from trial_tap_arrivals import read_arr
ph = json.load(open(physical))
cv = (run/'out_TT/combo.v').read_text()
inst = {}
import die_sta_related as D
for m in D._INST_RE.finditer(cv):
    inst[m.group(2)] = dict(D._PIN_RE.findall(m.group(3)))
out.mkdir(parents=True, exist_ok=True)
for f in ('mesh.json','droop_regions.json'):
    shutil.copy(old/f,out/f)
for corner in ('TT','FF'):
    raw = (run/f'out_{corner}/arr_{corner}.txt').read_text()
    T,N,F,M=read_arr(run/f'out_{corner}/arr_{corner}.txt')
    proof=json.load(open(old/f'tap_arrivals_{corner}.json'))
    by_cell = {v:k for k,v in proof['node_cell'].items() if k.startswith('h') and '@' not in k}
    for prefix, values in (('N', N), ('M', M)):
        for name, value in values.items():
            if 'ck_'+name in inst:
                raw += f'\n{prefix} ck_{name} {value[0]} {value[1]}\n'
    proof['node_cell'] = {k: ('ck_'+v if 'ck_'+v in inst else v) for k,v in proof['node_cell'].items()}
    alias=[]
    ntap=0
    for port, entry in ph['stage_clock_drivers'].items():
        name=entry['inst']; path=by_cell[entry['stage']]; dest=f'__st__{path}'
        y=inst[name]['Y']
        alias.append(f'assign {dest} = {y};')
        raw += f'\nN {name} {T[port][0]} {T[port][1]}\nM {name} {F[port][0]} {F[port][1]}\n'
        raw += f'T {dest} {T[port][0]} {T[port][1]}\nF {dest} {F[port][0]} {F[port][1]}\n'
        ntap += 1
    net=out/f'components_{corner}.v'; net.write_text(cv+'\n'+'\n'.join(alias)+'\n')
    rf=out/f'components_{corner}.txt'; rf.write_text(raw)
    result=C.annotate(proof,net,rf)
    (out/f'tap_arrivals_{corner}.json').write_text(json.dumps(result,indent=0)+'\n')
    print(corner,len(result['node_clock_components']),len(result['taps']),ntap)
