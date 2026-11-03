from pathlib import Path
from collections import defaultdict,Counter
import json,math,copy
import census as C
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D=C.D;g=C.g;P=C.P
# Native 64-bit chunks. Role ownership is propagated through the actual combinational DAG.
roles=defaultdict(set)
ffgroups=defaultdict(list)
for cid,bit in C.semantic.items():
 n=D.cells[cid][6].replace(chr(92),'');role='write' if 's_d[' in n else 'read'
 key=(bit//64,role);ffgroups[key].append(cid)
 for ni,ck in D.cell_in.get(cid,[]):
  if ck:continue
  dr=D.nets[ni][1]
  if dr and dr[0]=='i' and dr[1] in C.comb:roles[dr[1]].add(key)
for cid in reversed(C.order):
 for prev in C.prev[cid]:roles[prev]|=roles[cid]
groups=defaultdict(list);shared=[];unknown=[]
for cid in C.comb:
 r=roles[cid]
 if len(r)==1:groups[next(iter(r))].append(cid)
 elif r:shared.append(cid)
 else:unknown.append(cid)
# Boxes follow real native chunk positions, within the already reviewed 86.4um ring.
# This is a capacity/affinity proposal, not a native/legal placement prediction.
bounds={}
for key,fs in ffgroups.items():
 xs=[g.ctr(D.cells[c])[0] for c in fs];bounds[key]=(min(xs)-.54,max(xs)+.54)
records=[]
for key,cs in sorted(groups.items()):
 chunk,role=key;x0,x1=bounds[key];y0,y1=(17.28,56.16) if role=='write' else (56.16,82.08)
 area=sum((D.cells[c][4]-D.cells[c][2])*(D.cells[c][5]-D.cells[c][3]) for c in cs)
 other=0
 for cid,c in D.cells.items():
  if cid in cs:continue
  other+=max(0,min(x1,c[4])-max(x0,c[2]))*max(0,min(y1,c[5])-max(y0,c[3]))
 records.append(dict(chunk=chunk,role=role,cells=len(cs),box=[x0,y0,x1,y1],movable_area_um2=area,current_other_body_intersection_um2=other,conservative_fill=(area+other)/((x1-x0)*(y1-y0)),names=[D.cells[c][6] for c in sorted(cs)]))
# Wider actual pair-face candidate: retain upper endpoint to avoid adjacent return bus.
wide=[1294.2717,1380.6717];returnwin=[1380.9274,1406.8474]
summary={'scope':'STATIC PREP ONLY; no CAD or canonical plan/source edits','native_semantic_ff':len(C.semantic),'comb_total':len(C.comb),'role_owned_comb':sum(len(v) for v in groups.values()),'shared_comb':len(shared),'unowned_output_comb':len(unknown),'excluded_clock_cone':len(C.clock&C.comb),'guide_groups':records,'guide_limits':['Actual TSV omits TAP/FILL bodies; native site/TAP/PG qualification is held.','Guide release before DPL means actual cells can leave boxes.','Current other-body intersection is a conservative occupancy observation, not legal capacity.','No demand proxy claimed: target affinity boxes do not predict GPL result.'],'window_option':{'current':[1352.0957,1380.6717],'centered_86p4':[1323.1837,1409.5837],'centered_conflict':'overlaps paired return L1594_0','left_only_86p4':wide,'adjacent_return':returnwin,'gap_um':returnwin[0]-wide[1],'four_pair_bit_count':1200,'pad_locations_changed':2400,'proposed_new_pins':0,'proposed_added_cycles':0,'held':['Q12 hroot+1 interface compatibility','PCv3 output/last-relay physical reach','all four paired pins and controls/clock/bands coherent event','G0C zero new and bind0 before source-event physical']} }
(P/'comparison.json').write_text(json.dumps(summary,indent=1)+'\n')
fig,axs=plt.subplots(1,2,figsize=(15,6),sharey=True)
for ax in axs:
 for c in D.cells.values():
  if c[4]<1280 or c[2]>1450 or c[3]>130:continue
  target=C.prefix in c[6];color='#d78b2b' if target and c[0]!='S' else '#bc315e' if target else '#80959d'
  ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],facecolor=color,edgecolor='none',alpha=.35))
 ax.set(xlim=(1280,1450),ylim=(-6,130),xlabel='x (um)');ax.grid(alpha=.12)
for r in records:
 x0,y0,x1,y1=r['box'];axs[0].add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,lw=1.8,edgecolor=plt.cm.tab10(r['chunk'])))
 axs[0].text((x0+x1)/2,(y0+y1)/2,f"{r['chunk']} {r['role'][0]}\n{r['cells']}",fontsize=7,ha='center')
axs[0].set_title('Option A: actual native 64-bit/role guide affinity\nFFs/pins/source unchanged; shared/output comb unclaimed')
for ax in axs:
 ax.plot([1352.0957,1380.6717],[0,0],color='black',lw=4,label='current input')
axs[1].plot(wide,[5,5],color='#1678a6',lw=5,label='left-only 86.4um candidate')
axs[1].plot(returnwin,[10,10],color='#b83248',lw=4,label='existing return bus')
axs[1].set_title('Option B: wider real input window + paired PC pins\nCentered widening collides; left-only fits interval census')
axs[1].legend(fontsize=8,loc='upper left');axs[0].set_ylabel('y (um)')
fig.suptitle('STATIC actual-body comparison; no new placement or routing result',fontsize=12);fig.tight_layout();fig.savefig(P/'comparison.png',dpi=160)
print({k:v for k,v in summary.items() if k in ['role_owned_comb','shared_comb','unowned_output_comb']})
print([(r['chunk'],r['role'],r['cells'],round(r['conservative_fill'],3)) for r in records])
