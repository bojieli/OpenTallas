#!/usr/bin/env python3
"""Real HOST loader, typed metadata and actual macro write/readback component gate."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/qwen_sys/context_transport_20261014/tb_qkd_host_record_port.sv','rtl/qwen_sys/context_transport_20261014/qkd_host_record_port.sv','rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv','rtl/qwen_sys/host_20261013/qkd_host_program_loader.sv','rtl/qwen_sys/context_transport_20261014/qfd_program_record_port.sv','rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv']
def main():
 out=ROOT/'results/rtl/qwen_q_export_1014/host_record_port';out.mkdir(parents=True,exist_ok=True)
 macro='physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v'
 data=subprocess.check_output(['git','show','origin/main:'+macro],cwd=ROOT)
 with tempfile.TemporaryDirectory(prefix='q_host_record_')as td:
  mem=Path(td)/'macro.v';mem.write_bytes(data);exe=Path(td)/'sim'
  result=subprocess.run(['iverilog','-g2012','-s','tb_qkd_host_record_port','-o',str(exe)]+SOURCES+[str(mem)],cwd=ROOT,capture_output=True,text=True)
  (out/'compile.log').write_text((result.stdout+result.stderr).replace(td,'<gate_tmp>'))
  if result.returncode:raise RuntimeError(result.stderr)
  for mut,name in [(0,'actual_HOST_typed_macro_readback'),(5,'auth_digest_rejected'),(6,'capability_rejected'),(7,'missing_actual_commit_rejected')]:
   r=subprocess.run(['vvp',str(exe),'+MUT='+str(mut)],cwd=ROOT,capture_output=True,text=True)
   (out/(name+'.log')).write_text(r.stdout+r.stderr)
   if r.returncode or 'PASS 'not in r.stdout:raise RuntimeError(name+':'+r.stdout+r.stderr)
  revoke='rtl/qwen_sys/program_receiver_20261014/tb_qkd_program_join_revoke.sv'
  subprocess.run(['iverilog','-g2012','-s','tb_qkd_program_join_revoke','-o',str(exe),revoke,SOURCES[-1]],cwd=ROOT,check=True)
  r=subprocess.run(['vvp',str(exe)],cwd=ROOT,capture_output=True,text=True);(out/'actual_copy_revocations.log').write_text(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError(r.stdout+r.stderr)
  mutant=Path(td)/'stale_join.sv';mutant.write_text((ROOT/SOURCES[-1]).read_text().replace('if(complete&&(',"if(1'b0&&("))
  subprocess.run(['iverilog','-g2012','-s','tb_qkd_program_join_revoke','-o',str(exe),revoke,str(mutant)],cwd=ROOT,check=True)
  r=subprocess.run(['vvp',str(exe)],cwd=ROOT,capture_output=True,text=True);(out/'stale_copy_receipt_mutant.log').write_text(r.stdout+r.stderr)
  if not r.returncode or 'FATAL:'not in r.stdout:raise RuntimeError('stale copy receipt mutation escaped')
 status=dict(scope='real HOST loader -> typed kind13 -> two independent observed1024PW actual4SRAM inputs/readback plus one genuineSU8DW receipt with TT1edge observation relay -> typed kind14 -> trusted actual PW1023 footer HOST witness; parent lint separately required; no native complete-token/physical/phase qualification',sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in SOURCES+['rtl/qwen_sys/program_receiver_20261014/tb_qkd_program_join_revoke.sv']},macro_source=macro,macro_sha256=hashlib.sha256(data).hexdigest(),fixed_edges={'HOST_record_TX':2,'metadata_RX':1,'bench_actual_data_relay':4,'bench_macro_pin_register':1,'actual_write_observer_register':1,'witness_TX':1,'HOST_witness_RX':1},negative_controls=['auth_digest_rejected','capability_rejected','missing_actual_commit_rejected'])
 (out/'status.json').write_text(json.dumps(status,indent=2)+'\n');print('PASS actual HOST typed metadata/SRAM readback/commit witness and 3 rejection controls')
if __name__=='__main__':main()
