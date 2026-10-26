import json,re,itertools
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path('/srv/opentallas-scratch/claude/wt/codex-qc-a0-2157/results/qc_a0_2157')
old=json.loads((root/'m3flat/floorplan.json').read_text());out={};fig,axs=plt.subplots(1,2,figsize=(12,13))
for ax,(kind,v) in zip(axs,old.items()):
 v['status']='CANDIDATE actual zero-cycle rawfault LSL hierarchy; no old FP1 hardview substitution';v['hard_children']=[c for c in v['hard_children']]
 for c in v['hard_children']:
  c['size_um']=[47.52,432] if 'node' in c['view'] else [172.8,110.16]
  if 'node' in c['view']:c['at'][0]=394.416
 for c in v.pop('soft_LSL_regions'):
  n=int(re.search(r'g_sl\[(\d+)\]',c['inst']).group(1));col=2 if n<3 else 1 if n in(4,5) else 0
  c.update(view='PENDING_NEW_NATIVE_RAWFAULT_LEF_LIB',at=[[15.984,142.128,268.272][col],c['at'][1]],orient='MY' if col==1 else 'R0',size_um=[115.344,140.4],existing_flag_links=50,new_parent_links=41,source_cells=76731,source_ff=12030)
  v['hard_children'].append(c)
 boxes=[]
 for c in v['hard_children']:
  x,y=c['at'];w,h=c['size_um'];boxes.append((c['inst'],[x-5.4,y-5.4,x+w+5.4,y+h+5.4]))
 overlaps=[]
 for (na,a),(nb,b) in itertools.combinations(boxes,2):
  if min(a[2],b[2])-max(a[0],b[0])>1e-7 and min(a[3],b[3])-max(a[1],b[1])>1e-7:overlaps.append([na,nb])
 assert not overlaps,overlaps
 v['halo_audit']={'halo_um':5.4,'overlaps':overlaps,'lsl_gap_um':10.8,'node_gap_um':10.8}
 v['fault_cut']={'raw_flags_per_leaf':50,'extra_links_per_leaf':41,'extra_links_per_A0':328,'new_ff':0,'new_cycles':0,'existing_parent_fault_q_hub':[191.5,984.888],'maximum_estimated_route_um':365,'reach_limit_um':405,'actual_placed_reach_required':True}
 for c in v['hard_children']:
  x,y=c['at'];w,h=c['size_um'];lsl='PENDING' in c['view'];ax.add_patch(Rectangle((x-5.4,y-5.4),w+10.8,h+10.8,fill=False,ec='orange',lw=.4));ax.add_patch(Rectangle((x,y),w,h,fc='#abdbc5' if lsl else '#c3d6eb',ec='black',lw=.5))
  ax.text(x+w/2,y+h/2,('raw LSL'+re.search(r'g_sl\[(\d+)\]',c['inst']).group(1)) if lsl else 'node' if 'node' in c['view'] else 'ROM',ha='center',fontsize=7)
  if lsl:ax.plot([x+10,x+w-10],[y+h,y+h],color='red',lw=2)
 ax.scatter([191.5],[984.888],c='purple',s=35,zorder=10);ax.set_xlim(0,457.92);ax.set_ylim(0,1157.76);ax.set_aspect('equal');ax.set_title(kind.upper()+' zero-cycle rawfault candidate');out[kind]=v
fig.suptitle('Actual original MODE3/noFP1 structural successor\n115.344um leaf width; exact10.8um halo gaps; inward wide E face\nRed:50 native flag pins/leaf, purple:existing fault_q hub; new views pending');fig.tight_layout();d=root/'rawfault_cut';(d/'parent_floorplan.json').write_text(json.dumps(out,indent=2));fig.savefig(d/'parent_floorplan.png',dpi=150)
