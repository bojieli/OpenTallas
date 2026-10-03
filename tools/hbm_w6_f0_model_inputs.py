#!/usr/bin/env python3
"""F0-bound W6 model inputs and finite source-compatible reference.

No engine RTL, compact adapter, source quiescence implementation or priced
whole-bridge model is supplied here. Original W6 fixture remains historical.
"""
from dataclasses import asdict, dataclass
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
F0_REV='8535c3010c7354734ececca8a8d9109ced2f50a7'
F0_DIR='results/uarch/h4_hbm_f0_field_freeze_review_20261003'
F0_NAMES=('contract-r3.json','contract-r4-continuous.json','W2-interface-contract-r1.json')
F0_PINS={'contract-r3.json': '33cc4b195ace57bb28aa84c611a2f89bf219d17f35791af53cd9bf9cb5dc7a9e', 'contract-r4-continuous.json': '03a6f1973777cdf031986f605ceda9c74fa8f37d741757076ec59bd32efb7228', 'W2-interface-contract-r1.json': 'e3b21affdbe1e430311948a670f03e2a9f2f4b5d956c56e775744a12ca61707b'}
F0_ARCHIVE='results/uarch/hbm_W6_f0_model_inputs_20261003/r1/F0_inputs'


def require(ok, why):
    if not ok: raise ValueError(why)


def frozen_inputs():
    raw={n:(ROOT/F0_ARCHIVE/n).read_bytes() for n in F0_NAMES}
    require(all(hashlib.sha256(raw[n]).hexdigest()==F0_PINS[n] for n in F0_NAMES), 'immutable frozen F0 input pin')
    values={n:json.loads(v) for n,v in raw.items()}
    r3,r4,w2=(values[n] for n in F0_NAMES)
    require(w2['W2_model_extension']['original_client_tag_bits']==32 and
            w2['W2_model_extension']['backend_identity_total_bits']==39 and
            w2['W2_model_extension']['generation_bits']==4, 'frozen source-compatible fields')
    require(w2['exact_table']['row_minimum_raw_bits']==38, 'W2 minimum row')
    require(r4['source_program_domain']['Qwen']['required_program_PC_count']==1737 and
            r4['source_program_domain']['DS']['required_program_PC_count']==2213, 'full program domains')
    return values,{n:hashlib.sha256(v).hexdigest() for n,v in raw.items()}


@dataclass(frozen=True)
class SourceTuple:
    physical_PC:int
    client:int
    original_tag:int
    generation:int
    direction:int
    rank:int
    SM:int
    RF_slot:int
    program_PC:int
    home_id:int

    def validate(self, *, NC, model):
        require(NC in (5,6) and model in ('Qwen','DS'), 'explicit source variant/model')
        widths=dict(physical_PC=7,client=3,original_tag=32,generation=4,direction=1,
                    rank=7,SM=5,RF_slot=9,program_PC=12,home_id=32)
        for k,w in widths.items():
            v=getattr(self,k);require(type(v) is int and 0<=v<2**w,'source field bounds '+k)
        require(self.client<NC, 'client enrolled in exact NC variant')
        require(self.program_PC<(1737 if model=='Qwen' else 2213), 'source program PC domain')

    @property
    def physical_tag(self):
        return (self.client<<32)|self.original_tag

    def backend_echo(self):
        return dict(physical_PC=self.physical_PC,p_tag=self.physical_tag,p_generation=self.generation,
                    direction=self.direction)


def exact_backend_match(source, response):
    require(type(response) is dict and set(response)=={'physical_PC','p_tag','p_generation','direction'},
            'exact source-compatible echo fields')
    require(all(type(v) is int for v in response.values()), 'typed backend echo')
    require(response==source.backend_echo(), 'originaltag/generation/direction/PC mismatch')
    return True


def namespace_handle(*, namespace, physical_PC, tag):
    require(namespace in ('PC','coalescer'), 'explicit tag namespace')
    require(type(physical_PC) is int and 0<=physical_PC<128 and type(tag) is int and 0<=tag<65536,
            'scoped tag bounds')
    return namespace,physical_PC,tag


def generation_successor(generation):
    require(type(generation) is int and 0<=generation<16, 'generation4 range')
    return dict(next_generation=(generation+1)%16,
        admission='REQUIRES_SOURCE_ALL_COPIES_AND_MATCHED_REVERSE_CDC_QUIESCENCE',
        source_quiescence_installed=False, wrapped=(generation==15),run_cap=False)


