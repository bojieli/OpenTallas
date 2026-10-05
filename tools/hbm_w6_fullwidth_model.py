#!/usr/bin/env python3
"""Default-off prospective W6 owner46+RFslot9 construction price and golden.

Cycles/gate equivalents are explicit candidate assumptions for model admission,
not installed-source timing. W2/W4 payload and debt are charged by their owners.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT='results/uarch/hbm_W6_fullwidth_model_20261003/r1'
CANONICAL='canonical-fullwidth-C0-KV-read-r1.json'


def require(ok,why):
    if not ok: raise ValueError(why)


def canonical():
    raw=(ROOT/OUT/'F0_inputs'/CANONICAL).read_bytes()
    require(hashlib.sha256(raw).hexdigest()==CANONICAL_SHA,'canonical F0 pin')
    c=json.loads(raw)
    require(c['canonical_owner']['bits']==46 and c['W6']['RF_slot_bits']==9,'owner46/slot9')
    return c


# Set from immutable 887c76704 bytes; generated once during preparation.
CANONICAL_SHA='22e2e3c718807d91e3ef4bfd8b8a3db704583f452592975fc651b538f2827212'


def encode_owner(physical_PC,client,original_tag,generation):
    for value,width in ((physical_PC,7),(client,3),(original_tag,32),(generation,4)):
        require(type(value) is int and 0<=value<2**width,'canonical field bounds')
    require(client<6,'NC6 accepted caller; KV5 occupied')
    return (physical_PC<<39)|(client<<36)|(original_tag<<4)|generation


def decode_owner(owner):
    require(type(owner) is int and 0<=owner<2**46,'owner46 bounds')
    return dict(physical_PC=owner>>39,client=(owner>>36)&7,
                original_tag=(owner>>4)&0xFFFFFFFF,generation=owner&15)


class Golden:
    """Finite prospective single-owner control, no production receipt producer.

    Every transition is an explicit fixture input. Local reset enters quarantine;
    only an all-copies+matched CDC fixture can release it, with positive edges.
    """
    def __init__(self,*,enabled=False,SM=0):
        require(type(SM) is int and 0<=SM<32,'real per-SM port index')
        self.enabled,self.SM=enabled,SM;self.edge=0;self.last=-1
        self.phase='IDLE';self.owner=None;self.slot=None;self.trace=[];self.held=None

    def tick(self,n=1):
        require(type(n) is int and n>0,'positive edges');self.edge+=n

    def accept(self,*,owner,RF_slot,origin='host'):
        decode_owner(owner)
        require(decode_owner(owner)['client']<6,'NC6 client')
        require(type(RF_slot) is int and 0<=RF_slot<512,'RFslot9')
        require(self.enabled and self.phase=='IDLE' and self.edge>self.last,'default-off/live/quarantine/positive accept')
        require(origin in ('host','internal_SIMD'),'actual selected write owner origin')
        self.origin=origin
        self.owner,self.slot=owner,RF_slot;self.phase='ACK';self.last=self.edge
        self.trace.append(dict(event='source_accept_fixture',edge=self.edge,owner=owner,RF_slot=RF_slot,SM=self.SM))

    def event(self,*,owner,RF_slot,kind,ready=True,allcopies=None):
        require(self.enabled and (owner,RF_slot)==(self.owner,self.slot),'same owner46/RFslot9')
        transition={'common_ACK':('ACK','VISIBLE'),'internal_SIMD_ACK_retire':('ACK','VISIBLE'),'visible':('VISIBLE','CONSUMER'),
            'consumer':('CONSUMER','CHILD_REVERSE'),'child_reverse':('CHILD_REVERSE','PARENT_REVERSE'),
            'parent_reverse':('PARENT_REVERSE','CDC'),'reverse_CDC':('CDC','DRAIN_REQUEST'),
            'drain_request':('DRAIN_REQUEST','QUIESCENCE'),
            'allcopies':('QUIESCENCE','RETIRE'),'retire':('RETIRE','IDLE'),
            'reset_drain_request':('RESET_QUARANTINE','RESET_DRAIN_WAIT'),
            'reset_allcopies':('RESET_DRAIN_WAIT','IDLE')}
        require(kind in transition,'boundary kind')
        before,after=transition[kind]
        require(kind!='common_ACK' or self.origin=='host','host ACK cannot retire internal SIMD')
        require(kind!='internal_SIMD_ACK_retire' or self.origin=='internal_SIMD','internal ACK cannot retire host')
        minimum=3 if kind=='reverse_CDC' else 2
        require(self.phase==before and self.edge>=self.last+minimum and type(ready) is bool,'ordered positive boundary')
        if kind in ('allcopies','reset_allcopies'):
            require(type(allcopies) is tuple and len(allcopies)==9 and all(v is True for v in allcopies),
                    'fixture all9 source debt classes drained; not actual source proof')
        else:require(allcopies is None,'no retrospective invented drain')
        packet=(owner,RF_slot,kind,allcopies)
        require(self.held is None or self.held==packet,'held identity/drain stable')
        if not ready:self.held=packet;return False
        self.held=None;self.phase=after;self.last=self.edge
        self.trace.append(dict(event=kind+'_fixture',edge=self.edge,owner=owner,RF_slot=RF_slot,SM=self.SM))
        return True

    def reset(self):
        require(self.enabled,'default-off')
        self.phase='RESET_QUARANTINE';self.held=None;self.last=self.edge
        # Do not clear retained identity or release credit on local reset.
        self.trace.append(dict(event='reset_quarantine_fixture',edge=self.edge,owner=self.owner,RF_slot=self.slot,SM=self.SM))


def price():
    c=canonical();DFF=.2916;GATE=.2;SMs=32
    fields=dict(owner_and_RFslot=55,phase=4,valid=1,fault=1,owner_origin=1,common_ACK_seen=1,
        consumer_seen=1,child_reverse_seen=1,parent_reverse_seen=1,reverse_CDC_seen=1,allcopies_seen=1,drain_request_pending=1,boundary_pipeline_age=2)
    raw=sum(fields.values());protected=math.ceil(raw/64)*72
    gates=dict(identity_XNOR=5*55,identity_reduce=5*54,state_control=64,
               table_read_mux_bits=55,host_internal_completion_mux_bits=55,
               protection_encode_XOR=math.ceil(raw/64)*8*63,
               protection_decode_XOR=math.ceil(raw/64)*8*71,
               protection_syndrome_decode_AND=math.ceil(raw/64)*72*7,
               protection_correct_XOR=math.ceil(raw/64)*72,
               clock_reset_enable_buffers=3*math.ceil(protected/8))
    logic=protected*DFF+sum(gates.values())*GATE
    boundaries=[]
    for n,cycles in [('ACK_to_visible',2),('visible_to_consumer',2),('consumer_to_child_reverse',2),
                     ('child_to_parent_reverse',2),('parent_to_reverse_CDC',3),
                     ('reverse_CDC_to_drain_request',2),('drain_request_to_allcopies',2),('allcopies_to_retire',2),('retire_to_new_accept',2)]:
        bits=55+2+(9 if n=='drain_request_to_allcopies' else 0)
        boundaries.append(dict(name=n,candidate_minimum_edges=cycles,control_bits=bits,
            peak_control_bits_per_cycle=bits,minimum_routing_tracks=bits,channel_capacity=None,
            new_payload_bytes_per_cycle=0,replicas=SMs))
    minimum=sum(b['candidate_minimum_edges'] for b in boundaries)
    sensitivity=[dict(extra_consumer_stall=s,additional_source_quiescence_wait=q,
        reverse_CDC_edges=cdc,W6_edges=minimum+s+q+cdc-3,
        ns=(minimum+s+q+cdc-3)*5/6)
        for s,q,cdc in [(0,0,3),(8,4,4),(32,16,6),(64,64,8)]]
    return dict(schema='HBM_W6_CANONICAL_FULLWIDTH_PROSPECTIVE_MODEL_V1',
        canonical_revision='887c76704',canonical_sha256=CANONICAL_SHA,
        default_off=True,owner_bits=46,RF_slot_bits=9,total_identity_bits=55,
        generation='owner[3:0], already included; no duplicate generation FF',
        canonical_field_layout=c['canonical_owner'],NC=6,KV_client=5,directory_client_added=False,
        table=dict(slots_per_SM=1,raw_fields=fields,raw_bits_per_SM=raw,
            protected_bits_per_SM=protected,protected_bits_full32SM=protected*SMs,
            protection='mutable SECDED64 padded chunks, same scheme as F0 reference; actual check ports/logic proxy below',
            read_ports=1,write_ports=1,host_ACK_acceptance_separate_from_internal_SIMD_ACK_retire=True,
            identity_hold_until='matched child,parent,reverse CDC and source allcopies plus retire'),
        gate_proxy=gates,assumed_DFF_um2=DFF,assumed_gate_equivalent_um2=GATE,
        area=dict(prospective_logic_um2_per_SM=logic,full32SM_logic_um2=logic*SMs,
            utilization=.5,reserved_slot_um2_per_SM=logic/.5,full32SM_slot_mm2=logic*SMs/.5/1e6,
            proxy_not_mapped_or_placed=True,actual_slot_fit=None),
        boundaries=boundaries,
        completion_input_ports=dict(host_common_ACK_control_bits=57,internal_SIMD_ACK_retire_control_bits=57,
            source_origin_latch_bits=1,drain_request_control_bits=57,
            allcopies_response_control_bits=66,selection='exact retained host/internal origin; foreign ACK never advances owner',
            internal_SIMD_identity_retention='W4 separate55bit retention perSM if required, charged by Euclid not again here'),
        protection_price='naive upper gate-equivalent construction: each64b chunk8 check bits, encode504XOR/decode568XOR/syndrome504AND/correct72XOR; 2 chunks. Mapping may lower cost, not used for admission yet',
        fanout=dict(identity_comparison_loads_per_bit=5,identity_capture_FFs=55,
            protected_clock_and_reset_loads_per_SM=protected,buffer_proxy_group_load=8,
            data_bus_fanout_added=0,payload_mux_bits_added=0,control_mux_bits=55,
            drain_flag_input_loads=9,drain_flag_reduction_proxy_in_state_control=True),
        added_MACs_per_cycle=0,compute_intensity=0,communication_intensity='55bit retained identity; existing full RF/KV payload service charged once by W2/W4/Popper',
        retained_data_ports=dict(RF_write_logical_bytes=512,RF_mirrored_write_physical_bytes=1024,
            RF_operand_pair_read_bytes=1024,KV_read_bytes=32,
            C0_vector_backend_sectors=16,KV_read_backend_sectors=1),
        latency=dict(candidate_W6_minimum_edges=minimum,candidate_minimum_ns=minimum*5/6,
            target_clock_GHz=1.2,unconditional_finite_maximum=None,
            sensitivity=sensitivity,source_ACK_latency_charged_by='W4',
            W2_backend_and_assembly_charged_by='Nash/Popper',
            positive_source_drain_wait='additional q per actual reuse/reset/wrap; not zeroed by empty local table',
            sensitivity_is_not_watchdog=True,no_run_or_generation_cap=True,
            shared_arbitration='one pending owner/SM; full fairness/contender waits from Popper joint calendar'),
        model_scope='mandatory baseline correctness, not optional fusion; prospective component construction to compose once in unified model before engine RTL',
        minimum_gain_threshold_required=False,
        retained_hardware_handshake=dict(request='accepted per-SM owner46/RFslot9 and origin captured once',
            completion='separate host common_ACK and internal_SIMD ACK-retire identity ports; select retained origin and exact55bit match',
            visible='hold owner55 valid until exact consumer capture; source payload lease retained',
            reverse='child then parent then matched reverseCDC; duplicate flags block second advancement',
            drain='emit held owner55 drain_request valid/ready once; latch drain_request_pending. Source coordinator returns same55bit certificate +9 no-copy classes held valid/ready; consume only after outstanding matched request; all older copies/certificates and CDC credits included in source predicate. Price source assembly/transport by Popper' ,
            reset='disable new accepts; retain context/quarantine and request actual coordinated drain; never local valid-bit clear release'),
        reset=dict(local_abort='quarantine retained owner; no new grant',
            release='source-owned all9 source classes and matched reverse CDC coordinated drain/flush + synchronized release',
            source_predicate_installed=False,reset_cohort_transport_cost_owner='Popper/W2'),
        payload=dict(new_storage_bits=0,condition='source producer/W4 lease holds exact payload until consumer; otherwise Popper charges full landing',
            no_payload_timer_or_arithmetic_change=True),
        component_control_construction_costed_prospectively=True,
        external_composition_cost_owners={'Nash':'W2 service source latencies/generation echo',
            'Euclid':'W4 leaf and internal SIMD identity capture/commonACK',
            'Popper_Dewey':'caller adapter/assembly/new slots/full arbitration/reset/cohort and CDC queue construction'},
        remaining_composed_admission=['whole actual caller/slot map, named corridor capacity and reset source wiring',
            'source allcopies finite wait in joint calendar; sensitivity cannot certify unconditional max',
            'new slots and all transport construction charged once by named owners'],
        remaining_postbuild_qualification=['actual mapped protection/state paths and source exactness',
            'measured parent clocks/waits and commonreset/drain/copy conservation','contextual SS/FF/PG/routing'],
        continuous_stream=dict(Qwen_PCs=1737,DS_PCs=2213,repeated_tokens=True,transaction_count=None),
        whole_composed_build_admitted=False,headline_or_physical_qualified=False)


def finite_bench():
    traces=[]
    for client in (0,5):
        g=Golden(enabled=True,SM=31);o=encode_owner(127,client,0xFE123456,15)
        g.accept(owner=o,RF_slot=511)
        for event in ('common_ACK','visible','consumer','child_reverse','parent_reverse','reverse_CDC','drain_request','allcopies','retire'):
            g.tick(3 if event=='reverse_CDC' else 2)
            g.event(owner=o,RF_slot=511,kind=event,allcopies=(True,)*9 if event=='allcopies' else None)
        traces.append(dict(path='C0' if client==0 else 'KV_read',trace=g.trace,production_caller=False))
    return dict(verdict='PASS_OWNER55_FINITE_REFERENCE_ONLY',traces=traces,
        source_quiescence_receipts=False,hardware_qualified=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    for n,d in [('model.json',price()),('finite_golden.json',finite_bench())]:
        with (a.out/n).open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
