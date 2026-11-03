from pathlib import Path
import hashlib,json,sys,importlib.util
r=Path(sys.argv[1]);d=json.loads((r/'INPUT_HASHES.json').read_text())
for n,w in d.items():assert hashlib.sha256((r/n).read_bytes()).hexdigest()==w,n
k=r/'kit';e=r/'checker/lec.py'
assert hashlib.sha256(e.read_bytes()).hexdigest()=='1826084c39be03a337c29d54ca703871d88243fc04e58dcd84010e0bfdd18b4b'
assert hashlib.sha256((k/'1_2_yosys.v').read_bytes()).hexdigest()=='0192e029133af666b4471c050351de321f789c6199626cc1332761b2dd71f35e'
assert '.QK_ISSUE_AGE(34), .RESPONSE_LAT(18)' in (k/'rtl/qkd_ectlk_columns.sv').read_text()
s=importlib.util.spec_from_file_location('qualified_lec',e);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
v=m.reset_contract_gate(str(k),'qkd_ectlk_q1',{'OT_LEC_RESET_CYCLES':'4'})
assert v['used']==4 and v['requested']==4 and v['contract']['edges']==16 and not v['debug_overrides'] and not v.get('refused'),v
assert not (r/'proof').exists(),'refuse restart/overwrite'
print('HG9_Q1_CURRENT_NATIVE_INPUT_GUARD_PASS',len(d),'RESET_CONTRACT16_REQUESTED4_USED4_DEBUG_EMPTY')
