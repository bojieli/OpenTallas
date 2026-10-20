"""Conservative full combinational-cone endpoint Manhattan audit of saved GRT DB.
No combinational gate/clock/PG exception inferred from instance names.
"""
import collections,csv,gzip,json,sys,glob,re
from pathlib import Path
sys.path.insert(0,'/audit/tools/ref_tile')
import native_census as C
libs=glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*')+glob.glob('/src/physical/asap7_memory_macros/*/*_tt.lib')
roles,receipts=C.liberty_roles(libs)
terms={}; byinst=collections.defaultdict(list); bynet=collections.defaultdict(list); errors=[]
for row in csv.reader(open('/audit/terms.tsv'),delimiter='\t'):
 name,net,direction,master,block,x,y=row
 instance,pin=name.rsplit('/',1)
 if master=='PORT':role={'clock':pin in ('clk','ckh','ck')}; seq=False
 else:
  role=roles.get(master,{}).get('pins',{}).get(pin)
  if role is None:
   b=re.fullmatch(r'(.*)\[(-?\d+)\]',pin)
   if b and int(b[2]) in roles.get(master,{}).get('bus_order',{}).get(b[1],[]): role=roles[master]['pins'].get(b[1])
  if role is None: errors.append(f'missing actual Liberty role {name} {master}');continue
  seq=roles[master]['sequential']
 d=dict(name=name,net=net,direction=direction,master=master,block=bool(int(block)),x=float(x),y=float(y),instance=instance,pin=pin,clock=role['clock'],seq=seq)
 terms[name]=d;byinst[instance].append(name);bynet[net].append(name)
loads=collections.defaultdict(set);outputs=collections.defaultdict(set);sources=[]
for name,d in terms.items():
 if d['master']=='PORT':
  if d['direction']=='INPUT' and not d['clock']: sources.append(name)
  elif d['direction']=='OUTPUT':loads[d['net']].add(name)
 elif d['direction']=='INPUT' and not d['clock']: loads[d['net']].add(name)
 elif d['direction']=='OUTPUT':
  outputs[d['instance']].add(d['net'])
  if d['seq'] or d['block']: sources.append(name)
memo={}; visiting=set()
def endpoints(net):
 if net in memo:return memo[net]
 if net in visiting: raise ValueError('combinational cycle '+net)
 visiting.add(net);out=set()
 for name in loads[net]:
  d=terms[name]
  if d['seq'] or d['block'] or d['master']=='PORT':out.add(name)
  else:
   for nextnet in outputs[d['instance']]:out.update(endpoints(nextnet))
 visiting.remove(net);memo[net]=out;return out
worst=[];bad=[];pairs=0;categories=collections.Counter();maximum=0
for source in sources:
 s=terms[source]
 for endpoint in endpoints(s['net']):
  d=terms[endpoint]
  length=abs(s['x']-d['x'])+abs(s['y']-d['y']);pairs+=1; maximum=max(maximum,length)
  kind=('port' if s['master']=='PORT' else 'macro' if s['block'] else 'ff')+'->'+('port' if d['master']=='PORT' else 'macro' if d['block'] else 'ff')
  categories[kind]+=1
  row=dict(source=source,endpoint=endpoint,um=round(length,6),kind=kind,source_xy=[s['x'],s['y']],endpoint_xy=[d['x'],d['y']])
  if length>405:bad.append(row)
  worst.append(row)
  if len(worst)>1000:worst=sorted(worst,key=lambda r:-r['um'])[:100]
worst=sorted(worst,key=lambda r:-r['um'])[:100]
summary=dict(scope='Native CTS pin averageXY, full unrestricted combinational input-to-output cones, sequential/SRAM/port endpoints; conservative all-input combinational connectivity. Manhattan lower bound, NOT routed detour or final PG qualification',status='FAIL' if errors or bad else 'ENDPOINT_MANHATTAN_PASS',role_errors=errors,actual_liberty=receipts,terms=len(terms),sources=len(sources),pairs=pairs,categories=dict(categories),max_um=round(maximum,6),over405=len(bad),worst=worst)
Path('/audit/reach_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open('/audit/reach_over405.json.gz','wt') as f:json.dump(bad,f)
print({k:v for k,v in summary.items() if k not in ('actual_liberty','worst')})
