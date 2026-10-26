"""Fleet-only exact selected generator schema/default/source audit."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
code=r"""
import json,sys
sys.path.insert(0,sys.argv[1]);import kv_static_die as S
T=S.all_tiles(); B=S.bindings()
print(json.dumps(dict(rtl=S.rtl_text(), file=S.RTL_FILE, bindings=B,
 tiles={k:dict(kind=t['kind'], master=S.KIND_MASTER[t['kind']],ports=t['ports'],
 text=S.module_text(t,S.KIND_MASTER[t['kind']]),
 faces={p:S.pin_face(S.KIND_MASTER[t['kind']],p) for p in t['ports']},
 face_orders={f:S.face_order(S.KIND_MASTER[t['kind']],f,list(t['ports'])) for f in ['N','S','E','W']}) for k,t in T.items()})))
"""
records={}
for enabled in [False,True]:
 env=dict(os.environ,OT_KV_GRP_PRIVATE0='1' if enabled else '0')
 name='private' if enabled else 'default'
 proc=subprocess.run([sys.executable,'-c',code,str(root/'tools/qwen_kv_die')],env=env,text=True,capture_output=True)
 (out/(name+'.stderr')).write_text(proc.stderr)
 if proc.returncode: raise RuntimeError(name+' refused: '+proc.stderr)
 rec=json.loads(proc.stdout);records[name]=rec
 (out/(name+'.json')).write_text(proc.stdout)
old,new=records['default'],records['private']
import importlib.util
spec=importlib.util.spec_from_file_location('GP',root/'tools/qwen_kv_die/kv_grp_private0.py');gp=importlib.util.module_from_spec(spec);spec.loader.exec_module(gp)
original=(root/'rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv').read_text()
assert hashlib.sha256(original.encode()).hexdigest()==gp.SELECTED_SHA256
# Existing non-GRP generated modules can be newer than the frozen selected file.
# Compare generator defaults against the exact pre-change tool separately.
env=dict(os.environ,OT_KV_GRP_PRIVATE0='0')
basecode=code.replace('import kv_static_die as S','import kv_static_die_baseline as S')
baseline=subprocess.run([sys.executable,'-c',basecode,str(root/'tools/qwen_kv_die')],env=env,text=True,capture_output=True)
(out/'baseline.stderr').write_text(baseline.stderr)
assert baseline.returncode==0,baseline.stderr
base=json.loads(baseline.stdout)
assert old==base,'default generator behavior changed'
(out/'baseline.json').write_text(baseline.stdout)
private_pair=gp.private_text(original)
# Actual original and generated GRP bodies must still match exactly.
for name in gp.MODULE_SHA256:gp.check_selected(gp.module_body(old['rtl'],name),name)
removed=0;counts={'grp':0,'grp_h':0};ledger=[]
for inst,a in old['tiles'].items():
 b=new['tiles'][inst]; kind=a['kind']
 if kind not in counts:
  assert a==b,inst
  continue
 counts[kind]+=1
 name=a['master']; assert b['master']==name+'_private0'
 assert gp.module_body(b['text'],b['master'])==gp.module_body(private_pair,b['master']),inst
 removed_bits=sum(p['width'] for p in a['ports'].values())-sum(p['width'] for p in b['ports'].values())
 assert removed_bits==(428 if kind=='grp_h' else 80)
 removed+=removed_bits
 assert b['ports']['x__est']['width']==1 and b['ports']['x__est']['scalar']
 assert b['ports']['y__est__0_1']['expr']=='x__est'
 assert len(a['ports'])-len(b['ports'])==(5 if kind=='grp_h' else 4)
 for p in b['ports']:assert a['faces'][p]==b['faces'][p]
 binding=new['bindings'][b['master']]
 assert set(binding['ports'])=={p for p,v in b['ports'].items() if v['cls']!='pad'}
 assert binding['file']=='rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_grp_private0.sv' and binding['module']==b['master']
 ledger.append(dict(instance=inst,master=b['master'],removed_bits=removed_bits,ports={p:dict(direction=v['dir'],width=v['width']) for p,v in b['ports'].items()}))
assert counts=={'grp':28,'grp_h':4} and removed==3952
assert all(x not in new['bindings'] for x in gp.MODULE_SHA256)
for master,binding in old['bindings'].items():
 if master not in gp.MODULE_SHA256:assert binding==new['bindings'][master],master
expected=old['rtl']
for n in gp.MODULE_SHA256:
 expected=expected.replace(gp.module_body(expected,n),gp.module_body(private_pair,n+'_private0'))
 expected=expected.replace('// '+n+': GENERATED','// '+n+'_private0: GENERATED')
# Only module names, selected deletions and scalar EST representation change.
assert new['rtl']==expected,'generated private full file differs from exact deletion transform'
(out/'selected_private.sv').write_text(new['rtl'])
result=dict(status='PASS_SOURCE_SCHEMA_ONLY',removed_pins=removed,replicas=counts,public_sha256=gp.SELECTED_SHA256,private_sha256=hashlib.sha256(new['rtl'].encode()).hexdigest(),instances=ledger,GEN8_final_bind=None, inherited_non_GRP_generated_file_staleness=(old['rtl']!=original))
(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print('GRP_PRIVATE_GENERATOR PASS removed_pins=3952 GRP=28 H=4 default_public_byte_identity=PASS')
