"""Corrected product ownership and finite single-slot immutable-product service.

A candidate calendar, not an instantiated cache or whole-token timing claim.
"""
import argparse, ast, gzip, hashlib, json, subprocess, types
from decimal import Decimal
from pathlib import Path
import w17_crom_finite_prefetch as C

CURRENT='d84ba7b80904bd066ba71c19c169636a9dac96e8'
HELPER_COMMIT='5f44f6e0465db704dd90852c6cc2c318f5aee8f8'
HELPER_PATH='tools/w17_crom_finite_prefetch.py'
HELPER_SHA256='824aceef53a155810027e3f9a12319b956bf1d2a425f62ea4c88224461341569'

def verify_imported_helper(module=C):
    loaded=Path(module.__file__).read_bytes()
    if hashlib.sha256(loaded).hexdigest()!=HELPER_SHA256:
        raise ValueError('finite-prefetch runtime helper source mismatch; requires '+HELPER_COMMIT+':'+HELPER_PATH+' SHA256 '+HELPER_SHA256)
    return loaded


def release_slot(fill_tick, capture_ack=False):
    if capture_ack is not True:
        raise ValueError('actual owning read-capture acknowledgement required')
    emit=((fill_tick+3)//4)*4
    capture=emit+8*4  # candidate BCAST4 plus source normal capture4; not live adapter
    return ((capture+31+17*3+3+2)//3)*3

def build():
    imported_helper=verify_imported_helper()
    pins={}
    def raw(n,ref,path,gz=False):
        b=subprocess.check_output(['git','show',ref+':'+path])
        pins[n]=dict(commit=ref,path=path,sha256=hashlib.sha256(b).hexdigest())
        return gzip.decompress(b) if gz else b
    helper=raw('runtime_finite_prefetch_helper',HELPER_COMMIT,HELPER_PATH)
    assert helper==imported_helper and hashlib.sha256(helper).hexdigest()==HELPER_SHA256
    owner=json.loads(raw('owner',CURRENT,'results/arch/v41_stage_owner_product.json'))
    source=raw('uarch',CURRENT,'tools/uarch_model.py')
    env={}
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VMC_BLOCK' for t in n.targets))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<VMC_BLOCK>','exec'),env)
    hub=env['VMC_BLOCK'];assert Decimal(str(hub['lane_array_mm2']))+Decimal(str(hub['vm_block_mm2']))==Decimal(str(hub['block_mm2']))
    raw('actual_SU_adapter','d2c28c279','rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv')
    raw('actual_SU_lane_capture','d2c28c279','rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv')
    warm=json.loads(raw('warm','9bd2ccdf0','results/quality/w16_engram_initializer_20261001/warm_residency.json'))
    stages={s['layer']:s for s in warm['stages']}
    for layer in range(40):
        assert stages[layer]['other_words']<=3072
    demand=json.loads(raw('demand',*C.SOURCES['demand'],True))
    isa=types.ModuleType('isa');isa.__file__=C.__file__;exec(compile(raw('ISA',*C.SOURCES['ISA']),'<ISA>','exec'),isa.__dict__)
    src=raw('emit',*C.SOURCES['emit_source'])
    nodes=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ('clog','batches')]
    be={'I':isa};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<batches>','exec'),be)
    binary=raw('rank0',C.PIN,C.PREFIX+'.rank0.templates.bin.gz',True)
    union=json.loads(raw('union','8e28902ff','results/uarch/w11_stage_crom_union_20261001/read_union.json.gz',True))
    # Recover exactly the current compact address permutation, including holes.
    alladdr={}
    records=[]
    for rec in demand['ranks'][0]['records']:
        f=isa.decode(int.from_bytes(binary[rec['global_instruction']*256:(rec['global_instruction']+1)*256],'little'),full_shape=True)
        bursts=[]
        for batch in be['batches'](f):
            uses=[]
            for oi,o in enumerate(rec['operand_demands']):
                for lane,(outer,inner) in enumerate(batch):
                    a=o['base']+outer*o['outer_stride']+(inner//2 if o['half_inner'] else inner)*o['inner_stride']
                    if o['kind']=='unbound_generated':a+=508800+(20480 if rec['layer']==14 else 0);uses.append((oi,lane,a))
                    alladdr.setdefault(rec['layer'],set()).add(a)
            if uses:bursts.append(uses)
        if bursts:records.append((rec,bursts))
    assert len(records)==2
    calendars=[]
    for banks in (6,9,16,45):
        for credits in (2,4,128):
            commands=[]
            for rec,bursts in records:
                mapping={a:i for i,a in enumerate(sorted(alladdr[rec['layer']]))}
                cursor=0;events=[]
                for index,uses in enumerate(bursts):
                    assert len(uses)==1024 and len({a for _,_,a in uses})==1024
                    if banks==45:
                        # 45-bank row compaction preserves original bank conflicts.
                        addresses={a for _,_,a in uses}
                    else:addresses={mapping[a] for _,_,a in uses}
                    waves=C.bank_waves(addresses,ports=banks)
                    fill=cursor;packets=0
                    for wave in waves:
                        targets={(oi,lane//16) for oi,lane,a in uses if (a if banks==45 else mapping[a]) in wave}
                        packets+=len(targets)
                        fill+=12+C.credit_calendar(len(targets),credits,route=17)['last_cache_write_and_reverse_credit_tick']
                    reuse=release_slot(fill,True)
                    events.append(dict(vector=index,slot=3,start_tick=cursor,fill_and_packet_credit_complete_tick=fill,
                        emit_tick=((fill+3)//4)*4,read_capture_tick=((fill+3)//4)*4+32,
                        candidate_owning_slot_reverse_credit_tick=reuse,bank_waves=len(waves),fill_packets=packets))
                    cursor=reuse
                assert len(events)==20
                commands.append(dict(PC=rec['global_instruction'],logical_layer=rec['layer'],rank=0,
                    product_words=20480,source_valid=rec['layer']!=1,events=events,
                    nooverlap_product_service_ticks=cursor,partial_us=str(Decimal(cursor)/3600)))
            calendars.append(dict(banks=banks,credits=credits,commands=commands,
                per_reference_rank_warm_product_partial_us=str(Decimal(sum(c['nooverlap_product_service_ticks'] for c in commands))/3600)))
    return dict(schema='opentallas.CROM-hybrid-topology.v1',source_pins=pins,
        corrections_to_preserved_9bd=dict(logical_groups_not_physical_field_stages=True,
            accepted_whole_geometry_already_charges_hubs=True,prior164_head_as_field40_owner_assignment_rejected=True),
        topology=dict(status=owner['status'],physical_field_stages=41,field_dies=164,
            dense_cache_owners=[dict(field_stage=layer,logical_layer=layer,rank=rank) for layer in range(40) for rank in range(4)],
            field_stage40=dict(dense_CROM_cache_words=0,expert_weights_only=True,existing_hub_not_removed=True),
            head=dict(logical_norm_words_per_reference_rank=5120,reference_ranks=4,physical_head_dies=8,
                actual_norm_home_to_eight_heads_mapping=None,required_fanout_service_bits_per_word=32,
                actual_fanout_ports_routes_visibility_calendar=None,automatic_eight_full_image_copies=False)),
        area_bridge=dict(unit='mm2',existing_PRODUCT_HUB=hub,
            existing164_hub_reservation=str(Decimal(str(hub['block_mm2']))*164),
            historical_SU_core_per_home='11.956',historical_core_is_not_current_lane_array=True,
            bridge_increment_not_established=None,new_cache_or_routes_not_absorbed_without_slot_proof=True,
            actual_context_SSFF_provider=None),
        hybrid=dict(allocation_scope='candidate FF reservation, no instantiated RTLcache',
            gamma_words_per_layer_home=10240,operand_words_per_layer_home=4096,
            persistent_other_slots=[0,1,2],single_streamed_product_slot=3,
            maximum_other_words=max(stages[l]['other_words'] for l in range(40)),
            slot_role_controller_and_bank_to_lane_permutation_provider=None,
            no_extra655360bit_persistent_product_charge=True,no_existing_buffer_double_charge=True,
            actual_read_capture_ack_provider=None,current_adapter_EXT_input_connected=False,
            reset_image_epoch_tag_fill_mask_visibility_and_owning_lease_required=True,
            cold_init_deadlines_and_actual_TTFT=None,warm_actual_RTL_cycles=None),
        product_calendars=calendars,
        assumptions=dict(common_tick_hz=3600000000,route_fast_cycles_each_way=17,
            selected_FP32_outputs=16,read_capture_candidate_slow_cycles=8,
            reverse_CDC_ticks=31,slot_credit_serialization_fast_cycles=1,
            packet_credits_distinct_from_consumer_slot_lease=True,no_overlap=True,
            actual1152bit_route_capacity_SSFF_unqualified=True),
        failures=['L1 retained parameter provenance absent','actual cache/controller/read-capture ACK absent',
            'headnorm eight-head fanout unbound','current hub/cache fit and full power unqualified',
            'cold all-family init and complete operator deadlines not bound'],
        full_token_cycles=None,hardware_admission=False,jobs_launched=0,checkpoint_reads=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
