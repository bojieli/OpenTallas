#!/usr/bin/env python3
"""Run a source-pinned raw functional gate; output must be a new directory."""
import argparse, hashlib, json, os, pathlib, subprocess, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
R='rtl/model_ready_ds_shared_native_20261003/'
CASES={
 'ID':['tests/rtl/dsrom_shared_native/tb_id_parent.sv',R+'ot_hdc_qstream_related_ID.sv',R+'ot_ds_native_vm_related_parent.sv',R+'ot_ds_native_write_formats.sv',R+'ot_ds_shared_native_vm_provider.sv','rtl/model_ready_ds_seven_class_20261003/ot_ds_owned_ratio_boundary.sv','results/uarch/dsrom_seven_class_swap_20261003/inputs/ratio_fifo.sv'],
 'collective':['tests/rtl/dsrom_shared_native/tb_coll_parent.sv',R+'ot_w15_coll_dma_related_vm.sv',R+'ot_chip_v41x_coll_transpose_related_vm.sv',R+'ot_ds_native_vm_related_parent.sv',R+'ot_ds_native_write_formats.sv',R+'ot_ds_shared_native_vm_provider.sv','rtl/chip/ot_coll_topk_merge.sv','rtl/model_ready_ds_seven_class_20261003/ot_ds_owned_ratio_boundary.sv','results/uarch/dsrom_seven_class_swap_20261003/inputs/ratio_fifo.sv'],
 'provider':['tests/rtl/dsrom_shared_native/tb_provider.sv',R+'ot_ds_shared_native_vm_provider.sv'],
 'related':['tests/rtl/dsrom_shared_native/tb_related_parent.sv',R+'ot_ds_native_vm_related_parent.sv',R+'ot_ds_native_write_formats.sv',R+'ot_ds_shared_native_vm_provider.sv','rtl/model_ready_ds_seven_class_20261003/ot_ds_owned_ratio_boundary.sv','results/uarch/dsrom_seven_class_swap_20261003/inputs/ratio_fifo.sv'],
 'transpose':['tests/rtl/dsrom_shared_native/tb_transpose.sv',R+'ot_chip_v41x_coll_transpose_related_vm.sv']}
TAIL=['rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv','results/uarch/dsrom_seven_class_swap_20261003/inputs/native_sram.v']
PASS={'ID':'PASS ID_NATIVE_WRONG_COOKIE','collective':'PASS DMA_TOPK_NATIVE','provider':'PASS SHARED_NATIVE_PROVIDER','related':'PASS RELATED_NATIVE_PARENT','transpose':'TRANSPOSE_PASS'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True);p.add_argument('--simulator',choices=['iverilog','verilator'],default='iverilog');p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 from dsrom_shared_native_vm_model import model
 m=model()
 if not m['admission']['isolated_raw_provider_functional']:raise ValueError('raw gate not admitted')
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);snap=out/'sources';snap.mkdir()
 files=[];pins={}
 for i,name in enumerate(CASES[a.case]+([] if a.case=='transpose' else TAIL)):
  data=(ROOT/name).read_bytes();dest=snap/f'{i}_{pathlib.Path(name).name}';dest.write_bytes(data);files.append(str(dest));pins[name]=hashlib.sha256(data).hexdigest()
 rec=dict(pid=os.getpid(),host=os.uname().nodename,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_dirty=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),case=a.case,simulator=a.simulator,status='RUNNING',source_sha256=pins,scope='raw functional only; no protected VM, full-token, loaded parent clock, or physical credit',threads=1)
 rec['versions']={}
 for k,c in ({'verilator':['verilator','--version']} if a.simulator=='verilator' else {'iverilog':['iverilog','-V'],'vvp':['vvp','-V']}).items():
  v=subprocess.run(c,capture_output=True,text=True);rec['versions'][k]=v.stdout+v.stderr
 (out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
 def save():(out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
 save()
 if a.simulator=='verilator':
  cmd=['verilator','--binary','--timing','--assert','--threads','1','-j','1','-Wno-fatal','-DOT_MEM_NO_INIT','--top-module','tb','--Mdir',str(out/'obj')]+files
  simulation=[str(out/'obj/Vtb')]
 else:
  cmd=['iverilog','-g2012','-Wall','-DOT_MEM_NO_INIT','-s','tb','-o',str(out/'gate.vvp')]+files;simulation=['vvp',str(out/'gate.vvp')]
 for phase,c in [('compile',cmd),('simulation',simulation)]:
  start=time.time()
  with (out/(phase+'.log')).open('w') as log:code=subprocess.run(['/usr/bin/time','-v','-o',str(out/(phase+'.resources'))]+c,stdout=log,stderr=subprocess.STDOUT).returncode
  rec[phase]=dict(command=c,exit_code=code,elapsed_s=time.time()-start);save()
  if code:break
 rec['status']='TERMINAL';rec['terminal']=(out/'simulation.log').read_text() if (out/'simulation.log').exists() else (out/'compile.log').read_text()
 rec['verdict']='PASS' if rec.get('simulation',{}).get('exit_code')==0 and PASS[a.case] in rec['terminal'] else 'FAIL';save()
 print(json.dumps(dict(verdict=rec['verdict'],receipt=str(out/'record.json'),terminal=rec['terminal'])));return rec['verdict']!='PASS'
if __name__=='__main__':raise SystemExit(main())
