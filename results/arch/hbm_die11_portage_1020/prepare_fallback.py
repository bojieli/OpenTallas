"""Exact accepted h9c fallback proposal; does not grant die/model eligibility."""
import copy,hashlib,json,sys
from pathlib import Path
root=Path.cwd()
p=Path('/srv/opentallas-scratch/claude/hbm-die10-1020/planA/a/views/contract.json')
c=json.loads(p.read_text());before=copy.deepcopy(c)
old='ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face';new='ot_hbm_svc_pc_ctrl_leaf_cfg_h9b';sn='rtl/hbm_accel/loader/service_native/'
params=dict(OREG=1,KREG=1,KRREG=1,RREG=1,WPAY=1,QREG=1)
srcs=['rtl/lib/ot_rst_relay.sv',sn+'ot_hbm_svc_ring_h9b.sv',sn+new+'.sv',sn+'ot_hbm_svc_pc_ctrl_leaf.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v',sn+'ot_hbm_svc_pin_skid2_h9.sv']
identity=json.load(open('../fallback_source_identity.json'))
for path in srcs:
 assert hashlib.sha256((root/path).read_bytes()).hexdigest()==identity['sources'][path]['closed_sha256'],path
sys.path.insert(0,str(root/'tools/hbm_die_v16/d4g_layers'))
from l22_e4_compose import header_ports
np,ports=header_ports(sn+new+'.sv',new)
assert set(params)<=np
names=[]
for n,v in c['instances'].items():
 if v['master']!=old:continue
 assert set(v['ports'])==set(ports),(n,'port set')
 for port,meta in v['ports'].items():assert ports[port]==(meta['direction'],meta['bits']),(n,port)
 v.update(master=new,source=sn+new+'.sv',rtl_deps=[f for f in srcs if f!=sn+new+'.sv'],params=params.copy())
 v['note']+=' | accepted h9c fallback, exact closed source1aa2ec44b/record2ab20b600; legacy pre-BW-safe model required; no T242 eligibility'
 names.append(n)
assert len(names)==64,len(names)
for s in c.get('straps',[]):
 if s.get('master')==old:s['master']=new
assert before['edges']==c['edges']
assert all(before['instances'][n]['ports']==c['instances'][n]['ports'] for n in names)
json.dump(c,open('../fallback_contract.json','w'))
json.dump({'status':'SOURCE_BOUND_FALLBACK_PROPOSAL_ONLY','instances':names,'params':params,'oldrate_model_required':True,'static_calendar_requalification_owed':True,'strict_bind_owed':True,'closed_view':identity['closed_job'],'source_sha256':identity['sources']},open('../fallback_report.json','w'),indent=2)
print('FALLBACK_SOURCE_PROPOSAL',len(names),'EXACT_SOURCE7_PARAMS6_PORTS_AND_EDGES_PRESERVED')
