#!/usr/bin/env python3
"""Bind source-pinned native operand traces to actual one-port VM calendars.

Events name the bank INPUT capture edge relative to first VM programme output.
Thus word ordinal is capture_edge-1; this is the actual output/input register
seam, not a token timestamp. Producer traces and their absolute launch authority
must be supplied, never inferred from source operation order.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from hbm_vm_static_calendar import layout,compile_schedule


def compile_bindings(inventory, binding, abi, source_root=ROOT):
    if binding['inventory_source_sha256'] != inventory['source_sha256']:
        raise ValueError('Native allocation source profile changed')
    count=int(binding['programme_words'])
    if not 1 <= count <= 1024:
        raise ValueError('Actual VM programme capacity1024 exceeded; explicit paging source required')
    cycles={q:[{} for _ in range(count)] for q in abi['quadrants']}
    quadrant={value['sid']:q for q,value in abi['quadrants'].items()}
    used={};requests=[]
    for trace in binding['producers']:
        record=inventory['records'][int(trace['record_ordinal'])]
        if trace['record_sha256'] != record['record_sha256']:
            raise ValueError('Native operation record changed')
        rtl=source_root/trace['rtl']
        if hashlib.sha256(rtl.read_bytes()).hexdigest()!=trace['rtl_sha256']:
            raise ValueError('Actual producer RTL source changed')
        if not trace.get('launch_authority'):
            raise ValueError('Actual producer launch authority required')
        for event in trace['events']:
            operand=record['operands'][event['operand']]['allocation']
            if operand['status']!='static source range, no relocation granted':
                raise ValueError('Runtime operand requires actual runtime address producer proof')
            sector=int(event['sector']);bank=sector&7;sid=(sector>>13)&3
            if sector<0 or sector>=32768:
                raise ValueError('Native main VM sector range exceeded')
            if sector*8>=operand['word_end'] or (sector+1)*8<=operand['word_begin']:
                raise ValueError('Event is outside actual encoded operand allocation')
            q=quadrant[sid]
            if q!=event['quadrant']:
                raise ValueError('Physical quadrant differs from actual canonical SID; explicit transport required')
            kind=event['kind']
            if kind not in ('read','write'):raise ValueError('Unknown physical port direction')
            owner=int(event['owner']);params=abi['quadrants'][q]['params']
            if not 0<=owner<=(params['RG'] if kind=='read' else params['WG']+4):
                raise ValueError('Logical owner does not exist on actual bank')
            edge=int(event['bank_capture_edge']);word=edge-1
            if not 0<=word<count:raise ValueError('Reservation outside programme capture window')
            key=(q,bank,kind,edge)
            if key in used:
                raise ValueError(f'One physical {kind} port collision at {key}')
            used[key]=trace['record_ordinal']
            fields=cycles[q][word];name='rslot' if kind=='read' else 'wslot'
            fields[name+'_v']=fields.get(name+'_v',0)|(1<<bank)
            bits=params['RB' if kind=='read' else 'WB']
            fields[name]=fields.get(name,0)|(owner<<(bank*bits))
            if 'lg_tap' in event:
                tap=int(event['lg_tap'])
                if tap not in (0,1,2)or owner!=0:raise ValueError('LG source must own actual group0')
                local_word=word-2*(tap+1)
                if local_word<0:raise ValueError('LG request precedes programme start')
                flag='lg_local_'+kind
                fields_local=cycles[q][local_word]
                fields_local[flag]=fields_local.get(flag,0)|(1<<(tap*8+bank))
            requests.append(dict(record=trace['record_ordinal'],operand=event['operand'],quadrant=q,
                sector=sector,bank=bank,kind=kind,owner=owner,bank_capture_edge=edge,vm_word=word))
    programmes={q:compile_schedule(layout(abi,q),dict(cycles=c,loops=1))for q,c in cycles.items()}
    return dict(schema='opentallas.hbm.native-bound-port-programmes.v1',programmes=programmes,
        reservations=requests,source_binding=binding,qualification='Actual source allocation/port conflict/compiler check only; producer trace/native hardware composition and absolute whole-kernel clocks require separate proof')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','bindings','abi','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();result=compile_bindings(json.loads(a.inventory.read_text()),json.loads(a.bindings.read_text()),json.loads(a.abi.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(f"PASS {len(result['reservations'])} actual port reservations into four native SRAM programmes")
