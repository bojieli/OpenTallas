from pathlib import Path
import ast,subprocess,json,hashlib
ROOT=Path(__file__).parent;r=ROOT/'runtime';r.mkdir(exist_ok=True);p=ROOT/'reviewed_patch_entry.py';src=p.read_text();tree=ast.parse(src);wrapper=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='wrapper' for x in n.targets))
# Only harness-specific paths and native final exit replaced for observing Tcl completion.
wrapper=wrapper.replace('/work/',str(r)+'/').replace('exit 0','set ::review_reached_explicit_success 1')
results=[]
for name,body,end in [('typed_checkpoint','return -code error -errorcode {PC_GEO80 CHECKPOINT_READY} stop','return clean'),('generic_error','error generic','return clean'),('normal_early_return','return','return clean'),('cleanup_failure','return -code error -errorcode {PC_GEO80 CHECKPOINT_READY} stop','error cleanup_failed'),('nonlocal_early_return','return -code return escaped','return clean'),('cleanup_nonlocal_return','return -code error -errorcode {PC_GEO80 CHECKPOINT_READY} stop','return -code return cleanup_escaped'),('body_break','break','return clean')]:
 (r/'native_pg_entry_body.tcl').write_text(body+'\n');(r/'native_pg_binding.tcl').write_text('proc ot_pg_native_birth_begin args {set ::active 1}\nproc ot_pg_native_birth_end {} {set ::active 0;'+end+'}\nproc ot_native_pg_status {} {return [dict create active $::active]}\n')
 for f in ('repair_checkpoint.odb','repair_checkpoint.def','repair_checkpoint.v','REPAIR_CHECKPOINT'):(r/f).write_text('mock\n')
 (r/'wrapper.tcl').write_text(wrapper)
 harness='set ::env(OT_PG_STRICT) 1\nset ::review_reached_explicit_success 0\nset code [catch {source {'+str(r/'wrapper.tcl')+'}} result options]\nputs [list REVIEW $code $result $::review_reached_explicit_success $::active]\n'
 out=subprocess.run(['tclsh'],input=harness,text=True,capture_output=True)
 results.append(dict(case=name,output=out.stdout,stderr=out.stderr,process_exit=out.returncode))
(r/'CONTROLFLOW_RESULTS.json').write_text(json.dumps(dict(scope='Tcl controlflow mocks only; no nativePG qualification',reviewed_patch_sha256=hashlib.sha256(src.encode()).hexdigest(),cases=results),indent=2)+'\n')
for x in results:
 line=x['output'].splitlines()[-1]
 assert x['process_exit']==0
 if x['case']=='typed_checkpoint': assert line=='REVIEW 0 1 1 0',x
 else: assert line.startswith('REVIEW 1 ') and line.endswith(' 0 0'),x
 print(x['case'],line)
