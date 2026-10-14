#!/usr/bin/env python3
"""Source-bound negative wiring probe: posting is not downstream consumption."""
import pathlib,json,hashlib,subprocess,os,shutil
out=pathlib.Path.cwd();m=json.loads((out/'provenance.json').read_text());src=out/'src_post_retire_mutant';shutil.copytree(out/'src',src,dirs_exist_ok=True)
f=src/'rtl/test/qwen_kv_die/tb_qwen_numeric_stream_lifetime.sv';s=f.read_text();changes={
 'output_queue_v&&sink_ready&&output_queue_has_query':'output_queue.pending_post&&numeric_has_query',
 'retire_sequences[40*li+:40]=output_queue_tag[39:0]':'retire_sequences[40*li+:40]=numeric_query_seq',
 'retire_contexts[16*li+:16]=output_queue_tag[87:72]':'retire_contexts[16*li+:16]=numeric_identity[47:32]',
 'retire_versions[32*li+:32]=output_queue_tag[71:40]':'retire_versions[32*li+:32]=numeric_identity[31:0]',
 '#1;if(ledger_fault)':'#1;if(retired_total>typed_consumed)$fatal(1,"actual posting retired before numeric acceptance");if(ledger_fault)'}
for before,after in changes.items():
 if s.count(before)!=1:raise RuntimeError('nonunique premature-retire mutation '+before)
 s=s.replace(before,after)
f.write_text(s);receipt={'mutated_fixture_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'changes':changes,'production_sources_unchanged':True}
obj=out/'obj_post_retire_mutant';vlt=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator');cmd=[vlt,'--binary','--timing','-j','2','-Wno-fatal','-Wno-lint','--top-module','tb_qwen_numeric_stream_lifetime','--Mdir',str(obj),'-GMUT=4','-GALL_SPLITS=0','-GFULL_STALLS=0','-DXCACHE_TP8']+list(m['sources']);receipt['compiled_command']=cmd
with(out/'post_retire_mutant_build.log').open('w')as log:subprocess.run(cmd,cwd=src,stdout=log,stderr=subprocess.STDOUT,check=True)
binary=obj/'Vtb_qwen_numeric_stream_lifetime';r=subprocess.run([str(binary)],cwd=src,capture_output=True,text=True);text=r.stdout+r.stderr;(out/'post_retire_mutant.log').write_text(text);receipt.update(exit=r.returncode,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest());(out/'post_retire_mutant_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if not r.returncode or 'actual posting retired before numeric acceptance'not in text:raise RuntimeError('premature retirement escaped '+text)
print('PASS source-bound actual premature-post retirement refused: '+text,flush=True)
