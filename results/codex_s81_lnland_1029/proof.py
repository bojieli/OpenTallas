#!/usr/bin/env python3
"""Validate actual four-clock aliases, emit/run an exact full-width old-master vs one-entry miter."""
import argparse,hashlib,json,re,subprocess,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('parent',type=Path);p.add_argument('wrapper',type=Path);a=p.parse_args();b=a.run
parent=a.parent.read_text();aliases=[]
for i in range(4):
 name=f'u_u_lnl{i}';m=re.search(r'\bot_s81_mu72_lnland_nst\s*#\s*\(\s*\.MUT\(0\)\s*\)\s*'+name+r'\s*\((.*?)\);',parent,re.S)
 assert m,'Missing exact current landing instance '+name
 ports=dict(re.findall(r'\.(\w+)\s*\(\s*([^()]+?)\s*\)',m.group(1)));assert ports['ck_k']==ports['ck_n']=='clk',(name,ports)
 aliases.append(dict(inst=name,ck_k=ports['ck_k'],ck_n=ports['ck_n'],rs_k=ports['rs_k'],rs_n=ports['rs_n']))
(b/'actual_clock_aliases.json').write_text(json.dumps(dict(parent_sha256=hashlib.sha256(parent.encode()).hexdigest(),instances=aliases,added_cycles=0,new_clock_port='ck_k'),indent=1)+'\n')
(b/'wrapper.sv').write_bytes(a.wrapper.read_bytes())
inputs={'k_lo_v':1,'k_lo_d':553,'k_li_r':1,'k_rxv':1,'n_lo_r':1,'n_li_v':1,'n_li_d':553,'n_flt':3}
outputs={'k_lo_r':1,'k_li_v':1,'k_li_d':553,'k_flt':3,'n_lo_v':1,'n_lo_d':553,'n_li_r':1,'n_rxv':1}
L=['`timescale 1ns/1ps','module tb;','reg ck=0; always begin #0.416 ck=1; #0.417 ck=0; end','reg rs_k=0,rs_n=0;']
for n,w in inputs.items():L.append(f'reg [{w-1}:0] {n}=0;')
for label in ('g','d','m','r'):
 for n,w in outputs.items():L.append(f'wire [{w-1}:0] {label}_{n};')
def inst(mod,label,mut,wrong_reset=False):
 pr=['.ck_k(ck)']+(['.ck_n(ck)'] if label=='g' else [])
 pr+=['.rs_k('+('rs_n' if wrong_reset else 'rs_k')+')','.rs_n(rs_n)']
 pr += [f'.{n}({n})' for n in inputs];pr += [f'.{n}({label}_{n})' for n in outputs]
 return f'{mod} #(.MUT({mut})) u_{label} ('+', '.join(pr)+');'
L += [inst('ot_s81_mu72_lnland_nst','g',0),inst('ot_s81_mu72_lnland_nst_1ck','d',0),inst('ot_s81_mu72_lnland_nst_1ck','m',1),inst('ot_s81_mu72_lnland_nst_1ck','r',0,True)]
for label in ('g','d','m','r'):L.append(f'wire [1113:0] {label}_all = {{'+', '.join(label+'_'+n for n in outputs)+'};')
L += ['integer cycle,j; integer checks=0, mbad=0,rbad=0;','initial begin',' for(cycle=0;cycle<4096;cycle=cycle+1) begin','  @(negedge ck);',
      "  rs_k=(cycle>=16 && (cycle%211<202)); rs_n=(cycle>=20 && (cycle%197<187));"]
for n,w in inputs.items():
 if w==1:L.append(f"  {n}=1'($urandom);")
 else:L.append(f"  for(j=0;j<{w};j=j+1) {n}[j]=1'($urandom);")
L += ['  @(posedge ck); #0.01;','  if(cycle>=32) begin','   if(g_all !== d_all) $fatal(1,"LOCKSTEP_MISMATCH cycle=%0d",cycle);','   if(^g_all === 1\'bx) $fatal(1,"OBSERVED_UNKNOWN cycle=%0d",cycle);','   checks=checks+1114;','   if(g_all !== m_all) mbad=mbad+1;','   if(g_all !== r_all) rbad=rbad+1;','  end',' end',' if(mbad==0 || rbad==0) $fatal(1,"MUTANTS_NOT_CAUGHT %0d %0d",mbad,rbad);',
      ' $display("LN_ONECLK_PASS cycles=%0d checks=%0d latency_mutant=%0d reset_mutant=%0d",4096,checks,mbad,rbad); $finish;','end','endmodule']
(b/'miter.sv').write_text('\n'.join(L)+'\n');sources=[str(b/x.removeprefix('/out/')) for x in (b/'sources.f').read_text().splitlines()]
vl=Path.home()/'.local/opentallas-tools/bin/verilator'
version=subprocess.check_output([str(vl),'--version'],text=True).strip();assert '5.050' in version,version
cmd=[str(vl),'--binary','--timing','-Wno-fatal','-Werror-WIDTH','-Werror-SELRANGE','--top-module','tb','-j','4','--Mdir',str(b/'obj'),'-o','miter_sim','-DSYNTHESIS']+sources+[str(b/'wrapper.sv'),str(b/'miter.sv')]
r=subprocess.run(cmd,capture_output=True,text=True);(b/'build.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr[-4000:]
r=subprocess.run([str(b/'obj/miter_sim')],capture_output=True,text=True);(b/'miter.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr);assert r.returncode==0
