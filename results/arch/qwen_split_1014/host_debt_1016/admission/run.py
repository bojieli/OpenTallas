import subprocess,json,pathlib
p=pathlib.Path.cwd(); cases=[]
for m in [0,1]:
 with open(f'build{m}.log','w') as f:subprocess.run(['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--binary','--timing','-Wno-fatal','-j','2','--top-module','tb_host_rx_admission','-GMUT='+str(m),'--Mdir',f'obj{m}','qkd_host_rx_class.sv','qkd_host_rx_class_admission.sv','tb_host_rx_admission.sv'],stdout=f,stderr=subprocess.STDOUT,check=True)
 r=subprocess.run([str(p/f'obj{m}/Vtb_host_rx_admission')],capture_output=True,text=True);pathlib.Path(f'run{m}.log').write_text(r.stdout+r.stderr);print(m,r.returncode,r.stdout,flush=True)
 cases.append({'mut':m,'rc':r.returncode,'passed':r.returncode==0 if m==0 else r.returncode!=0 and 'RESERVATION_LEAK' in r.stdout})
pathlib.Path('receipt.json').write_text(json.dumps(cases,indent=2));assert all(c['passed'] for c in cases)
