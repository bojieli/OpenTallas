import json,hashlib,collections,time
from pathlib import Path
from clock_sites import allocate,SIZES
start=time.monotonic();m=json.load(open('manifest.json'));b=json.load(open('buffers.json'))
trees={d:{'buffers':[r for r in b if r[0].startswith(p)],'model':{}} for d,p in [('hbm','dkh_'),('stream','dks_')]}
obs=[(v['x'],v['y'],v['x']+v['w'],v['y']+v['h']) for v in m['placement'].values()]
before=collections.Counter((r[2],r[3]) for r in b)
allocate(trees,*m['die_um'],obs)
a=[r for t in trees.values() for r in t['buffers']]
assert len(a)==len(b) and len({r[0] for r in a})==len(a)
assert len({(r[2],r[3]) for r in a})==len(a)
# Independent exact physical rectangle/hard-block intersection check.
for n,c,x,y in a:
 w,h=SIZES[c]
 assert 0<=x and 0<=y and x+w<=m['die_um'][0] and y+h<=m['die_um'][1]
 assert not any(x<ox1 and x+w>ox0 and y<oy1 and y+h>oy0 for ox0,oy0,ox1,oy1 in obs),n
# Actual cells must also not overlap any other clock cell, across domains.
bins=collections.defaultdict(list)
for n,c,x,y in a:
 w,h=SIZES[c];ix,iy=int(x//2),int(y//2)
 for i in range(ix-1,ix+2):
  for j in range(iy-1,iy+2):
   for nn,xx,yy,ww,hh in bins[i,j]:
    assert not(x<xx+ww-1e-6 and x+w>xx+1e-6 and y<yy+hh-1e-6 and y+h>yy+1e-6),(n,nn)
 bins[ix,iy].append((n,x,y,w,h))
r={'scope':'source-bound d3a clock site replay; NO electrical/route qualification','input_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ['manifest.json','buffers.json','clock_sites.py','die_clock_tree.py']},'cells':len(a),'original_unique_origins':len(before),'original_coincident_excess':len(b)-len(before),'original_max_origin_multiplicity':max(before.values()),'result_overlap':0,'result_hardblock_intersections':0,'result_outside':0,'domains':{d:t['model'] for d,t in trees.items()},'elapsed_s':round(time.monotonic()-start,2)}
Path('replay.json').write_text(json.dumps(r,indent=2)+'\n');Path('allocated.json').write_text(json.dumps(a));print(json.dumps(r),flush=True)
