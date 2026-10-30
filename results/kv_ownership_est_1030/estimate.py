from pathlib import Path
import json
import sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json'
p=json.load(open(P));t=p['partition_types']['kv3_hub_Wi'];mac=t['hard_cores'];band=[1157.76,1141.08,1183.68,1149.72]
pts=[(1157.76,1141.08),(1157.76,829.44),(1036.8,648),(725.76,648),(587.616,483.624)]
paths=[[pts[0],pts[1]],[pts[1],(1157.76,648),pts[2]],[pts[2],pts[3]],[pts[3],(570.24,648),(570.24,483.624),pts[4]]]
lengths=[sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])) for path in paths]
worst0=max(abs(x-pts[1][0])+abs(y-pts[1][1]) for x in band[::2] for y in [band[1],band[3]])
assert max(lengths+[worst0])<=405
# Parent glue can route through the reserved macro channels, never through a foreign body/halo.
for i,path in enumerate(paths):
 for k,(a,b) in enumerate(zip(path,path[1:])):
  for c in mac:
   if i==3 and k==2 and c['module']=='qkd_hr_core_rx':continue # own final pin-access segment
   x,y=c['origin_um'];w,h=c['outline_um'];x0,y0,x1,y1=x-4.32,y-4.32,x+w+4.32,y+h+4.32
   hit=(max(min(a[0],b[0]),x0)<min(max(a[0],b[0]),x1) and y0<a[1]<y1) if a[1]==b[1] else (x0<a[0]<x1 and max(min(a[1],b[1]),y0)<min(max(a[1],b[1]),y1))
   assert not hit,(i,k,c['inst'])
report={'status':'ANALYTIC CANDIDATE ONLY; owner contract decision pending; no plan/RTL change','new_receiver_relays':2,'existing_u_bin_relocated':True,'logical_path':'CA readout ->newrelay1 ->newrelay2 ->existing u_bin ->RX','points_parent_um':pts,'paths_parent_um':paths,'hop_lengths_um':lengths,'first_hop_worst_band_corner_um':worst0,'reach_limit_um':405,'macro_halo_um':4.32,'macro_halo_intersections_except_own_final_pin':0,'new_cycles':2,'area_estimate':'4FF per 2-bit data+epoch bundle; paired qualification signals may require coherent relays too, under token/guard analysis','not_checked':['actual standard-cell occupancy/row sites','reset and local clock feed','fault/close and R8 paired-qualification behavior','routed timing and PG'],'steady_rate':'not claimed; TOK source price pending'}
D=Path(__file__).parent;(D/'estimate.json').write_text(json.dumps(report,indent=1)+'\n')
fig,ax=plt.subplots(figsize=(7,9))
for c in mac:
 x,y=c['origin_um'];w,h=c['outline_um'];ax.add_patch(Rectangle((x,y),w,h,fc='#d9dfe9',ec='#7b8799'));ax.text(x+w/2,y+h/2,c['module'].replace('qkd_hr_',''),fontsize=5,ha='center')
ax.add_patch(Rectangle((band[0],band[1]),band[2]-band[0],band[3]-band[1],fc='red'));ax.text(band[0]-5,band[3]+12,'existing CA band',ha='right',fontsize=8)
for i,path in enumerate(paths):
 ax.plot(*zip(*path),'-o',lw=2,label=f'hop{i+1} {lengths[i]:.2f}um'+(f' (band worst{worst0:.2f})' if i==0 else''))
for label,xy in zip(['source','new1','new2','existing u_bin','RXpin'],pts):ax.annotate(label,xy,xytext=(5,8),textcoords='offset points',fontsize=8)
ax.set_xlim(0,t['outline_um'][0]);ax.set_ylim(0,t['outline_um'][1]);ax.set_aspect('equal');ax.legend(fontsize=6,loc='upper right');ax.set_xlabel('parent x (um)');ax.set_ylabel('parent y (um)');ax.set_title('Ownership receiver: +2-relay candidate, not adopted\nFour legal-length channel hops; owner/clock/reset/guard gates pending',fontsize=10);fig.tight_layout();fig.savefig(D/'ownership_four_hops.png',dpi=140)
print(report)
