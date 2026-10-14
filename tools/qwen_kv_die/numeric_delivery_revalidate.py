#!/usr/bin/env python3
"""Re-execute exactly frozen compiled cases after classifier-only correction."""
import pathlib,json,hashlib,shlex,subprocess
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());records=[]
cases=[('repair',0,0,None),('raw_split_repair',0,1,None),('queue_word_mutant',4,0,'actual posted numeric word mismatch'),('queue_type_mutant',4,1,'actual delivery ledger startup or event fault'),('math_context_mutant',4,0,'actual every-math numeric context mismatch'),('startup_collision',5,0,'actual delivery ledger startup or event fault')]
for name,mut,allsp,expected in cases:
 src=out/('src_'+name)if name.endswith('mutant')else out/'src'
 # Each mutant SHA was recorded before its admitted compilation.
 mutant=json.loads((out/(name+'_provenance.json')).read_text())if name.endswith('mutant')else None
 for f,sha in m['sources'].items():
  actual=hashlib.sha256((src/f).read_bytes()).hexdigest()
  if mutant and f in ['rtl/physical/ot_qwen_numeric_output_queue.sv','rtl/physical/ot_qwen_tile_numeric_output_identity.sv'] and actual==mutant['sha256']:continue
  if actual!=sha:raise RuntimeError('source drift '+name+' '+f)
 obj=out/('obj_'+name);line=next(x for x in (obj/'Vtb_qwen_numeric_delivery_lifetime__verFiles.dat').read_text().splitlines()if x.startswith('C '));cmd=shlex.split(json.loads(line[2:]))
 if f'-GMUT={mut}'not in cmd or f'-GALL_SPLITS={allsp}'not in cmd or cmd[-len(m['sources']):]!=list(m['sources']):raise RuntimeError('compiled argument drift '+name)
 binary=obj/'Vtb_qwen_numeric_delivery_lifetime';r=subprocess.run([str(binary)],cwd=src,capture_output=True,text=True);(out/(name+'_revalidated.log')).write_text(r.stdout+r.stderr)
 if expected:
  if not r.returncode or expected not in r.stdout+r.stderr:raise RuntimeError(name+' escaped '+r.stdout+r.stderr)
  print('PASS observed '+name+': '+expected,flush=True)
 else:
  if r.returncode or 'PASS production acceptedIB and request ports'not in r.stdout:raise RuntimeError(r.stdout+r.stderr)
  print(r.stdout,flush=True)
 records.append({'case':name,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'exit':r.returncode,'expected_observed':expected,'compiled_command':cmd})
(out/'compiled_case_receipts.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS frozen numeric delivery lifetime six gates',flush=True)
