from pathlib import Path
import json,math
from collections import defaultdict
src=Path('.')
tr=json.load(open(src/'remaining45_port_trace.json'))
portff={'dn_i[45]':'u.u_15646/Q$_DFF_P_'}
for x in tr:
 for port in x['launch_input_ports']:portff[port]=x['launch']
 for port in x['capture_output_ports']:portff[port]=x['capture']
import sys
sys.path.insert(0,str(Path(__file__).parent));import geom_rules as g
D=g.Design(str(src/'sc_geom.tsv'))
for pp in D.pins:
 name=pp['name']
 if name in {'ck','rst_n'} or pp['k'] not in D.pin_net:continue
 ni=D.pin_net[pp['k']];todo=[ni];seen=set();found=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  isinput=pp['io']=='INPUT';refs=D.nets[n][2] if isinput else [D.nets[n][1]]
  for ref in refs:
   if not ref or ref[0]!='i' or ref[2]:continue
   cid=ref[1];c=D.cells[cid]
   if c[0]=='S':found.add(c[6])
   elif c[0]=='B':todo.extend(D.drives.get(cid,[]) if isinput else [nn for nn,clk in D.cell_in.get(cid,[]) if not clk])
 if len(found)!=1:raise ValueError((name,found))
 portff[name]=found.pop()
reset=['u.u_24798/Q$_DFF_PN0_','u.u_24799/Q$_DFF_PN0_']
boundary=set(portff.values());move=set(reset)|{'u.u_24609/Q$_DFF_P_'};unrepairable=[]
for pair in json.load(open(src/'r2r_capture_failures.json'))['captures']:
 if pair['capture'] not in boundary:move.add(pair['capture'])
 elif pair['launch'] not in boundary:move.add(pair['launch'])
 else:unrepairable.append(pair)
if unrepairable:raise ValueError(('bothboundary',unrepairable))
raw=[x.rstrip().split('\t') for x in (src/'sc_geom.tsv').open()]
cells={x[-1]:x for x in raw if x[0]=='C'}
occ=defaultdict(list)
def add(x0,y0,x1,y1):
 for y in range(y0,y1,270):occ[y].append((x0,x1))
for n,x in cells.items():
 if n in move:continue
 add(*(round(float(v)*1000) for v in x[4:8]))
for ln in Path('floorplan_sites.tsv').open():
 a=ln.split()
 if a[0]=='OBS':add(*map(int,a[3:7]))
# Exact ALL actual42665 FF extrema: region shrunk2um in eachUVcoordinate for legal-site slack.
ULO,UHI,VLO,VHI=341579,441799,-168505,-101495
moves=[]
for n in sorted(move):
 c=cells[n];old=[float(v) for v in c[4:8]];width=round((old[2]-old[0])*1000);ox=(old[0]+old[2])*500;oy=(old[1]+old[3])*500
 if n in reset:tx,ty=64812,22000
 else:
  u=min(UHI,max(ULO,ox+oy));v=min(VHI,max(VLO,ox-oy));tx=(u+v)/2;ty=(u-v)/2
 options=[]
 for k in range(1872):
  y=4320+270*k;yc=y+135
  if n in reset:
   if abs(yc-ty)>8000:continue
   h=8000-abs(yc-ty);lo=tx-h-width/2;hi=tx+h-width/2
  else:
   lo=max(ULO-yc,VLO+yc)-width/2;hi=min(UHI-yc,VHI+yc)-width/2
   if lo>hi:continue
  # Exact intervals include every actualfixed/movable body plus physicalTAPs; oldselected FFs removed.
  last=lo;gaps=[]
  for aa,bb in sorted(occ[y]):
   if bb<lo or aa>hi+width:continue
   if aa>last:gaps.append((last,min(aa-width,hi)))
   last=max(last,bb)
  if last<=hi:gaps.append((last,hi))
  for left,right in gaps:
   low=4320+math.ceil((left-4320)/54)*54;high=4320+math.floor((right-4320)/54)*54
   if low>high:continue
   x=min(high,max(low,4320+round((tx-width/2-4320)/54)*54))
   options.append((abs(x+width/2-tx)+abs(yc-ty),x,y))
 if not options:raise ValueError(('no free legal site',n,len(moves)))
 _,x,y=min(options);occ[y].append((x,x+width));new=[x/1000,y/1000,(x+width)/1000,(y+270)/1000]
 moves.append(dict(instance=n,master=c[3],old_bbox=old,new_bbox=new));c[4:8]=[f'{v:.4f}' for v in new]
pm=[]
Path('candidate.tsv').write_text('\n'.join('\t'.join(x) for x in raw)+'\n')
Path('candidate.json').write_text(json.dumps(dict(scope='PREP same original pin contract; all original masters and clock seed fixed; not actual ODB or physical release',new_ff=0,new_cycles=0,ff_moves=moves,pin_changes=pm,port_ff=portff),indent=2)+'\n')
print('PREP',len(moves),'FF moves',len(pm),'ports')
