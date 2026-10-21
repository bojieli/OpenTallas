import subprocess,json,hashlib
from pathlib import Path
out={}
for name in ['add','mul3','mul5','negative']:
 cmd=['yosys','-Q','-p',f'read_verilog -sv {name}.sv; prep -top m -flatten; techmap; opt; sat -timeout 180 -verify -prove ok 1 -show-inputs']
 p=subprocess.run(cmd,capture_output=True,text=True);Path(name+'.log').write_text(p.stdout+p.stderr);out[name]={'rc':p.returncode,'expected_rc':'nonzero' if name=='negative' else 0,'pass':(p.returncode!=0 if name=='negative' else p.returncode==0)};print(name,out[name],flush=True)
p=subprocess.run(['iverilog','-g2012','-s','tb','-o','fourstate.vvp','fourstate.sv'],capture_output=True,text=True);Path('fourstate_compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
p=subprocess.run(['vvp','fourstate.vvp'],capture_output=True,text=True);Path('fourstate.log').write_text(p.stdout+p.stderr);out['fourstate']={'rc':p.returncode,'pass':p.returncode==0,'output':p.stdout};print('fourstate',out['fourstate'],flush=True)
out['tool']={t:subprocess.run([t,'-V'],capture_output=True,text=True).stdout for t in ['yosys','iverilog']};out['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in Path('.').glob('*.sv')};Path('receipt.json').write_text(json.dumps(out,indent=2)+'\n');assert all(v['pass'] for k,v in out.items() if k in ['add','mul3','mul5','negative','fourstate'])
