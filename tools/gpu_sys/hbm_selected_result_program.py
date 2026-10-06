#!/usr/bin/env python3
"""Opt-in native-LSU consumer of the real formatter HBM sink.

Produces instruction/command source only. It neither supplies result data nor
asserts publication, book, release, CP launch, or completion. Gibbs installs
this program in his existing parent only after the actual retained allocation
and same-context launch contract are bound. Gauss owns its numerical writer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from isa import enc,dec

SINK_BASE=0x70000
SINK_LIMIT=0x70800
PROGRAM_WORDS=(
    enc('UMOVI',4,0,0,SINK_BASE),
    enc('LDG',0,4,0,0),             # U4, 32-bit raw bits, exactly one lane
    enc('UFROMV',5,0,0,0),         # scoreboard waits for V0, actual loaded lane0
    enc('RESULT',0,5,0,0),         # U5; never the input token in U0
    enc('EXIT'),
)

def source_program(*,enable=False,entry_pc=None,imw=14):
    if not enable:
        return None
    if entry_pc is None or not isinstance(entry_pc,int) or entry_pc<0:
        raise ValueError('caller must allocate the actual result entry PC')
    if imw!=14 or entry_pc+len(PROGRAM_WORDS)>(1<<imw):
        raise ValueError('five words must fit actual selected-parent IMW14')
    # Original CP launches SM0 only, then original END validates RESULT/TOKEN17.
    # Gibbs inserts this list into the actual protected current CP session;
    # this helper does not start a new doorbell or invent a job/frame.
    commands=((1<<60)|(1<<44)|entry_pc,2<<60)
    return dict(instructions=PROGRAM_WORDS,commands=commands,entry_pc=entry_pc,
                instruction_addresses=list(range(entry_pc,entry_pc+5)),
                enabled=True,allocation_and_launch_bound=False,
                native_producer_to_RESULT_qualified=False)

def emit(out:Path,*,enable=False,entry_pc=None):
    program=source_program(enable=enable,entry_pc=entry_pc)
    if program is None:
        raise ValueError('default OFF; --enable explicitly selects source generation')
    out.mkdir(parents=True,exist_ok=False)
    # Readmemh placement is actual caller-supplied PC, not an invented global0.
    text='@%x\n'%entry_pc+''.join('%016x\n'%w for w in program['instructions'])
    (out/'result_kernel.mem').write_text(text)
    (out/'result_commands.mem').write_text(''.join('%016x\n'%w for w in program['commands']))
    lines=[]
    for pc,word in zip(program['instruction_addresses'],program['instructions']):
        lines.append(dict(pc=pc,word='%016x'%word,decoded=list(dec(word))))
    root=Path(__file__).resolve().parents[2]
    pins={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in [
        'tools/gpu_sys/isa.py','tools/gpu_sys/hbm_selected_result_program.py',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_simt_sm20.sv',
        'rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv']}
    manifest=dict(schema='opentallas.hbm.selected_result.program.v1',**program,
        instruction_disassembly=lines,source_pins=pins,
        sink_byte_base=SINK_BASE,sink_byte_limit=SINK_LIMIT,selected_ID_ordinal=0,
        semantics='native LSU reads real stored U32 selected-ID; UFROMV transfers lane0 to U5; RESULT publishes U5',
        expected_payload_injected=False,new_SM_opcode=False,new_parent=False,
        launch_owner='Gibbs actual protected CP session and disjoint integration',
        launch_requirements=['Gauss actual32 checked full73 sink rows accepted and final ACK/debt drained',
          'actual consumer/source reverse then shared borrower release/native route drained',
          'same full73 actual CP context plus real sink reservation retained through LSU read/RESULT/EXIT/CP completion',
          'five caller-allocated instruction words and actual existing CP LAUNCH/END commands installed without touching pinned prior commands'],
        CP_contract='full32bit SM result; original CP END refuses values above TOKEN17 as status3; no truncation waiver',
        integration_block='current preinstall/install-consumer clear retained book at shared release; persistent same-frame sink reservation/entry allocation must come from real parent owner',
        numerical_qualified=False,physical_qualified=False)
    (out/'program.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--enable',action='store_true');p.add_argument('--entry-pc',type=lambda x:int(x,0),required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();emit(a.out,enable=a.enable,entry_pc=a.entry_pc)
