"""Pinned original catalog replay and verifier refutation; no producer changes."""
import copy, gzip, hashlib, json, subprocess, sys, types
from decimal import Decimal
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
P = 'results/uarch/w11_crom_control_catalog_20261001/'
PINS = {}
def read(commit, path):
    commit = subprocess.check_output(['git', 'rev-parse', commit], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(['git', 'show', commit+':'+path], cwd=ROOT)
    PINS[commit+':'+path] = dict(commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest())
    return raw

def load(commit, name):
    path='tools/'+name+'.py';raw=read(commit,path)
    mod=types.ModuleType(name);mod.__file__=str(ROOT/path);sys.modules[name]=mod
    exec(compile(raw,mod.__file__,'exec'),mod.__dict__)
    return mod

def build():
    sys.path.insert(0,str(ROOT/'tools'))
    load('e57e08aad','hdc_isa_v41')
    demand_module=load('e57e08aad','w11_dsrom_crom_demand')
    C=load('e57e08aad','w11_dsrom_crom_control_catalog')
    m=json.loads(gzip.decompress(read('3c99ce15f',P+'compiled_v2/catalog.json.gz')))
    requests=gzip.decompress(read('3c99ce15f',P+'compiled_v2/request-controls.bin.gz'))
    fills=gzip.decompress(read('3c99ce15f',P+'compiled_v2/fill-controls.bin.gz'))
    source=json.loads(gzip.decompress(read('f4bce8fa0','results/uarch/w11_crom_demand_20261001/demand_v2.json.gz')))
    records=source['ranks'][0]['records']
    assert len(records)==len(m['commands'])==491
    audit=json.loads(read(demand_module.PIN,demand_module.PREFIX+'.json'))
    axes=set(); axis_uses={};both=0; nonzero_outer=0;halves=0
    for rank in range(4):
        encoded=gzip.decompress(read(demand_module.PIN,demand_module.PREFIX+f'.rank{rank}.templates.bin.gz'))
        assert hashlib.sha256(encoded).hexdigest()==audit['ranks'][rank]['encoded_template_sha256']
        assert source['ranks'][rank]['records']==records
        for command,rec in zip(m['commands'],records):
            assert (command['pc'],command['layer'],command['pred'],command['operands']) == (rec['global_instruction'],rec['layer'],rec['pred'],rec['operand_demands'])
            f=C.I.decode(int.from_bytes(encoded[command['pc']*256:(command['pc']+1)*256],'little'),full_shape=True)
            assert f['pred']==command['pred']
            coords=list(demand_module.batches(f))
            assert len(coords)==len(command['bursts'])
            for o in command['operands']:
                axis=o['operand']
                assert (o['base'],o['outer_stride'],o['inner_stride'])==(f[axis+'_base'],f[axis+'_so'],f[axis+'_si'])
                assert o['half_inner']==(axis in 'bd' and bool(f['b_half']))
                if rank==0:
                    axes.add(axis);axis_uses[axis]=axis_uses.get(axis,0)+sum(len(c) for c in coords)
                    nonzero_outer+=bool(o['outer_stride']);halves+=bool(o['half_inner'])
            if rank==0: both+=len(command['operands'])==2
    accepted=C.verify_serialized(m,requests,fills)
    assert accepted==549760 and sum(axis_uses.values())==accepted
    mutants=[]
    for name in ('predicate','empty_commands','encoded_source_hash','declared_command_count'):
        bad=copy.deepcopy(m)
        if name=='predicate': bad['commands'][0]['pred']^=1
        elif name=='empty_commands':bad['commands']=[];bad['counts']['coefficient_uses_per_rank']=0
        elif name=='encoded_source_hash':bad['encoded_program_source']['sha256']='0'*64
        else:bad['counts']['commands_per_rank']=0
        result=C.verify_serialized(bad,requests,fills)
        mutants.append(dict(mutation=name,original_verifier_accepted_uses=result,verdict='REFUTED_SOURCE_COMPLETENESS_GATE'))
    # Replay owner geometry without changing the frozen default calendar.
    load('47b715428','w17_crom_finite_prefetch')
    L=load('47b715428','w17_crom_local_home')
    local=L.build()
    persisted=json.loads(read('47b715428','results/quality/w16_w17_crom_finite_prefetch_20261001/local_home.json'))
    assert local==persisted
    def bind_nested(value):
        if isinstance(value,dict):
            if all(k in value for k in ('commit','path','sha256')):
                assert hashlib.sha256(read(value['commit'],value['path'])).hexdigest()==value['sha256']
            for item in value.values(): bind_nested(item)
        elif isinstance(value,list):
            for item in value: bind_nested(item)
    bind_nested(local['source_pins'])
    bind_nested(m['model_source'])
    bind_nested(m['encoded_program_source'])
    assert hashlib.sha256(read('e57e08aad','tools/w11_dsrom_crom_control_catalog.py')).hexdigest()==m['compiler_sha256']
    assert local['placement_verdict']=='REJECT_UNRESERVED_SU_DISPLACEMENT'
    assert local['registered_route_fast_cycles_each_direction']==11
    width,height=map(Decimal,map(str,local['SU_region_um'][2:]))
    assert str(width*height/Decimal(1000000))==local['current_SU_region_area_mm2']
    read('ce7f34f45','results/quality/parent_dsrom_crom_buffer_budget_review_20261001/catalog_source_binding_counterexamples.json')
    read('1360ff9e',m['model_source']['path'])
    return dict(schema='w10.crom.independent.original-gate-refutation.v1',source_pins=list(PINS.values()),
      canonical_catalog_counts=m['counts'],all_four_encoded_rank_metadata_match=True,
      independent_operand_axes=sorted(axes),uses_by_axis=axis_uses,two_operand_commands=both,
      nonzero_outer_stride_operands=nonzero_outer,half_inner_operands=halves,
      persisted_all_address_mask_operand_roundtrip_uses=accepted,original_verifier_counterexamples=mutants,
      compiled_catalog_canonical_correct=True,persisted_verifier_source_complete=False,
      compiled_6c7_join_qualified=False,corrected_verifier_review_pending=True,
      local_geometry_replay_equal=True,SU_region_area_mm2=local['current_SU_region_area_mm2'],
      local_route_each_direction_fast_cycles=11,local_scenarios=local['scenarios'],
      placement_verdict=local['placement_verdict'],selected_local_candidate=local['selected_model_candidate'],
      no_old_route_power_subtraction=True,
      remaining=['Fermat immutable command/count/source binding fix and mutation replay',
      'actual SU and macro coordinates with displacement reservation',
      'catalog read ports, capture/page mux/decoder and CTS',
      'receiver ready, cold refill deadlines, reset/epoch and both-direction topology',
      'characterized local bidirectional control/data pipeline power and physical SS/FF'],
      full_operator_latency=None,hardware_admission=False,headline_rate=None,jobs_launched=0)
if __name__=='__main__':
    out=Path(sys.argv[1]);out.write_text(json.dumps(build(),sort_keys=True,indent=2)+'\n')
