#!/usr/bin/env python3
"""Read-only, source-bound clock provenance for the fixed flat HP13 ABI."""
from pathlib import Path
import re,json,hashlib,collections,sys
sys.setrecursionlimit(300000)
root=Path(__file__).resolve().parents[2]
def audit(path):
 raw=path.read_bytes();text=raw.decode();ports={}
 for direction,hi,lo,name in re.findall(r'^(input|output) wire \[(\d+):(\d+)\] (\w+);',text,re.M):
  ports[name]=(direction,int(hi),int(lo))
 def bits(expr):
  expr=expr.strip()
  if expr.startswith('{'):return [b for term in expr[1:-1].split(',') for b in bits(term)]
  if expr in ports:return [f'{expr}[{i}]' for i in range(ports[expr][1],ports[expr][2]-1,-1)]
  assert re.fullmatch(r'n_\d+|\w+\[\d+\]|[01]b[01]|1\x27b[01]',expr),repr(expr)
  return [expr]
 deps={};driven={};seq={};cons=collections.defaultdict(list)
 publisher_path=root/'rtl/qwen_dv/headprep13/corepub39/qfd_hp13_corepub39.sv'
 publisher_raw=publisher_path.read_bytes();assert re.findall(r'posedge\s+(\w+)',publisher_raw.decode())==['ck']
 assert 'assign o=q[STAGES-1];' in publisher_raw.decode()
 def drive(out,inputs,label):
  assert out not in driven,(out,driven.get(out),label)
  driven[out]=label;deps[out]=inputs
 for lhs,rhs in re.findall(r'^assign (.*?) = (.*?);',text,re.M):
  aa,bb=bits(lhs),bits(rhs);assert len(aa)==len(bb),(lhs,rhs)
  for a,b in zip(aa,bb):drive(a,[b],'assign')
 cells=0
 for typ,name,body in re.findall(r'\b(qfd_\w+)\s*#\([^;]*?\)\s+(u_\w+)\s*\((.*?)\);',text,re.S):
  pins=dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|$)',body));cells+=1
  if typ=='qfd_hp13_corepub39':
   clock=bits(pins['ck'])[0]
   for b in bits(pins['o']):
    drive(b,[],name);seq[b]=(clock,name,'publisher')
   continue
  assert typ.startswith('qfd_bmath_'),typ
  if 'dff' in typ:
   q=bits(pins['Q'])[0];drive(q,[],name);seq[q]=(bits(pins['C'])[0],name,typ)
   for role in ['D','R']:
    if role in pins:
     for b in bits(pins[role]):cons[b].append((name,role,bits(pins['C'])[0]))
  else:
   assert 'Y' in pins,(typ,name,pins)
   ins=[b for p,e in pins.items() if p!='Y' for b in bits(e)]
   for b in bits(pins['Y']):drive(b,ins,name)
 # Flatten the retained HR child using exact selected source, rather than assigning
 # its whole output bus from its single clock input by assumption.
 child_path=root/'rtl/qwen_dv/headprep13/h16za/native32_1r_param.v'
 child_raw=child_path.read_bytes();ct=child_raw.decode()
 cp={n:(d,int(h),int(l)) for d,h,l,n in re.findall(r'^(input|output) wire \[(\d+):(\d+)\] (\w+);',ct,re.M)}
 child_instance=re.search(r'\bu_hr\((.*?)\);',text,re.S);assert child_instance
 pb=dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|$)',child_instance.group(1)))
 cw={n:(int(h),int(l)) for h,l,n in re.findall(r'wire\s+\[(\d+):(\d+)\]\s+(\\[^;\s]+)\s*;',ct)}
 def cbits(e):
  e=e.strip()
  if e.startswith('{'):return [b for term in e[1:-1].split(',') for b in cbits(term)]
  if e in cw:return [f'u_hr/{e}[{i}]'for i in range(cw[e][0],cw[e][1]-1,-1)]
  if e in cp:return [f'u_hr/{e}[{i}]'for i in range(cp[e][1],cp[e][2]-1,-1)]
  assert re.fullmatch(r'n_\d+|1\x27b[01]|\\[\w.$]+',e),repr(e)
  return [e if e.startswith("1'") else 'u_hr/'+e]
 for name,(direction,hi,lo)in cp.items():
  if name not in pb or not pb[name]:continue
  aa=cbits(name);bb=bits(pb[name]);assert len(aa)==len(bb),(name,len(aa),len(bb))
  for a,b in zip(aa,bb):
   if direction=='input':drive(a,[b],'assign')
   else:drive(b,[a],'assign')
 for lhs,rhs in re.findall(r'^assign (.*?) = (.*?);',ct,re.M):
  aa,bb=cbits(lhs),cbits(rhs);assert len(aa)==len(bb),(lhs,rhs,len(aa),len(bb))
  for a,b in zip(aa,bb):drive(a,[b],'assign')
 child_count=0
 for typ,name,body in re.findall(r'\b(qhs_\w+)\s*#\([^;]*?\)\s+(u_\w+)\s*\((.*?)\);',ct,re.S):
  pins=dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|$)',body));name='u_hr/'+name;child_count+=1
  if 'dff' in typ:
   q=cbits(pins['Q'])[0];drive(q,[],name);seq[q]=(cbits(pins['C'])[0],name,typ)
   for role in ['D','R']:
    if role in pins:
     for b in cbits(pins[role]):cons[b].append((name,role,cbits(pins['C'])[0]))
  else:
   assert 'Y' in pins,(typ,name,pins)
   for b in cbits(pins['Y']):drive(b,[i for k,e in pins.items()if k!='Y'for i in cbits(e)],name)
 assert child_count==25328,child_count
 # Actual top ROM/SRAM primitive ports carry their explicit clock and output.
 macro_count=0
 for typ,name,body in re.findall(r'^(ot_(?:rom|sram)_\w+)\s+(?:#\([^;]*?\)\s+)?(\\\S+)\s*\((.*?)\);',text,re.M):
  pins=dict(re.findall(r'\.(\w+)\((.*?)\)(?:,|$)',body));assert 'clk'in pins and 'rd_out'in pins,(typ,name,pins.keys());macro_count+=1
  for b in bits(pins['rd_out']):drive(b,[],name);seq[b]=(bits(pins['clk'])[0],name,'macro')
  for role,e in pins.items():
   if role not in ['clk','rd_out']:
    for b in bits(e):cons[b].append((name,role,bits(pins['clk'])[0]))
 # Follow alias-only clock paths to actual input pins; any derived clock refuses.
 def clock(n,seen=None):
  if n in ['ck_core[0]','ck_hr[0]']:return n.split('[')[0]
  seen=set()if seen is None else seen
  assert n not in seen,n;seen.add(n)
  assert driven.get(n)=='assign' and len(deps[n])==1,('unresolved clock',n,driven.get(n))
  return clock(deps[n][0],seen)
 memo={};visiting=set()
 def provenance(n):
  if n in memo:return memo[n]
  if n in seq:r={('FF',clock(seq[n][0]),seq[n][1])}
  elif n in ['n_0','n_1','u_hr/n_0','u_hr/n_1',"1'b0","1'b1"]:r={('CONST',n,'')}
  elif n not in driven:r={('INPUT' if n.split('[')[0] in ports else 'UNKNOWN',n,'')}
  else:
   assert n not in visiting,('comb cycle',n);visiting.add(n)
   r=set().union(*(provenance(p)for p in deps[n]));visiting.remove(n)
  memo[n]=r;return r
 out={}
 for name,(direction,hi,lo)in ports.items():
  if direction!='output':continue
  rows=[];domains=set();unknown=[]
  for b in bits(name):
   pp=provenance(b);ds=sorted({p[1] for p in pp if p[0]=='FF'});other=sorted(p for p in pp if p[0] not in ['FF','CONST']);domains.update(ds);unknown.extend(other)
   rows.append(dict(bit=b,clock_ports=ds,other_sources=other,producer_ff_count=sum(p[0]=='FF'for p in pp),producer_sample=sorted(p for p in pp if p[0]=='FF')[:8]))
  status='PROVEN' if len(domains)==1 and not unknown else 'MIXED' if len(domains)>1 else 'UNRESOLVED' if unknown else 'CONSTANT'
  row=dict(status=status,basis='Exact flat source assignments and combinational paths traced to first sequential producer; no timing, phase, crossing or availability inference.',clock_ports=sorted(domains),bits=rows)
  if status=='PROVEN':row['clock_port']=next(iter(domains))
  out[name]=row
 # Input captures: propagate through aliases/combinational logic to first FF D/reset. Stop at sequential boundaries.
 fan=collections.defaultdict(list)
 for dst,ss in deps.items():
  for src in ss:fan[src].append(dst)
 captures={}
 for name,(direction,hi,lo)in ports.items():
  if direction!='input' or name.startswith('ck_'):continue
  seen=set();todo=bits(name);found=set()
  while todo:
   n=todo.pop()
   if n in seen:continue
   seen.add(n);found.update(cons.get(n,[]));todo.extend(fan[n])
  ds=sorted({clock(x[2]) for x in found});captures[name]=dict(status='UNUSED' if not found else 'PROVEN' if len(ds)==1 else 'MIXED',clock_ports=ds,capture_count=len(found),capture_roles=dict(collections.Counter(x[1]for x in found)),sample=[dict(instance=a,pin=b,clock_port=clock(c))for a,b,c in sorted(found)[:12]])
 for name,row in captures.items():
  detail=dict(row,basis='Actual first sequential input captures, not downstream release, phase or availability authority.')
  if name=='rst_n':detail['status']='RESET_CONTRACT_REQUIRED'
  elif row['status']=='PROVEN':detail['clock_port']=row['clock_ports'][0]
  out[name]=detail
 return dict(master=re.search(r'module (\w+)',text).group(1),rtl=str(path.relative_to(root)),rtl_sha256=hashlib.sha256(raw).hexdigest(),ports=out,input_captures=captures,primitive_cells=cells,child_primitive_cells=child_count,macro_cells=macro_count,source_dependencies=[dict(rtl=str(child_path.relative_to(root)),sha256=hashlib.sha256(child_raw).hexdigest()),dict(rtl=str(publisher_path.relative_to(root)),sha256=hashlib.sha256(publisher_raw).hexdigest())])
rows=[audit(root/f'rtl/qwen_dv/headprep13/corepub39/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_{i}.sv')for i in [1,2]]
out=root/'results/arch/hp13_corepub39_1021/DATA_CLOCK_OWNERS.json';out.write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:
 print(row['master'],row['rtl_sha256'])
 for name,p in row['ports'].items():print(name,p['status'],p['clock_ports'])
 print('INPUTS',json.dumps({k:{z:v[z]for z in ['status','clock_ports','capture_count']}for k,v in row['input_captures'].items()}))
