#!/usr/bin/env python3
"""Reproduce explicit SID0 SW Quant target125 boundary fixture and bank calendar.

The first record uses original source addresses. Later records use independent
SID0 fixture regions to measure pipeline service. No native token dependency or
SU producer/DMA consumer issue epoch is invented by this component generator.
"""
import argparse
import dataclasses
import hashlib
import json
from pathlib import Path
from hgi_sim.records import decode_one
from hgi_static_quant_calendar import compact_record_words,lower_record


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path('results/hbm_static_quant_1015/SW_replica'))
    ap.add_argument('--io-regs',type=int,choices=[0,1],default=0);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True);vectors=a.out/'vectors';vectors.mkdir(exist_ok=True)
    source=Path('results/hbm_static_quant_1015/native_inventory/records.json')
    original=next(x for x in json.loads(source.read_text()) if x['source_profile']=='full_rank0_g25')
    r,end=decode_one(bytes.fromhex(original['record_hex']),0)
    assert r.op=='QDQ_FP8' and r.desc['A'].base==51776 and r.desc['O'].base==52288 and r.desc['A'].n==512
    layout_source=a.out/'VM_layout_v2.json';layout=json.loads(layout_source.read_text())['SW']
    assert layout['params']['RG']==6 and layout['params']['WG']==2 and layout['bits']==202
    fields={f['name']:f for f in layout['fields']}
    records=[];times=[];rows=[];meta=[]
    for k in range(8):
        a_base,o_base=51776+1024*k,52288+1024*k
        rr=dataclasses.replace(r,desc={'A':dataclasses.replace(r.desc['A'],base=a_base),'O':dataclasses.replace(r.desc['O'],base=o_base)})
        records.append(rr);times.append(8+16*k);rows.append(f'4 512 {a_base} {o_base} 24 32')
        for side in ['in','out']:(vectors/f'{side}_{k}.hex').write_bytes(Path(f'tools/hgi_unit_tput/vectors/qdqvec/{side}_0.hex').read_bytes())
        meta.append(dict(record_hex=rr.encode().hex(),source_record_hex=original['record_hex'],source_path=original['source_path'],
            issue_cycle=8+16*k,component_fixture=True,
            relocation='first real L0 addresses preserved; independent k*1024-word SID0 fixture regions only, not full native programme allocation'))
    (vectors/'recs.txt').write_text('8\n'+'\n'.join(rows)+'\n')
    (vectors/'records.json').write_text(json.dumps(dict(resident_sid=0,component_boundary_only=True,records=meta),indent=2)+'\n')
    words=compact_record_words(records,times,0)
    (a.out/'program.hex').write_text(''.join(f'{w:064x}\n' for w in words))
    commands=[c for r,t in zip(records,times) for c in lower_record(r,t,0)]
    # Real host timing: SW programme reaches bank ordinal+7; command at tickt
    # reaches engine LCP+t+7. Read bank tick+8; write bank tick+42.
    write_delta=35+2*a.io_regs;length=max(c['cycle']+write_delta for c in commands)+5;slots=[0]*length
    for c in commands:
        for delta,address,enabled,selected,owner in [(1,'src','rslot_v','rslot',5),(write_delta,'dst','wslot_v','wslot',1)]:
            e,s=fields[enabled],fields[selected]
            for lane in range(4):
                bank=(c[address]+lane)&7;pc=c['cycle']+delta
                assert not (slots[pc]>>(e['lo']+bank)&1)
                slots[pc]|=(1<<(e['lo']+bank))|(owner<<(s['lo']+bank*3))
    words=[(0xc7a1<<240)|(pc<<224)|v for pc,v in enumerate(slots)]
    (a.out/'SW_program.hex').write_text(''.join(f'{w:064x}\n' for w in words))
    receipt=dict(component_boundary_only=True,target=125,resident_SID=0,native_source=original['source_path'],
        inventory_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),layout_sha256=hashlib.sha256(layout_source.read_bytes()).hexdigest(),
        records=8,beats=128,words=4096,immutable_per_record_price=24,immutable_sum_price=192,
        source_programme_words=8,SW_programme_words=length,model_elapsed_LCP_to_commit=181+2*a.io_regs,io_registered_boundary=a.io_regs,
        actual_SU_norm_rope_producer_join=False,actual_DMA_consumer_join=False)
    (a.out/'compiler_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
