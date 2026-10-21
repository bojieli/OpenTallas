import os,sys,subprocess,re,json
from pathlib import Path
root=Path(__file__).parent;src=root/'src';v=int(sys.argv[1]);env=dict(os.environ,LP_ROOT=str(src));rc=0;rows=[]
for m in [0,1,2,3,5,6]:
 out=root/('witness_v'+str(v))/('m'+str(m))
 one=subprocess.call(['bash',str(src/'rtl/hbm_accel/sm/repack/h2a5/run_rp5_2_one.sh'),str(out),str(v),str(m)],env=env)
 raw=(out/'run.log').read_text() if (out/'run.log').exists() else ''
 expected='PASS' if m==0 else 'FAIL'
 ok=bool(re.search(r'^R5_LOCKSTEP '+expected+' VAR='+str(v)+' HMUT='+str(m)+r'\b',raw,re.M)) and ((one==0) if m==0 else True)
 rows.append(dict(var=v,hmut=m,process_rc=one,expected=expected,qualified=ok))
 print('R5_CASE_QUALIFICATION',v,m,one,ok,flush=True);rc=max(rc,int(not ok))
 (root/('witness_v'+str(v))/'batch_receipt.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(rc)
