#!/usr/bin/env python3
import re,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent; R=D.parents[2]
def modules(t): return dict(re.findall(r'(?ms)^\s*module\s+(\w+)\b(.*?^\s*endmodule\b)',t))
def strip(t): return re.sub(r'//[^\n]*|/\*.*?\*/','',t,flags=re.S)
orig=modules((D/'selected.sv').read_text()); priv=modules((D/'private.sv').read_text())
idx={}
for p in list((R/'rtl/qwen_sys').rglob('*.sv'))+list((R/'rtl/lib').rglob('*.sv')):
 if '/test/' in str(p): continue
 for n,b in modules(p.read_text(errors='replace')).items(): idx.setdefault(n,[]).append((p,'module '+n+b))
root={n:'module '+n+orig[n] for n in ['qkd_kvs_grp','qkd_kvs_grp_h']}
closure={}; todo=list(root.values())
while todo:
 text=todo.pop()
 for n in set(re.findall(r'(?m)^\s*(\w+)\s+(?:#\s*\(.*?\)\s*)?\w+\s*\(',strip(text),re.S)):
  if n in closure or n in ['module','if','for','case','always','begin','assign']: continue
  if n.startswith('ot_sram_'):
   p=R/f'physical/asap7_memory_macros_v2/{n}/{n}.v'; candidates=[(p,p.read_text())]
  else: candidates=idx.get(n,[])
  if not candidates: continue
  exact=[v for v in candidates if v[0].stem==n]
  candidates=exact or candidates
  if len(candidates)!=1: raise RuntimeError((n,[str(v[0]) for v in candidates]))
  p,b=candidates[0]; closure[n]=(str(p.relative_to(R)),hashlib.sha256(b.encode()).hexdigest(),b); todo.append(b)
(D/'leaves.sv').write_text('`timescale 1ns/1ps\n'+'\n'.join(v[2] for v in closure.values()))
(D/'original.sv').write_text('`timescale 1ns/1ps\n'+'\n'.join(root.values()))
(D/'closure.json').write_text(json.dumps({n:dict(path=v[0],sha256=v[1]) for n,v in closure.items()},indent=2)+'\n')
# Two actual components and one private mutant wrapper per run: plusargs change live retained output comparisons.
L=['`timescale 1ns/1ps','module tb;','reg ck=0,hck=0; always #5 ck=~ck; always #7 hck=~hck;','integer edge_i,checks=0,mut=0; integer seed=173;']
for kind in ['grp','grp_h']:
 on='qkd_kvs_'+kind; pn=on.replace(kind,kind+'_private0'); ob=orig[on]; pb=priv[pn]
 def ports(b): return [(d,int(hi or 0)+1,n) for d,hi,n in re.findall(r'(input|output) wire\s*(?:\[(\d+):0\]\s*)?(\w+)',b.split(');',1)[0])]
 po,pp=ports(ob),ports(pb); pd={n:(d,w) for d,w,n in pp}
 for d,w,n in po:
  if n in ['ck','hck']: continue
  L.append(f'{"reg" if d=="input" else "wire"} [{w-1}:0] {kind}_{n}{"=0" if d=="input" else ""};')
 for d,w,n in pp:
  if d=='output': L.append(f'wire [{w-1}:0] n_{kind}_{n};')
 def conns(private):
  out=[]
  for d,w,n in (pp if private else po):
   expr=n if n in ['ck','hck'] else ((f'n_{kind}_'+n) if private and d=='output' else f'{kind}_{n}')
   if private and d=='input' and pd[n][1]!=dict((n,w) for d,w,n in po)[n]: expr+=f'[{w-1}:0]'
   out.append(f'.{n}({expr})')
  return ','.join(out)
 L+= [f'{on} old_{kind}({conns(False)});',f'{pn} new_{kind}({conns(True)});']
L+=['initial begin','if (!$value$plusargs("mut=%d",mut)) mut=0;','for(edge_i=0;edge_i<2048;edge_i=edge_i+1) begin','@(negedge ck);']
for kind in ['grp','grp_h']:
 po=[(d,int(hi or 0)+1,n) for d,hi,n in re.findall(r'(input|output) wire\s*(?:\[(\d+):0\]\s*)?(\w+)',orig['qkd_kvs_'+kind].split(');',1)[0])]
 for d,w,n in po:
  if d!='input' or n in ['ck','hck']: continue
  if n in ['rst_n','hrst_n']: ex='!(edge_i<8 || (edge_i>=900 && edge_i<909) || (edge_i>=1400 && edge_i<1408))'
  else: ex='{'+','.join('$random(seed)' for _ in range((w+31)//32))+'}'
  L.append(f'{kind}_{n} = {ex};')
 # Fully random traffic tests exactness including invalid faults; deterministic directed EST and down/up cohorts ensure witnesses.
 L.append(f'{kind}_x__est[0] = edge_i[0];')
L+=['@(posedge ck); #1;']
for ki,kind in enumerate(['grp','grp_h']):
 for d,w,n in [(d,int(hi or 0)+1,n) for d,hi,n in re.findall(r'(input|output) wire\s*(?:\[(\d+):0\]\s*)?(\w+)',priv['qkd_kvs_'+kind+'_private0'].split(');',1)[0])]:
  if d!='output': continue
  ex=f'n_{kind}_{n}'




  L.append(f'checks=checks+1; if ({kind}_{n} !== {ex}) begin $display("PRIVATE_FAIL kind={kind} output={n} edge=%0d mut=%0d",edge_i,mut); $fatal(1); end')
L+=['end','$display("PRIVATE_PASS checks=%0d edges=2048 mut=%0d",checks,mut); $finish; end','endmodule']
(D/'tb.sv').write_text('\n'.join(L)+'\n')
print('Prepared',len(closure),'real leaf modules')
