import re,json,hashlib
from pathlib import Path
base=Path(__file__).parent
v=(base/'su_gap_predpl/pre_dpl.v').read_text()
def norm(n):return n.strip().lstrip('\\')
parent={}
def find(a):
 a=norm(a)
 while a in parent:a=parent[a]
 return a
for a,b in re.findall(r'assign\s+(\S+)\s*=\s*(\S+)\s*;',v):
 a,b=find(a),find(b)
 if a!=b:parent[a]=b
inst={};driver={}
for master,name,body in re.findall(r'\b((?:DFF|BUF|INV)\w+)\s+(\S+)\s*\((.*?)\);',v,re.S):
 pins={p:find(n) for p,n in re.findall(r'\.(\w+)\(([^)]+)\)',body)};inst[name]=(master,pins)
 for pin in ('QN','Q','Y'):
  if pin in pins:driver[pins[pin]]=(name,pin)
actual={}
for ln in (base/'su_gap_apply/post_dpl_insts.tsv').read_text().splitlines():
 a=ln.split('\t');z=list(map(float,a[2:6]));actual[a[0]]=((z[0]+z[2])/2000,(z[1]+z[3])/2000)
ports={find(n):(float(x),float(y)) for n,x,y in re.findall(r'place_pin -pin_name \{([^}]+)\} -layer \S+ -location \{([\d.]+) ([\d.]+)\}',(base/'su_gap_predpl/io.tcl').read_text())}
def origin(net):
 seen=set();hops=[]
 while net in driver:
  if net in seen:raise ValueError('comb cycle '+net)
  seen.add(net);name,pin=driver[net];m,ps=inst[name]
  if m.startswith('DFF'):return ('FF:'+name,actual[name],hops)
  hops.append(name);net=ps['A']
 if net in ports:return ('PIN:'+net,ports[net],hops)
 if net in ("1'b0","1'b1"):return None
 return ('UNRESOLVED:'+net,None,hops)
ledger=[];unknown=[]
def add(dst,xy,net):
 o=origin(net)
 if not o:return
 src,p,hops=o
 if p is None:unknown.append((dst,src));return
 dist=abs(p[0]-xy[0])+abs(p[1]-xy[1]);ledger.append(dict(src=src,dst=dst,src_um=p,dst_um=xy,endpoint_L1_um=dist,buffer_count=len(hops)))
for name,(m,ps) in inst.items():
 if m.startswith('DFF'):add('FF:'+name,actual[name],ps['D'])
for net,xy in ports.items():
 if net in driver:add('PIN:'+net,xy,net)
ledger.sort(key=lambda a:a['endpoint_L1_um'],reverse=True)
r=dict(scope='Every DFF D endpoint plus every driven physical BPin, combinational BUF/INV aliases traced back to FF Q/QN or input BPin; actual postDPL FFcenters/exact plannedBPinpoints; constants excluded',count=len(ledger),unknown=unknown,max_um=ledger[0]['endpoint_L1_um'],over405=[a for a in ledger if a['endpoint_L1_um']>405],ledger=ledger)
(base/'registered_hops.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='ledger'})[:2500]);print('TOP',ledger[:3])
