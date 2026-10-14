#!/usr/bin/env python3
"""Admitted isolated lifetime component gate; no production binding claim."""
import hashlib, json, pathlib, subprocess
root=pathlib.Path.cwd()
src=root/'ot_qwen_xdelivery_lifetime.sv'
tb=root/'tb_qwen_xdelivery_lifetime.sv'
original=src.read_text()
cases=[('positive',None,None,None),
 ('version_mutant','retire_version==version_q','1\'b1','late version ACK'),
 ('source_drain_mutant','source_output_drained && !fault','1\'b1 && !fault','release before source quiescence'),
 ('context_mutant','accept_context!=held_context','1\'b0','late context acceptance'),
 ('accepted_ib_mutant','accept_ib!=held_ib','1\'b0','offered IB substituted')]
receipt={'scope':'LIFETIME_COMPONENT_ONLY_NOT_ACTUAL_TILE_VM_COMPOSITION',
 'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (src,tb)},'cases':[]}
for name,old,new,expected in cases:
 text=original
 if old:
  assert text.count(old)==1,(name,text.count(old))
  text=text.replace(old,new)
 variant=root/(name+'.sv');variant.write_text(text)
 build=subprocess.run(['iverilog','-g2012','-s','tb_qwen_xdelivery_lifetime','-o',name+'.vvp',str(variant),str(tb)],capture_output=True,text=True)
 (root/(name+'.build.log')).write_text(build.stdout+build.stderr)
 if build.returncode:raise RuntimeError(build.stderr)
 run=subprocess.run(['vvp',name+'.vvp'],capture_output=True,text=True,timeout=30)
 output=run.stdout+run.stderr;(root/(name+'.log')).write_text(output)
 if expected:
  if run.returncode==0 or expected not in output:raise RuntimeError('mutant escaped: '+name+' '+output)
 else:
  if run.returncode or 'PASS lifetime:' not in output:raise RuntimeError(output)
 receipt['cases'].append({'case':name,'exit':run.returncode,'observed':output.strip(),
  'source_sha256':hashlib.sha256(variant.read_bytes()).hexdigest()})
 print(('PASS rejected ' if expected else 'PASS ')+name,flush=True)
(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
