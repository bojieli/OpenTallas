"""Fail-closed existing-VM immutable constant baseline, no compiler/RTL change."""
import argparse,ast,hashlib,json,subprocess
from decimal import Decimal

CURRENT='b519af4947acc413a3c750c5871e1a59720b6bb0'

def reserve(base,words,capacity,excluded):
    if type(base) is not int or type(words) is not int or base<0 or words<0 or base+words>capacity:
        raise ValueError('constant arena capacity')
    if excluded is None:raise ValueError('no authoritative writable/lifetime exclusion manifest')
    for start,end in excluded:
        if base<end and base+words>start:raise ValueError('constant/writable address alias')
    return True

def build():
    pins={}
    def raw(name,ref,path):
        b=subprocess.check_output(['git','show',ref+':'+path]);pins[name]=dict(commit=ref,path=path,sha256=hashlib.sha256(b).hexdigest());return b
    warm=json.loads(raw('logical_mapping','9bd2ccdf0','results/quality/w16_engram_initializer_20261001/warm_residency.json'))
    raw('corrected_topology','f1af146d6','results/quality/w16_engram_initializer_20261001/hybrid_topology.json')
    source=raw('declared_shape_VM_allocator','d2c28c279','tools/hdc_replay_v41.py')
    program=raw('allocator_implementation','d2c28c279','tools/hdc_program_v41.py')
    raw('current_product_VM_model',CURRENT,'tools/uarch_model.py')
    raw('current_configured_VM_service',CURRENT,'rtl/chip/ot_v41_vm_bank4_macro_pipe.sv')
    options=json.loads(raw('C_rotate_cost','3cc18731','results/uarch/w11_vm_options.json'))['options']['C_rotate']
    tree=ast.parse(source);env={}
    for n in tree.body:
        names={x.id for t in getattr(n,'targets',[]) for x in ast.walk(t) if isinstance(x,ast.Name)}
        if isinstance(n,ast.Assign) and names & {'SHIPPED','RATIO','KV_SRC'}:
            exec(compile(ast.Module([n],[]),'<shape>','exec'),env)
    alloc=next(n for n in ast.parse(program).body if isinstance(n,ast.ClassDef) and n.name=='Alloc')
    exec(compile(ast.Module([alloc],[]),'<alloc>','exec'),env);baseclass=env['Alloc']
    class TrackAlloc(baseclass):
        def __init__(self):super().__init__(1<<40);self.ranges=[]
        def __call__(self,name,n,align=None):
            a=super().__call__(name,n,align);self.ranges.append(dict(name=name,start=a,end=a+n,words=n));return a
    env['Alloc']=TrackAlloc;env['cdiv']=lambda a,b:(a+b-1)//b
    shape=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='ShapeLayout')
    init=next(n for n in shape.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    cut=next(i for i,n in enumerate(init.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='kv' for t in n.targets))
    init.body=init.body[:cut];shape.body=[init];exec(compile(ast.Module([shape],[]),'<VM allocation prefix>','exec'),env)
    vm=env['ShapeLayout'](env['SHIPPED'],tp_exact=True).vm
    capacity=524288;maxwords=max(s['gamma_words']+s['other_words']+s['product_words'] for s in warm['stages'])
    assert maxwords==33648
    base=capacity-maxwords;maps=[];coverage=0
    for stage in warm['stages']:
        addresses=sorted({a for f in stage['static_families'] for lo,hi in f['global_address_ranges'] for a in range(lo,hi)})
        assert len(addresses)==stage['gamma_words']+stage['other_words']+stage['product_words']
        pairs=[(a,base+i) for i,a in enumerate(addresses)]
        assert len({v for _,v in pairs})==len(pairs)
        maps.append(dict(logical_layer=stage['layer'],words=len(pairs),bytes=4*len(pairs),
            proposed_VM_range=[base,base+len(pairs)],bijection_sha256=hashlib.sha256(b''.join(a.to_bytes(4,'little')+v.to_bytes(4,'little') for a,v in pairs)).hexdigest(),
            command_PCs=sorted(c['PC'] for c in stage['command_hits']),
            source_invalid_words=20480 if stage['layer']==1 else 0,
            compiler_source_and_address_change_implemented=False))
        coverage+=len(stage['command_hits'])
    assert coverage==491
    aliases=[r for r in vm.ranges if r['start']<capacity and base<r['end']]
    assert aliases
    return dict(schema='opentallas.CROM-existing-VM-baseline.v1',source_pins=pins,
        verdict='REJECTED_NO_PROVED_FREE_VM_RESERVATION',hardware_admission=False,
        logical_stage_maps=maps,commands_per_rank=491,reference_ranks=4,
        all4rank_prior_retained_value_checks=warm['retained_value_checks'],
        mapping_scope='candidate offline source/address bijection; not an adopted compiler or liveness/port proof',
        stage_capacity=dict(capacity_words=capacity,max_stage_words=maxwords,max_stage_bytes=4*maxwords,
            normal_stage_words=12528,normal_stage_bytes=50112,constant_only_stage_capacity_pass=True,
            sequential_all40_and_head_words=549760,sequential_constant_only_deficit_words=25472,
            automatic_alllayer_residency=False),
        proposed_regular_arena=[base,capacity],declared_VM_allocation_ranges=vm.ranges,
        declared_global_shape_VM_top=vm.top,arena_declared_allocation_aliases=aliases,
        actual_backend_remap_and_perhome_live_ranges=None,
        alias_scope='declared global ShapeLayout exclusion counterexample, not assertion that all CKV is physically in 2MiB SRAM',
        authoritative_free_row_reservation=None,
        mandatory_source_address_ports=dict(existing_VM_four_operand_interface=True,
            CLO_to_VM_compiler_bijection_classA_gate=False,all491_operand_ports_and_lifetimes_proved=False,
            immutable_reset_image_generation_and_writable_exclusion_provider=None),
        warm=dict(C_rotate_su_op_extra_slow_cycles=options['su_op_extra_cycles'],
            source_cost_already_part_of_PRODUCT_HUB=True,no_free_fusion=True,
            nominal491command_extra_slow_cycle_sum=491*options['su_op_extra_cycles'],
            nominal_serial_partial_us=str(Decimal(491*options['su_op_extra_cycles'])/900),
            partial_is_not_new_model_delta_or_full_token_latency=True,actual_RTL_cycles=None),
        cold=dict(once_per_image_generation=True,source_L1_invalid=True,
            ROM_selected16_output_stage_floor_fast_cycles=(maxwords+15)//16,
            actual_ROM_to_VM_write_ports=None,backend_WRACK_visibility_bound=None,
            CDC_and_init_deadline_calendar=None,actual_TTFT=None),
        no_new_constant_cache_FF_EXT_or_mux_assumed=True,no_area_power_or_latency_credit=True,
        rejection_dependencies=['actual perhome VM reservation excludes all writable/collective/context/MTP aliases',
            'all491/4rank operand address/source/port exactness gate','image/reset publication and cold WRACK/CDC calendar',
            'actual L1 provenance','current contextual SSFF'],jobs_launched=0,checkpoint_reads=0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
