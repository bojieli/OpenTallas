#!/usr/bin/env python3
import json,sys,math,collections
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
out=Path(sys.argv[1]);D=G.Design('/srv/opentallas-scratch/claude/codex-geom-1029/kv/ahub.tsv');orig=dict(D.cells)
report=json.load(open(out/'ahub_reach_lp.json'));pairs=json.load(open(out/'ahub_seq_pairs.json'));fixed={x['id'] for x in json.load(open('/srv/opentallas-scratch/claude/codex-geom-1029/kv/ahub_face_ff.json'))};mac=[c for c in D.cells.values() if c[0]=='M'];occ=[c[2:6] for i,c in D.cells.items() if i in fixed]
for ln in (out/'ahub_fixed_obstacles.tsv').read_text().splitlines():
 z=ln.split('\t');occ.append(tuple(map(float,z[1:5])))
near=collections.defaultdict(list)
for a,b in pairs:near[a].append(b);near[b].append(a)
for m in report['moves']:
 c=D.cells[m['id']];x,y=m['xy_center'];w,h=c[4]-c[2],c[5]-c[3];D.cells[m['id']]=c[:2]+(x-w/2,y-h/2,x+w/2,y+h/2)+c[6:]
def intersect(a,b):return min(a[2],b[2])>max(a[0],b[0])+1e-6 and min(a[3],b[3])>max(a[1],b[1])+1e-6
anchors=[]
for m in sorted(report['moves'],key=lambda m:len(near[m['id']]),reverse=True):
 cid=m['id'];c=D.cells[cid];w,h=c[4]-c[2],c[5]-c[3];x,y=m['xy_center'];cx=round((x-w/2-4.32)/.054);cy=round((y-h/2-4.32)/.27)
 candidates=[]
 for dx in range(-12,13):
  for dy in range(-24,25):
   xx=4.32+(cx+dx*10)*.054;yy=4.32+(cy+dy)*.27
   candidates.append((abs(xx+w/2-x)+abs(yy+h/2-y),xx,yy))
 for dist,xx,yy in sorted(candidates):
  box=(xx,yy,xx+w,yy+h)
  if xx<4.32 or yy<4.32 or xx+w>600.48 or yy+h>436.32:continue
  if any(intersect(box,(c[2]-2.16,c[3]-2.16,c[4]+2.16,c[5]+2.16)) for c in mac):continue
  if any(intersect(box,b) for b in occ):continue
  if any(abs(xx+w/2-G.ctr(D.cells[j])[0])+abs(yy+h/2-G.ctr(D.cells[j])[1])>400.00001 for j in near[cid]):continue
  break
 else:raise SystemExit('NO_LEGAL_SNAP '+m['name'])
 D.cells[cid]=c[:2]+box+c[6:];occ.append(box);anchors.append({'id':cid,'name':c[6],'xy_um':[xx,yy],'box_um':box,'old_center':G.ctr(orig[cid])})
metrics=G.r2r_metrics(D)
if metrics['r2r_captures_gt405']:raise SystemExit('SNAP_REACH_FAIL '+str(metrics))
(out/'ahub_anchors.json').write_text(json.dumps({'metrics':metrics,'fixed_faces':sorted(fixed),'anchors':anchors},indent=1)+'\n')
# Use braced exact dbInst names. Actual escaping in names is preserved verbatim.
t=['# Actual-connectivity planned FF anchors; no net/master/RTL/pin changes.','set b [ord::get_db_block]','set u [[ord::get_db_tech] getDbUnitsPerMicron]']
for i in sorted(fixed):t += ['set c [$b findInst {'+D.cells[i][6]+'}]','if {$c eq "NULL"} {error "missing fixed face flop"}','$c setPlacementStatus FIRM']
for a in anchors:
 t+=['set c [$b findInst {'+a['name']+'}]','if {$c eq "NULL"} {error "missing anchor flop"}','$c setPlacementStatus PLACED',f'$c setLocation [expr {{round({a["xy_um"][0]:.6f} * $u)}}] [expr {{round({a["xy_um"][1]:.6f} * $u)}}]','$c setPlacementStatus FIRM']
(out/'ahub_anchors.tcl').write_text('\n'.join(t)+'\n')
f,ax=plt.subplots(figsize=(12,9));ax.add_patch(Rectangle((0,0),604.8,440.64,fill=False,ec='black'))
for c in mac:ax.add_patch(Rectangle((c[2]-2.16,c[3]-2.16),c[4]-c[2]+4.32,c[5]-c[3]+4.32,fc='#ddd',ec='gray',hatch='//'))
for a in anchors:
 ox,oy=a['old_center'];x,y=G.ctr(D.cells[a['id']]);ax.plot([ox,x],[oy,y],c='#77a',alpha=.2,lw=.6)
ax.scatter(*zip(*(G.ctr(D.cells[i]) for i in fixed)),s=3,c='#2a5',label=f'{len(fixed)} unchanged face FFs')
ax.scatter(*zip(*(G.ctr(D.cells[a['id']]) for a in anchors)),s=8,c='#c32',label=f'{len(anchors)} planned snapped internal FF anchors')
ax.set(xlim=(-5,610),ylim=(-5,446),aspect='equal',title=f'AHUB PLANNED changed-input DPL | actual full FF connectivity max {metrics["r2r_max"]:.2f}um | 0>405\nFixed macros/halos/pins/faces; links show internal FF moves; no clock-tree or route claim')
ax.legend(loc='upper right');f.tight_layout();f.savefig(out/'ahub_anchor_overlay.png',dpi=140)
print('AHUB_SNAPPED_ANCHOR_ESTIMATE',len(anchors),metrics)
