#!/usr/bin/env python3
"""Source-connected alternative: collect each operand's eight real bank pairs."""
import gzip,json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=R/'results/arch/qwen_vm_residual_1015';src=json.loads((D/'physical_inventory/inventory.json').read_text());old=src['alternatives']['regional_paired'];lookup={(b['region'],b['class'],b['n']):b for b in old['rectangles']};W,H=old['outline_um'];gap=40.;bw,bh=371.52,241.92;sw,sh=86.4,21.6;pairw=2*bw+2*gap+sw;gw=2*pairw+gap;gh=4*bh+3*gap
boxes=[]
for c in range(3):
 gx=(c%2)*(gw+gap);gy=(c//2)*(gh+gap)
 for r in range(8):
  x=gx+(r%2)*(pairw+gap);y=gy+(r//2)*(bh+gap)
  for j in range(2):
   b=lookup[r,'qvm_su_bank_native',2*c+j];boxes.append(dict(b,x=x+(0 if j==0 else bw+gap+sw+gap),y=y))
  b=lookup[r,'ot_qfd_vm_su1024_t',c];boxes.append(dict(b,x=x+bw+gap,y=y+(bh-sh)/2))
# Three occupied operand-group envelopes. Disjoint remaining strips are explicit.
free=[[2*gw+gap,0,W-(2*gw+gap),H],[0,2*gh+gap,2*gw+gap,H-(2*gh+gap)],[gw+gap,gh+gap,gw,gh]]
rest=[b for b in old['rectangles'] if b['class'] not in ['qvm_su_bank_native','ot_qfd_vm_su1024_t']]
# Shelves consume remaining hard masters, largest first; this is geometry only.
for b in sorted(rest,key=lambda b:(-b['h'],-b['w'])):
 opts=[(min(f[2]-b['w'],f[3]-b['h']),i) for i,f in enumerate(free) if f[2]>=b['w'] and f[3]>=b['h']]
 assert opts,('No actual master fit',b)
 _,i=min(opts);x,y,w,h=free.pop(i);boxes.append(dict(b,x=x,y=y));dx=b['w']+20;dy=b['h']+20
 if w>dx:free.append([x+dx,y,w-dx,b['h']])
 if h>dy:free.append([x,y+dy,w,h-dy])
assert len(boxes)==487
for i,a in enumerate(boxes):
 assert a['x']>=0 and a['y']>=0 and a['x']+a['w']<=W+1e-6 and a['y']+a['h']<=H+1e-6
 for b in boxes[i+1:]:assert min(a['x']+a['w'],b['x']+b['w'])<=max(a['x'],b['x'])+1e-6 or min(a['y']+a['h'],b['y']+b['h'])<=max(a['y'],b['y'])+1e-6
out=D/'relay_parent_0253';new={(b['region'],b['class'],b['n']):b for b in boxes};rows=json.loads(gzip.decompress((D/'physical_inventory/return_incident_graph_regional_paired.json.gz').read_bytes()))['rows']
for a in rows:
 r=int(re.search(r'g_t\[(\d+)\]',a['capture']).group(1));c=int(re.search(r'g_cp\[(\d+)\]',a['target']).group(1));j=int(re.search(r'g_j\[(\d+)\]',a['source']).group(1))
 for cls,n,keys in [('qvm_su_bank_native',2*c+j,['source_xy']),('ot_qfd_vm_su1024_t',c,['capture_xy','su1024_output_xy'])]:
  o=lookup[r,cls,n];b=new[r,cls,n]
  for k in keys:a[k]=[a[k][0]+b['x']-o['x'],a[k][1]+b['y']-o['y']]
 a['bank_to_su1024_L1_um']=sum(abs(a['source_xy'][k]-a['capture_xy'][k]) for k in [0,1])
report={'scope':'UNADOPTED whole existing-hardmaster screen. Actual bank/capture motifs regrouped by operand; all487 rectangles retained. No new99 leaves/relay homes/remaining write/control. All incident writes/control/row-return arcs, cuts, clock/PG and phase need fresh proof.','outline_um':[W,H],'overlap':0,'outside':0,'rectangles':boxes,'open_free_rectangles':free,'native_bank_capture_max_L1_um':max(r['bank_to_su1024_L1_um'] for r in rows)}
(out/'operand_group_screen.json').write_text(json.dumps(report,indent=2)+'\n');(out/'return_incident_operand_group.json.gz').write_bytes(gzip.compress(json.dumps({'scope':report['scope'],'rows':rows},separators=(',',':')).encode(),mtime=0))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(14,10))
for b in boxes:
 color='#d6ab72' if b['class']=='qvm_su_bank_native' else ('#70a575' if b['class']=='ot_qfd_vm_su1024_t' else '#7896ab');ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor=color,edgecolor='white',lw=.3))
 if b['class']=='qvm_su_bank_native':ax.text(b['x']+b['w']/2,b['y']+b['h']/2,f"operand{b['n']//2} region{b['region']}",ha='center',fontsize=5)
ax.set(xlim=(0,W),ylim=(0,H),xlabel='um',ylabel='um',title='UNADOPTED operand-group alternative: all487 actual hard rectangles\nReturn locality improves; write/control/row-read arcs, new leaves, clock/PG/cuts OPEN');ax.set_aspect('equal');fig.tight_layout();fig.savefig(out/'operand_group_screen.png',dpi=130)
print(json.dumps({'rectangles':len(boxes),'outline_um':[W,H],'native_bank_capture_max_L1_um':report['native_bank_capture_max_L1_um']}))
