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
  scope='Actual source program into real control/SU/embedding/VM; no measured physical route or full token claim'),indent=2)+'\n')
if __name__=='__main__':write(sys.argv[1])
