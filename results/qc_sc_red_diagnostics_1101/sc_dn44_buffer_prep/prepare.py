from pathlib import Path
from collections import defaultdict
import json,math
src=Path('/srv/opentallas-scratch/claude/codex-sc-buffer-actual-review-0158/geom.tsv')
names=['u.u_15645/place27055','u.u_15645/place27054']
start='u.u_15645/Q$_DFF_P_';end='u.u_15645/_1_'
raw=[x.rstrip().split('\t') for x in src.open()];cs={x[-1]:x for x in raw if x[0]=='C'};ids={x[1]:x[-1] for x in cs.values()};occ=defaultdict(list);orient={}
def ctr(x):return[(float(x[4])+float(x[6]))/2,(float(x[5])+float(x[7]))/2]
for n,x in cs.items():
 if n not in names:
  x0,y0,x1,y1=[round(float(v)*1000)for v in x[4:8]];occ[y0].append((x0,x1))
for line in Path('/srv/opentallas-scratch/claude/codex-qc-sc-red-1101/sc_tap_plan/floorplan_sites.tsv').open():
 a=line.split()
 if a[0]=='ROW':orient[int(a[3])]=a[7]
 if a[0]=='OBS':occ[int(a[4])].append((int(a[3]),int(a[5])))
a=ctr(cs[start]);b=ctr(cs[end]);moves=[]
for k,n in enumerate(names):
 c=cs[n];old=[float(v) for v in c[4:8]];w=round((old[2]-old[0])*1000);h=round((old[3]-old[1])*1000);assert h==270
 tx=(a[0]+(b[0]-a[0])*(k+1)/3)*1000;ty=(a[1]+(b[1]-a[1])*(k+1)/3)*1000;opts=[]
 for y in orient:
  if abs(y+h/2-ty)>5000:continue
  for si in range(math.floor((tx-5000-4320)/54),math.ceil((tx+5000-4320)/54)):
   x=4320+si*54
   if x<4320 or x+w>240192:continue
   if all(x+w<=lo or x>=hi for lo,hi in occ[y]):opts.append((abs(x+w/2-tx)+abs(y+h/2-ty),x,y))
 if not opts:raise ValueError(('no legal target',n))
 _,x,y=min(opts);new=[x/1000,y/1000,(x+w)/1000,(y+h)/1000];occ[y].append((x,x+w));moves.append(dict(instance=n,master=c[3],old_bbox=old,new_bbox=new,orient=orient[y]));c[4:8]=[f'{v:.4f}'for v in new]
chain=[start]+names+[end];points=[ctr(cs[n])for n in chain];hops=[abs(x[0]-y[0])+abs(x[1]-y[1])for x,y in zip(points,points[1:])]
fanouts=[]
for driver,sink in zip(chain,chain[1:]):
 matches=[]
 for x in raw:
  if x[0]=='N' and x[1]=='SIGNAL' and x[2]=='i'+cs[driver][1]:
   found=[ids[v[1:]]for v in x[3:] if v.startswith('i')and v[1:]in ids]
   if sink in found:matches.append(found)
 assert len(matches)==1 and matches[0]==[sink],(driver,sink,matches)
 fanouts.append(dict(driver=driver,sinks=matches[0],fanout=1))
report=dict(scope='PREP_ONLY_TWO_EXISTING_DN44_DATA_BUFFER_MOVES',source_input='actual current SC threeBUF geometry, source unchanged',control_semantic='dn_i[44] data capture (sourceRTL3900 n149), fresh worst path -388.81ps',start=start,end=end,moves=moves,points=points,hop_l1_um=hops,max_hop_l1_um=max(hops),chain_fanouts=fanouts,original_first_hop_um=None,new_cells=0,new_ff=0,new_cycles=0,public_pin_changes=0,clock_changes=0,all_existing_bodies_and_physical_TAPs_checked=True)
Path('targets.json').write_text(json.dumps(report,indent=2)+'\n');Path('candidate.tsv').write_text('\n'.join('\t'.join(x)for x in raw)+'\n');print(json.dumps(report,indent=2))
