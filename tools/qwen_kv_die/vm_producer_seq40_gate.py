#!/usr/bin/env python3
"""Source-bound isolated lease gate; no native writer/physical adoption."""
import hashlib,json,pathlib,subprocess
r=pathlib.Path.cwd();src=r/'ot_qfd_vm_producer_lease_seq40.sv';tb=r/'tb_qfd_vm_producer_lease_seq40.sv'
receipt={'scope':'LEASE_COMPONENT_ONLY_NOT_NATIVE_WRITER_COMPOSITION','sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,tb]},'cases':[]}
for m in range(11):
 name='positive' if m==0 else 'mutant'+str(m)
 b=subprocess.run(['iverilog','-g2012','-s',tb.stem,'-P'+tb.stem+'.MUT='+str(m),'-o',name+'.vvp',str(src),str(tb)],capture_output=True,text=True)
 (r/(name+'.build.log')).write_text(b.stdout+b.stderr)
 if b.returncode:raise RuntimeError(b.stderr)
 x=subprocess.run(['vvp',name+'.vvp'],capture_output=True,text=True,timeout=30);o=x.stdout+x.stderr;(r/(name+'.log')).write_text(o)
 if (m==0 and (x.returncode or 'PASS lease' not in o)) or (m>0 and (x.returncode==0 or 'FAIL ' not in o)):raise RuntimeError(name+': '+o)
 receipt['cases'].append({'mutant':m,'exit':x.returncode,'observed':o.strip()});print('PASS '+name,flush=True)
(r/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
