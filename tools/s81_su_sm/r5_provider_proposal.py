import json,re,argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
ap=argparse.ArgumentParser();ap.add_argument('--geometry',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
J=json.loads(a.geometry.read_text());O=a.out;O.mkdir(exist_ok=True,parents=True)
cols={'SML':'#f7bb63','H4':'#ef8e91','SMD':'#f4dc76','IRG':'#c8d9ef','GLUE':'#ddd'}
proposal={}
fig,axes=plt.subplots(1,2,figsize=(12,13))
for ax,(typ,t) in zip(axes,[(k,J[k]) for k in ['svc_hi_dsdv_svc_rs__t2','svc_lo_dsdv_svc_rs__t5']]):
 W,H=t['outline'];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5))
 for name,mod,p,d in t['hard']:
  if mod=='ot_s81c_attn_hcore':
   h=int(re.search(r'g_h\[(\d+)\]',name).group(1))
   if h>=8:continue
   ax.add_patch(Rectangle(p,*d,facecolor='#5496ca',edgecolor='#333',lw=.4));ax.text(p[0]+d[0]/2,p[1]+d[1]/2,f'RT2 h{h}',ha='center',va='center',fontsize=4.7)
  else:ax.add_patch(Rectangle(p,*d,facecolor='#b68cbe',edgecolor='#333',lw=.4))
 for name,mod,p,d in t['macros']:ax.add_patch(Rectangle(p,*d,facecolor='#83b993',edgecolor='#164b27',lw=.3))
 ax.add_patch(Circle((725.76,1226.88),21.6,color='red',fill=False,lw=1.2));ax.text(725.76,1271,'clock bay unchanged',fontsize=5,ha='center')
 boxes=[];bands=[311.04,864,1598.4,2151.36]
 counters={k:0 for k in cols}
 for bi,y in enumerate(bands):
  seq=[('SML',120.96),('SML',120.96),('H4',103.68)]+[('IRG' if 'lo_' in typ else 'SPACE',60.48)]*8+[('H4',103.68),('SMD',69.12)]+[('GLUE',120.96)]*(2 if bi<3 else (1 if 'lo_' in typ else 0))
  x=34.56
  for kind,w in seq:
   if kind=='SPACE':x+=w+8.64;continue
   idx=counters[kind];counters[kind]+=1
   b=dict(kind=kind,index=idx,origin_um=[x,y],outline_um=[w,259.2],qualification='UNQUALIFIED_PROVIDER_BOX',clock='center entry; local tree unbuilt',pin_cycles='not adopted',area_basis='mapped body known' if kind in ('SML','H4','SMD') else 'PENDING_ACTUAL_INVENTORY')
   boxes.append(b);ax.add_patch(Rectangle((x,y),w,259.2,facecolor=cols[kind],edgecolor='#555',ls='--',lw=.6));ax.text(x+w/2,y+129.6,f'{kind}\n{idx}',ha='center',va='center',fontsize=4.8)
   x+=w+8.64
  if x-8.64>1401.84+1e-6:raise ValueError('overflow')
 proposal[typ]=dict(outline_um=t['outline'],source_geometry='SVC5 extracted exact current H16 provider/macro geometry',dy_um=0,new_provider_boxes=boxes,counts=counters,existing_SRAMs_unchanged=len(t['macros']),existing_SX_unchanged=8,retained_RT2_slots=32,clock_bay_um=[725.76,1226.88],gaps_um=8.64,not_qualified=['actual H8 native memory-closed parent inventory','IRG actual mapped hslice area','GLUE number and shape','new provider pin maps/abutment/track budget','clock/reset domain and existing native stage latency','all links <=405um with registered hops','provider physical signoff','H8 slice proof/calibration'],source_cut_added_cycles=0)
 ax.set(xlim=(-25,W+25),ylim=(-30,H+45),aspect='equal',xlabel='um',ylabel='um',title=typ+'\nCandidate only: dY=0, every dashed box unqualified')
 ax.grid(alpha=.1)
fig.suptitle('R5 rectangular placement proposal outside POR\nExact existing SRAM/SX/retained RT2 outlines; estimated provider boxes highlighted',fontsize=12)
fig.tight_layout(rect=[0,0,.99,.95]);fig.savefig(O/'r5_candidate_unqualified.png',dpi=180)
(O/'proposal.json').write_text(json.dumps(proposal,indent=1)+'\n')
