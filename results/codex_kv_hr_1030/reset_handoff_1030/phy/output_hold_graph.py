"""Narrow actual native-ECO graph certificate; no RTL recompilation."""
from pathlib import Path
import json,re,collections,sys
before,after,plan,out=map(Path,sys.argv[1:]);d=json.load(open(plan));norm=lambda s:s.replace('\\','')
def parse(p):
 result={}
 for m in re.finditer(r'(?m)^\s*(\S+)\s+(\S+)\s*\((.*?)\);',p.read_text(),re.S):
  master,name,body=m.groups()
  if master in['module','input','output','wire','assign','endmodule']:continue
  ports={a:norm(b.strip())for a,b in re.findall(r'\.(\w+)\s*\(([^)]+)\)',body)}
  if ports:result[norm(name)]=(master,ports)
 return result
b=parse(before);a=parse(after);new=set(a)-set(b);assert len(new)==488 and set(b)<=set(a)
def public_ports(p):
 result={}
 for m in re.finditer(r'(?m)^\s*(input|output|inout)\s*(?:\[(\d+):(\d+)\]\s*)?(\S+)\s*;',p.read_text()):
  direction,hi,lo,name=m.groups();name=norm(name)
  if hi is None:result[name]=direction
  else:
   for bit in range(min(int(hi),int(lo)),max(int(hi),int(lo))+1):result[f'{name}[{bit}]']=direction
 return result
ports=public_ports(before);assert len(ports)==560 and ports==public_ports(after),'public ABI changed'
for n in b:assert a[n][0]==b[n][0],('oldmaster',n)
for n in new:assert a[n][0]=='HB4xp67_ASAP7_75t_R' and set(a[n][1])=={'A','Y'},('newcell',n)
parents={}
def find(n):
 if n not in parents:parents[n]=n
 if parents[n]!=n:parents[n]=find(parents[n])
 return parents[n]
def union(x,y):parents[find(x)]=find(y)
for n in new:union(a[n][1]['A'],a[n][1]['Y'])
def groups(c,collapse):
 g=collections.defaultdict(set)
 for n in b:
  for pin,net in c[n][1].items():g[find(net)if collapse else net].add((n,pin))
 for ep in ports:g[find(ep)if collapse else ep].add(('PORT',ep))
 return {frozenset(v)for v in g.values()}
assert groups(b,False)==groups(a,True),'collapsed oldpin connectivity differs'
drivers={}
for n,(m,p)in a.items():
 for q in ['Y','Q','QN']:
  if q in p:drivers[p[q]]=(n,m)
visited=set();hist=collections.Counter()
for row in d['plans']:
 ep=row['port'];net=ep;seen=set();chain=[]
 while True:
  n,m=drivers[net]
  if n not in new:break
  assert n not in seen,('cycle',ep);seen.add(n);chain.append(n);net=a[n][1]['A']
 assert n==norm(row['old_last_driver']) and len(chain)==row['new_HB4'],('chain',ep,n,chain)
 assert not(visited&seen),('sharedpad',ep);visited|=seen;hist[len(chain)]+=1
assert visited==new and hist=={2:209,1:70}
r={'status':'PASS_ACTUAL_CELL_PIN_GRAPH','old_cells':len(b),'new_cells':len(a),'new_positive_HB4':488,'unique_outputs':279,'chain_histogram':dict(hist),'oldmasters_exact':True,'all_old_pin_connectivity_after_positive_HB4_collapse_exact':True,'newFFs':0,'added_cycles':0,'normal_primitive_budget':'Each output retains oldINV+BUF2 and adds1or2HB4; total3or4pureprimitives, maxHB4=2','scope':'Nativeported ECO; actualLiberty HB4Y=A primitive from existingRTL fourstate+mutantcoupon. Electrical/RC gates separate.'};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
