#!/usr/bin/env python3
"""All-input unsigned32 modulo equivalence of the exact HOST carry function."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
src=Path('rtl/hdc/ingest/ot_hdc_kv_ingest.sv');text=src.read_text();m=re.search(r'    function automatic \[31:0\] host_addr_add32_prefix;.*?    endfunction',text,re.S);assert m
fn=m[0]
# Prove the exact source function over all 2^64 input pairs, including overflow.
# Default aliases retain their original AW-sized assignment context; AW>32
# deliberately keeps legacy operators even when HOST opt-in is selected.
aliases={}
for mode,pattern in [('selected',r'    wire \[AW-1:0\] host_rows_addr=.*?`else'),('default',r'`else\n    wire \[AW-1:0\] host_rows_addr=.*?`endif')]:
 part=re.search(pattern,text,re.S);assert part
 aliases[mode]='\n'.join(x for x in part[0].splitlines()if 'wire [AW-1:0] host_'in x)
base='module proof(input[31:0]a,b,input[4:0]sec,input[2:0]ph,output ok);\nFN\nwire[31:0]fast=host_addr_add32_prefix(a,b);\nwire[31:0]refsum=a+b;\n'
checks=['fast==refsum']
for width in [31,32,33,64]:
 base+=f"wire[{width-1}:0]ref{width}r=a+sec,ref{width}k=a+ph,ref{width}s=a+(ph==4?1:0);\n"
 for mode,alias in aliases.items():
  atext=alias.replace('AW',str(width)).replace('u_raddr','a').replace('u_kcode','a').replace('u_kscal','a').replace('st_sec','sec').replace('st_ph','ph')
  for name,short in [('rows','r'),('key','k'),('scale','s')]:atext=atext.replace('host_'+name+'_addr',mode+str(width)+short)
  base+=atext+'\n'
  checks.append('{' + ','.join(mode+str(width)+x for x in 'rks') + '}=={' + ','.join('ref'+str(width)+x for x in 'rks')+'}')
base+='assign ok='+ '&&'.join('('+x+')'for x in checks)+';\nendmodule\n'

cases=[]
for mutant in [False,True]:
 name='wrong_carry'if mutant else'exact';f=a.out/(name+'.sv');body=fn
 if mutant:
  needle='g3[i]=g2[i]|(p2[i]&g2[i-4])';assert body.count(needle)==1;body=body.replace(needle,'g3[i]=g2[i]')
 f.write_text(base.replace('FN',body));log=a.out/(name+'.log')
 cmd=['yosys','-Q','-T','-p',f'read_verilog -sv {f}; prep -top proof; flatten; opt; sat -verify -prove ok 1 -show a,b -timeout 120']
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=180);log.write_text(r.stdout+r.stderr)
 marker='SUCCESS'if not mutant else'proof did fail'
 if ((r.returncode==0)==mutant)or marker not in log.read_text():raise SystemExit('HOST_ADDR_SAT unexpected '+name+' '+log.read_text()[-1000:])
 if mutant:
  witness_cmd=cmd[:-1]+[cmd[-1].replace('sat -verify -prove','sat -prove')]
  witness=subprocess.run(witness_cmd,capture_output=True,text=True,timeout=180)
  (a.out/'wrong_carry_witness.log').write_text(witness.stdout+witness.stderr)
  if witness.returncode or 'FAIL'not in witness.stdout:raise SystemExit('SAT mutant witness missing')
 cases.append(dict(case=name,exit=r.returncode,log=str(log)));print(name,marker,flush=True)
record=dict(scope=__doc__,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),yosys_version=subprocess.check_output(['yosys','-V'],text=True).strip(),source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),function_sha256=hashlib.sha256(fn.encode()).hexdigest(),selected_define='OT_S81_HOST_ADDR_PREFIX',default='off; other vehicles/closed views unchanged',width_semantics='unsigned32 modulo2^32, AW31 truncates, AW>32 stream expressions retain original wider evaluation',added_FF=0,added_cycles=0,cases=cases,physical_qualification='OPEN: actual mapped depth/area/route required')
(a.out/'record.json').write_text(json.dumps(record,indent=1)+'\n');print('HOST_ADDR_PREFIX_SAT PASS all64inputbits +wrongcarrymutantFAIL')
