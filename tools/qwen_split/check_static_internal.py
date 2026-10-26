#!/usr/bin/env python3
"""Lightweight actual-decoder/PW-calendar and native-route mechanism gates."""
from pathlib import Path
import subprocess,tempfile,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
D=Path('rtl/qwen_sys/static_schedule_20261014')
def run():
 out=ROOT/'results/rtl/qwen_q_export_1014/dense_controller_join';out.mkdir(exist_ok=True,parents=True)
 src=['rtl/hdc/ot_hdc_dyn_ttiles.sv']+[str(D/f) for f in ['ot_qwen_rom_core_ctrl_static.sv','ot_qwen_fixed_issue.sv','ot_qwen_fixed_issue_pw.sv','ot_qwen_fixed_issue_dense_pw.sv','tb_qfd_static_internal_issue.sv']]
 program=Path('results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/head_program_rank7.hex')
 program_bytes=subprocess.check_output(['git','show','origin/main:'+str(program)],cwd=ROOT)
 if hashlib.sha256(program_bytes).hexdigest()!='08c4c30c2c41cc3473280e33bf84dba3c0bca9180a21f233aad4682b5558a6a9':raise RuntimeError('source program changed; review pin')
 with tempfile.TemporaryDirectory(prefix='q_static_internal_') as tmp:
  program_local=Path(tmp)/'head_rank7.hex';program_local.write_bytes(program_bytes)
  from check_dense_image import fixture
  dense=fixture(program_bytes);image_local=Path(tmp)/'dense.hex';image_local.write_text(''.join(w['data_hex']+'\n'for w in dense['writes']if not w['desc']))
  exe=str(Path(tmp)/'sim')
  for name,params,success in [('actual_head',[],True),('typed_cp_head',['USE_COPY=1'],True),('typed_cp_busy_fault_timeline',['USE_COPY=1','CP_BUSY=1'],True),('missing_cp_payload_mutant',['USE_COPY=1','MUT_MISSING_CP=1'],False),('unavailable_fault_timeline',['AVAIL_FALSE=1'],True),('row18_boundary',['ROW_HIGH=1'],True),('row18_mutant',['ROW_HIGH=1','MUT_DROP_ROW_HIGH=1'],False)]:
   cmd=['iverilog','-g2012','-s','tb_qfd_static_internal_issue','-o',exe]+['-Ptb_qfd_static_internal_issue.'+x for x in params]+src
   subprocess.run(cmd,cwd=ROOT,check=True);r=subprocess.run(['vvp',exe,'+PROGRAM='+str(program_local)],cwd=ROOT,capture_output=True,text=True)
   (out/(name+'.log')).write_text(r.stdout+r.stderr)
   if (r.returncode==0)!=success:raise RuntimeError(name+': '+r.stdout+r.stderr)
  headsrc=[str(D/f) for f in ['ot_qwen_rom_core_ctrl_static.sv','ot_qfd_tt_ctlm_split_static.sv','ot_qwen_fixed_issue.sv','ot_qwen_fixed_issue_pw.sv','ot_qwen_fixed_issue_dense_pw.sv','tb_qfd_static_head_face.sv']]+['rtl/hdc/ot_hdc_dyn_ttiles.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv','rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv','rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv','rtl/physical/ot_qfd_tt_ctlm_split.sv']
  macro_path='physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v'
  macro_bytes=subprocess.check_output(['git','show','origin/main:'+macro_path],cwd=ROOT)
  macro_local=Path(tmp)/'program_sram.v';macro_local.write_bytes(macro_bytes)
  headsrc+=['rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv','rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_dense_pw_loader.sv','rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_static_schedule.sv']
  headsrc.append(str(macro_local))
  for name,mut,params in [('actual_head_face',False,[]),('actual_head_sram_face',False,['PSRAM=1']),('actual_dense_head_sram_face',False,['PSRAM=1','DENSE_IMAGE=1']),('head_cp_busy_fault_timeline',False,['CP_BUSY=1']),('head_program_write_fault_timeline',False,['ACTIVE_WRITE=1']),('head_context_mutant',True,[])]:
   paths=headsrc.copy()
   if mut:
    newhead=Path(tmp)/'head.sv';newhead.write_text((ROOT/D/'ot_qfd_tt_ctlm_split_static.sv').read_text().replace('if(accepted_start)begin native_tok','if(1\'b1)begin native_tok'));paths[1]=str(newhead)
   compiled=subprocess.run(['iverilog','-g2012','-s','tb_qfd_static_head_face','-o',exe]+['-Ptb_qfd_static_head_face.'+p for p in params]+paths,cwd=ROOT,capture_output=True,text=True)
   (out/(name+'_compile.log')).write_text((compiled.stdout+compiled.stderr).replace(tmp,'<gate_tmp>'))
   if compiled.returncode:raise RuntimeError(compiled.stderr)
   r=subprocess.run(['vvp',exe,'+PROGRAM='+str(program_local),'+IMAGE='+str(image_local)],cwd=ROOT,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
   if (r.returncode==0)==mut:raise RuntimeError(name+': '+r.stdout+r.stderr)
   if name=='actual_dense_head_sram_face':
    for bad_name,addr,bit in [('dense_footer_reserved_mutant',1023,13),('dense_unused_SU_row_mutant',988,0),('dense_XPF_padding_mutant',1015,63)]:
     changed=[int(w['data_hex'],16)for w in dense['writes']if not w['desc']];changed[addr]^=1<<bit
     bad_image=Path(tmp)/(bad_name+'.hex');bad_image.write_text(''.join(f'{word:016x}\n'for word in changed))
     bad=subprocess.run(['vvp',exe,'+PROGRAM='+str(program_local),'+IMAGE='+str(bad_image)],cwd=ROOT,capture_output=True,text=True)
     (out/(bad_name+'.log')).write_text(bad.stdout+bad.stderr)
     if bad.returncode==0:raise RuntimeError(bad_name+' unexpectedly configured')
  route=ROOT/D/'ot_qfd_native_cmd_route.sv';tb=str(D/'tb_qfd_native_cmd_route.sv')
  for name,mut in [('native_route',False),('native_route_mutant',True)]:
   p=Path(tmp)/'route.sv';s=route.read_text()
   if mut:s=s.replace("cmd[0]&&!cmd[55]", "cmd[0]")
   p.write_text(s);subprocess.run(['iverilog','-g2012','-s','tb_qfd_native_cmd_route','-o',exe,str(p),tb],cwd=ROOT,check=True)
   r=subprocess.run(['vvp',exe],cwd=ROOT,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
   if (r.returncode==0)==mut:raise RuntimeError(name+': '+r.stdout+r.stderr)
 status={'scope':'Actual production decoder+PW FF issuer internal mechanism, explicit engine-response stimuli; not native end-to-end qualification','source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in list(dict.fromkeys(src+headsrc[:-1]+[str(D/'ot_qfd_native_cmd_route.sv'),tb]))},'program_source':str(program),'program_sha256':hashlib.sha256(program_bytes).hexdigest(),'fixed_issue_cycles':[40,60,80,100],'fixed_END_cycle':120,'typed_CP_profile':{'ME':[40,180,320,460],'CP':[60,200,340],'END':600,'scope':'real PW CPstore+source head/decoder; explicit engine stimuli'},'head_face_gate':'actual program PW writes, IS1/GO1/CP1, PSRAM0 FF and PSRAM1 production macro functional profiles; real accepted context vs future raw pins. Clock root/physical qualification remain open','SRAM_macro_source':macro_path,'SRAM_macro_sha256':hashlib.sha256(macro_bytes).hexdigest(),'clock_enable':'normal1; mem_ok0 leaves clocks unchanged','row18_boundary_variant':'Actual ISA bit898 set1 in four head ME words','remaining':['actual endpoint/status and parent composition','physical phase/reset/pin/cost qualification','real fullstage compiler calendar']}
 (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
 print('PASS actual decoder/head face/PW CPstores/numeric fold and fault-only timelines; row18/context/missingCP/route mutants observed FAIL')
if __name__=='__main__':run()
