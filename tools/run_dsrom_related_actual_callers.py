#!/usr/bin/env python3
"""Replay one source-selected caller diagnostic; no physical/parent admission."""
import argparse, hashlib, io, json, pathlib, subprocess, tarfile, time
ROOT=pathlib.Path(__file__).resolve().parents[1]
R='rtl/model_ready_ds_seven_class_20261003/'
D='results/uarch/dsrom_seven_class_swap_20261003/'
CASES={
 'field': ['tests/rtl/dsrom_related_native/tb.sv',R+'ot_ds_field_x_related_native.sv',D+'inputs/spine_related_vm.sv',R+'ot_ds_owned_ratio_boundary.sv',D+'inputs/ratio_fifo.sv','rtl/model_ready_ds_native_vm_r2_20261003/ot_v41_vm_bank4_macro_pipe_masked_visible_r2.sv',D+'inputs/native_sram.v','rtl/hdc/v41/ot_hdc_actquant.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv'],
 'SU_KV': ['tests/rtl/dsrom_su_kv_visible/tb.sv',R+'ot_ds_su_kv_related_visible.sv',R+'ot_chip_v41x_kv_prefetch_visible.sv',R+'ot_ds_owned_ratio_boundary.sv',D+'inputs/ratio_fifo.sv',D+'inputs/native_sram.v'],
 'index': ['tests/rtl/dsrom_idx_related/tb.sv',R+'ot_hdc_v41x_idx_pool_adapt_related_vm.sv']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--case',choices=CASES,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 model=json.loads((ROOT/D/'model.json').read_text())
 if not model['admission']['raw_boundary_RTL_and_functional_gate']:raise RuntimeError('raw functional model not admitted')
 src=out/'sources';src.mkdir();files=[];pins={}
 for i,name in enumerate(CASES[a.case]):
  data=(ROOT/name).read_bytes();dest=src/f'{i}_{pathlib.Path(name).name}';dest.write_bytes(data);files.append(str(dest));pins[name]=hashlib.sha256(data).hexdigest()
 cmd=['iverilog','-g2012','-Wall','-s','tb','-o',str(out/'gate.vvp')]
 if a.case=='field':cmd+=['-DOT_MEM_NO_INIT']
 cmd+=files
 if a.case=='index':
  pin=json.loads((ROOT/D/'actual_callers/implementation.json').read_text())['source_library_pin']
  archive=subprocess.check_output(['git','archive',pin,'rtl/hdc','rtl/chip','rtl/common'],cwd=ROOT)
  lib=out/'retained';lib.mkdir()
  with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(lib)
  for name in ['rtl/hdc/ot_hdc_fpu.sv','rtl/hdc/ot_hdc_fp32_mul_pipe.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv']:cmd.append(str(lib/name))
  for d in sorted({str(x.parent) for x in lib.rglob('*.sv')}):cmd+=['-y',d]
  cmd+=['-Y','.sv']
  for x in lib.rglob('*.sv'):pins[str(x.relative_to(lib))]=hashlib.sha256(x.read_bytes()).hexdigest()
 rec={'case':a.case,'status':'RUNNING','source_sha256':pins,'parent_physical_credit':False,'protected_parent_credit':False,'scope':'source-selected caller diagnostic only'}
 def save():(out/'record.json').write_text(json.dumps(rec,indent=2)+'\n')
 save()
 for phase,c in [('compile',cmd),('simulation',['vvp',str(out/'gate.vvp')])]:
  start=time.time()
  with (out/(phase+'.log')).open('w') as log:code=subprocess.run(['/usr/bin/time','-v','-o',str(out/(phase+'.resources'))]+c,stdout=log,stderr=subprocess.STDOUT).returncode
  rec[phase]={'command':c,'exit_code':code,'elapsed_s':time.time()-start};save()
  if code:break
 rec['status']='TERMINAL';rec['terminal']=(out/'simulation.log').read_text() if (out/'simulation.log').exists() else ''
 rec['verdict']='PASS' if rec.get('simulation',{}).get('exit_code')==0 and 'PASS ' in rec['terminal'] else 'FAIL';save()
 print(json.dumps({'verdict':rec['verdict'],'receipt':str(out/'record.json'),'terminal':rec['terminal']}));return 0 if rec['verdict']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
