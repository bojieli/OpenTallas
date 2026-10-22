#!/usr/bin/env python3
"""Fixed head/xleaf contacts only; no routed/soft-landing reach claim."""
import sys,re,json,hashlib,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'tools/landed_parent'),str(R/'tools/hier_contract')]
import lp,child_lint as C
s=json.loads((R/'tools/ref_tile/specs_qw2_slice2_native/qfd_dv_slice2_w9.json').read_text())
rtl=R/'rtl/qwen_dv/s5/s7/lp/qfd_dv_s7_lp.sv'
m=lp.parse_module(lp.preprocess(rtl.read_text(),['OT_S5_HARD']),'qfd_dv_s7_lp');w,_,ins=lp.parse_body(m['body']);w.update({p['name']:p['range'] for p in m['ports']})
def width(n):return lp.eval_width(w[n],{})
def expr(t):
 t=t.strip()
 if t.startswith('{')and t.endswith('}'):
  return [b for q in reversed(lp.split_top(t[1:-1])) for b in expr(q)]
 if re.fullmatch(r"\d+'[bdh][0-9a-fA-F_xz]+",t):
  return [None]*int(t.split("'")[0])
 a=re.fullmatch(r'(\w+)(?:\[([^] ]+)\])?',t)
 if not a:raise ValueError(t)
 n,ix=a.groups()
 if not ix:return [(n,i) for i in range(width(n))]
 if ':'in ix:
  h,l=map(int,ix.split(':'));return[(n,i)for i in range(l,h+1)]
 return[(n,int(ix))]
uf={}
def root(x):
 if x is None:return None
 uf.setdefault(x,x)
 while uf[x]!=x:uf[x]=uf[uf[x]];x=uf[x]
 return x
def union(a,b):
 if a is not None and b is not None:uf[root(a)]=root(b)
skipped=[]
for a in re.finditer(r'\bassign\s+([^;]+?)\s*=\s*([^;]+);',m['body']):
 try:
  x,y=expr(a[1]),expr(a[2]);assert len(x)==len(y)
  for i,j in zip(x,y):union(i,j)
 except(Exception,SystemExit):skipped.append(a[0][:150])
contacts=collections.defaultdict(list);views={};bind={k['inst']:k for k in s['children']if k['inst'].startswith(('u_xl','u_xh'))};counts=collections.Counter();unmapped=[]
for i in ins:
 if i['inst']not in bind:continue
 k=bind[i['inst']];v=k['view'];name=Path(v).name
 if v not in views:views[v]=C.parse_lef((R/v/(name+'.lef')).read_text())
 lef=views[v];assert k.get('orient','R0')=='R0'
 for port,ex in i['conns'].items():
  if port in ['ck','clk','rst_n']:continue
  try:bits=expr(ex)
  except(Exception,SystemExit):unmapped.append([i['inst'],port,ex]);continue
  for b,net in enumerate(bits):
   pn=port if len(bits)==1 else f'{port}[{b}]'
   if pn not in lef['pins']:unmapped.append([i['inst'],pn,ex]);continue
   pin=lef['pins'][pn];rect=pin['rects'];xy=[((x0+x1)/2+k['at'][0],(y0+y1)/2+k['at'][1])for layer,x0,y0,x1,y1 in rect]
   contacts[root(net)].append((i['inst'],pn,pin['direction'],xy));counts[i['inst']]+=1
edges=[]
for n,cs in contacts.items():
 for a in cs:
  if a[2]!='OUTPUT':continue
  for b in cs:
   if b[2]!='INPUT'or a[0]==b[0]:continue
   d=min(abs(x-u)+abs(y-v)for x,y in a[3]for u,v in b[3]);edges.append(dict(net=str(n),source=a[0]+'.'+a[1],sink=b[0]+'.'+b[1],manhattan_um=round(d,4)))
out=dict(scope='R0 hard XHEAD3/xleaf matching-bit endpoints via exact parent assign aliases; soft landing/input hops and routed detours unqualified',source_rtl_sha256=hashlib.sha256(rtl.read_bytes()).hexdigest(),bindings=len(bind),contact_bits=sum(counts.values()),mapped_matching_bit_edges=len(edges),unmapped_hard_ports=unmapped,skipped_other_parent_assignments=skipped,max_manhattan_um=max((e['manhattan_um']for e in edges),default=0),over405=sum(e['manhattan_um']>405 for e in edges),worst=sorted(edges,key=lambda e:e['manhattan_um'],reverse=True)[:24],all_edges=edges)
p=R/'results/arch/codex_slice2_native_1021/attempt3';p.mkdir(exist_ok=True);(p/'head_leaf_fixed_reach.json').write_text(json.dumps(out,indent=2)+'\n');print({k:v for k,v in out.items()if k not in ['all_edges','worst','skipped_other_parent_assignments']})
