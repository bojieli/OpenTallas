#!/usr/bin/env python3
import pathlib,gzip,json,re
P=pathlib.Path(__file__).resolve().parent
A=P.parent/'s81_hb1_diagnostic_census_1019'
G=P/'generated01'
m=json.load(gzip.open(A/'receipt/mapped.json.gz'))['modules']['ot_s81sl_xr3'];cs=m['cells'];keys=list(cs); indices={n:i for i,n in enumerate(keys)}
model=json.load(gzip.open(P.parent/'s81_hb1_fixedpoint_model_1019/correspondence.json.gz'));copies={r['driver'].replace('\\',''):r['copies'] for r in model['rows']}
(G/'native_reference.sv').write_text(gzip.open(A/'receipt/normalized.v.gz','rt').read().replace('module ot_s81sl_xr3 (','module ot_s81sl_xr3_native_reference_1019 ('))
# Match exact normalized module header if whitespace differs.
p=G/'native_reference.sv';t=p.read_text();t=re.sub(r'\bmodule ot_s81sl_xr3\b','module ot_s81sl_xr3_native_reference_1019',t);p.write_text(t)
l=['`timescale 1ns/1ps','module tb_first_use #(parameter PATTERN=0);','reg clk=0; always #5 clk=~clk;','integer edge_count=0; integer differences=0;']
for n,p in m['ports'].items():
 if n=='clk':continue
 w=len(p['bits']);d=f'[{w-1}:0] ' if w>1 else ''
 if p['direction']=='input':l.append(f'reg {d}{n}=0;')
 else:
  for pre in ('a','n','c','d'):l.append(f'wire {d}{pre}_{n};')
for pre,mod,param in [('a','ot_s81sl_xr3_hb1_anchor_1019',''),('n','ot_s81sl_xr3_native_reference_1019',''),('c','ot_s81sl_xr3_hb1_graph_1019',''),('d','ot_s81sl_xr3_hb1_retained_1019','')]:
 ports=', '.join(f'.{n}({n if p["direction"]=="input" else pre+"_"+n})' for n,p in m['ports'].items())
 l.append(f'{mod} {pre} ({ports});')
# Initialize canonical source to zero and exact corresponding original QN=1.
# Added copies are independently alternating, not coupled to canonical QN.
l+=['initial begin']
ff=[(n,c) for n,c in cs.items() if c['type'].startswith('DFF')]
# Whole declared objects initialize otherwise optimized-away state too.
base=set(n.split('$_')[0].split('[')[0] for n,c in ff)
arrays={'u_ot_pr_core.u.ud':5,'u_ot_pr_core.u.ur':5,'u_ot_pr_core.u.ul':5,'u_ot_pr_core.u.un':5,'u_ot_pr_core.u.pq':5,'u_ot_pr_core.u.eqd':5}
def obj(b):
 if b=='u_ot_pr_core.u.bo':return 'u_ot_pr_core.u.g_bo.bo_r'
 if b=='u_ot_pr_core.u.u_rr.rst_n':return 'u_ot_pr_core.u.u_rr.relay_q[0]'
 return b
for b in sorted(base):
 for pre in ('a','d.identity.u'):
  if b in arrays:
   for j in range(arrays[b]):l.append(f'  {pre}.{obj(b)}[{j}] = 0;')
  else:l.append(f'  {pre}.{obj(b)} = 0;')
# Parameters seed only simulation UDP initial states, never implementation source.
params=[]
for n,c in ff:
 idx=indices[n]
 canonical=f"((PATTERN==0) ? 0 : {((idx*1103515245+12345)>>12)&1})"
 src=n.split('$_')[0]
 if src.startswith('u_ot_pr_core.u.bo['):src=src.replace('u_ot_pr_core.u.bo[','u_ot_pr_core.u.g_bo.bo_r[')
 if src.startswith('u_ot_pr_core.u.u_rr.rst_n['):src=src.replace('u_ot_pr_core.u.u_rr.rst_n[','u_ot_pr_core.u.u_rr.relay_q[0][')
 for pre in ('a','d.identity.u'):l.append(f'  {pre}.{src} = {canonical};')
 params.append(f'  defparam n.\\{n} .INIT = !{canonical};')
 params.append(f'  defparam c.u_{idx}_0.INIT = !{canonical};')
 for ci in range(1,copies.get(n,1)):
  params.append(f'  defparam c.u_{idx}_{ci}.INIT = (PATTERN==0) ? {ci%2} : {((idx*1664525+ci*1013904223)>>13)&1};')
l+=['  #0.2; compare();','end','task compare; begin']
for pn,p in m['ports'].items():
 if p['direction']!='output':continue
 l.append(f'if (a_{pn} !== n_{pn}) begin $display("ANCHOR_NATIVE_MISMATCH port={pn} edge=%0d A=%h N=%h", edge_count,a_{pn},n_{pn}); differences=differences+1; end')
 l.append(f'if (n_{pn} !== c_{pn}) begin $display("COPY_FIRSTUSE_MISMATCH port={pn} edge=%0d N=%h C=%h", edge_count,n_{pn},c_{pn}); differences=differences+1; end')
 l.append(f'if (a_{pn} !== d_{pn}) begin $display("DEFAULT_IDENTITY_MISMATCH port={pn} edge=%0d", edge_count); differences=differences+1; end')
l+=['if (differences) $fatal(1,"FIRSTUSE_COUNTEREXAMPLE differences=%0d",differences);','end endtask','always @(posedge clk) begin edge_count=edge_count+1; #0.2; compare(); if(edge_count==30) begin $display("FIRSTUSE_ALL_OUTPUT_PASS edges=%0d",edge_count);$finish;end end',
'initial begin #1; dl_ev=1; dl_e=0; dl_e[3:1]=4; dl_e[21]=1; dl_e[50+:2]=3; dl_e[52+:1024]={1024{1\'b1}}; #10; dl_ev=0; #29; rst_n=1; end','endmodule']
l[2:2]=params
(G/'tb_first_use.sv').write_text('\n'.join(l)+'\n')
print('Generated exact fullshape firstuse3way+default0; no simulation run')
