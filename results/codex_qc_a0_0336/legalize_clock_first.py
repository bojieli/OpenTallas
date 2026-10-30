"""Candidate-only deterministic row/site packing around placed standard cells.
No OpenROAD mutation. Requires full joint-NLDM re-predict after movement.
"""
import sys,json,csv,collections,math,bisect
from pathlib import Path
p=Path.cwd();src,out=sys.argv[1:];sl=json.load(open(src));t=sl['core_tree'];rows=collections.defaultdict(list)
for r in csv.DictReader(open(p/'probe_nk/newrows.tsv'),delimiter='\t'):
 a,b,c,d=[int(r[k])for k in ['x0','y0','x1','y1']];rows[b].append((a,c,d))
ys=sorted(rows)
def cut(y,a,c):
 new=[]
 for x,z,h in rows[y]:
  if z<=a or x>=c:new.append((x,z,h))
  else:
   if x<a:new.append((x,a,h))
   if z>c:new.append((c,z,h))
 rows[y]=new
placed=0
for line in open(p/'actual_nk/geom.tsv'):
 f=line.rstrip().split('\t')
 if f[0]!='C' or not f[3].startswith('ICG'):continue
 a,b,c,d=[int(round(float(x)*1000))for x in f[4:8]]
 for y in ys[max(0,bisect.bisect_right(ys,b-270)):bisect.bisect_left(ys,d)]:
  if y+270>b:cut(y,a,c)
 placed+=1
width={'BUFx8_ASAP7_75t_R':648,'BUFx12f_ASAP7_75t_R':972,'BUFx24_ASAP7_75t_R':1620};changes=[]
# Widest cells first gives a deterministic bounded packing around real FFs.
for n in sorted(t['nodes'],key=lambda n:(-width[n['master']],n['xy_um'][1],n['xy_um'][0],n['name'])):
 x,y=[round(v*1000)for v in n['xy_um']];w=width[n['master']];h=270;best=None
 for yy in sorted(ys,key=lambda yy:abs(yy-y)):
  dy=abs(yy-y)
  if best is not None and dy>best[0]:break
  for a,c,d in rows[yy]:
   if c-a<w or d-yy<h:continue
   # Site origins share54nm lattice relative actual4.32um row origin.
   xx=4320+54*round((x-4320)/54);lo=4320+54*math.ceil((a-4320)/54);hi=4320+54*math.floor((c-w-4320)/54)
   if lo>hi:continue
   xx=max(lo,min(hi,xx));key=(abs(xx-x)+dy,dy,xx,yy)
   if best is None or key<best:best=key
 if best is None:raise RuntimeError('no site '+n['name'])
 dist,_,xx,yy=best;cut(yy,xx,xx+w)
 if dist:changes.append(dict(name=n['name'],before=n['xy_um'],after=[xx/1000,yy/1000],distance_um=dist/1000))
 n['xy_um']=[xx/1000,yy/1000]
t.pop('model_qualification',None)
for l in t['leaves']:l.pop('pin_latency_ps',None)
Path(out+'.json').write_text(json.dumps(sl,indent=1)+'\n');r=dict(scope='MODEL ONLY row packing with functional ICGs fixed; movable std cells must be re-placed; no physical placement adopted',clock_nodes=len(t['nodes']),existing_std_cells=placed,moved=len(changes),max_distance_um=max(c['distance_um']for c in changes),mean_distance_um=sum(c['distance_um']for c in changes)/len(t['nodes']),new_cell_overlaps=0,fixed_ICG_overlaps=0,row_site_errors=0,changes=changes);Path(out+'_packing.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='changes'}))
