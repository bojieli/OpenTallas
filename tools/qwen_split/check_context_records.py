#!/usr/bin/env python3
"""Actual HOST identity + static SRAM transport component; no physical claim."""
from pathlib import Path
import subprocess,tempfile,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
D=Path('rtl/qwen_sys/context_transport_20261014')
DEPENDENCIES=[('35697e26c','rtl/qwen_sys/host_20261013/qkd_host_ctrl_token_service_packet.sv'),('35697e26c','rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_epoch_allocator.sv'),('35697e26c','rtl/qwen_sys/host_integrated_20261014/qkd_host_native_token_endpoint_cancel.sv'),('5f8109ed6','rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv'),('5f8109ed6','rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv'),('5f8109ed6','rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv'),('origin/main','physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v')]
def run():
 out=ROOT/'results/rtl/qwen_q_export_1014/context_records';out.mkdir(parents=True,exist_ok=True)
 pins={}
 with tempfile.TemporaryDirectory(prefix='q_context_')as td:
  src=[str(ROOT/D/'qkd_context_records.sv'),str(ROOT/D/'tb_qkd_context_records.sv'),str(ROOT/'rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv')]
  for revision,path in DEPENDENCIES:
   data=subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT);p=Path(td)/Path(path).name;p.write_bytes(data);src.append(str(p));pins[path]=dict(revision=revision,sha256=hashlib.sha256(data).hexdigest())
  from check_dense_image import fixture
  program=subprocess.check_output(['git','show','origin/main:results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/head_program_rank7.hex'],cwd=ROOT)
  image=fixture(program);image_path=Path(td)/'head_dense.hex';image_path.write_text(''.join(w['data_hex']+'\n'for w in image['writes']if not w['desc']))
  S=ROOT/'rtl/qwen_sys/static_schedule_20261014'
  src += [str(S/f)for f in ['ot_qwen_rom_core_ctrl_static.sv','ot_qfd_tt_ctlm_split_static.sv','ot_qwen_fixed_issue.sv','ot_qwen_fixed_issue_pw.sv','ot_qwen_fixed_issue_dense_pw.sv']]
  src += [str(ROOT/p)for p in ['rtl/hdc/ot_hdc_dyn_ttiles.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv','rtl/qwen_sys/missing_masters_20261007/ot_qfd_split_exact.sv','rtl/qwen_sys/missing_masters_20261007/ot_qfd_spine_masters.sv','rtl/physical/ot_qfd_tt_ctlm_split.sv']]
  for mutant,name in [(0,'actual_HOST_SRAM_context'),(1,'image_digest_mutant'),(2,'capability_mutant'),(3,'runtime_epoch_mutant')]:
   exe=str(Path(td)/'sim');c=subprocess.run(['iverilog','-g2012','-s','tb_qkd_context_records','-Ptb_qkd_context_records.MUT='+str(mutant),'-o',exe]+src,cwd=ROOT,capture_output=True,text=True)
   (out/(name+'_compile.log')).write_text((c.stdout+c.stderr).replace(td,'<gate_tmp>'))
   if c.returncode:raise RuntimeError(c.stderr)
   r=subprocess.run(['vvp',exe,'+IMAGE='+str(image_path)],cwd=ROOT,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
   if (r.returncode==0)!=(mutant==0):raise RuntimeError(name+': '+r.stdout+r.stderr)
  for mutant,name in [(0,'program_metadata_witness'),(1,'auth_digest_mutant'),(2,'footer_cap_mutant'),(3,'missing_actual_commit_mutant')]:
   exe=str(Path(td)/'program_sim');paths=[str(ROOT/D/'qkd_context_records.sv'),str(ROOT/D/'tb_qkd_program_records.sv'),str(ROOT/'rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv')]
   c=subprocess.run(['iverilog','-g2012','-s','tb_qkd_program_records','-Ptb_qkd_program_records.MUT='+str(mutant),'-o',exe]+paths,cwd=ROOT,capture_output=True,text=True)
   (out/(name+'_compile.log')).write_text((c.stdout+c.stderr).replace(td,'<gate_tmp>'))
   if c.returncode:raise RuntimeError(c.stderr)
   r=subprocess.run(['vvp',exe],cwd=ROOT,capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
   if (r.returncode==0)!=(mutant==0):raise RuntimeError(name+': '+r.stdout+r.stderr)
 status=dict(scope='actual HOST allocator/HC22/native endpoint -> typed548 -> real static SRAM/CRC link -> retained receiver -> actual head accepted context; actual TT macro receipt ledger, DW event fixture; two-copy/cohort/physical joins remain open',sources=pins,codec_sha256=hashlib.sha256((ROOT/D/'qkd_context_records.sv').read_bytes()).hexdigest(),outcomes='positive PASS, image digest/cap/runtime epoch mutants observed FAIL',fixed_edges=dict(codecTX=1,linkTX=3,modeledPHY=5,linkRX=1,codecRX=1))
 (out/'status.json').write_text(json.dumps(status,indent=2)+'\n');print('PASS actual HOST source/static SRAM context and observed image/cap/epoch mutants')
if __name__=='__main__':run()
