#!/usr/bin/env python3
"""Actual embedding ISA image for logical region execution, never physical release.

The chosen test clocks have equal phase. Fixed mechanism slots are explicit test
parameters. The production lowerer still requires its qualified route receipt.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_static_schedule.issue_rom import pw_image
from qwen_static_schedule.collective import pw_image as coll
from qwen_static_schedule.segments import program_segments,requires_constant_rom
import hdc_qwen_fullshape_isa_w12 as ISA

def write(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 source=ROOT/'results/arch/qwen_tp8_native_dispatch_1014/token_source_plan/embedding_program.hex';raw=source.read_bytes();words=[int(w,16)for w in raw.split()]
 descriptors=[0]*8;segments=program_segments(raw,descriptors)
 assert len(words)==2 and len(segments)==1 and not requires_constant_rom(raw)
 # Component mechanism clock: all roots share an explicit logical fixture phase.
 # This is deliberately not a measured die/native production profile.
 core_start=4;me_stop=360;su_stop=400;outer_end=core_start+su_stop+2;stop=420
 cal=dict(issues=[dict(stage=0,pc=0,unit=2,time_fs=40),dict(stage=0,pc=1,unit=0,time_fs=su_stop)],
  events=[dict(stage=0,pc=1,kind='owner_end',owner=o,time_fs=t)for o,t in [(1,me_stop),(2,su_stop)]])
 image=[0]*1024
 for pc,word in enumerate(words):
  for k in range(16):image[16*pc+k]=(word>>(64*k))&((1<<64)-1)
 for w in pw_image(cal,0,dict(period_fs=1,phase_fs=0,stop_cycle=me_stop),dict(period_fs=1,phase_fs=0,stop_cycle=su_stop),2)+coll([],0,0,stop,2):image[w['address']]=int(w['data_hex'],16)
 image[961]=core_start|(outer_end<<32);image[964]=0
 image[973]=(0x53475431<<32)|stop;image[974]=(0x53475453<<32)|1
 image[1023]=(0x58504631<<32)|6 # source footer has one XPF slot; this region emits no XPF work
 (out/'PW.hex').write_text(''.join(f'{v:016x}\n'for v in image));(out/'DW.hex').write_text('0000000000000000\n'*8)
 (out/'contract.json').write_text(json.dumps(dict(status='LOGICAL_COMPONENT_CLOCKS_NOT_PRODUCTION_PROFILE',
  source_program=str(source.relative_to(ROOT)),source_program_sha256=hashlib.sha256(raw).hexdigest(),
  actual_instruction_count=2,actual_descriptors=segments,requires_constant_rom=False,
  fixed_test_slots=dict(core_start=core_start,ME_END=me_stop,SU_END=su_stop,core_end=outer_end,stage_stop=stop),
  operation_binding=[dict(pc=0,encoded_sha256=hashlib.sha256(words[0].to_bytes(128,'little')).hexdigest(),
    rtl_instance='u_control_vm.u_seq.u_seq.u_ctrl',rtl_source='rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_su_static.sv',
    command_port='po_su_go',receiver='u_math.si[481:0]',
    raw_operand_provider='u_embedding.embed_code_q[511:0]/embed_scale_q[15:0]',decoded_operand='u_math.external_a_q[2047:0]',
    result='u_math.va[2366:0] -> u_control_vm.u_vm.sa',
    actual_elements=ISA.decode_instruction(words[0])['su_nin'],vector_bits_per_edge=2048,vector_write_slots=64,
    scalar_reduction_port='u_math.va[2366:2310]',scalar_reduction_address=ISA.decode_instruction(words[0])['r_base'],
    scalar_reduction_count=1,source_vector_address=ISA.decode_instruction(words[0])['d_base'],
    scalar_address_end=ISA.decode_instruction(words[0])['d_base']+4095,
    VM_address_overflow=False,raw_token_address_wrap='intentional AW24 element offset; controller recovers full token18 in token*64 code address'),
    dict(pc=1,command_port='fixed_end',result='u_me_control.m_fin_o -> xm[50] and actual SU core_done -> fixed outer integrity check')],
  source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in[
    'rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_su_static.sv','rtl/qwen_split/qfd_sp_su64_sfu.sv',
    'rtl/qwen_split/qfd_su_vm_pack.sv','rtl/qwen_split/qfd_embedding_stage_static.sv']},
  scope='Actual source program into real control/SU/embedding/VM; no measured physical route or full token claim'),indent=2)+'\n')
if __name__=='__main__':write(sys.argv[1])