class SourceFenceReference:
    """One complete C0 or KV-read fixture; preserves source tuple at each edge.

    Generation allocator/reset/quiescence is externally owned by Popper/W2.
    This fixture neither accepts a reuse certificate nor clears a real lease.
    """
    def __init__(self, *, enabled=False, NC=6, model='Qwen'):
        require(NC in (5,6) and model in ('Qwen','DS'),'source variant/model')
        self.enabled,self.NC,self.model=enabled,NC,model
        self.edge=0;self.phase='IDLE';self.active=None;self.last=-1;self.trace=[];self.held=None

    def tick(self,n=1):
        require(type(n) is int and n>0,'positive reference edges');self.edge+=n

    def accept(self, source, *, path, payload, read_version=None):
        require(self.enabled and self.phase=='IDLE','default-off/one outstanding source owner')
        source.validate(NC=self.NC,model=self.model)
        require(self.edge>self.last,'positive prior release to request edge')
        require(path in ('C0','KV_READ'),'first C0 then KV read scope')
        require(type(payload) is bytes and len(payload)==(512 if path=='C0' else 32),'full payload width')
        require(source.direction==(1 if path=='C0' else 0),'exact source direction')
        require((path=='C0' and read_version is None) or
                (path=='KV_READ' and type(read_version) is int and read_version>=0),'KV published version binding')
        self.active,self.path,self.payload,self.version=source,path,payload,read_version
        self.phase='COMPLETION';self.last=self.edge
        self.trace.append(dict(event='source_accept_fixture',edge=self.edge,source=asdict(source)))

    def completion(self, source, *, echo, payload, copy_mask=None, read_version=None):
        require(source==self.active and self.phase=='COMPLETION','stale/duplicate completion')
        exact_backend_match(source,echo)
        require(self.edge>self.last and type(payload) is bytes and payload==self.payload,'positive exact completion')
        if self.path=='C0':
            require(type(copy_mask) is int and copy_mask==3 and read_version is None,'both-copy write fixture prerequisite')
        else:
            require(copy_mask is None and type(read_version) is int and read_version==self.version,'KV exact read version')
        self.phase='VISIBILITY';self.last=self.edge
        self.trace.append(dict(event='completion_fixture',edge=self.edge,source=asdict(source),backend_echo=echo))

    def boundary(self, source, *, event, ready=True):
        transitions={'visibility':('VISIBILITY','CONSUMER'),'consumer':('CONSUMER','REVERSE'),
                     'reverse':('REVERSE','RETIRE'),'retire':('RETIRE','REUSE_PENDING')}
        require(source==self.active and event in transitions,'matching full owner source tuple')
        before,after=transitions[event]
        require(self.phase==before and self.edge>self.last and type(ready) is bool,'ordered positive boundary')
        # Reverse here is an explicit fixture stimulus, never an actual CDC receipt.
        packet=(source,event)
        require(self.held is None or self.held==packet,'stable held source tuple')
        if not ready:self.held=packet;return False
        self.held=None;self.phase=after;self.last=self.edge
        self.trace.append(dict(event=event+'_fixture',edge=self.edge,source=asdict(source),
                               payload_sha256=hashlib.sha256(self.payload).hexdigest()))
        # Retain source/credit in REUSE_PENDING: no local fake all-empty release.
        return True


