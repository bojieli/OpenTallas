"""Repack previously compiled immutable layer images without re-running the legaliser."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools/s81_dv/layer_prog'))
import xs_field_calendar as F
D=Path(sys.argv[1]);O=Path(sys.argv[2])
def decode(path):
 a=[int(x,16) for x in path.read_text().split()]
 return [sum(((a[n//8]>>(b*8+n%8))&1)<<b for b in range(72)) for n in range(4096)]
r=json.loads((D/'field_calendar.json').read_text())
p=decode(D/'pq_phase0.viamap.hex')
s=sum([decode(D/f'pq_stream{i}.viamap.hex') for i in range(4)],[])
cs=[F.op_calendar(op,p,s,[v['phase'] for v in c['phases']],period=c['period']) for op,c in r['ops'].items()]
lc=F.layer_calendar(cs)
F.write_layer_images(lc,p,s,O)
r.update(rows=lc['rows'],layer_windows=lc['windows'],segments=lc['segments'],unique_intervals=lc['unique_intervals'],action_edge_proof=True)
(O/'field_calendar.json').write_text(json.dumps(r,indent=1)+'\n')
loaded={str(Path(m.__file__).resolve().relative_to(ROOT)):hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT)}
(O/'compiler_sources.json').write_text(json.dumps(loaded,indent=1)+'\n')
print('REPACK',D,'uncompressed',sum(c['cal_rows'] for c in cs),'rows',lc['rows'],'intervals',len(lc['segments']),'unique',lc['unique_intervals'],flush=True)
