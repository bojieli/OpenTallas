import hashlib,json,os,re,subprocess,time
from pathlib import Path
S=Path('/tmp/ds-native-reset-r2-d33a531f7-source');O=Path('/tmp/ds-native-reset-r2-d33a531f7-run')
R={'source_SHA':'d33a531f7','scope':'Full256macro raw reset/mask/tag visibility only; no protection/timing/rate qualification','pid':os.getpid(),'host':os.uname().nodename,'output':str(O),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'runs':{}}
def save(): (O/'record.json').write_text(json.dumps(R,indent=2,sort_keys=True)+'\n')
def run(name,args):
 with (O/(name+'.log')).open('w') as log:
  p=subprocess.run(['/usr/bin/time','-v','-o',str(O/(name+'.resource.txt'))]+args,cwd=S,stdout=log,stderr=subprocess.STDOUT)
 return p.returncode
save()
assert subprocess.check_output(['git','status','--porcelain'],cwd=S,text=True)==''
R['source_SHA']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()
R['versions']={x:subprocess.run([x,'-V'],text=True,capture_output=True).stdout for x in ['iverilog','vvp']}
assert run('source_preflight',['python3','tools/dsrom_native_masked_r2_verify.py'])==0
for label,mod,path in [('r1','ot_v41_vm_bank4_macro_pipe_masked_visible','rtl/model_ready_ds_native_vm_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible.sv'),('r2','ot_v41_vm_bank4_macro_pipe_masked_visible_r2','rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv')]:
 exe=O/(label+'.vvp');cmd=['iverilog','-g2012','-DOT_MEM_NO_INIT','-DDUT='+mod,'-s','tb','-o',str(exe),'tests/rtl/dsrom_native_masked_r2/tb.sv',path,'results/uarch/dsrom_native_masked_backend_r2_20261003/inputs/native_sram.v']
 R['runs'][label]={'compile_command':cmd,'source_sha256':hashlib.sha256((S/path).read_bytes()).hexdigest()};save()
 rc=run(label+'_compile',cmd);R['runs'][label]['compile_rc']=rc;save()
 if rc: R['terminal']='FAIL_COMPILE_'+label;save();raise SystemExit(1)
 text=exe.read_text();c=sum(1 for l in text.splitlines() if '.scope module, "u_sram" "ot_sram_1r1w_512x128_m4_r2c2"' in l)
 R['runs'][label]['elaborated_native_macro_instances']=c
 R['runs'][label]['compiled_sha256']=hashlib.sha256(exe.read_bytes()).hexdigest()
 if c!=256:R['terminal']='FAIL_INSTANCE_CENSUS';save();raise SystemExit(1)
 rc=run(label+'_simulation',['vvp',str(exe)]);log=(O/(label+'_simulation.log')).read_text()
 R['runs'][label]['simulation_rc']=rc;R['runs'][label]['terminal_output']=log;save()
 if label=='r1':
  if rc==0 or 'RESET_ACCEPTANCE_DEFECT' not in log:R['terminal']='FAIL_NEGATIVE_CONTROL';save();raise SystemExit(1)
 else:
  if rc!=0 or not re.search(r'^PASS RAW_NATIVE_R2_RESET_MASK_VISIBILITY cases=\d+$',log,re.M):R['terminal']='FAIL_R2_SIMULATION';save();raise SystemExit(1)
R['terminal']='PASS_ISOLATED_RAW_R2_WITH_R1_FAILURE_PRESERVED'
R['finished_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
R['evidence_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.glob('*') if p.is_file() and p.name!='record.json'}
save();print(R['terminal'])
