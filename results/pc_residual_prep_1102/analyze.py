import gzip,json,re,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;I=R/'inputs';q=json.loads((I/'native_query_with_DEF.json').read_text());maps=json.loads((I/'spef_name_map.json').read_text())['ids'];sys.path.insert(0,str(R.parents[1]/'tools/die_plan'));import hard_pinreg as HP
libs={}
for p in (I/'libs').glob('*.gz'):
 txt=gzip.decompress(p.read_bytes()).decode()
 for m in re.finditer(r'\bcell\s*\(\s*(\w+)\s*\)',txt):
  body,_=HP._block(txt,m.end());pins={}
  for pm in re.finditer(r'\bpin\s*\(\s*(\w+)\s*\)',body):
   b,_=HP._block(body,pm.end());v=re.search(r'(?m)^\s*capacitance\s*:\s*([\d.eE+-]+)',b)
   pins[pm[1]]=float(v[1]) if v else None
  libs[m[1]]=pins
caps={}
for sec in (I/'selected_nets.spef').read_text().split('*D_NET ')[1:]:
 n,v=sec.splitlines()[0].split();caps[maps[n]]=float(v)*1000
s=(I/'selected_nets.def').read_text();routes={};metrics={}
for n in q['nets']:
 m=re.search(r'^\s*- '+re.escape(n)+r'\b.*?;',s,re.S|re.M);pts=[];segs=[]
 for section in re.split(r'\b(?:NEW|ROUTED)\s+',m.group() if m else '')[1:]:
  layer=section.split()[0];prior=None
  for x,y in re.findall(r'\(\s*(-?\d+|\*)\s+(-?\d+|\*)\s*\)',section.split('RECT')[0]):
   if prior is None and '*' in (x,y):continue
   xy=(prior[0] if x=='*' else int(x)/1000,prior[1] if y=='*' else int(y)/1000)
   pts.append(xy)
   if prior and xy!=prior:segs.append((layer,prior,xy))
   prior=xy
 routes[n]=segs
 sinkvals=[libs.get(r['master'],{}).get(r['pin']) for r in q['nets'][n] if r['pin']!='Y'];sinkcap=sum(sinkvals) if all(v is not None for v in sinkvals) else None
 metrics[n]={'wire_cap_fF':caps[n],'sink_pin_cap_fF':sinkcap,'total_cap_fF':caps[n]+sinkcap if sinkcap is not None else None,'route_length_um':sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for _,a,b in segs),'bbox_um':[min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)] if pts else None,'connections':q['nets'][n]}
fig,axes=plt.subplots(1,2,figsize=(13,7))
for ax,n in zip(axes,['net41987','_168484_']):
 for layer,a,b in routes[n]:ax.plot([a[0],b[0]],[a[1],b[1]],lw=1,color={'M2':'#7393b3','M3':'#222b53','M4':'#d48222','M5':'#b32883'}.get(layer,'black'))
 for r in q['nets'][n]:
  p=q['positions'][r['instance']];ax.scatter(p['x'],p['y'],s=40,color='red' if r['pin']=='Y' else 'green');ax.annotate(r['instance']+'/'+r['pin'],(p['x'],p['y']),xytext=(4,4),textcoords='offset points',fontsize=8)
 ax.set_title(f"{n}: native route {metrics[n]['route_length_um']:.3f}um / wire {caps[n]:.4f}fF");ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('um');ax.set_ylabel('um')
fig.suptitle('Actual PC data routes — no placement/route modification; no free-site/PG legality claim');fig.tight_layout();fig.savefig(R/'actual_INV_input_output_routes.png',dpi=160)
(R/'DATA_NET_METRICS.json').write_text(json.dumps({'status':'PASSIVE_NATIVE_QUERY','metrics':metrics,'candidate_master_input_caps':{m:libs[m] for m in libs if m.startswith(('INVx','BUFx'))},'STA_new_run':False},indent=2)+'\n')
for n in ('net41987','_168484_','_126906_'):print(n,metrics[n])
