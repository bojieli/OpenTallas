#!/usr/bin/env python3
"""Compile one actual fixed-slot P8/K5120 FP32 activation operation and VM owner slots.

The record base is caller-owned, never relocated. This component compiler does
not invent whole-token issue timestamps, input provenance or a global allocator.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from hbm_vm_static_calendar import layout,compile_schedule


def compile_operation(base_word=0):
    if base_word%64 or not 0 <= base_word < 65536 or base_word+8*5120>65536:
        raise ValueError('Actual SID0 FP32 P8K5120 tensor must be64wordaligned and whollyresident; no modulo relocation')
    words=[0]*703;requests=[];emissions=[]
    for pair in range(20):
        g,tp=divmod(pair,4)
        for j in range(4):
            for p in range(8):
                t=pair*32+j*8+p
                sector=base_word//8+p*640+(g*4+j)*32+tp*8
                word=1|(sector<<1)|((pair&1)<<17)|(p<<18)|(j<<21)|(pair<<39)
                words[t]|=word
                requests.append(dict(programme_ordinal=t,sector=sector,pair=pair,column=p,lane=j,VM_owner_ordinal=t+3,VM_read_group=2))
        for b in range(26):
            t=pair*32+61+b;a=2*pair+b//13;group=b%13;last=pair==19 and b==25
            words[t]|=(1<<23)|((pair&1)<<24)|(a<<25)|(group<<32)|(int(last)<<36)
            emissions.append(dict(programme_ordinal=t,address=a,group=group,last=last))
    abi=json.loads((ROOT/'results/arch/hbm_vm_static_1014/quadrant_abi_sw_quant_v2.json').read_text())
    vm=[{} for _ in words]
    for r in requests:vm[r['VM_owner_ordinal']]=dict(rslot_v=255,rslot=sum(2<<(3*b) for b in range(8)))
    vm_program=compile_schedule(layout(abi,'SW'),dict(cycles=vm))
    programme=dict(start=dict(base=0,limit=len(words),loops=1),configuration_writes=[
        dict(addr=pc,data=f'{(0xc7a1<<240)|(pc<<224)|word:064x}') for pc,word in enumerate(words)])
    return dict(schema='opentallas.hbm.sm-activation-operation.v1',target=126,PCW=10,payload_bits=44,
                vm_profile='sw_quant_v2',native_shape=dict(P=8,K=5120,fmt=1,NC=8,SUB=4),base_word=base_word,
                programme=programme,VM_programme=vm_program,requests=requests,emissions=emissions,
                relative_start='Decoded engine start = decoded VM start+2, matching measured external-target versus VM start rungs; actual host composition separate',
                expected=dict(read_waves=640,source_FP32_words=40960,xwrite_beats=520,predicted_first_XWRITE_after_engine_start=71,predicted_last_XWRITE_after_engine_start=704),
                qualification='One full-shape activation operation; actual source/VM/SRAM/golden gate required. Fulltoken programme paging/VM allocation/producer timestamps and32SM physicalbroadcast not qualified.')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('out',type=Path);ap.add_argument('--base-word',type=lambda x:int(x,0),default=0);a=ap.parse_args()
    image=compile_operation(a.base_word);a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'operation.json').write_text(json.dumps(image,indent=2)+'\n')
    for name,program in [('activation',image['programme']),('vm',image['VM_programme'])]:
        (a.out/(name+'.hex')).write_text('\n'.join(item['data'] for item in program['configuration_writes'])+'\n')
    print('Compiled640fixedVMwaves/520originalXWRITEbeats withactualindependentVMprogramme')
