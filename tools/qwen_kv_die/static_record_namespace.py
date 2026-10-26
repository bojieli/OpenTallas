#!/usr/bin/env python3
"""Canonical shared548 namespace; a reserved kind is not an implemented producer.

The historical528 class adapters add20 sequence/class/credit bits to form548.
That old framing is not this static payload and cannot be passed through as if
it were a new typed record. HOST physical class8 program loading remains on
its separate528 transport until an actual bridge is implemented and measured.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CODEC='rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv'
LEGACY_KV='rtl/qwen_sys/split_20261014/ot_qkvd_split_kvlink.sv'
LEGACY_COMPUTE='rtl/qwen_sys/split_20261014/ot_qfd_split_romlink.sv'

def schema():
    kinds=[]
    for code,name,direction,bits,detail in [
        (1,'NATIVE_COMMAND','compute_to_kv',19,'data[18:1]=position18,data[0]=capability; beat0'),
        (2,'NATIVE_Q','compute_to_kv',512,'32 actual Q512 beats; beat0..31'),
        (3,'NATIVE_RESULT','kv_to_compute',512,'32 actual result512 beats; beat0..31'),
        (4,'NATIVE_STATUS','kv_to_compute',5,'data[4:0]={q_ready,done,fault,busy,ready}; beat0; observation/fault only'),
        (5,'KV_ROW_WRITE','compute_to_kv',512,'Legacy KVN tag3 is reserved in beat[2:0],beat[4:3]=0; source phase/epoch/layer required'),
        (6,'EMBEDDING_REQUEST','compute_to_kv',25,'Legacy ea_kind=data[24],ea_addr=data[23:0]; beat0'),
        (7,'EMBEDDING_RESULT','kv_to_compute',512,'Actual gateway eq_d512; beat0'),
        (8,'SEQUENCER_CONFIG','compute_to_kv',56,'Legacy sd56 full levels; beat0'),
        (9,'KV_WRITE_DESCRIPTOR','compute_to_kv',43,'Legacy kvd[42:0]; actual event is kvd[43]; beat0'),
        (10,'SEQUENCER_CONTROL','kv_to_compute',262,'Legacy data[261:0]={pw75,ds187}; beat0'),
    ]:
        attention=code<=4
        kinds.append(dict(code=code,name=name,direction=direction,data_bits=bits,format=detail,
            boundary_rtl=CODEC if attention else None,
            actual_static_producer='MISSING_INTEGRATED_COMPILED_PRODUCER',
            legacy_source=None if attention else [LEGACY_COMPUTE,LEGACY_KV],
            status='TYPED_BOUNDARY_COMPONENT_VERIFIED' if attention else 'RESERVED_SOURCE_BACKED_FORMAT_ONLY',
            production_adoption='REQUIRES_ACTUAL_SOURCE_PRODUCER_CONSUMER_AND_COMPILED_SLOT_CONTRACT'))
    kinds += [dict(code=12,name='HOST_NATIVE_CONTEXT',direction='kv_to_compute',data_bits=142,
        format=dict(tag59=[58,0],generation2=[60,59],attested_fused_capability=61,
                    image_epoch16=[77,62],image_digest64=[141,78],reserved_zero=[511,142],
                    header_layer=63,token_context='Actual HOST token-wide TAG59 stage0/beat0; later layer comes from actual accepted CALS stage'),
        layout_owner='q_control_transport',actual_static_producer='MISSING_INTEGRATED_COMPILED_PRODUCER',
        production_adoption='REQUIRES_ACTUAL_HOST_CONTEXT_AND_INSTALLED_PROGRAM_CAPABILITY_WITNESS')]
    for code,name,direction in [(13,'PROGRAM_IMAGE_AUTH_METADATA','kv_to_compute'),
                                (14,'PROGRAM_IMAGE_COMMIT_WITNESS','compute_to_kv')]:
        kinds.append(dict(code=code,name=name,direction=direction,data_bits=None,
            format='RESERVED; exact actual encoder/receiver field ABI pending q_control_transport',
            layout_owner='q_control_transport',actual_static_producer='MISSING_INTEGRATED_COMPILED_PRODUCER',
            production_adoption='REJECT_UNTIL_EXACT_SOURCE_LAYOUT_AND_ACTUAL_COMMIT_PRODUCER_EXIST'))
    sources=[CODEC,LEGACY_KV,LEGACY_COMPUTE]
    return dict(schema='opentallas.shared548.namespace.v2',payload_bits=548,
        fields=dict(reserved_zero=[547,543],kind=[542,539],layer=[538,533],epoch=[532,517],beat=[516,512],data=[511,0]),
        kinds=kinds,invalid_kind=0,unassigned_kinds=[11,15],
        separate_transport=[dict(name='HOST_PROGRAM_CLASS8',width=528,
            producer='qkd_host_program_loader:pr143',route='actual per-rank HOST physical class8',
            status='NOT_A_548_PRODUCER; no implicit conversion',
            reason='A real static548 bridge must be implemented before this namespace can carry it')],
        full_command380='Compute-local native59 accepted descriptor; not silently replaced by native CMD19. Native CMD carries only actual kernel interface after full descriptor validation.',
        legacy_framing='Historical548={sequence/credits/class20,class_word528}; incompatible with this typed548 static payload.',
        scheduling='Compiler slots exclusively select every source and resource; no runtime priority, credits or ready-driven selection.',
        sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources})


def require_producer(name,contract):
    """Reject namespace reservations as compiler producer contracts.

    Compiler owns the complete source/port/reservation join. This guard checks
    only minimal mandatory source evidence and never certifies native timing.
    """
    kind=next((x for x in schema()['kinds'] if x['name']==name),None)
    if kind is None:
        raise ValueError(f'undeclared shared548 kind {name}')
    if kind['data_bits'] is None:
        raise ValueError(f'{name}: reserved kind has no exact actual source field layout')
    required=('producer_rtl','producer_module','producer_event_port','consumer_rtl','consumer_module',
              'consumer_event_port','normal_issue','source_clock_family','destination_clock_family',
              'fixed_latency_edges','compiled_slot_contract')
    missing=[x for x in required if x not in contract]
    if missing:
        raise ValueError(f'{name}: missing actual static producer/consumer contract: {missing}')
    if contract['normal_issue']!='compiled_event':
        raise ValueError(f'{name}: normal issue must be a compiled event')
    if type(contract['fixed_latency_edges']) is not int or contract['fixed_latency_edges']<0:
        raise ValueError(f'{name}: missing fixed actual latency')
    for role in ('producer','consumer'):
        file=ROOT/contract[role+'_rtl']
        if not file.is_file():
            raise ValueError(f'{name}: missing actual {role} RTL {file}')
        # Actual elaboration/port/phase evidence is joined by compiler/native
        # binding audits, not inferred from a reserved code or a file name.
    return kind['code']

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(schema(),indent=2)+'\n')
