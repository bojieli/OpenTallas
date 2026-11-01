from pathlib import Path
import json,copy,sys
p=Path(sys.argv[1]);r=json.load(open(p/'rec_drt.json'));f=copy.deepcopy(r)
for c in ('TT','FF'):
 rows={(v[1],v[0]):list(map(float,v[5:8])) for ln in (p/f'both_{c}.txt').read_text().splitlines() if (v:=ln.split())}
 for n in f['nodes']:
  vals=rows[(n['tag'],'A' if n['driver'] else 'Y')];n['arr'][c]=dict(zip(('late','early','slew'),vals))
 for t in f.get('early_taps',[]):t['arr'][c]=dict(zip(('late','early','slew'),rows[(t['leaf'],'A')]))
f['edge']='fall; same published linear Thevenin driver model, measured fall tree input waveforms'
(p/'rec_drt_fall.json').write_text(json.dumps(f))
