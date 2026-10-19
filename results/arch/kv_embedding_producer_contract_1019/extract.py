import hashlib,json,re,subprocess
from pathlib import Path
W=Path('/home/ubuntu/wt/codex-kv-embedding-producer-contract-1019'); A=Path('/home/ubuntu/artifacts/kv-embedding-producer-contract-1019')
def sha(b): return hashlib.sha256(b).hexdigest()
def git(rev,p): return subprocess.check_output(['git','-C',str(W),'show',rev+':'+p])
files=['rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv']
files += ['rtl/qwen_sys/static_embedding_20261014/'+s+'.sv' for s in ['qkd_embedding_row_tx','qkd_embedding_static_join','qkd_embedding_static_join4','qkd_embedding_static_join4_cal','qkd_embedding_static_pc','qkd_embedding_static_map','qkd_kv_pc_chain_station_b','qkd_static_kv_pc_es_merge_b','qkd_embgw_boot_s','qkd_embedding_static_return_head','qkd_embedding_static_return_hop']]
files += ['rtl/qwen_sys/d2d_static_20261015/'+s+'.sv' for s in ['ot_qwen_d2d_dies','ot_qwen_d2d_services']]
files += ['tools/qwen_kv_die/'+s+'.py' for s in ['kvjc3_pc_chain','kv_static','kv_static_die']]
files += ['tools/qwen_split/d2d_link_calendar.py']
records=[]
for p in files:
 b=(W/p).read_bytes(); d=A/'source/5f2'/p;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(b);records.append(dict(commit='5f2ce19bc',path=p,sha256=sha(b),bytes=len(b)))
def module(b,name):return re.search(rb'module '+name.encode()+rb'\b.*?endmodule',b,re.S).group()
sel=(W/files[0]).read_bytes(); old=git('c84feb9f9','rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k.sv')
ms=module(sel,'qkd_kvs_emb');mo=module(old,'qkd_kvs_emb')
(A/'selected_qkd_kvs_emb.sv').write_bytes(ms+b'\n');(A/'e1_qkd_kvs_emb.sv').write_bytes(mo+b'\n')
comparison=dict(selected_file=files[0],selected_file_sha256=sha(sel),selected_module_sha256=sha(ms),e1_source_commit='c84feb9f9',e1_file='rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k.sv',e1_file_sha256=sha(old),e1_module_sha256=sha(mo),module_bytes_identical=ms==mo)
for p in ['results/closure_loop/qkd_kvs_emb-e1-c84feb9f9/verdict.json','results/closure_loop/qkd_kvs_emb-e1-c84feb9f9/port_latency.json']:
 b=git('origin/main',p);(A/Path(p).name).write_bytes(b)
 v=json.loads(b)
 if p.endswith('verdict.json'):comparison['e1_record']=dict(job=v['job'],source_commit=v['source_commit'],metrics=v['metrics'])
(A/'module_comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
die=Path('/home/ubuntu/artifacts/d2d-boot-acceptance-1019/input/die.v.preexp').read_bytes()
assert sha(die)=='00a3de7cd445198b147af744e5dd3c00f824a3222767b3fb4c8274392dd8b36e'
lines=[]
for n,l in enumerate(die.decode().splitlines(),1):
 if ('qkd_kvs_emb kvs_emb ' in l or 'qkd_embgw embgw ' in l or ('qkd_rly_' in l and any(x in l for x in ['rly_ks_kvs_hroot_WS__o_emb_','rly_ks_kvs_hroot_WN__o_emb_','rly_ks_kvs_hroot_ES__o_emb_','rly_ks_kvs_hroot_EN__o_emb_','rly_ks_kvs_emb__rowtx','rly_ks_kvs_ctl__o_emb_']))):lines.append(f'{n}: {l}')
(A/'actual_connections.txt').write_text('\n'.join(lines)+'\n')
(A/'sources.json').write_text(json.dumps(dict(selected_commit='5f2ce19bc',die_preexp_sha256=sha(die),files=records),indent=2)+'\n')
print(json.dumps(comparison,indent=2))
