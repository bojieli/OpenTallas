import sys,json
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_provider_clock_contract as P

def samples():
    s={k:0 for k in P.REQUIRED}
    s.update(edge=100,pc=66,st=6,d_unit=3,qe_mode=0,X_ROM=1,FULL_SHAPE=1,waited=1,unit_ready=1,q_gate=1,kv_gate=1,m0_gate=1,win_admit=1,rom_ready=1)
    n=dict(s,edge=101,st=7,qe_go=1,rom_q_go=1)
    return s,n

def test_source_hook_and_registered_admission(provenance):
    c=P.source_hook_contract();assert c['observed_program_origin'] is None
    b=P.bind_program_origin(samples(),provenance)[0]
    assert b['core_issue_edge']==100 and b['native_adapter_accept_edge']==101
    assert b['actual_coll_busy_release'] is None and not b['physical_or_fulltoken_credit']

@pytest.mark.parametrize('gate',['waited','unit_ready','q_gate','kv_gate','m0_gate'])
def test_held_gate_is_not_offered_start(gate,provenance):
    s,n=samples();s[gate]=0
    assert P.bind_program_origin([s,n],provenance)==[]

def test_fullsource_provider_and_nextedge_required(provenance):
    s,n=samples();s['X_ROM']=0
    with pytest.raises(ValueError,match='D1HBM'):P.bind_program_origin([s,n],provenance)
    s,n=samples();n['edge']=102
    with pytest.raises(ValueError,match='next-edge'):P.bind_program_origin([s,n],provenance)

def test_do_not_invent_direct_collbusy_QE_predicate(provenance):
    s,n=samples();s['coll_busy']=1
    assert P.bind_program_origin([s,n],provenance)[0]['coll_busy_at_issue']==1

def test_provider_unknowns_and_measured_margin_are_not_zero_cost():
    m=P.provider_model()
    assert m['broadcast']['source_BST']==17 and m['broadcast']['full_bus_bits']==1632
    assert m['broadcast']['physical_wire_clock_delivery_ps'] is None
    assert m['configuration']['remaining_single_edge_before_capture_setup_route_clock_ps']==pytest.approx(106.2577504850932)
    assert m['weight_capture']['single_edge_residual_before_setup_route_clock_ps']==pytest.approx(29.370633106610285)
    assert m['root_and_writer']['transport_ps'] is None and not m['context_admission']
    assert m['imposed_process_limits']==[]

@pytest.fixture
def provenance(tmp_path):
    # Artificial static gate inputs for unit tests, never a runtime receipt.
    i=P.OUT/'inputs';word=P.S.load(i/'I66_current_patched_word.json')['word_hex']
    paths={};hashes={};plus={}
    for rank in range(4):
        d=tmp_path/str(rank);d.mkdir();p=d/'prog.hex';p.write_text('0\n'*66+word+'\n');paths[str(rank)]=str(p);hashes[str(rank)]=P.S.sha(p);plus[str(rank)]=['+DIR='+str(d),'+OT_ROM_DIR='+str(d)]
        for name in ['spine_phase.hex','spine_keys.hex','spine_stream.hex']:(d/name).write_text('0\n')
    params=dict(FULL_SHAPE=1,X_ROM=1,ROM_PHW=10,ROM_R=128,ROM_BST=17,logical_NP=4096,NBF=724,ROM_FBW=1632)
    binary=tmp_path/'binary';binary.write_bytes(b'artificial gate test only')
    sources=dict(core=str(i/'core.sv.txt'),spine=str(i/'runtime_spine.sv.txt'),wrapper=str(i/'runtime_wrapper.sv.txt'))
    record=tmp_path/'compile.json';record.write_text(json.dumps(dict(binary_sha256=P.S.sha(binary),parameters=params,source_sha256={k:P.S.sha(Path(v)) for k,v in sources.items()})))
    return dict(parameters=params,binary_path=str(binary),binary_sha256=P.S.sha(binary),compile_manifest_path=str(record),source_paths=sources,program_paths=paths,program_sha256=hashes,enrolled_plusargs=plus,field_image_paths={str(rank):str(tmp_path/str(rank)) for rank in range(4)},field_image_sha256={str(rank):{name:P.S.sha(tmp_path/str(rank)/name) for name in ['spine_phase.hex','spine_keys.hex','spine_stream.hex']} for rank in range(4)})

@pytest.mark.parametrize('mutation',['PHW6','old_word','no_program_enrollment','wrong_compiled_source'])
def test_current_program_source_provenance_mutants_fail(provenance,mutation):
    if mutation=='PHW6':provenance['parameters']['ROM_PHW']=6
    elif mutation=='old_word':
        p=Path(provenance['program_paths']['0']);p.write_text('0\n'*67);provenance['program_sha256']['0']=P.S.sha(p)
    elif mutation=='no_program_enrollment':provenance['enrolled_plusargs']['0']=[]
    else:
        p=Path(provenance['compile_manifest_path']);m=json.loads(p.read_text());m['source_sha256']['core']='0'*64;p.write_text(json.dumps(m))
    with pytest.raises(ValueError):P.enrollment_gate(provenance)

def test_registered_EID_read_and_dynamic_stage_cannot_alias_local_I66():
    frame=[dict(edge=101,rom_vre=1,rom_vaddr=366688),dict(edge=102,rom_vq=0),dict(edge=105,phase_accept=1,phase=10,key_word=2149580800)]
    assert P.bind_indexed_read(frame,100,0)['EID']==0
    frame[1]['rom_vq']=383;frame[2].update(phase=285,key_word=2151149568)
    with pytest.raises(ValueError,match='dispatch missing'):P.bind_indexed_read(frame,100,0)
    assert P.bind_indexed_read(frame,100,1)['owner_stage']==1
    frame[1]['rom_vq']=384
    with pytest.raises(ValueError,match='invalid EID'):P.bind_indexed_read(frame,100,1)
