#!/usr/bin/env python3
"""Collect exact compiled source/flags/binary and admitted execution logs; no rerun."""
import pathlib,json,hashlib,shlex,subprocess
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());records=[]
cases=[('repair',0,0,None),('full_stalls',0,1,None),('raw_split_repair',0,1,None),('queue_word_mutant',4,0,'actual posted numeric word mismatch'),('queue_type_mutant',4,1,'actual delivery ledger startup or event fault'),('math_context_mutant',4,0,'ESCAPED_IDENTITY_OFFSET'),('startup_collision',5,0,'actual delivery ledger startup or event fault')]
for name,mut,allsp,expected in cases:
 src=out/('src_'+name)if name.endswith('mutant')else out/'src'
 # Each mutant SHA was recorded before its admitted compilation.
 mutant=json.loads((out/(name+'_provenance.json')).read_text())if name.endswith('mutant')else None
 for f,sha in m['sources'].items():
  actual=hashlib.sha256((src/f).read_bytes()).hexdigest()
  if mutant and f in ['rtl/physical/ot_qwen_numeric_stream_queue.sv','rtl/physical/ot_qwen_tile_numeric_output_metadata.sv'] and actual==mutant['sha256']:continue
  if actual!=sha:raise RuntimeError('source drift '+name+' '+f)
 obj=out/('obj_'+name);line=next(x for x in (obj/'Vtb_qwen_numeric_stream_lifetime__verFiles.dat').read_text().splitlines()if x.startswith('C '));cmd=shlex.split(json.loads(line[2:]))
 if f'-GFULL_STALLS={int(name=="full_stalls")}'not in cmd or f'-GMUT={mut}'not in cmd or f'-GALL_SPLITS={allsp}'not in cmd or cmd[-len(m['sources']):]!=list(m['sources']):raise RuntimeError('compiled argument drift '+name)
 binary=obj/'Vtb_qwen_numeric_stream_lifetime';log=(out/(name+'.log')).read_text()
 if expected=='ESCAPED_IDENTITY_OFFSET':
  if '%Fatal:'in log or 'PASS production acceptedIB and request ports'not in log:raise RuntimeError('escaped diagnostic changed '+log)
  print('DIAGNOSTIC identity-only offset unobserved under constant operation identity/drain-before-next-accept',flush=True)
 elif expected:
  if expected not in log or '%Fatal:'not in log:raise RuntimeError(name+' escaped '+log)
  print('PASS observed '+name+': '+expected,flush=True)
 else:
  if '%Fatal:'in log or 'PASS production acceptedIB and request ports'not in log:raise RuntimeError(log)
  print(log,flush=True)
 records.append({'case':name,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'expected_exit_nonzero':bool(expected and expected!='ESCAPED_IDENTITY_OFFSET'), 'raw_execution_log_sha256':hashlib.sha256(log.encode()).hexdigest(),'expected_observed':expected,'qualification_case':expected!='ESCAPED_IDENTITY_OFFSET','compiled_command':cmd})
(out/'compiled_case_receipts.json').write_text(json.dumps(records,indent=2)+'\n');print('COLLECT frozen streaming cases with explicit escaped diagnostic',flush=True)