def model_inputs():
    frozen,pins=frozen_inputs();r3,r4,w2=(frozen[n] for n in F0_NAMES)
    row=r3['layout_authorities']['private_context_fields']
    require(sum(row.values())==199,'exact F0 private context width')
    fields=dict(row,physical_PC=7,program_PC=12,copy_write_mask=2,
                consumer_accepted=1,child_reverse_accepted=1,parent_reverse_accepted=1,reverse_CDC_accepted=1)
    raw_bits=sum(fields.values());protected_bits=((raw_bits+63)//64)*72
    base_identity=35+4+7+1
    boundaries=[
      dict(name='W2_accept_to_W6_owner',owner='Nash/Goodall',identity_bits=base_identity,
           payload_bits=256,port_bytes=32,source_ready_is_visibility=False),
      dict(name='W4_common_ACK_to_visibility',owner='Euclid/Goodall',identity_bits=32+4+7+3+5+7+9,
           payload_bits=0,port_bytes=0,common_ACK_bit=1,old_RF_ACK_identity=False),
      dict(name='visibility_to_consumer_accept',owner='Goodall/Popper',identity_bits=32+4+7+3+5+7+9,
           payload_bits=4096,port_bytes=512),
      dict(name='KV_read_capture_to_consumer',owner='Nash/Goodall/Popper',identity_bits=base_identity,
           payload_bits=256,port_bytes=32,published_version_width=None),
      dict(name='consumer_to_child_reverse_to_parent_reverse',owner='Goodall/Dewey/Popper',
           identity_bits=base_identity,payload_bits=0,port_bytes=0),
      dict(name='reverse_CDC_to_reuse',owner='Popper/Nash',identity_bits=base_identity,
           payload_bits=0,port_bytes=0,reset_epoch_wire_width=None)]
    for b in boundaries:
        b.update(valid_ready_bits=2,positive_cycles_required=True,cycles=None,
                 priced_bits_per_cycle=None,routing_tracks=None,channel_capacity=None,
                 metadata='source tuple retained in private context; actual boundary layout/lookup ports must be composed, no compact/tag truncation',
                 minimum_known_bits=b['identity_bits']+b['payload_bits']+2+b.get('common_ACK_bit',0))
    return dict(schema='HBM_W6_F0_SOURCE_COMPATIBLE_MODEL_INPUTS_V1',
        status='F0_BOUND_W2_W4_W6_COMPOSED_MODEL_AND_ACTUAL_CALLER_BINDING_PENDING',
        F0_revision=F0_REV,F0_contract_sha256=pins,default_off=True,new_engine_RTL=False,
        source_compatible=dict(CTAGW=32,PTAGW=35,generation_sideband=4,backend_tag_plus_generation=39,
            original_tag_overwritten=False,compact_parent16_selected=False,
            physical_PC_namespace_bits=7,program_PC_bits=12),
        W2=dict(row_minimum_bits=38,NC5_rows_per_PC=80,NC6_rows_per_PC=96,
            NC5_raw_bits_per_PC=3040,NC6_raw_bits_per_PC=3648,PCs=128,
            row_minimum_is_full_context=False,full_wrapper_client5='occupied KV',directory_caller_mapping=None),
        caller_mapping=dict(C0='actual service requester SM/rank/programPC/home not yet port-bound',
            KV='actual source adapter client5 in NC6 fixture; caller generation echo absent',
            old_C0_software_owner64='not original hardware CTAG32; reversible source adapter required',
            coalescer16='client6/batchslot6/gen4; distinct from PC client3/SM5/slot4/gen4'),
        W6_state_candidate=dict(raw_fields=fields,raw_bits_per_slot=raw_bits,
            SECDED64_padded_protected_bits_per_slot=protected_bits,
            one_pending_slot_per_SM_candidate=32,aggregate_protected_bits=protected_bits*32,
            allocation='candidate W6 slots only, not W2 table or full bridge contexts; reconcile F0 baseline once, avoid double charge',
            payload_landing_bits=0,landing_zero_condition='actual source lease retains payload through consumer; if unavailable charge512B C0/32B KV buffer',
            identity_compare_widths_by_boundary={b['name']:b['identity_bits'] for b in boundaries},
            full_fixture_source_tuple_bits=112,
            full_context_lookup_requires='originaltag32/gen4/PC7/client3 must resolve retained SM/rank/RF/home/programPC; narrower wire does not discard private identity',
            identity_compare_count=6,
            RF_bank_enable_fanout=32,full_model_replication_count=None,selector_and_fanout_area=None,
            mutable_control_protection_retained=True,reset_cohort_width=None,model_area_admitted=False,
            raw_state_count_is_complete=False,
            unpriced_state=['accepted beat masks/counts if W2/Popper assembly does not retain them',
                'source reset cohort and synchronized release state','held reverse CDC seats',
                'payload landing when source lease cannot hold','actual W4 per-bank completion reduction state'],
            payload_assembly='full512B RF vector needs16x32B backend sectors; KV32B read needs1sector; no free single-sector-to-vector promotion',
            required_backend_sectors={'C0_RF_vector':16,'KV_read_sector':1}),
        boundary_model_inputs=boundaries,
        geometry=dict(RF_vectors=512,lanes=128,RF_vector_bytes=512,
            RF_physical_mirrored_write_bytes=1024,RF_operand_read_bytes=1024,KV_sector_bytes=32),
        wrap=dict(generation_bits=4,modulo=16,run_cap=False,
            legal_transition=r4['revised_wrap_and_reset']['legal_reuse'],
            all_copy_obligations=r4['revised_wrap_and_reset']['quiescence_includes'],
            source_quiescence_installed=False,wait_cycles=None,
            old_monotonic_ParentLeases_is_stream_implementation=False,
            no_empty_table_or_local_reset_as_drain=True),
        continuous_program=dict(Qwen_PCs=1737,DS_PCs=2213,repeated_tokens=True,
            transaction_count_is_PC_count=False,source_transactions_enrolled=None),
        full_pricing_requires=['exact accepted C0/KV/directory caller map and arbitration',
            'source allcopies quiescence + matched reverse CDC reset/drain implementation and finite wait',
            'all positive boundary cycles/port rates/bits/tracks/slot and protection/selector/fanout area',
            'whole composed model clocks/rate/replicas/area and reset admission'],
        build_admitted=False,physical_qualified=False,whole_program_qualified=False)


def bench():
    cases=[]
    for path in ('C0','KV_READ'):
        source=SourceTuple(127,5,0xFE123456,4,1 if path=='C0' else 0,7,31,511,1736,0xFEDCBA98)
        g=SourceFenceReference(enabled=True)
        payload=bytes(range(256))*2 if path=='C0' else bytes(range(32))
        g.accept(source,path=path,payload=payload,read_version=None if path=='C0' else 17)
        g.tick();g.completion(source,echo=source.backend_echo(),payload=payload,
            copy_mask=3 if path=='C0' else None,read_version=None if path=='C0' else 17)
        for event in ('visibility','consumer','reverse','retire'):
            g.tick();g.boundary(source,event=event,ready=False);g.tick();g.boundary(source,event=event)
        cases.append(dict(path=path,trace=g.trace,final_phase=g.phase,
                          reuse_source_quiescence_missing=True,actual_hardware_events=False))
    return dict(verdict='PASS_F0_SOURCE_COMPATIBLE_FINITE_REFERENCE_ONLY',cases=cases,
                production_lifecycle_qualified=False,hardware_qualified=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    for name,value in [('model_inputs.json',model_inputs()),('finite_reference.json',bench())]:
        with (args.out/name).open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
