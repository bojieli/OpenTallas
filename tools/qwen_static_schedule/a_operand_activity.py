#!/usr/bin/env python3
"""Source-pinned A-operand demand; never substitutes logical beats for die ages."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import hdc_qwen_fullshape_isa_w12 as ISA
PLAN=ROOT/'results/arch/qwen_tp8_native_dispatch_1014/token_source_plan'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def activity(path):
 ops=[];total=dict(SU_vector_issue_edges=0,A_lane_reads=0,A_VM_vector_requests=0,A_embedding_vector_requests=0,A_return_payload_bits=0)
 for pc,w in enumerate(path.read_text().split()):
  f=ISA.decode_instruction(int(w,16));op=dict(pc=pc,unit=f['unit'],instruction_sha256=hashlib.sha256(int(w,16).to_bytes(128,'little')).hexdigest(),compiled_issue_cycle=None,completion_cycle=None)
  if f['unit']==2:
   if f['su_d_nin']!=0:raise ValueError('dynamic nin requires actual runtime context; do not invent count')
   nout,nin=f['su_nout'],f['su_nin'];beats=nout*((nin+63)//64);lanes=nout*nin;embedding=bool(f['a_src'])
   op.update(command='SU',nout=nout,nin=nin,vector_issue_edges=beats,active_lane_reads=lanes,A_source='embedding'if embedding else'VM',A_base=f['a_base'],A_inner_stride=f['a_si'],A_outer_stride=f['a_so'],dynamic_A_base_selector=f['a_d'],A_VM_vector_requests=0 if embedding else beats,A_embedding_vector_requests=beats if embedding else 0,request_mask_address_bus_bits=1600,return_bus_bits=2048,active_return_payload_bits=lanes*32,provider_code_read_bus_bits=512 if embedding else 0,dependencies=['actual SU lane A request -> gateway registered select/index -> selected VM/embedding result -> actual SU alignment'],B_source='CROM'if f['b_src']else'VM',C_source='CROM'if f['c_src']else'VM')
   total['SU_vector_issue_edges']+=beats;total['A_lane_reads']+=lanes;total['A_VM_vector_requests']+=op['A_VM_vector_requests'];total['A_embedding_vector_requests']+=op['A_embedding_vector_requests'];total['A_return_payload_bits']+=lanes*32
  elif f['unit']==1:op.update(command='ME',descriptor={k:f[k]for k in ['me_nout','me_tiles','me_k','me_xbase','me_obase','me_wbase']},dependencies=['actual fixed TT command -> physical ME operand/ROM producer -> actual registered result -> VM visibility'],missing_fields=['actual ME stage calendar and qualified physical transport ages'])
  else:op.update(command='END',dependencies=['fixed owner END calendar and actual observation fault checks'])
  ops.append(op)
 return dict(program=str(path.relative_to(ROOT)),program_sha256=sha(path),operations=ops,totals=total,physical_scheduled_cycles=None,qualification='SOURCE_DEMAND_ONLY_NOT_MEASURED_EXECUTION_OR_PRODUCTION_PROFILE')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=ROOT/'results/arch/qwen_a_operand_gateway_1015/programme_activity.json');args=ap.parse_args()
 files=['tools/hdc_qwen_fullshape_isa_w12.py','rtl/qwen_sys/static_schedule_20261014/ot_qwen_a_operand_gateway_v1.sv','rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_su_static.sv','rtl/qwen_sys/static_schedule_20261014/ot_hdc_vstream_static_entries.sv','rtl/hdc/ot_hdc_vstream_lane.sv','rtl/qwen_sys/static_schedule_20261014/ot_qfd_sp_su64_static_entries.sv']
 out=dict(status='ACTUAL_PROGRAMME_SOURCE_BOUND_DEMAND',lane_width=64,programmes=[activity(PLAN/name)for name in ['embedding_program.hex','layer_candidate_program.hex']],source_sha256={p:sha(ROOT/p)for p in files},boundary_ownership=dict(before=['SU requests1600 -> seq gateway','gateway VM requests1600 -> SU compact pack -> VM','VM return2048 -> seq gateway','gateway selected return2048 -> SU'],after=['SU requests1600 -> local gateway','local gateway VM requests1600 -> local SU compact pack -> VM','VM return2048 -> local gateway','local gateway selected return2048 -> SU'],controller_to_gateway='start_idle1 + current token18 + captured token18 + su_go1 + a_src1; same source clock observations',gateway_to_controller='64 fault bits; original registered sticky fault capture unchanged'),unknown_fields=['global issue cycles','actual ME completion cycles','physical root phases','gateway outline/home/route ages','complete token/MTP schedule'])
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({p['program']:p['totals']for p in out['programmes']},indent=2))
if __name__=='__main__':main()
