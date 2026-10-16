"""Source-pinned geometric bounds only; no rotated hard views or physical claim."""
import hashlib,json,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=pathlib.Path(__file__).resolve().parents[2]
p=R/'results/arch/hbm_sm_repack_1015/rp4_clock_candidate/plan.json'
a=json.loads(p.read_text());tw,th=a['outline_um'];gap=21.6
body=16*tw+15*gap;front=345.6;old=body+front+gap;xcw,xch=500,1200
side=old+gap+xcw;top=th+gap+500
out=R/'results/arch/hbm_sm_repack_1015/xc_frame_bounds';out.mkdir(parents=True,exist_ok=True)
d=dict(schema='opentallas.sm_xc_frame_bounds.v1',scope='Lower bounds only; MATVEC RP4 body not closed, attention/fullSM still absent. XC500x1200 is preliminary proposed rebuilt real leaf, not accepted existing hard view.',rp4_plan_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),tile_outline_um=[tw,th],body16_tiles_width_um=body,front_column_um=[front,1765.44],total_body_front_width_um=old,slot_um=[7200,1800],current_residual_width_um=7200-old,current_top_strip_height_um=1800-th-gap,xc_preliminary_um=[xcw,xch],fits_7200x1800=False,reason='Side remainder11.52um cannot hold500um XC; top strip456.48um cannot hold1200um tall XC or500um tall rebuilt wide XC.',alternatives=[dict(name='side_XC',outline_lower_bound_um=[side,1800],added_frame_area_mm2=(side-7200)*1800/1e6,added32SM_area_mm2=32*(side-7200)*1800/1e6,dependency='Actual500x1200 XC leaf pin/macro layout plus7200-wide SM body/front closure. Whole die row expansion and all connected cut/hop/relay changes required.'),dict(name='rebuilt_wide_XC_top',outline_lower_bound_um=[7200,top],added_frame_area_mm2=7200*(top-1800)/1e6,added32SM_area_mm2=32*7200*(top-1800)/1e6,dependency='New1200x500 XC floorplan with actual unrotated SRAM macros; not a90degree rotation of an existing hard view. Requires macro/pin/clock/route proof. Exact173bit command capture adjacency/calendar cycles unresolved.')],open=['XC upper strip placed beside static-front column, never overlaid; no physical90degree hard-view rotation','Exact173bit endpoints and capture alignment','Attention PV/wave/prob/BE outline and actual graph','Source-bound full static front/feed physical views','Independent28root real clock distributor placement','Actual edgepins and cut<=0.60','Physical relay homes and fixed compiler cycles','Full native TT/FF/DRC0 and end-to-end rate'])
(out/'bounds.json').write_text(json.dumps(d,indent=2)+'\n')
fig,axs=plt.subplots(2,1,figsize=(16,7),dpi=140)
for ax,(w,h,mode) in zip(axs,[(side,1800,'side_XC'),(7200,top,'rebuilt_wide_XC_top')]):
 ax.add_patch(Rectangle((0,0),w,h,fill=False,ec='black'))
 x=0
 for i in range(16):
  if i==8:
   ax.add_patch(Rectangle((x,0),front,1765.44,fc='#b07aa1',alpha=.6));ax.text(x+front/2,800,'static\nfront',ha='center',fontsize=6);x+=front+gap
  ax.add_patch(Rectangle((x,0),tw,th,fc='#4e79a7',alpha=.6));ax.text(x+tw/2,th/2,str(i),ha='center',fontsize=7);x+=tw+gap
 if mode=='side_XC':xx,yy,ww,hh=old+gap,0,500,1200
 else:xx,yy,ww,hh=8*(tw+gap)+front+gap,th+gap,1200,500
 ax.add_patch(Rectangle((xx,yy),ww,hh,fc='#f28e2b',alpha=.7));ax.text(xx+ww/2,yy+hh/2,'XC\nproposed\nnew leaf',ha='center',va='center',fontsize=6)
 ax.set(xlim=(-40,w+40),ylim=(-40,h+40),title=f'{mode}: {w:.2f} x {h:.2f} um LOWER BOUND (attention + exact pins/relays OPEN)');ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
fig.tight_layout();fig.savefig(out/'alternatives.png');print(json.dumps(d,indent=2))
