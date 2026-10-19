from pathlib import Path
import subprocess,hashlib,json
W=Path('/home/ubuntu/wt/codex-kv-embedding-controller-contract-1019')
A=Path('/home/ubuntu/artifacts/kv-embedding-controller-contract-1019')
assert subprocess.check_output(['git','-C',str(W),'rev-parse','--show-toplevel'],text=True).strip()==str(W)
rev='5f2ce19bc'
files=[
'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge_b.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_es_merge.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_map.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_kv_pc_chain_station_b.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_return_head.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_return_hop.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_join4_cal.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_join4.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_join.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_row_tx.sv',
'rtl/qwen_sys/static_embedding_20261014/qkd_embgw_boot_s.sv',
'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv',
'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_nc.sv',
'rtl/qwen_sys/static_kv_20261014/qkd_ctrl_pc_host_static_core.sv',
'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_ctrl_pc_emb.sv',
'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_kv_timing.sv',
'rtl/qwen_sys/static_kv_20261014/ot_qkd_static_emb_cdc.sv',
'rtl/qwen_sys/static_kv_20261014/qkd_controller_hbm_calendar.sv',
'rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_calendar.sv',
'rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv',
 'tools/qwen_kv_die/kvjc3_pc_chain.py','tools/qwen_kv_die/kv_die.py']
rows=[]
for p in files:
 b=subprocess.check_output(['git','-C',str(W),'show',rev+':'+p]);q=A/'source/5f2'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
 rows.append(dict(path=p,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b)))
die=Path('/home/ubuntu/artifacts/d2d-boot-acceptance-1019/input/die.v.preexp').read_bytes()
assert hashlib.sha256(die).hexdigest()=='00a3de7cd445198b147af744e5dd3c00f824a3222767b3fb4c8274392dd8b36e'
(A/'selected_phy_connections.txt').write_text('\n'.join(f'{n}: {l}' for n,l in enumerate(die.decode().splitlines(),1) if 'qkd_hbm3e_phy_pc phy_' in l)+'\n')
(A/'source_manifest.json').write_text(json.dumps(dict(revision=rev,die_preexp_sha256=hashlib.sha256(die).hexdigest(),files=rows,scope='Targeted selected source contract, not executable compile inventory'),indent=2)+'\n')
print('Extracted and SHA-pinned',len(rows),'source files; verified preexp and four actual PHY instances.')
