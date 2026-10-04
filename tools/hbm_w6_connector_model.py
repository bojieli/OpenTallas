#!/usr/bin/env python3
"""R14-connected W6 model successor and finite allocation/frame reference.

Source allocation, backend echo, codec and reverse below are prospective fixture
ports. No original R14 module is modified or claimed to implement this ABI.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT='results/uarch/hbm_W6_connector_model_20261003/r1'


def require(ok,why):
    if not ok:raise ValueError(why)


def load_sources():
    path=ROOT/OUT/'inputs';manifest=(path/'pins.json').read_bytes()
    require(hashlib.sha256(manifest).hexdigest()=='5bb961e49c495eea9326d25ab17f294da0a1ca3293b8613cf90d067009079bdd','immutable connector manifest pin')
    pins=json.loads(manifest)
    raw={n:(path/n).read_bytes() for n in pins}
    for n,v in raw.items():require(hashlib.sha256(v).hexdigest()==pins[n],'connector frozen pin '+n)
    tree=ast.parse(raw['r17.py'])
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='physical')
    env={};exec(compile(ast.Module(body=[node],type_ignores=[]),'pinned_r17_physical','exec'),env)
    return json.loads(raw['cost-inputs.json']),env['physical'],pins


def owner46(pc,client,tag,generation):
    for v,w in ((pc,7),(client,3),(tag,32),(generation,4)):
        require(type(v) is int and 0<=v<2**w,'full source child fields')
    require(client<6,'actual NC6; no unmapped seventh client')
    return pc<<39|client<<36|tag<<4|generation


def metadata92(child,SM,RFslot,parentref):
    for v,w in ((child,46),(SM,5),(RFslot,9),(parentref,32)):
        require(type(v) is int and 0<=v<2**w,'meta92 aperture')
    return child<<46|SM<<41|RFslot<<32|parentref


def full_backend16(tag12,generation4):
    require(type(tag12) is int and 0<=tag12<4096 and type(generation4) is int and 0<=generation4<16,'independent physical tag12/gen4')
    return generation4<<12|tag12


class ParentFrame:
    """One bound parent, sixteen child rows; proposal fixture only.

    Actual source allocator must bind the tuple before acceptance. Parent55 is
    immutable and never replaced by a final child. Early legacy ore is refused.
    """
    def __init__(self,*,parentref,parent_owner,SM,RFslot,base_byte,format='FP32_LE128',old_frame=None,DIE=0,enabled=False):
        require(enabled is True,'default-off prospective fixture')
        metadata92(parent_owner,SM,RFslot,parentref)
        require(type(DIE) is int and DIE in (0,1),'explicit scoped source DIE1')
        self.DIE=DIE
        require(type(base_byte) is int and base_byte>=0 and base_byte%512==0,'aligned full RF512B parent frame')
        require(format in ('FP32_LE128','FP8_KV_RAW'),'explicit source byte codec')
        require(old_frame is None or type(old_frame) is bytes and len(old_frame)==512,'positive preserved old512B frame')
        self.parentref,self.owner,self.SM,self.slot=parentref,parent_owner,SM,RFslot
        self.parent55=(parent_owner<<9)|RFslot
        self.base,self.format,self.old=base_byte,format,old_frame
        self.children={};self.data={};self.reverse_mask=0;self.phase='READ';self.released=False
        self.cost,self.physical,self.pins=load_sources()

    def bind(self,index,*,client,originaltag,source_generation,physical_tag,backend_generation,legacy_identity,request_LEN=1):
        require(type(request_LEN) is int and request_LEN==1,'W2 one32B sector requires R14 LEN1')
        require(self.phase=='READ' and type(index) is int and 0<=index<16 and index not in self.children,'unique sector child before capture')
        require(type(legacy_identity) is dict and set(legacy_identity)=={'die','stack','sector','producer','transport','caller','client','irs_slot','irs_serial'},'legacy192 kept separately')
        p=self.physical(self.base+32*index);pc=32*p['stack']+p['PC']
        require(legacy_identity['die']==self.DIE and legacy_identity['stack']==p['stack'] and legacy_identity['sector']==p['local_sector31'],'legacy source address preserved')
        widths={'die':1,'stack':2,'sector':34,'producer':64,'transport':32,'caller':16,'client':6,'irs_slot':5,'irs_serial':32}
        for k,w in widths.items():require(type(legacy_identity[k]) is int and 0<=legacy_identity[k]<2**w,'legacy192 field aperture')
        child=owner46(pc,client,originaltag,source_generation)
        token=full_backend16(physical_tag,backend_generation)
        require(all((r['PC'],r['child'])!=(pc,child) for r in self.children.values()),'ambiguous samePC child owner; allocator must assign unique tag')
        require(all((r['stack'],r['token'])!=(p['stack'],token) for r in self.children.values()),'duplicate backend token allocation')
        self.children[index]=dict(direction=0,LEN=1,BEAT=0,DIE=self.DIE,PC=pc,stack=p['stack'],child=child,token=token,
            backend_generation=backend_generation,meta92=metadata92(child,self.SM,self.slot,self.parentref),
            legacy=copy.deepcopy(legacy_identity),captured=False,quarantined=True)
        return copy.deepcopy(self.children[index])

    def capture(self,index,*,backend_token,meta92,legacy_identity,data,direction=0,BEAT=0):
        r=self.children.get(index)
        require(self.phase=='READ' and r is not None and not r['captured'],'reserved unique physical child')
        require(type(backend_token) is int and backend_token==r['token'],'full16 echo; upper4 cannot truncate')
        require(type(meta92) is int and meta92==r['meta92'] and legacy_identity==r['legacy'],'logical source/SM/slot/ref and legacy192 restored exactly')
        require(type(BEAT) is int and BEAT==0,'W2 one-sector terminal BEAT0')
        require(type(direction) is int and direction==r['direction'],'read only matches read')
        require(type(data) is bytes and len(data)==32,'sector payload32')
        r['captured']=True;self.data[index]=data
        # Completion/owner ore cannot return physical credit; retain quarantine.

    def legacy_ore(self,index):
        require(index in self.children,'live physical child')
        raise ValueError('early R14 ore retirement prohibited until W2/RF/consumer/parent/reverseCDC/allcopies')

    def rf_frame(self):
        require(self.format=='FP32_LE128','FP8 raw KV needs exact source codec before FP32 RF deposition')
        require(self.phase=='READ' and len(self.data)>0,'actual captured payload required')
        require(len(self.data)==16 or self.old is not None,'partial frame requires positive old512B origin; no zero fill')
        # Full old data is an explicit fixture input, not a fabricated valid bit.
        result=b''.join(self.data.get(i,self.old[32*i:32*(i+1)] if self.old is not None else b'') for i in range(16))
        require(len(result)==512,'complete512B frame')
        self.phase='RF_ACK';return dict(parent55=self.parent55,SM=self.SM,RFslot=self.slot,data=result)

    def event(self,kind,*,parentref,parent55,backend_token=None,index=None,meta92=None,drain=None,reverse_DIE=None,reverse_STACK=None,reverse_direction=None,reverse_BEAT=None):
        require(parentref==self.parentref and parent55==self.parent55,'bound stable parent55/ref; not last child')
        steps={'RF_ACK':('RF_ACK','VISIBLE'),'visible':('VISIBLE','CONSUMER'),
            'consumer':('CONSUMER','CHILD_REVERSE'),'parent_reverse':('PARENT_REVERSE','CDC'),
            'reverse_CDC':('CDC','DRAIN_REQUEST'),'drain_request':('DRAIN_REQUEST','ALLCOPIES'),'allcopies':('ALLCOPIES','RETIRED')}
        if kind=='child_reverse':
            r=self.children.get(index)
            require(self.phase=='CHILD_REVERSE' and r is not None and type(backend_token) is int and backend_token==r['token'] and not(self.reverse_mask>>index&1),'matching unique child full16 reverse')
            require(type(reverse_DIE) is int and reverse_DIE==r['DIE'] and
                    type(reverse_STACK) is int and reverse_STACK==r['stack'] and
                    type(reverse_direction) is int and reverse_direction==0 and
                    type(reverse_BEAT) is int and reverse_BEAT==0,'reverse saved DIE/STACK/direction/BEAT scope')
            require(type(meta92) is int and meta92==r['meta92'],'full saved child source metadata for reverse')
            self.reverse_mask|=1<<index
            if self.reverse_mask==sum(1<<i for i in self.children):self.phase='PARENT_REVERSE'
        else:
            require(kind in steps and self.phase==steps[kind][0],'ordered actual source handshake fixture')
            if kind=='allcopies':require(type(drain) is tuple and len(drain)==9 and all(v is True for v in drain),'all source copy/CDC drain classes, fixture only')
            else:require(drain is None,'drain only after matched reverse/request')
            self.phase=steps[kind][1]
        if self.phase=='RETIRED':
            for r in self.children.values():r['quarantined']=False
            self.released=True


def model():
    cost,physical,pins=load_sources()
    W2=json.loads((ROOT/OUT/'inputs/W2-composition.json').read_bytes())
    require(W2['p_wr_done_ready_required'] is True and
            W2['chosen_endpoint_contract']['R14_LEN6_value_for_this_minimum_sector_route']==1 and
            W2['chosen_endpoint_contract']['R14_BEAT5_value_for_this_minimum_sector_route']==0,'frozen W2 ready/LEN1/BEAT0 endpoint')
    spec=importlib.util.spec_from_file_location('w6_component_price',ROOT/'tools/hbm_w6_fullwidth_model.py')
    base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
    component=base.price()
    fields=cost['additional_fields'];require(sum(fields.values())==50,'W10 missing50raw')
    pipeline=144*38*2*(72+72);require(pipeline==cost['pipeline_two_seats_38stages_144lanes_increment_bits'],'full protected pipeline cost')
    source_address=physical(32)
    return dict(schema='W6_R14_LOSSLESS_CONNECTOR_MODEL_SUCCESSOR_V1',
        connector_revision='1bfbbda5afeafde216ab5c6d79dd3b72efaa2800',
        W2_composition_revision='a9cab7990bdd24b6fe3b3ea24bd4cb53e9d8962b',
        Nash_source_revision='67ab2420e2ad8cb273be74d884f84f6bc260c261',source_pins=pins,
        W2_frozen=dict(full_wrapper_costs=W2['W2_model_costs']['full_wrapper_variant'],
            boundary_signal_bits=W2['boundary_signal_bits'],latency=W2['latency'],
            p_wr_done_ready_required=True,old_pulse_only_compatibility_superseded=True,
            no_legacy_adapter_assumed=True,R14_LEN=1,R14_BEAT=0,
            separate_DIE_scope_required=True,STACK2_preserved=True,
            matched_old_W2_debit=None,net_increment_area=None,
            gross_is_not_additive_delta=True,composition_rule=W2['once_only_composition']['rule']),
        route='actual R14 currently bypasses W2; successor connects W2 matched hold before RF/frame/W4/W6',
        widths=dict(child_owner=46,meta=92,meta_plus_backend_generation=96,parent_capture=55,
            backend_token=16,backend_tag=12,backend_generation=4,producer_generation=4,
            provider_request=547,owned_return=561,command=343,legacy_identity=192),
        authority=dict(child='actual child PC/client/originaltag/sourcegen',
            parent='pre-bound parentref32 lookup; same parent55 for all children',
            backend='atomic accepted tag12/backendgen4 receipt; independent from sourcegen4',
            provider_class6_not_client3=True,NC=6,KVclient5_occupied=True,new_directory_client=False),
        address=dict(source='AST executed pinned r17 physical()',example_B32=source_address,
            old_low7_PC_B32=1,actual_PC_B32=32*source_address['stack']+source_address['PC'],
            address_low_bits_unchanged=True,full512B_sectors=16,full512B_stripes=4),
        pipeline_delta=dict(fields=fields,raw_request=389,raw_return=353,protected_request=504,protected_return=432,
            protected_increment_FFs=pipeline,register_logic_proxy_um2=pipeline*.2916,
            register_slot_proxy_mm2=pipeline*.2916/.5/1e6,
            charge_owner='Popper W10 full pipeline; additive replaces omitted metadata debit, not added twice',
            wider_selectors_protection_clock_route_not_free=True),
        connector_ports=dict(provider_request_plus_valid_ready_bits=549,owned_return_plus_valid_ready_bits=563,
            full_command_payload_bits=343,backend_physical_token_bits=16,
            source_meta_input_per_child_bits=92,
            expanded_validated_reverse_envelope_raw_bits=192+92+16+55+1+5+2,
            expanded_reverse_protected_bits=math.ceil((192+92+16+55+1+5+2)/64)*72,
            reverse_envelope_scope='same legacy192/meta92/backend16/parent55/direction/BEAT+v/r; price actual transport or proven reconstruction adapter, not free55bit reverse across R14',
            owned_take_frees_only_output_holder=True,validated_retire_is_separate_new_handshake=True,source_PC_control_W2_packet_different_from_W10=True,
            one_command_bus_per_stack=1,write_done_ready_required=True),
        sidecar=dict(raw_per_context=96,logical_bits=1572864,macros=128,macro_shape=[128,256],
            physical_bits=4194304,protected_payload_per_context=144,
            write_ports=1,read_ports=1,read_write_payload_bits_per_bank_cycle=144,
            four_stack_macro_active_payload_bits_per_cycle=4*32*144,
            same_R14_CAM_index=True,second_CAM_added=False,
            existing_spare24bits_cannot_hold_meta92=True,SS_macro_area_slot=None,
            register_unrolled_alternative_not_selected=True,
            macro_mux_32to1_256bit_node_equivalents_all4stacks=4*31*256,
            macro_mux_gate_proxy_um2=4*31*256*.2,
            physical_write_enable_loads_per_stack=32,metadata_write_pin_incidences_all4stacks=4*32*144,
            prospective_added_capture_CORE_edges=1,
            read_clock_to_Q_SS_qualified=False,charge_owner='Popper context lifetime source extension'),
        frame=dict(data_bits_full32SM=131072,sector_mask_bits=512,
            data_FF_proxy_um2=131072*.2916,mask_FF_proxy_um2=512*.2916,
            data_protected_full32SM_bits=32*math.ceil(4096/64)*72,
            sector_mask_protected_full32SM_bits=32*72,
            data_protected_FF_proxy_um2=32*64*72*.2916,
            sector_mask_protected_FF_proxy_um2=32*72*.2916,
            source_codecs_and_protection_logic_not_zero_cost=True,
            child_row_fields=dict(owner=46,backend_token=16,valid=1,captured=1,reversed=1,quarantined=1),
            child_owner_backend_and_state_16rows_per_SM_raw_bits=16*66,
            full32SM_child_row_raw_bits=32*16*66,
            full32SM_child_row_protected_bits=32*16*math.ceil(66/64)*72,
            child_row_protection_FF_proxy_um2=32*16*144*.2916,
            DIE_scope_header_bits_per_SM=1,
            oldframe_bytes_are_fixture_not_source_origin_proof=True,
            input_payload_bytes_per_cycle=32,output_payload_bytes_per_cycle=512,
            lower_capture_edges=16,frame_emit_edges=1,
            full_width_read_mux_bits_per_SM=16*256,write_enable_fanout_per_SM=256,
            full_old_frame_RMW_tail_required_for_partial=True,raw_FP8_into_FP32_RF_refused=True,
            format_and_exact_codec_cost_owner='Popper actual requester/source codec; no numeric callback or substitution',
            actual_macro_vs_register_selection=None,charge_owner='Popper frame allocation; W6 consumes stable parent55 from this row'),
        W6_component=component,
        lifetime=dict(early_original_ore_is_unsafe=True,retain_physical_context_through='W2 hold/frame/RF_ACK/consumer/childreverse/parentreverse/reverseCDC/allcopies',
            allocation_and_retirement_joint_old_live_state=True,
            critical_holder_tag_credit_separation='owned ov/ready takes restored return and unblocks lookup; retain live/CAM/context until separate matched reverse retirement. Holding old ore wholesale through parent RF frame would block subsequent child data',
            post_terminal_quarantine_capacity_and_wait_charged=True,source_reuse_counter_cap=False,
            whole_program_PCs={'Qwen':1737,'DS':2213},allcopy_wait_positive=True),
        latency_terms=dict(tag_owner_source_CORE_edges=12,return_arbiter_source_CORE_edges=7,
            W2_read_client_edges_lower=2,W2_write_client_edges_lower=3,
            W6_candidate_edges=component['latency']['candidate_W6_minimum_edges'],
            RF_frame_serial_input_edges_lower=16,actual_CORE_domain_period_ps=None,
            no_free_PC_parallelism_from32banks=True,one_command_bus_per_stack=True,
            join_price='exact boundary DAG; tag lookup/arbiter per actual occurrence, W2/W6 count once, assembly and CDC costs composed by source domains'),
        remaining_admission=['actual caller parent/child/backend allocation and directory row/ports/new slots',
            'source full16 echo including PC/backing/matcher, write visibility and late-copy quarantine',
            'same-index96-bit sidecar actualmacro/protection and held lookup/select costs',
            'whole-calendar corridor/control/protection/clock/reset and exact codec/partial frame cost',
            'separate R14 holder-accept versus validated physical-retire ports, counters and full reverse envelope transport'],
        default_off=True,build_admitted=False,original_source_changed=False,production_or_physical_credit=False)


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    with (a.out/'model.json').open('x') as f:json.dump(model(),f,sort_keys=True,indent=2);f.write('\n')
