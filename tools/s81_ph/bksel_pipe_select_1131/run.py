#!/usr/bin/env python3
import argparse, hashlib, json, re, subprocess, time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
r=Path(__file__).resolve().parent;out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
mod=re.compile(r'module ot_s81ph_sel_su_pipe\b.*?\bendmodule',re.S)
parts=[]
for name in ['original','r1','r2']:
 text=(r/'source'/f'{name}.sv').read_text();m=mod.search(text);assert m
 parts.append(m.group().replace('module ot_s81ph_sel_su_pipe','module su_'+name,1))
orig_r2=parts[-1];start=orig_r2.index('// BEGIN registered selector');end=orig_r2.index('// END registered selector')
mutant=orig_r2[:start]+orig_r2[start:end].replace('geb_nx','geb')+orig_r2[end:]
mutant=mutant.replace('module su_r2','module su_mutant',1);parts.append(mutant)
(out/'su_miter.sv').write_text('`timescale 1ps/1fs\n'+'\n'.join(parts)+'\n')
results=[];t=time.time()
for qw in [11,21]:
 exe=out/f'tb_qw{qw}.vvp';cl=out/f'compile_qw{qw}.log';lg=out/f'run_qw{qw}.log'
 with cl.open('w') as f:subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.QW={qw}','-Ptb.XR=6','-o',str(exe),str(r/'source/ot_hdc_prefix.sv'),str(out/'su_miter.sv'),str(r/'tb.sv')],check=True,stdout=f,stderr=subprocess.STDOUT)
 with lg.open('w') as f:proc=subprocess.run(['vvp',str(exe)],stdout=f,stderr=subprocess.STDOUT)
 log=lg.read_text();print(log,flush=True)
 m=re.search(r'RESULT QW=(\d+) XR=(\d+) edges=(\d+) checks=(\d+) errors=(\d+) mutant_errors=(\d+) buckets=(\w+) no_qualify=(\d+)',log)
 result=dict(qw=qw,xr=6,exit=proc.returncode,pass_gate=proc.returncode==0 and 'BKSEL_PIPE_LOCKSTEP_PASS' in log)
 if m:result.update(zip(['qw','xr','edges','checks','errors','mutant_errors','buckets','no_qualify'],[int(v) if i!=6 else v for i,v in enumerate(m.groups())]))
 results.append(result)
record=dict(schema='opentallas.s81.bksel_pipe_select.lockstep.v1',status='PASS' if all(x['pass_gate'] for x in results) else 'FAIL',module='ot_s81ph_sel_su_pipe',Q=4,CB=11,XR=6,QW=[11,21],clock_ps=833,scope='Actual production pipeline search module only; exact every output each edge, changing interface inputs; no whole-selector or physical adoption claim',results=results,mutant='R2 selector registers driven by stale geb instead of same-edge geb_nx; no other changes',source_sha256={str(x.relative_to(r)):hashlib.sha256(x.read_bytes()).hexdigest() for x in list((r/'source').glob('*.sv'))+[r/'tb.sv',r/'run.py']},seconds=round(time.time()-t,3),adopted=False)
(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');raise SystemExit(0 if record['status']=='PASS' else 1)
