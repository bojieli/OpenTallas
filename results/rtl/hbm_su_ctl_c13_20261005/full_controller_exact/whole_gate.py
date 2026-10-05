import hashlib,json,os,pathlib,sys,time
root=pathlib.Path(__file__).resolve().parent;src=root/'src';sys.path.insert(0,str(src/'tools'))
import hbm_su_ctl_c13 as C
import rtl_hdc_v41x_vec_campaign as V
import numpy as np
V.BCAST=7;V.RET=8;C.apply(V,dpi=True)
exe=root/'work/obj_N64_M16_b7r8m6a6_dpi_beh/Vtb';assert exe.exists()
rows=[]
for no in (2,3,5):
 for ni in (8,24,40):
  for tree in (0,1):
   f=V.op_defaults();f.update(nout=no,nin=ni,asrc=V.I.SRC_VM,abase=64,aso=ni+1,asi=1,red=V.I.RED_SUM,redwhole=1-tree,redtree=tree,rbase=2048,rso=1,dst=V.I.DST_VM,obase=4096,oso=ni+1,osi=1)
   lay=V.layout(f,64,16);assert lay['wnf'] and not lay['bad'],lay
   vm=np.zeros(1<<V.VMA,dtype=np.uint32);vm[64:64+no*(ni+1)]=V.fbits(np.arange(no*(ni+1),dtype=np.float32)/256)
   mem=V.Mem(vm,np.zeros(1<<V.KVA,dtype=np.uint32),np.zeros((1<<V.CRA,2),dtype=np.uint32),np.zeros(1<<V.WRA,dtype=np.uint16))
   tag=f'whole_n{no}_i{ni}_tree{tree}';r,tr,ops,lays=V.run_program(exe,root/'work'/tag,mem,[f],64,16)
   r.update(case=tag,layout=lay);rows.append(r);print(tag,r['pass_'],r['vm_mismatch_words'],r['cycles'],flush=True)
rec=dict(schema='opentallas.hbm.su.controller.whole_unflattened_exact.v1',status='pass' if all(x['pass_'] for x in rows) else 'fail',source_commit='1659b138d',rows=rows,existing_executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),no_rebuild=True,source_shape=dict(N=64,M=16),case_source_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),clock_qualified=False,adopted=False)
(root/'out/whole_unflattened_gate.json').write_text(json.dumps(rec,indent=2)+'\n')
raise SystemExit(0 if rec['status']=='pass' else 1)
