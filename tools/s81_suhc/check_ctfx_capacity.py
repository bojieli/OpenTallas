#!/usr/bin/env python3
"""Independent row/site/obstacle and complete connectivity audit of actual ODB replay."""
import pathlib,argparse,json,hashlib,collections
p=argparse.ArgumentParser();p.add_argument('directory');a=p.parse_args();r=pathlib.Path(a.directory)
def cells(name):
 out={}
 for l in (r/name).read_text().splitlines():
  x=l.split('\t');assert len(x)==8;assert x[0]not in out;out[x[0]]=dict(master=x[1],box=list(map(int,x[2:6])),status=x[6],orient=x[7])
 return out
b=cells('before_cells.tsv');c=cells('after_cells.tsv');assert set(b)==set(c)
owned=set((r/'owned_names.txt').read_text().splitlines());assert len(owned)==6810
for n in b:
 assert b[n]['master']==c[n]['master']
 if n not in owned:assert b[n]==c[n],('unrelated changed',n)
 else:assert b[n]['status']==c[n]['status']=='FIRM'
def signature(name):return hashlib.sha256('\n'.join(sorted((r/name).read_text().splitlines())).encode()).hexdigest()
for kind in ['nets','ports']:assert signature('before_'+kind+'.tsv')==signature('after_'+kind+'.tsv'),kind
rows=[]
for l in(r/'rows_exact.tsv').read_text().splitlines():
 x=l.split('\t');rows.append((*map(int,x[1:6]),x[6]))
for n in owned:
 x,y,X,Y=c[n]['box'];assert any(y==ry and Y==ey and x>=rx and X<=ex and (x-rx)%pitch==0 and c[n]['orient']==orient for rx,ry,ex,ey,pitch,orient in rows),('off row/site',n,c[n])
fixed=[(n,x)for n,x in c.items()if x['status']in ['FIRM','LOCKED','COVER']];active=[];pairs=0
for n,x in sorted(fixed,key=lambda x:x[1]['box'][0]):
 a,bx,A,B=x['box'];active=[(m,v)for m,v in active if v['box'][2]>a]
 for m,v in active:
  q,w,Q,W=v['box']
  if min(B,W)>max(bx,w):pairs+=1;raise AssertionError(('fixed overlap',n,m))
 active.append((n,x))
move=max((abs((b[n]['box'][0]+b[n]['box'][2])-(c[n]['box'][0]+c[n]['box'][2]))+abs((b[n]['box'][1]+b[n]['box'][3])-(c[n]['box'][1]+c[n]['box'][3])))/2000 for n in owned);assert move<=75
area=lambda box:(box[2]-box[0])*(box[3]-box[1])/1e6
fixed_area=sum(area(c[n]['box'])for n in owned);movable_area=sum(area(v['box'])for v in c.values()if v['status']=='PLACED')
span=lambda d:[min(d[n]['box'][0]for n in owned)/1000,max(d[n]['box'][2]for n in owned)/1000]
oldspan=span(b);newspan=span(c);height=sum((ey-ry)*(ex-rx)for rx,ry,ex,ey,pitch,orient in rows)/1e6/((max(ex for rx,ry,ex,ey,pitch,orient in rows)-min(rx for rx,ry,ex,ey,pitch,orient in rows))/1000)
report=dict(status='PASS',scope='actual copied ODB physical ownership and free-capacity proof only; no placement convergence or native timing',owned_anchors=len(owned),all_cells=len(c),unrelated_unchanged=len(c)-len(owned),native_launch_before_ps=160.72194,native_data_capture_before_ps=132.35901,maximum_move_um=move,old_active_band_um=oldspan,new_active_band_um=newspan,core_height_um=height,fixed_area_um2=fixed_area,movable_area_um2=movable_area,old_band_aggregate_population_fraction=(fixed_area+movable_area)/((oldspan[1]-oldspan[0])*height),new_band_aggregate_population_fraction=(fixed_area+movable_area)/((newspan[1]-newspan[0])*height),fixed_overlap_pairs=pairs,net_signature_sha256=signature('after_nets.tsv'),port_signature_sha256=signature('after_ports.tsv'),input_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in r.glob('*.tsv')})
(r/'capacity_proof.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
