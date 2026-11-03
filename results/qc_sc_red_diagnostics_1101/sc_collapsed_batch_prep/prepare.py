from pathlib import Path
from collections import defaultdict
import json,math
src=Path('/srv/opentallas-scratch/claude/codex-sc-buffer-actual-review-0158/geom.tsv')
doc=json.loads(Path('/srv/opentallas-scratch/claude/codex-sc-buffer-actual-review-0158/collapsed_chains.json').read_text())
chains=doc['long_first_hop_chains'];names=[b['name']for c in chains for b in c['buffers']]
assert len(names)==len(set(names))==49
raw=[x.rstrip().split('\t') for x in src.open()];cs={x[-1]:x for x in raw if x[0]=='C'};ids={x[1]:x[-1] for x in cs.values()};occ=defaultdict(list);orient={}
def ctr(x):return[(float(x[4])+float(x[6]))/2,(float(x[5])+float(x[7]))/2]
for n,x in cs.items():
 if n not in names:
  x0,y0,x1,y1=[round(float(v)*1000)for v in x[4:8]];occ[y0].append((x0,x1))
for line in Path('/srv/opentallas-scratch/claude/codex-qc-sc-red-1101/sc_tap_plan/floorplan_sites.tsv').open():
 a=line.split()
 if a[0]=='ROW':orient[int(a[3])]=a[7]
 if a[0]=='OBS':occ[int(a[4])].append((int(a[3]),int(a[5])))
moves=[];reports=[]
for chain in chains:
 start=chain['source_ff'];end=chain['endpoint']['name'];chain_names=[b['name']for b in chain['buffers']]
 a=ctr(cs[start]);b=ctr(cs[end])
 for k,n in enumerate(chain_names):
  c=cs[n];old=[float(v) for v in c[4:8]];w=round((old[2]-old[0])*1000);h=round((old[3]-old[1])*1000);assert h==270
  tx=(a[0]+(b[0]-a[0])*(k+1)/(len(chain_names)+1))*1000;ty=(a[1]+(b[1]-a[1])*(k+1)/(len(chain_names)+1))*1000;opts=[]
  for y in orient:
   if abs(y+h/2-ty)>5000:continue
   for si in range(math.floor((tx-5000-4320)/54),math.ceil((tx+5000-4320)/54)):
    x=4320+si*54
    if x<4320 or x+w>240192:continue
    if all(x+w<=lo or x>=hi for lo,hi in occ[y]):opts.append((abs(x+w/2-tx)+abs(y+h/2-ty),x,y))
  if not opts:raise ValueError(('no legal target',n))
  _,x,y=min(opts);new=[x/1000,y/1000,(x+w)/1000,(y+h)/1000];occ[y].append((x,x+w));moves.append(dict(instance=n,master=c[3],old_bbox=old,new_bbox=new,orient=orient[y]));c[4:8]=[f'{v:.4f}'for v in new]
 points=[a]+[ctr(cs[n])for n in chain_names]+[b]
 hops=[abs(x[0]-y[0])+abs(x[1]-y[1])for x,y in zip(points,points[1:])]
 assert all(e['fanout']==1 for e in chain['edges'])
 reports.append(dict(source_ff=start,endpoint=end,public_input_candidates=chain['public_input_candidates'],points=points,hop_l1_um=hops,old_first_hop_um=chain['first_hop_centre_l1_um'],max_new_hop_um=max(hops),edges=chain['edges']))
report=dict(scope='PREP_ONLY_49_EXISTING_DATA_BUFFER_POSES_24_CHAINS',moves=moves,chains=reports,new_cells=0,new_ff=0,new_cycles=0,public_pin_changes=0,clock_changes=0,all_existing_bodies_and_physical_TAPs_checked=True,max_old_first_hop_um=max(c['old_first_hop_um']for c in reports),max_new_hop_um=max(c['max_new_hop_um']for c in reports),dispatch_authorized=False)
Path('targets.json').write_text(json.dumps(report,indent=2)+'\n');Path('candidate.tsv').write_text('\n'.join('\t'.join(x)for x in raw)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in ["moves","chains"]},indent=2))
