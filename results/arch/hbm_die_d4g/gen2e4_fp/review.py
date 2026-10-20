import json,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parents[1]
a=json.load(open(R/'grants_d4g.json'));b=json.load(open(R/'grants_d4g_fp.json'))
A={s['name']:s for s in a['slots']};B={s['name']:s for s in b['slots']}
moved=b['fp_channel_shift_1019']['moved']
for n,s in A.items():
 if n not in moved: assert s==B[n], n
 else:
  assert s['outline']==B[n]['outline']
  assert s['origin']['y']==B[n]['origin']['y']
  assert abs(abs(s['origin']['x']-B[n]['origin']['x'])-43.2)<1e-6
for q in ('NW','SW','NE','SE'):
 for i in range(8):
  assert abs((A[f'hcb_{q}{i}']['origin']['x']-A[f'hc_{q}']['origin']['x'])-(B[f'hcb_{q}{i}']['origin']['x']-B[f'hc_{q}']['origin']['x']))<1e-6
fig,axs=plt.subplots(2,2,figsize=(14,12))
for ax,q in zip(axs.flat,('NW','NE','SW','SE')):
 for n,s in B.items():
  if not (n in moved or n.startswith('sfucore_')) or q not in n:continue
  x,y=s['origin']['x'],s['origin']['y'];w,h=s['outline']['w'],s['outline']['h']
  color='#f3bb4b' if n.startswith('hcb_') else '#62b4c9' if n.startswith('hc_') else '#9b9cc7'
  ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor='black',alpha=.6))
  ax.text(x+w/2,y+h/2,n,ha='center',va='center',fontsize=7)
  if n in moved:
   ax.add_patch(Rectangle((A[n]['origin']['x'],y),w,h,fill=False,edgecolor='red',linestyle='--',linewidth=.7))
 ax.autoscale_view();ax.set_aspect('equal');ax.set_title(q+' shifted grants; red dash = baseline');ax.set_xlabel('um');ax.set_ylabel('um')
fig.suptitle('GEN2e4 channel candidate: 39 grants shifted, ring geometry preserved; no new slot overlaps')
fig.tight_layout();fig.savefig(R/'gen2e4_fp/grant_shift_review.png',dpi=140)
report={'source':'11bf17f45','moved_slots':len(moved),'unmoved_byte_equal':True,'ring_relative_geometry_preserved':True,'new_slot_overlaps':b['fp_channel_shift_1019']['new_overlaps'],'inherited_slot_overlap_count':28,'relay_reach':'NOT MEASURED: requires fresh GEN + relay stations/landing','release':'CANDIDATE ONLY; no active source/grants changed'}
(R/'gen2e4_fp/review.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
