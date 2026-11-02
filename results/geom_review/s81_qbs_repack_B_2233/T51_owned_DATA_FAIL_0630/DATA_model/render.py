from pathlib import Path
import json,gzip
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent;P=R/'inputs';C=[json.loads(x)for x in gzip.open(P/'cells.jsonl.gz','rt')];F=json.load(open(P/'FF_targets.json'));T=json.load(open(R/'DATA_targets.json'));M=json.load(open(R/'model.json'));bands=json.load(open(P/'other_declared_band_reservations.json'))['rectangles'];fig,(a,b,z)=plt.subplots(1,3,figsize=(17,8),gridspec_kw={'width_ratios':[1.2,1.2,.85]})
for ax in(a,b):
 for band in bands:
  x,y,x1,y1=[v/1000 for v in band['bbox_dbu']]
  if x1<0 or x>230 or y1<1090 or y>1230:continue
  ax.add_patch(Rectangle((x,y),x1-x,y1-y,fc='#eedec4',ec='#b69a70',lw=.5,alpha=.8))
 for c in C:
  bb=[v/1000 for v in c[2]]
  if c[0]in T or c[0]in F or bb[0]>230 or bb[2]<0 or bb[1]>1230 or bb[3]<1090:continue
  if c[1].startswith('TAPCELL'):col='#be9c97'
  else:col='#c3cbd0'
  ax.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc=col,ec='none',alpha=.6))
 for name,t in F.items():
  if t['family']!='ft2_ring_band_FFs':continue
  bb=[v/1000 for v in t['bbox_dbu']];ax.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc='#087d9b',ec='none'))
 ax.plot(61.536,1224.224,'r*',ms=8);ax.set(xlim=(0,230),ylim=(1090,1230),xlabel='µm',ylabel='µm');ax.set_aspect('equal')
for c in C:
 if c[0]not in T:continue
 bb=[v/1000 for v in c[2]]
 if bb[0]<=230 and bb[3]>=1090 and bb[1]<=1230:a.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc='#ce7623',ec='none',alpha=.7))
for name,t in T.items():
 bb=[v/1000 for v in t['bbox_dbu']]
 if bb[0]<=230 and bb[3]>=1090 and bb[1]<=1230:b.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc='#ce7623',ec='none',alpha=.8))
b.add_patch(Rectangle((60,1090),10,140,fill=False,ec='red',ls='--',lw=1));b.axhline(1137.5,c='red',lw=.8,ls='--');b.text(73,1138.7,'new cut2.703',c='red',fontsize=8)
a.set_title('FF-only model: old owned comb remains at y~950\nOld cut2.241 at60/967.5; blue=2677ring FFs')
b.set_title('One exact-owned DATA-cone model:9288cells\nOld cut drops.231; compact ring creates new2.703')
z.bar([0,1,2],[2.240607,.230819,2.702951],color=['#a1673f','#559672','#b7473c']);z.axhline(1,c='black',ls='--',lw=1);z.set_xticks([0,1,2],['prior cut\nbefore DATA','prior cut\nafter DATA','new global\nring cut'],fontsize=8);z.set(ylabel='projected M2–M7 column demand',ylim=(0,3.1));z.set_title('Same unchanged source graph\nCapacity remains FAIL')
z.text(.02,.40,'0 footprint / row / master violations\n52other bands +137673TAP held\n9shared +447reset/START held\nAllFF targets / pins / cycles fixed\nR2R402.33 /0; pin149.81\nNo native DB / CAD changes',transform=z.transAxes,fontsize=9,va='top')
fig.suptitle('T51 DISABLED ownership-constrained DATA placement — HOLD / NO PHYSICAL RELEASE\nExact pins/roles prove data ownership and fix the stranded cone, but the current narrow FF field lacks local routing spread.',fontsize=11);fig.tight_layout();fig.savefig(R/'T51_owned_DATA_MODEL_LOOK.png',dpi=160)
