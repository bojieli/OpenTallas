import json,subprocess,pathlib,hashlib
ss=json.load(open('sources.json'));cases=[]
for m in [0,3]:
 with open(f'target-final-build{m}.log','w') as f:subprocess.run(['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--binary','--timing','-Wno-fatal','-j','2','--top-module','tb_host_program_target','-GMUT='+str(m),'--Mdir',f'obj_target_final{m}',*ss,'tb_host_program_target.sv'],stdout=f,stderr=subprocess.STDOUT,check=True)
 for neg in ([0,1,2,3] if m==0 else [1]):
  r=subprocess.run([str(pathlib.Path.cwd()/f'obj_target_final{m}/Vtb_host_program_target'),f'+negative={neg}'],capture_output=True,text=True);pathlib.Path(f'target-final-run{m}-neg{neg}.log').write_text(r.stdout+r.stderr);print(m,neg,r.returncode,r.stdout,flush=True)
  ok=(r.returncode==0 and 'PASS' in r.stdout) if m==0 else (r.returncode!=0 and ('EXPECTED_AUTH_TARGET_FAULT' in r.stdout or 'NEGATIVE_REPLAY' in r.stdout))
  cases.append({'mutant':m,'negative':neg,'rc':r.returncode,'expected':ok})
manifest={p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in ss+['tb_host_program_target.sv']}
pathlib.Path('target-final-receipt.json').write_text(json.dumps({'status':'PASS' if all(c['expected'] for c in cases) else 'FAIL','cases':cases,'sources':manifest},indent=2));assert all(c['expected'] for c in cases)
