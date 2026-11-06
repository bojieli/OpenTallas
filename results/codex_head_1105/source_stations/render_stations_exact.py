import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path('/home/ubuntu/coord/tmp/codex-head-1105');types=json.load(open(r/'station_geometry.json'));types['hd_spn']['internal_stations']=[json.load(open(r/'spn_xo_exact_patch.json')) if e['conn']=='bus:x_o' else e for e in types['hd_spn']['internal_stations']];fig,axes=plt.subplots(1,2,figsize=(10,12));report={}
for ax,(tn,t) in zip(axes,types.items()):
 pins=json.load(open(r/('spn_pins.json' if tn=='hd_spn' else 'spn_end_pins.json')));taps=json.load(open(r/('spn_taps.json' if tn=='hd_spn' else 'spn_end_taps.json')));w,h=t['outline_um'];ax.add_patch(Rectangle((0,0),w,h,fill=False));mx=0;cmx=0;perclock={}
 for c in t['contents']:
  x,y=c['origin_um'];cw,ch=c['outline_um'];ax.add_patch(Rectangle((x,y),cw,ch,facecolor='.7'));ax.text(x,y+ch+8,c['inst'],fontsize=7)
 for tap in taps:ax.plot(*tap['xy_um'],'.',color='purple',markersize=3)
 for ci,e in enumerate(t['internal_stations']):
  b=e['conn'].split(':')[1];spec=next(q for q in t['buses'] if q['name']==b);pp=[q for q in pins if q['bus']==b];assert pp;face=spec['face'];lx,ly=e['leaf_um'];leaf=next(c for c in t['contents'] if c['inst']==spec['leaf'].split('.')[0]);off=max(0,min(15,leaf['outline_um'][0 if face in 'EW' else 1]/2-2));lx+=(-off if face=='W' else off if face=='E' else 0);ly+=(-off if face=='S' else off if face=='N' else 0);xs=[q['x'] for q in pp];ys=[q['y'] for q in pp]
  normal=max(abs(min(xs)-lx),abs(max(xs)-lx)) if face in 'EW' else max(abs(min(ys)-ly),abs(max(ys)-ly));along=max(abs(min(ys)-ly),abs(max(ys)-ly)) if face in 'EW' else max(abs(min(xs)-lx),abs(max(xs)-lx));n=len(e['regs_um']);edges=n+1;first,second=(normal,along) if spec['dir']=='in' else (along,normal);split=0 if first<1e-8 else edges if second<1e-8 else min(range(1,edges),key=lambda j:max(first/j,second/(edges-j)))
  color=plt.get_cmap('tab10')(ci);cloud=[]
  for bi,p in enumerate(pp):
   px,py=p['x'],p['y'];cx,cy=(lx,py) if face in 'EW' else (px,ly);a=(px,py) if spec['dir']=='in' else (lx,ly);bpt=(lx,ly) if spec['dir']=='in' else (px,py);pts=[a]
   for k in range(1,edges):
    if k<=split:f=k/split;x=a[0]+f*(cx-a[0]);y=a[1]+f*(cy-a[1])
    else:f=(k-split)/(edges-split);x=cx+f*(bpt[0]-cx);y=cy+f*(bpt[1]-cy)
    if 'bit_sites_um' in e:x,y=e['bit_sites_um'][k-1][p['bit']]
    pts.append((x,y));cloud.append((x,y));cd,tap=min(((abs(x-tap['xy_um'][0])+abs(y-tap['xy_um'][1]),tap) for tap in taps),key=lambda v:v[0])
    perclock[b]=max(perclock.get(b,0),cd)
    if cd>cmx:cmx=cd;far=dict(bus=b,stage=k-1,bit=p['bit'],xy=[x,y],tap=tap)
   pts.append(bpt);mx=max(mx,max(abs(q[0]-z[0])+abs(q[1]-z[1]) for q,z in zip(pts,pts[1:])))
   if bi%65==0:ax.plot(*zip(*pts),color=color,alpha=.18,lw=.5)
  ax.scatter(*zip(*cloud),s=.4,color=color,label=e['conn'][4:]+' '+str(n)+' stages');ax.scatter(xs,ys,s=.5,color=color,marker='s')
 ax.set_xlim(-20,w+20);ax.set_ylim(-20,h+70);ax.set_aspect('equal');ax.set_title(tn+' actual pin to leaf relay banks',fontsize=9);ax.set_xlabel('um');ax.set_ylabel('um');ax.legend(fontsize=6,loc='center left',bbox_to_anchor=(1,0.5));report[tn]=dict(max_ideal_data_hop_um=round(mx,3),max_nearest_clock_entry_um=round(cmx,3),actual_plan_stages=sum(len(e['regs_um']) for e in t['internal_stations']),far_clock=far,clock_by_bus=perclock)
fig.tight_layout();fig.savefig(r/'stations_exact_review.png',dpi=145);(r/'stations_exact_review.json').write_text(json.dumps(report,indent=1)+'\n');print(report)
