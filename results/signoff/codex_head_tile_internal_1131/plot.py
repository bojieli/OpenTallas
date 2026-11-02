from pathlib import Path
import json,re,ast
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
b=Path('/home/ubuntu/coord/codex-head-1131/tile_internal_diag');j=json.loads((b/'trace.json').read_text());pins=ast.literal_eval(re.search(r'^pins=(.*)$',(b/'trace.py').read_text(),re.M).group(1));inst=[p.rsplit('/',1)[0] for p in pins];c=j['cells'];xy=[]
for i in inst:
 p=c[i]['placement'];xy.append((int(p[1])/1000,int(p[2])/1000))
fig,ax=plt.subplots(figsize=(10,8));cols=plt.cm.tab20.colors
for k,(n,d) in enumerate(j['nets'].items()):
 for layer,body in re.findall(r'(?:ROUTED|NEW)\s+(M\d+)\s+([^\n]+)',d['route_def'] or ''):
  prev=None
  for x,y in re.findall(r'\(\s*(\*|\d+)\s+(\*|\d+)\s*\)',body):
   if '*' in [x,y] and prev is None:continue
   p=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y))
   if prev:ax.plot([prev[0]/1000,p[0]/1000],[prev[1]/1000,p[1]/1000],color=cols[k%20],alpha=.65,lw=1)
   prev=p
for k,((x,y),i) in enumerate(zip(xy,inst)):
 ax.scatter(x,y,c='red' if k in [0,len(inst)-1] else 'black',s=50 if k in [0,len(inst)-1] else 20,zorder=4)
 if k in [0,len(inst)-1] or not i.startswith(('wire','place','rebuffer','load_slew')):ax.annotate(str(k)+':'+i.split('/')[-1],(x,y),xytext=(4,5),textcoords='offset points',fontsize=8)
reach=sum(abs(x1-x0)+abs(y1-y0) for (x0,y0),(x1,y1) in zip(xy,xy[1:]));ff=abs(xy[-1][0]-xy[0][0])+abs(xy[-1][1]-xy[0][1]);ax.set_title(f'Actual old-V1 c_cb31 → kh_gt routed comparator cone\nFF origin separation {ff:.3f}um; summed path-origin hops {reach:.3f}um; TT−1105.27ps');ax.set_xlabel('X um');ax.set_ylabel('Y um');ax.grid(alpha=.25);ax.set_aspect('equal');fig.tight_layout();fig.savefig(b/'actual_comparator_routes.png',dpi=150)
(b/'path_summary.json').write_text(json.dumps({'pins':pins,'xy_placement_origins_um':xy,'summed_path_origin_hops_um':reach,'ff_origin_manhattan_um':ff,'scope':'Actual oldV1; no result or prediction for advancing tileIO'},indent=1));print(reach,ff)
