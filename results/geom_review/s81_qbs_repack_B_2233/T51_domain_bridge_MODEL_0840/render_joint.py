from pathlib import Path
import json,gzip,collections
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent;P=R/'inputs';C=[json.loads(s)for s in gzip.open(P/'cells.jsonl.gz','rt')];F=json.load(open(P/'joint_FF_targets.json'));T=json.load(open(R/'DATA_targets.json'));M=json.load(open(R/'model.json'));ck=json.load(open(R/'clock_price.json'))if(R/'clock_price.json').exists()else None;clocknet={r[0]:r[2]for r in json.load(open(P/'clock_pins.json'))};bands=json.load(open(P/'other_declared_band_reservations.json'))['rectangles'];plan=json.load(open(P/'current_plan.json'));taps=plan['partition_types']['slice_station__t51']['clock']['taps'];fig,axes=plt.subplots(1,3,figsize=(18,9),gridspec_kw={'width_ratios':[1.6,1.05,1.]});ax,st,txt=axes
for a,limits in [(ax,(0,235,1070,1230)),(st,(0,235,740,910))]:
 x0,x1,y0,y1=limits
 for band in bands:
  bb=[v/1000 for v in band['bbox_dbu']]
  if bb[2]<x0 or bb[0]>x1 or bb[3]<y0 or bb[1]>y1:continue
  a.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc='#edddbd',ec='#b5a18a',lw=.5,alpha=.8))
 for c in C:
  if c[0]in F or c[0]in T:continue
  bb=[v/1000 for v in c[2]]
  if bb[2]<x0 or bb[0]>x1 or bb[3]<y0 or bb[1]>y1:continue
  a.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc='#bfaaa4'if c[1].startswith('TAPCELL')else'#ccd1d5',ec='none',alpha=.7))
 for name,t in F.items():
  bb=[v/1000 for v in t['bbox_dbu']]
  if bb[2]<x0 or bb[0]>x1 or bb[3]<y0 or bb[1]>y1:continue
  col='#1679b5'if clocknet.get(name)=='fclk_in_ft2_i[0]'else'#549c58'if t['family']=='ft2_ring_band_FFs'else'#9a53b7'
  a.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc=col,ec='none'))
 for name,t in T.items():
  bb=[v/1000 for v in t['bbox_dbu']]
  if bb[2]<x0 or bb[0]>x1 or bb[3]<y0 or bb[1]>y1:continue
  a.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc='#d18527',ec='none',alpha=.8))
 for t in taps:
  x,y=t['xy']
  if x0<=x<=x1 and y0<=y<=y1:a.plot(x,y,'r+',ms=8);a.text(x+2,y+1,t['name'],fontsize=7)
 a.set(xlim=(x0,x1),ylim=(y0,y1),xlabel='µm',ylabel='µm');a.set_aspect('equal')
ax.plot(61.536,1224.224,'r*',ms=10);ax.set_title('Actual held rows / TAP / other52bands\nBlue:2077 forwarded write; green:600mission read/control')
st.set_title('Existing stage0 bridge / local clock taps\nPurple:515stationFFs; orange:ownedDATA')
txt.axis('off');d=M['projected_M2M7_demand'];text=['ONE DISABLED DOMAIN-AWARE MODEL','No native DB / GEN / CAD',f"FF targets {len(F)}; DATA {len(T)}",f"R2R max {M['r2r']['r2r_max']}um; over405 {M['r2r']['r2r_captures_gt405']}",f"DATA failures: {M['failed']}",f"Footprint overlaps: {len(M['overlaps'])}",f"Site/master/orient failures: {len(M['row_site_failures'])}/{len(M['master_orientation_dimension_failures'])}",'','Same FF/source/clock/reset/pins/cycles','95696 buffer PG opens remain held','Original physical4843 / sparsefill /','2partialfaces / sourcephase holds remain','','Projected M2–M7 demand:',f"column max {d['col_v_max']} at {d['col_v_at']}"]
if ck:
 for label,v in ck['results'].items():text.extend(['',label,f"Mission {v['mission_FFs']}; forwarded {v['forwarded_FFs']}",f"Max load {v['max_load']}; max reach {v['max_radius_um']:.3f}um",f"Moved radius failures {v['moved_radius_violation_FFs']}"])
txt.text(0,1,'\n'.join(text),va='top',fontsize=9,wrap=True,parse_math=False);fig.suptitle('T51 joint write/read/stage0 + exact-owned DATA geometry — MODEL ONLY / HOLD',fontsize=14);fig.tight_layout();fig.savefig(R/'T51_domain_bridge_MODEL_LOOK.png',dpi=150)
