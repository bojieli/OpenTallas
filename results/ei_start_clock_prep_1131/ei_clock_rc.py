#!/usr/bin/env python3
"""Disabled idealized geometric buffered tree: actual TT NLDM + M6/M7 RC, no route/signoff claim."""
import re,json,math,bisect,collections,hashlib
from pathlib import Path
root=Path('.')
def block(s,start):
 a=s.index('{',start);n=1;b=a+1
 while n:n+=(s[b]=='{')-(s[b]=='}');b+=1
 return s[a+1:b-1]
def named(s,kind,name):return block(s,re.search(r'\b'+kind+r'\s*\(\s*'+re.escape(name)+r'\s*\)',s).start())
def num(s,key):return float(re.search(r'\b'+key+r'\s*:\s*([\d.eE+-]+)',s)[1])
lib=Path('INVBUF_TT.lib').read_text();seq=Path('SEQ_TT.lib').read_text();buf={}
for name in ['BUFx2_ASAP7_75t_R','BUFx4_ASAP7_75t_R','BUFx8_ASAP7_75t_R','BUFx24_ASAP7_75t_R']:
 s=named(lib,'cell',name);a=named(s,'pin','A');y=named(s,'pin','Y');tabs={}
 for typ in ['cell_rise','cell_fall','rise_transition','fall_transition']:
  t=block(y,re.search(r'\b'+typ+r'\s*\(',y).start());axes=[]
  for ax in ['index_1','index_2']:axes.append(list(map(float,re.search(ax+r'\s*\("([^"]+)"\)',t)[1].split(','))))
  vals=[list(map(float,row.split(','))) for row in re.findall(r'"([\d., eE+-]+)"',t[t.index('values'):])];tabs[typ]=(axes[0],axes[1],vals)
 buf[name]={'cap':num(a,'capacitance'),'maxcap':num(y,'max_capacitance'),'tables':tabs}
caps={}
for m in re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)',seq):
 s=block(seq,m.start())
 try:caps[m[1]]=num(named(s,'pin','CLK'),'capacitance')
 except (AttributeError,ValueError):pass
