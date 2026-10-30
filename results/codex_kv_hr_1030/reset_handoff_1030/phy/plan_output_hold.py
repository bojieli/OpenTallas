from pathlib import Path
import json,math,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;d=json.load(open(P/'output_hold_model.json'));raw=[l.split('\t')for l in(P.parent/'geom_phy103_cts1/geom.tsv').read_text().splitlines()];norm=lambda s:s.replace('\\','');box={norm(a[8]):list(map(float,a[4:8]))for a in raw if a[0]=='C'};master={norm(a[8]):a[3]for a in raw if a[0]=='C'};ports={a[2]:list(map(float,a[6:8]))for a in raw if a[0]=='P'};classes={norm(a[8]):a[2]for a in raw if a[0]=='C'}
rows=[]
for a in[l.split('\t')for l in(P/'native_sites.tsv').read_text().splitlines()]:
 if a[0]=='R':rows.append([int(a[4]),int(a[3]),int(a[5]),a[2],int(a[7])])
# ActualDBU1000, sameunchanged594nativefloorplanrowsegments.
occ=collections.defaultdict(list)
for b in box.values():
 for yy in range(round(b[1]*1000),round(b[3]*1000),270):occ[yy].append((round(b[0]*1000),round(b[2]*1000)))
for a in occ.values():a.sort()
def choose(target,prev,port,last,last_limit):
 cand=[]
 for y,lo,hi,ori,sw in rows:
  cy=y+135
  if abs(cy-prev[1]*1000)>10000:continue
  cur=lo
  for a,b in sorted(occ[y])+[(hi,hi)]:
   low=lo+math.ceil((cur-lo)/sw)*sw;high=lo+math.floor((min(a,hi)-378-lo)/sw)*sw
   if high>=low:
    anchor=round((target[0]*1000-189-lo)/sw)*sw+lo;x=max(low,min(high,anchor));cx=x+189
    new=[cx/1000,cy/1000];h1=abs(new[0]-prev[0])+abs(new[1]-prev[1]);h2=abs(new[0]-port[0])+abs(new[1]-port[1])
    if h1<=10 and(not last or h2<=last_limit):cand.append((h1+h2,x,y,ori,h1,h2))
   cur=max(cur,b)
 if not cand:raise RuntimeError(('no <=10um freeholdsite',target,prev,port,last))
 _,x,y,ori,h1,h2=min(cand);occ[y].append((x,x+378));return[x/1000,y/1000,ori,h1,h2]
plans=[]
for c in sorted(d['plans'],key=lambda x:x['FF_slack_ps']):
 ep=c['port'];b=box[norm(c['old_last_driver'])];src=[(b[0]+b[2])/2,(b[1]+b[3])/2];pt=ports[ep];prev=src;homes=[]
 for j in range(c['new_HB4']):
  frac=(j+1)/(c['new_HB4']+1);target=[src[k]+frac*(pt[k]-src[k])for k in[0,1]];h=choose(target,prev,pt,j==c['new_HB4']-1,10+abs(src[0]-pt[0])+abs(src[1]-pt[1]));homes.append(h);prev=[h[0]+.189,h[1]+.135]
 plans.append(dict(c,old_driver_bbox=b,port_xy=pt,homes=homes))
q={k:v for k,v in d.items()if k!='plans'};q.update(status='LEGAL_PREP_ESTIMATE_NOT_APPLIED',plans=plans,all_old_cells_fixed=True,actual_clock_FF_macro_pins_wires_unchanged=True,actual_native_rows_used=594,HB4_TAP_oldcell_macro_overlap=0,max_chain_segment_L1_estimate_um=max(max(h[3],h[4]if j==len(c['homes'])-1 else 0)for c in plans for j,h in enumerate(c['homes'])),routing_coupling='NOT_QUALIFIED; freshallCLOCK+DATA GRTandTTFFrequiredafternativeapplyandROOTLOOK')
(P/'output_hold_plan.json').write_text(json.dumps(q,indent=1)+'\n')
with(P/'output_hold_plan.tsv').open('w')as f:
 for i,c in enumerate(plans):
  for j,h in enumerate(c['homes']):f.write('\t'.join(map(str,[c['port'],j,h[0],h[1],h[2],f'phy_outhp_{i}_{j}']))+'\n')
fig,ax=plt.subplots(figsize=(12,10));ax.add_patch(Rectangle((0,0),103.68,95.04,fill=False,lw=2));ax.add_patch(Rectangle((30.24,12.972),57.912,69.672,fc='#cdd2d6',ec='black'))
for n,b in box.items():
 if master[n].startswith('ot_sram'):continue
 col='#b8bdc2';ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fc=col,alpha=.55))
for c in plans:
 b=c['old_driver_bbox'];pts=[[(b[0]+b[2])/2,(b[1]+b[3])/2]]
 for h in c['homes']:ax.add_patch(Rectangle((h[0],h[1]),.378,.27,fc='#a700bb'));pts.append([h[0]+.189,h[1]+.135])
 pts.append(c['port_xy']);ax.plot([p[0]for p in pts],[p[1]for p in pts],c='#a700bb',alpha=.17,lw=.4)
ax.set(xlim=(-1,105),ylim=(-1,97),aspect='equal',xlabel='um',ylabel='um');ax.set_title(f'SAME PHY103 actualCTS; PREP ONLY {d["new_HB4_count"]} outputHB4 for279ports\nAlloldcells/FF/clock/macropinsfixed; NEWpurple pads, GRAYoldcells; newinternalhops<=10um; finaloldporthop+<=10um')
fig.tight_layout();fig.savefig(P/'output_hold_plan.png',dpi=160);print({k:v for k,v in q.items()if k not in ['plans','method']})
