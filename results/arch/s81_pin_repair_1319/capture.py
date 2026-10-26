from pathlib import Path
p=Path('/srv/opentallas-scratch/codex/s81-pin-repair-1319/replay.py')
s=p.read_text();s=s[:s.index('G.finalize_r8(m)')]+'''G.finalize_r8(m)
import gzip
with (OUT/'candidate-final.pickle').open('wb') as f:cloudpickle.dump(m,f,protocol=5)
texts=G.die_lef_texts(m)
with gzip.open(OUT/'candidate-exact-pins.lef.gz','wt') as f:f.write('\\n'.join(texts))
record=dict(insts=[[i.name,i.master,i.x,i.y,i.w,i.h,i.orient,i.kind,i.region] for i in m['insts']],buses=m['buses'],port_aliases=G.real_ports(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),checkpoint_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),frozen_loads=list(m.get('spread_load_pin_maps',{})))
with gzip.open(OUT/'candidate-final-plan.json.gz','wt') as f:json.dump(record,f)
print('CAPTURE_DONE',record['source_sha256'],record['checkpoint_sha256'],record['frozen_loads'],flush=True)
'''
exec(compile(s,'capture_generated.py','exec'))
