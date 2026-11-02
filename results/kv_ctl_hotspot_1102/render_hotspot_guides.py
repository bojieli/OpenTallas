import json,gzip
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
O=Path(__file__).resolve().parent;P=O.parent/'kv_ctl_compact233x302_PREP_1102';before={c[6]:c for c in json.loads(gzip.decompress((P/'source_cell_model_PREP.json.gz').read_bytes()))};after={c[6]:c for c in json.loads(gzip.decompress((O/'guided_cell_model.json.gz').read_bytes()))};model=json.loads(gzip.decompress((O/'comb_road_model.json.gz').read_bytes()));hot=json.loads(gzip.decompress((O/'hotspot_contributors.json.gz').read_bytes()));coupons=json.load(open(O/'road_path_coupons.json'));result=json.load(open(O/'guided_source_model.json'));guide={p['name']:p for p in model['cells']};zones=model['report']['zones'];ff=[c for c in before.values() if c[0]=='S'];macros=[c for c in before.values() if c[0]=='M'];fig,aa=plt.subplots(2,3,figsize=(18,11));colors={'H0':'#de8d21','H1':'#af6c18','H2':'#764a15','V0':'#2f9d6d','V1':'#23834e','V2':'#115b40'}
def base(ax,view):
 for c in macros:ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],fc='#bbcad2',ec='#526c7b'));ax.add_patch(Rectangle((c[2]-4.32,c[3]-4.32),c[4]-c[2]+8.64,c[5]-c[3]+8.64,fill=False,ec='#799c8b',ls=':',lw=.7))
 ax.scatter([(c[2]+c[4])/2 for c in ff],[(c[3]+c[5])/2 for c in ff],s=.6,c='#4b91bd',alpha=.65)
 ax.add_patch(Rectangle((112.12,146.68),9.04,9.04,fill=False,ec='#c72d37',lw=1.1));ax.plot(116.616,151.2,'*',c='#c72d37',ms=7)
 ax.set(xlim=view[0],ylim=view[1],xlabel='local x (um)',ylabel='local y (um)');ax.set_aspect('equal')
for row,direction in enumerate(['H','V']):
 win=next(w for w in hot['windows'] if w['direction']==direction);view=((25,155),(245,302)) if direction=='H' else ((75,157),(105,192));names=[n for n,p in guide.items() if p['zone'].startswith(direction)]
 for col in [0,1]:
  ax=aa[row,col];base(ax,view)
  data=before if col==0 else after
  for name in names:
   c=data[name];ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],fc=colors[guide[name]['zone']] if col else '#d4822d',ec='none',alpha=.8))
  a,b=win['window_um'];cut=win['cut_um']
  if direction=='H':ax.add_patch(Rectangle((cut-1,a),2,b-a,fc='none',ec='#d23645',lw=1.5));ax.plot([cut,cut],view[1],c='#d23645',lw=.6,ls='--')
  else:ax.add_patch(Rectangle((a,cut-1),b-a,2,fc='none',ec='#d23645',lw=1.5));ax.plot(view[0],[cut,cut],c='#d23645',lw=.6,ls='--')
  if col:
   for z in zones:
    if z['direction']!=direction:continue
    x0,y0,x1,y1=z['bbox_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec=colors[z['name']],lw=.8,ls='--'));ax.text(x0+1,y1-1,z['name'],va='top',fontsize=7,color=colors[z['name']])
  label=f"{direction} existing model: {win['source_nets']} nets / {win['crossing_share']:.1f} shares" if not col else f"{direction} finite existing-comb guides; same FFs/clock"
  ratio=next(q for q in result['original_window_ratios_after'] if q['direction']==direction);ax.set_title(label+'\n'+(f"old window proxy {ratio['before']:.3f}" if not col else f"old-window model {ratio['after']:.3f}; global proxy still HOLD"),fontsize=10)
 ax=aa[row,2];base(ax,((0,233.28),(0,302.4)))
 for z in zones:
  x0,y0,x1,y1=z['bbox_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec=colors[z['name']],lw=.7));ax.text((x0+x1)/2,(y0+y1)/2,z['name'],fontsize=6,color=colors[z['name']],ha='center')
 p=next(p for p in coupons['paths'] if p['direction']==direction)
 for seg in p['segments']:
  x=[seg['start'][0],seg['end'][0]];y=[seg['start'][1],seg['end'][1]];ax.plot(x,y,c='#b12572' if seg['layer']=='M4' else '#2b6fb0',lw=1.7,ls=':' if seg['layer']=='LOCAL_ACCESS_OPEN' else '-')
 for e,symbol in [(p['driver'],'s'),(p['sink'],'o')]:ax.plot(*e['xy'],symbol,c='#af235b',ms=4)
 ax.set_title(f"Real-pin metal-road coupon {p['native_net_name']}\nM4/M5 trunk leaves hot window; local access OPEN",fontsize=10)
fig.suptitle('CTL233.28×302.4 SOURCE/GUIDE PREP ONLY — no new native FP, PLACE or route\n2,212 existing data-comb cells (204.15um²); zero FF/master/clock moves; zero inserted cells/cycles\nMeasured predecessor normal-buffer class:470.72um² cell area /784.53um² space reserve; max regional space budget33.5%',fontsize=12)
fig.tight_layout(rect=(0,0,.99,.92));fig.savefig(O/'hotspot_comb_roads_review.png',dpi=160)
