#!/usr/bin/env python3
"""Recover short native PG fragments through bounded M8 bridges to same-net M9.
The VIA78 bottom pad stays inside native M7. All newly added M8 metal obeys
actual track, native width/minarea and spacing; no abstract OBS is waived.
"""
import argparse,bisect,collections,json,math
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree

def hit(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--direct',required=True);p.add_argument('--geometry',required=True);p.add_argument('--grid',required=True);p.add_argument('--reserved',action='append',default=[]);p.add_argument('--out',required=True);a=p.parse_args();plan=json.load(open(a.direct));g=json.load(open(a.geometry));D=plan['dbu'];pg=json.load(open(a.grid));blocked=[];labels=[]
 gridkeys={(ly,*[round(v*D) for v in r]) for n,ly,*r in pg}
 for owner,ly,*r in g['obstructions']:
  if ly=='M8' and not (owner=='BLOCK' and (ly,*r) in gridkeys):blocked.append(r);labels.append('OBS:'+owner)
 for inst,pin,ly,*r in g['signal_shapes']:
  if ly=='M8':blocked.append(r);labels.append('SIGNAL:'+inst+'/'+pin)
 power=collections.defaultdict(list)
 for n,ly,*r in pg:
  if ly=='M8':power[n].append([round(v*D) for v in r])
 for f in a.reserved:
  for n,ly,*r in json.load(open(f)):
   if ly!='M8':continue
   r=[round(v*D) for v in r]
   if n in ['VDD','VSS']:power[n].append(r)
   else:blocked.append(r);labels.append('RESERVED:'+n)
 bt=STRtree([box(*r) for r in blocked]);pt={n:STRtree([box(*r) for r in rr]) for n,rr in power.items()};stripes={n:sorted([tuple(round(v*D) for v in r) for nn,ly,*r in pg if nn==n and ly=='M9']) for n in ['VDD','VSS']}
 # Track definitions are read from the actual target ODB, not an assumed pitch.
 tracks=g['tracks']['M8']['Y'];ys=[]
 for offset,count,pitch in tracks:ys.extend(offset+i*pitch for i in range(count))
 ys=sorted(set(ys));print('indexed_M8',len(blocked),'supplies', {n:len(r) for n,r in power.items()},flush=True)
 new=collections.defaultdict(list);outpaths=[];fails=[];reasons=collections.Counter()
 for f in plan['failed']:
  if f['reason']!='no_enclosed_same_net_M8_crossing':fails.append(f);continue
  n='VDD' if f['pin']=='VDD' else 'VSS';opp='VSS' if n=='VDD' else 'VDD';x0,y0,x1,y1=f['rect_dbu'];x=(x0+x1)//2;ylo,yhi=y0+27,y1-27
  yy=sorted(ys[bisect.bisect_left(ys,ylo):bisect.bisect_right(ys,yhi)],key=lambda y:abs(2*y-y0-y1));ss=sorted(stripes[n],key=lambda r:abs((r[0]+r[2])//2-x));found=None;last=None
  for y in yy:
   for s in ss[:4]:
    if not s[1]+20<=y<=s[3]-20:continue
    xx=max(s[0]+20,min(x,s[2]-20));r=[min(x,xx)-96,y-40,max(x,xx)+96,y+40];q=[r[0]-40,r[1]-40,r[2]+40,r[3]+40];qb=box(*q)
    if r[0]<0 or r[2]>g['die_dbu'][2]:continue
    idx=[int(i) for i in bt.query(qb) if hit(q,blocked[int(i)])]
    if idx:last=labels[idx[0]];reasons['signal_or_obstruction']+=1;continue
    idx=[int(i) for i in pt[opp].query(qb) if hit(q,power[opp][int(i)])]
    if idx:last='OPPOSITE_EXISTING_PG';reasons['opposite_existing_PG']+=1;continue
    if any(hit(q,z) for z in new[opp]):last='OPPOSITE_NEW_BRIDGE';reasons['opposite_new_bridge']+=1;continue
    found=dict(inst=f['inst'],pin=f['pin'],shape=f['shape'],net=n,native_pin_dbu=f['rect_dbu'],via78=[x,y],via89=[xx,y],m8_dbu=r,m9_grid_dbu=s);break
   if found:break
  if found:outpaths.append(found);new[n].append(found['m8_dbu'])
  else:fails.append(dict(**f,last_obstacle=last,candidate_tracks=len(yy)))
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True);json.dump(dict(source=plan['source'],dbu=D,paths=outpaths,failed=fails,reserved_inputs=a.reserved),open(out/'bridge_plan.json','w'),separators=(',',':'));json.dump([[q['net'],'M8',*[v/D for v in q['m8_dbu']]] for q in outpaths],open(out/'reserved_bridges.json','w'),separators=(',',':'))
 result=dict(short_fragments=len(plan['failed']),bridged=len(outpaths),failed=len(fails),max_bridge_um=max((q['m8_dbu'][2]-q['m8_dbu'][0])/D for q in outpaths) if outpaths else 0,rejections=dict(reasons),verdict='GEOMETRY_CANDIDATE' if not fails else 'INCOMPLETE_NO_MATERIALIZATION')
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
