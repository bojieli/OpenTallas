#!/usr/bin/env python3
"""All-value R7 context proof; actual geographic VM bank integration is separate."""
import argparse,pathlib,subprocess,tempfile,json
p=argparse.ArgumentParser();p.add_argument('--rtl',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parent;src=pathlib.Path(a.rtl).read_text();results={}
variants={'baseline':src,'wrong_north_qid':src.replace('p[15]?p[14:13]:strap_vm_qid',"p[15]?p[14:13]:2'd2"),'rewrite_mirror':src.replace('p[15]?p[14:13]:strap_vm_qid','strap_vm_qid')}
with tempfile.TemporaryDirectory() as d:
 d=pathlib.Path(d)
 for name,body in variants.items():
  f=d/(name+'.sv');f.write_text(body);exe=d/name
  subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(f),str(root/'tb_vm_rq_context.sv')],check=True)
  r=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
  (root/('vm_rq_context_'+name+'.log')).write_text(r.stdout+r.stderr)
  ok=r.returncode==0
  if ok!=(name=='baseline'):raise SystemExit('unexpected outcome '+name)
  results[name]={'returncode':r.returncode,'expected':'PASS' if name=='baseline' else 'CONTROL_CAUGHT'}
(root/'vm_rq_context_receipt.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
