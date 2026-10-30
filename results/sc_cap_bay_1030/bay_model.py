"""SC natural-cut floorplan proposal. Geometry/model only, no physical qualification."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parent
I=R.parent/'sc_cap_0336'
D=json.load(open(I/'reserved_corridors.json'))
F=json.load(open(I/'public_faces.json'))
W,H=D['parent_outline_um']
B=[345.6,656.64,598.8,1162.08]
halo=4.32
area=36859.27518
usable=(B[2]-B[0]-2*halo)*(B[3]-B[1]-2*halo)
faces={b['bus']:b for b in F['buses']}
# Independent span bounds: all output bits are covered without assuming an
# undocumented per-bit correspondence. Two signal layers give one slot per pair.
N=[B[0]+.048,B[0]+.048+59*.048,B[3],B[3]]
E=[B[2],B[2],B[1]+.048,B[1]+.048+23*.048]
A=[B[0],B[0],892.368,893.472]
def bound(pin,face):
 return max(abs(x-y)+abs(a-b) for x in pin[:2] for y in [face['xmin'],face['xmax']] for a in pin[2:] for b in [face['ymin'],face['ymax']])
reach={bus:bound(pin,faces[bus]) for bus,pin in [('x_ctl_o',N),('x_fe_o',E),('x_fw_o',A)]}
def overlaps(b):
 return B[0]-halo<b[2] and b[0]<B[2]+halo and B[1]-halo<b[3] and b[1]<B[3]+halo
hit=[q for q in D['landing_groups'] if overlaps(q['rect_um'])]
ft=[]
for f in D['ft_target_envelopes']:
 for s in f['stages']:
  b=s['ideal_bbox_um']
  if overlaps(b):ft.append(dict(slot=f['slot'],stage=s['stage'],bits=s['bit_count'],ideal_bbox_um=b))
report=dict(verdict='CONDITIONAL CHILD PLAN ONLY; parent placement HOLD',body_um=B,halo_um=halo,
 child_cells=281884,parent_remaining_cells=260481,child_cell_area_um2=area,
 usable_child_core_area_um2=usable,child_utilization=area/usable,
 parent_outline_um=[W,H],state_or_data_cycles_added=0,output_port_to_public_face_L1_upper_um=reach,
 output_proxy_all_le405=all(v<=405 for v in reach.values()),
 source_scope='Existing u_bound.u_core only. 27ports/572bits unchanged. Output-pin model is not actual parent boutFF geometry or child timing.',
 preserved_parent_clock_reset=[311.04,673.92],preserved_count_strap_bounds=[280.8,643.68,341.28,704.16],
 intersecting_reserved_groups=hit,intersecting_FT_ideal_stages=ft,
 required_work=['Move same-depth reset/run/collector instances intersecting bay and recheck entire reset graph.',
 'Retarget existing FT stages around bay with actual per-bit constraints and .4 footprints; no new FF stages.',
 'Place CA read outputs/R8 final stages near child input faces while checking every source cone.',
 'Generate and qualify actual child source/LEF/pins; retain all native state and whole-logical LEC baseline.',
 'Actual parent fixed-body/clock/PG/geometry and TT/FF closure required before route.'])
(R/'bay_model.json').write_text(json.dumps(report,indent=1)+'\n')
fig,ax=plt.subplots(figsize=(7,11))
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2))
for r in D['landing_groups']:
 x,y,X,Y=r['rect_um'];c='red' if overlaps(r['rect_um']) else 'grey'
 ax.add_patch(Rectangle((x,y),X-x,Y-y,facecolor=c,alpha=.6))
for f in D['ft_target_envelopes']:
 for s in f['stages']:
  x,y,X,Y=s['ideal_bbox_um'];ax.plot([x,X],[y,Y],color='orange',lw=.7)
ax.add_patch(Rectangle((B[0]-halo,B[1]-halo),B[2]-B[0]+2*halo,B[3]-B[1]+2*halo,fill=False,ls='--',ec='blue'))
ax.add_patch(Rectangle((B[0],B[1]),B[2]-B[0],B[3]-B[1],facecolor='#cde5ff',ec='blue',alpha=.8))
ax.text((B[0]+B[2])/2,(B[1]+B[3])/2,'Existing u_core child\n281,884 cells\n36,859 um² cells\nNO new data cycles',ha='center',fontsize=9)
ax.add_patch(Rectangle((280.8,643.68),60.48,60.48,fill=False,ec='purple'));ax.plot(311.04,673.92,'m*',ms=9)
for bus,pin in [('x_ctl_o',N),('x_fe_o',E),('x_fw_o',A)]:
 f=faces[bus];x=sum(pin[:2])/2;y=sum(pin[2:])/2;X=(f['xmin']+f['xmax'])/2;Y=(f['ymin']+f['ymax'])/2
 ax.plot([x,X],[y,Y],color='green',lw=1.2);ax.text((x+X)/2,(y+Y)/2,bus+' ≤%.2fum'%reach[bus],fontsize=8)
ax.set_xlim(-20,W+20);ax.set_ylim(-20,H+20);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
ax.set_title('SC same-outline natural-cut bay proposal\nRed reset groups / orange FT targets require relocation\nMODEL ONLY — no parent placement or route approval')
fig.tight_layout();fig.savefig(R/'bay_model.png',dpi=150)
print(json.dumps({k:report[k] for k in ['body_um','child_utilization','output_port_to_public_face_L1_upper_um','output_proxy_all_le405']},indent=1))