j=json.loads(Path('clock_clusters.json').read_text());cells={}
for line in Path('/srv/opentallas-scratch2/claude/codex-kv-residuals-1101/hubei/ff/geom_final1131/geom.tsv').open():
 f=line.rstrip().split('\t')
 if f[0]=='C':cells[int(f[1])]=((float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2,f[3])
# Same actual legal routing envelope as candidate config, M6 horizontal/M7 vertical. R kOhm/um, C fF/um.
RC={0:(.0118796,.187426),1:(.0125096,.162979)}
nodes=[];leafcap_unknown=collections.Counter();BUF='BUFx4_ASAP7_75t_R'
def centre(pts):return tuple(sorted(p[i] for p in pts)[len(pts)//2] for i in (0,1))
def node(xy,children=None,cap=None,cid=None):
 n={'xy':xy,'children':children or [],'cap':cap,'cid':cid,'buf':BUF};nodes.append(n);return n
def tree(pts):
 if len(pts)<=16:
  kids=[]
  for p in pts:
   cap=caps.get(p[3])
   if cap is None:leafcap_unknown[p[3]]+=1;cap=0
   kids.append(node(p[:2],cap=cap,cid=p[2]))
  return node(centre(pts),kids)
 a=0 if max(p[0] for p in pts)-min(p[0] for p in pts)>=max(p[1] for p in pts)-min(p[1] for p in pts) else 1
 pts=sorted(pts,key=lambda p:p[a]);k=len(pts)//2
 return node(centre(pts),[tree(pts[:k]),tree(pts[k:])])
def wire(a,b):
 dx,dy=abs(a[0]-b[0]),abs(a[1]-b[1]);return dx*RC[0][0]+dy*RC[1][0],dx*RC[0][1]+dy*RC[1][1]
def split_edges(n):
 for i,c in enumerate(n['children']):
  split_edges(c);a=n['xy'];b=c['xy'];dist=abs(a[0]-b[0])+abs(a[1]-b[1]);segments=math.ceil(dist/120)
  for k in range(segments-1,0,-1):
   xy=(a[0]+(b[0]-a[0])*k/segments,a[1]+(b[1]-a[1])*k/segments);c=node(xy,[c])
  n['children'][i]=c
roots=[]
# root ingress XY comes from exact dump pins; preserve assignment, do not rewrite forwarded roots.
pins={}
for line in Path('/srv/opentallas-scratch2/claude/codex-kv-residuals-1101/hubei/ff/geom_final1131/geom.tsv').open():
 f=line.rstrip().split('\t')
 if f[0]=='P':pins[f[2]]=(float(f[6]),float(f[7]))
for name in sorted(j['planned_root_weights']):
 kids=[]
 for group in j['groups']:
  if group['root']==name:
   pts=[(*cells[cid][:2],cid,cells[cid][2]) for cid in group['endpoint_ids']];kids.append(tree(pts))
 n=node(pins[name],kids);n['buf']='BUFx24_ASAP7_75t_R';split_edges(n);roots.append((name,n))
def inp(n):return n['cap'] if not n['children'] else buf[n['buf']]['cap']
def interp(table,x,y):
 xs,ys,vs=table
 # No silent clamp/extrapolation: small-load edge gets explicit characterized minimum padding below.
 assert xs[0]<=x<=xs[-1] and ys[0]<=y<=ys[-1],(x,y,xs,ys)
 i=max(0,min(len(xs)-2,bisect.bisect_right(xs,x)-1));k=max(0,min(len(ys)-2,bisect.bisect_right(ys,y)-1));u=(x-xs[i])/(xs[i+1]-xs[i]);v=(y-ys[k])/(ys[k+1]-ys[k]);return (1-u)*((1-v)*vs[i][k]+v*vs[i][k+1])+u*((1-v)*vs[i+1][k]+v*vs[i+1][k+1])
arrivals={};viol=[];padding=0;maxload=0
for name,n in roots:
 vals=[]
 def visit(n,arrival,slew,depth):
  global padding,maxload
  if not n['children']:vals.append((arrival,n['cid'],depth));return
  b=buf[n['buf']];load=sum(inp(c)+wire(n['xy'],c['xy'])[1] for c in n['children']);maxload=max(maxload,load)
  domain=b['tables']['cell_rise'];minimum=domain[1][0]
  if load<minimum:padding+=1;load=minimum # Explicit proposed dummy input capacitance, geometry not adopted.
  if load>b['maxcap'] or not domain[0][0]<=slew<=domain[0][-1]:viol.append({'root':name,'load':load,'slew':slew,'depth':depth});return
  delay=max(interp(b['tables'][t],slew,load) for t in ['cell_rise','cell_fall']);out=max(interp(b['tables'][t],slew,load) for t in ['rise_transition','fall_transition'])
  for c in n['children']:
   r,cap=wire(n['xy'],c['xy']);elmore=r*(cap/2+inp(c));visit(c,arrival+delay+elmore,math.sqrt(out*out+(2.2*elmore)**2),depth+1)
 visit(n,0,20,0)
 arrivals[name]={'evaluated_ff':len(vals),'min_ps':min([a for a,_,_ in vals],default=None),'max_ps':max([a for a,_,_ in vals],default=None),'max_depth':max([d for _,_,d in vals],default=None)}
report={'status':'FINITE_DISABLED_RC_NLDM_PROPOSAL_NOT_PLACED_NOT_SIGNOFF','model':'20ps ingress slew; bilinear TT NLDM, layer-aware Elmore, buffered Manhattan idealized edges <=120um; endpoint loads actual master CLK capacitance','root_results':arrivals,'buffers':sum(bool(n['children']) for n in nodes),'leaf_ff':sum(not n['children'] for n in nodes),'unknown_clock_master_loads':dict(leafcap_unknown),'domain_violations':viol,'explicit_min_load_padding_nodes':padding,'max_driver_load_fF':maxload,'forwarded_domains_untouched':j['forwarded_ff_count'],'legal_layers':['M6','M7'],'wire_rc':RC,'wire_rc_units':{'resistance':'kOhm/um','capacitance':'fF/um','delay':'ps = kOhm*fF'},'libraries':{f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ['INVBUF_TT.lib','SEQ_TT.lib']},'limits':'No routed geometry, clock-root electrical source, balancing ECO, FF corner, crosstalk or signoff claim. Padding is a priced proposal, never implicit table clipping.'}
Path('clock_rc_nldm.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))
