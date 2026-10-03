#!/usr/bin/env python3
"""Elaborate actual full-width caller copies, using the retained runtime dependencies."""
import argparse,hashlib,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
R='rtl/model_ready_ds_shared_native_20261003/'
CASES={
 'core':('ot_hdc_core_v41x_native_callers',dict(NATIVE_VM=1,FULL_SHAPE=1,X_ROM=1,X_ATT=1,X_IDX=2,X_SEL=1,MP=1,SUN=256,SUM=64,PAW=14,IDX_RING=1)),
 'ME':('ot_hdc_v41x_me_adapt_native_vm',dict(VM_RESPONSE_WAIT=1,OUTPUT_CREDIT=1,AW=30,NW=21,MP=1,G=4,KMAX=5120,MG=8)),
 'attention':('ot_hdc_v41x_att_adapt_native_vm',dict(VM_RESPONSE_WAIT=1,OUTPUT_CREDIT=1,AW=30,NW=21,MP=1,G=4,D=512,TROWS=640,PACKED_KV=1,NHMAX=16)),
 'index':('ot_hdc_v41x_idx_pool_adapt_native_vm',dict(VM_RESPONSE_WAIT=1,OUTPUT_CREDIT=1,AW=30,NW=21,MP=1,G=4,HAW=30,RING=1)),
 'XU':('ot_hdc_v41x_xu_adapt_native_vm',dict(VM_RESPONSE_WAIT=1,OUTPUT_CREDIT=1,AW=30,NW=21,K=512,IKW=12,SK=2048,X_SEL=1,SQ=4,SW=16))}
def main():
 from dsrom_shared_native_vm_model import model
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 m=model();assert m['caller_integration']['raw_source_integration_admission']
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 names=(ROOT/'tools/w17_current_fastpp_l20_window_owner_safe_sources.txt').read_text().split()
 names += [R+n+'.sv' for n,_ in CASES.values()]
 names=list(dict.fromkeys(names));names.sort(key=lambda n:('pkg' not in n and 'package' not in n,n))
 snapshot=out/'sources';snapshot.mkdir();files=[];pins={}
 for i,n in enumerate(names):
  b=(ROOT/n).read_bytes();pins[n]=hashlib.sha256(b).hexdigest()
  d=snapshot/(str(i)+'_'+pathlib.Path(n).name);d.write_bytes(b);files.append(str(d))
 rec=dict(pid=os.getpid(),host=os.uname().nodename,status='RUNNING',scope='full-width source elaboration only; no arithmetic simulation, protected parent, physical or token credit',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),source_sha256=pins,cases={},versions=subprocess.check_output(['verilator','--version'],text=True))
 def save():(out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
 save();(out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
 for case,(top,params) in CASES.items():
  cmd=['verilator','--lint-only','--timing','-Wno-fatal','-DV41_ATT_CUT','-I'+str(ROOT/'rtl/hdc/v41'),'--top-module',top,*['-G'+k+'='+str(v) for k,v in params.items()],*files]
  start=time.time()
  with (out/(case+'.log')).open('w') as log:
   code=subprocess.run(['/usr/bin/time','-v','-o',str(out/(case+'.resources')),*cmd],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT).returncode
  rec['cases'][case]=dict(command=cmd,parameters=params,exit_code=code,elapsed_s=time.time()-start);save()
  if code:break
 rec['status']='TERMINAL';rec['verdict']='PASS' if len(rec['cases'])==5 and all(c['exit_code']==0 for c in rec['cases'].values()) else 'FAIL';save();print(json.dumps(dict(receipt=str(out/'record.json'),verdict=rec['verdict'])));return rec['verdict']!='PASS'
if __name__=='__main__':raise SystemExit(main())
