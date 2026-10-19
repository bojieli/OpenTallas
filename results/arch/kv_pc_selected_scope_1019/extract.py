import re, json, hashlib, subprocess, sys
from pathlib import Path
wt=Path(sys.argv[1]); die=Path(sys.argv[2]); out=Path(sys.argv[3])
sha=lambda b:hashlib.sha256(b).hexdigest()
s=die.read_text()
assert sha(die.read_bytes())=='00a3de7cd445198b147af744e5dd3c00f824a3222767b3fb4c8274392dd8b36e'
def pins(body):
    pairs=re.findall(r'\.(\w+)\(([^()]*)\)',body)
    assert len(dict(pairs))==len(pairs)
    return dict(pairs)
pcs=[];phys={}
for m in re.finditer(r'^\s*(qkd_kvs_pc(?:_h)?|qkd_hbm3e_phy_pc)\s+(\w+)\s*\((.*?)\);',s,re.M|re.S):
    typ,name,body=m.groups(); ps=pins(body)
    if typ=='qkd_hbm3e_phy_pc':phys[name]=ps
    else:pcs.append({'master':typ,'instance':name,'pins':ps})
assert len(pcs)==128 and sum(x['master']=='qkd_kvs_pc_h' for x in pcs)==4
assert len(phys)==4
for pc in pcs:
    _,region,index=pc['instance'].split('_'); ph=phys['phy_'+region]; pp=pc['pins']
    assert pp['pc__front_hbm_data']==ph['fh'+index]
    assert pp['pc__return_hbm_data']==ph['rh'+index]
    assert pp['hck']==ph['clk']
    pc['storage_clock_producer']={'instance':'phy_'+region,'master':'qkd_hbm3e_phy_pc','front_port':'fh'+index,'return_port':'rh'+index,'clock':ph['clk'],'reset':ph['rst_n']}
paths=['rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv','rtl/qwen_sys/static_kv_20261014/qkd_static_kv_pc_path_nc.sv','rtl/qwen_sys/static_embedding_20261014/qkd_static_kv_pc_path_fan_nc_b.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v']
records=[]
for path in paths:
    b=subprocess.check_output(['git','-C',str(wt),'show','HEAD:'+path]);records.append({'path':path,'sha256':sha(b),'git_blob':subprocess.check_output(['git','-C',str(wt),'rev-parse','HEAD:'+path],text=True).strip()})
old=json.loads(Path('/home/ubuntu/artifacts/kv-pc-fault-export-1019/component_source_identity.json').read_text())
for record in records:
    match=[r for r in old['records'] if r['path']==record['path']]
    if match:assert record['sha256']==match[0]['selected_sha256']
result={'status':'WAITS_PHY_CLOCK_COLLISION_LIFETIME_CONTRACT','source_commit':'5f2ce19bc','generated_die_sha256':sha(die.read_bytes()),'stage':'pre-expansion only; no native receipt','source_records':records,'pcs':pcs,'phy':phys,'checks':{'pc_count':128,'pc_h_count':4,'phy_count':4,'front_return_hck_phy_connections_checked':128,'all_bound_storage_clock_phase_known':False,'native_selected_census_available':False,'successor_latency_edges':None}}
out.write_text(json.dumps(result,indent=2)+'\n')
print('PASS: 128 PC clock/reset/PHY bindings; 124 PC + 4 PC_H; exact source hashes. Phase/native readiness remains OPEN.')
