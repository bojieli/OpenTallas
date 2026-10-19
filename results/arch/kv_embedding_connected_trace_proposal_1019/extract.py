import hashlib,json,subprocess
from pathlib import Path
W=Path('/home/ubuntu/wt/codex-kv-embedding-connected-trace-proposal-1019')
A=Path('/home/ubuntu/artifacts/kv-embedding-connected-trace-proposal-1019')
def git(r,p):return subprocess.check_output(['git','-C',str(W),'show',r+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
base='results/arch/kv_embedding_producer_contract_1019/'
prior=json.loads(git('af18be728',base+'MANIFEST.json'))
assert len(prior)==28
for r in prior:
 b=git('af18be728',base+r['path']);assert sha(b)==r['sha256'] and len(b)==r['bytes']
(A/'prior_manifest.json').write_text(json.dumps(dict(commit='af18be728',verified_payload_count=len(prior),payloads=prior),indent=2)+'\n')
files=['rtl/physical/ot_qwen_host_ctl.sv','rtl/qwen_sys/host_integrated_20261014/ot_host_if_pb2_observed.sv','rtl/qwen_sys/host_integrated_20261014/qkd_host_native_token_endpoint_cancel.sv','rtl/qwen_sys/split_20261014/qkd_host_root_admission.sv','rtl/qwen_sys/host_20261013/qkd_host_ctl_service_pins.sv','rtl/qwen_sys/host_20261013/qkd_host_rst_role_pins.sv','rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv','rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv','rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv','rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv','rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_children.sv','rtl/qwen_sys/split_20261014/qkd_host_pc_slice_die.sv','tools/qwen_kv_die/kv_die.py']
rows=[]
for p in files:
 b=git('5f2ce19bc',p);q=A/'source/5f2'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);rows.append(dict(path=p,sha256=sha(b),bytes=len(b)))
die=Path('/home/ubuntu/artifacts/d2d-boot-acceptance-1019/input/die.v.preexp').read_bytes();assert sha(die)=='00a3de7cd445198b147af744e5dd3c00f824a3222767b3fb4c8274392dd8b36e'
lines=[]
for n,l in enumerate(die.decode().splitlines(),1):
 if ('qkd_host_rt host (' in l or 'qkd_d2ds d2d_kv (' in l or 'qkd_kvs_ctl kvs_ctl (' in l or 'qkd_kvs_emb kvs_emb (' in l or 'qkd_kvs_pc_h kvpc_WS_0 (' in l or 'qkd_kvs_pc kvpc_WS_1 (' in l or 'n_hsvc' in l and ('qkd_rly' in l or 'assign' in l)):lines.append(f'{n}: {l}')
(A/'selected_edges.txt').write_text('\n'.join(lines)+'\n')
(A/'source_manifest.json').write_text(json.dumps(dict(revision='5f2ce19bc',die_preexp_sha256=sha(die),files=rows,scope='targeted source extraction; not compile inventory'),indent=2)+'\n')
print('Verified 28 prior payloads and selected preexp; extracted',len(rows),'targeted source files.')
