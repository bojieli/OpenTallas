#!/usr/bin/env python3
"""Admitted isolated lifetime component gate; no production binding claim."""
import hashlib, json, pathlib, subprocess
root=pathlib.Path.cwd()
src=root/'ot_qwen_xdelivery_lifetime.sv'
tb=root/'tb_qwen_xdelivery_lifetime.sv'
original=src.read_text()
cases=[('positive',None,None,None),
 ('begin_overlap_mutant','if(issue_v || retire_v || seal_v) fault<=1; // BEGIN_EVENT_FENCE_SCALAR','if(1\'b0) fault<=1; // BEGIN_EVENT_FENCE_SCALAR','scalar begin overlap silently dropped event'),
 ('vector_begin_overlap_mutant','if((|issue_v) || (|retire_v) || (|seal_v)) control_fault<=1; // BEGIN_EVENT_FENCE_VECTOR','if(1\'b0) control_fault<=1; // BEGIN_EVENT_FENCE_VECTOR','vector begin overlap silently dropped event'),
 ('version_mutant','retire_version==version_q','1\'b1','late version ACK'),
 ('source_drain_mutant','source_output_drained && !fault','1\'b1 && !fault','release before source quiescence'),
 ('context_mutant','accept_context!=held_context','1\'b0','late context acceptance'),
 ('accepted_ib_mutant','accept_ib!=held_ib','1\'b0','offered IB substituted'),
 ('wrap_fence_mutant','state<=WRAP_FENCE','state<=IDLE','context wrap reopened'),
 ('pending_retire_mutant','outstanding[j]!=0','1\'b0','seal waived outstanding'),
 ('vector_positive',None,None,None),
 ('vector_version_mutant','retire_version[g*32+:32]==version_q','1\'b1','one stale version escaped'),
 ('vector_capacity_mutant','assign issue_ready[g]=issue_match','assign issue_ready[g]=(g==0) && issue_match','parallel48 issue capacity lost'),
 ('vector_seq_highbit_mutant','VECTOR_SEQ_TRUNCATION',None,'query sequence high bit truncated'),
 ('vector_outstanding_capacity_mutant','parameter integer ENABLE=0, N=48, SEQ_W=40, COUNT_W=7\n','parameter integer ENABLE=0, N=48, SEQ_W=40, COUNT_W=4\n','49-stage outstanding capacity lost')]
receipt={'scope':'LIFETIME_COMPONENT_ONLY_NOT_ACTUAL_TILE_VM_COMPOSITION',
 'sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (src,tb,root/'tb_qwen_xdelivery_vector.sv')},'cases':[]}
for name,old,new,expected in cases:
 text=original
 if old=='VECTOR_SEQ_TRUNCATION':
  for op in ['==','!=']:
   a='issue_seq[g*SEQ_W+:SEQ_W]'+op+'issued'
   b='issue_seq[g*SEQ_W+:32]'+op+'issued[31:0]'
   assert text.count(a)==1
   text=text.replace(a,b)
 elif old:
  assert text.count(old)==1,(name,text.count(old))
  text=text.replace(old,new)
 variant=root/(name+'.sv');variant.write_text(text)
 case_tb=root/'tb_qwen_xdelivery_vector.sv' if name.startswith('vector') else tb
 top=case_tb.stem
 build=subprocess.run(['iverilog','-g2012','-s',top,'-o',name+'.vvp',str(variant),str(case_tb)],capture_output=True,text=True)
 (root/(name+'.build.log')).write_text(build.stdout+build.stderr)
 if build.returncode:raise RuntimeError(build.stderr)
 run=subprocess.run(['vvp',name+'.vvp'],capture_output=True,text=True,timeout=30)
 output=run.stdout+run.stderr;(root/(name+'.log')).write_text(output)
 if expected:
  if run.returncode==0 or expected not in output:raise RuntimeError('mutant escaped: '+name+' '+output)
 else:
  if run.returncode or 'PASS ' not in output:raise RuntimeError(output)
 receipt['cases'].append({'case':name,'exit':run.returncode,'observed':output.strip(),
  'source_sha256':hashlib.sha256(variant.read_bytes()).hexdigest()})
 print(('PASS rejected ' if expected else 'PASS ')+name,flush=True)
(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
