"""Source-pinned structural bit proofs only: no compiler or hardware claim."""
import copy,json,sys,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import prepare_observer_explicit_widths as widths
import run_observer_explicit_width_lint as runner
OUT=ROOT/widths.OUT;DATA=(OUT/'plan.json').read_bytes();PLAN=json.loads(DATA)
PRIOR=json.loads((ROOT/widths.PRIOR).read_bytes())

def test_plan_valid_without_compiler():runner.validate_plan(PLAN)

@pytest.mark.parametrize('i',[0,1])
def test_exact_inverse_original_defaultoff_and_unchanged_observer(i):
    results=widths.validate_inverse_to_real(ROOT)
    assert results[i]['exact_inverse_to_original'] and results[i]['default_observation']==0
    old,_,new,_=widths.COPIES[i];before=(ROOT/old).read_text();after=(ROOT/new).read_text()
    assert widths.inverse(after,i)==before
    assert after==widths.render(before,i)
    assert 'lint_off' not in after and 'lint_on' not in after
    marker='// BEGIN WINDOW ONLY OBSERVER' if i==0 else '// BEGIN SIM OBSERVER'
    assert after[after.index(marker):]==before[before.index(marker):]

def evaluate(bit_map,values):return ''.join('0' if b=='0' else values[b] for b in bit_map)

@pytest.mark.parametrize('i',[0,1])
@pytest.mark.parametrize('name',['dbg_faults','dbg_state'])
def test_symbolic_fourstate_all_bit_identity_and_adversarial_patterns(i,name):
    old,_,new,_=widths.COPIES[i];a=widths.mapping((ROOT/old).read_text(),name);b=widths.mapping((ROOT/new).read_text(),name)
    assert a==b # Each field bit is independent; identity proves arbitrary combinations.
    tokens=set(a)-{'0'}
    for sym in ['0','1','X','Z']:
        all_same={t:sym for t in tokens};assert evaluate(a,all_same)==evaluate(b,all_same)
        for t in tokens:
            basis={k:'0' for k in tokens};basis[t]=sym
            assert evaluate(a,basis)==evaluate(b,basis)
    if name=='dbg_state':
        assert a[:4]==['0']*4
        assert a[4:36]==['dbg_fsticky['+str(k)+']' for k in range(31,-1,-1)]
        assert evaluate(b,{t:'1' for t in tokens})[:4]=='0000'
    else:assert a[:12]==['0']*12 and a[-1]=='0'

@pytest.mark.parametrize('i',[0,1])
def test_packed_port_all_zero_source_binding(i):
    records=widths.source_field_authority(ROOT,PRIOR)
    assert records[i]['packed_input']['FULL_SHAPE']==1
    assert records[i]['packed_input']['width']==4*(512//32)*265==16960
    _,_,new,_=widths.COPIES[i]
    assert ".att_packed_kv_w(16960'd0)" in (ROOT/new).read_text()
    assert 0==int('0'*16960,2)

@pytest.mark.parametrize('i',[0,1])
@pytest.mark.parametrize('name',['dbg_faults','dbg_state'])
def test_real_field_swap_mutant_rejected(i,name):
    old,_,new,_=widths.COPIES[i];before=(ROOT/old).read_text();after=(ROOT/new).read_text()
    first,second=('dut.u_tile.u_core.su_fault','dut.u_tile.u_core.me_fault') if name=='dbg_faults' else ('dut.e_valid','dut.e_ready')
    prefix,expr=after.split('wire [31:0] dbg_faults = ',1) if name=='dbg_faults' else after.split('assign dbg_state = ',1)
    packed,suffix=expr.split('};',1)
    mutated=packed.replace(first,'TEMP_SWAP').replace(second,first).replace('TEMP_SWAP',second)
    assert packed!=mutated
    changed=prefix+('wire [31:0] dbg_faults = ' if name=='dbg_faults' else 'assign dbg_state = ')+mutated+'};'+suffix
    with pytest.raises(ValueError,match='field mapping changed'):widths.prove_mapping(before,changed)

@pytest.mark.parametrize('i',[0,1])
def test_extra_fault_padding_moves_fields_rejected(i):
    old,_,new,_=widths.COPIES[i]
    changed=(ROOT/new).read_text().replace("dbg_faults = {12'd0,","dbg_faults = {13'd0,")
    with pytest.raises(ValueError,match='packing overflow'):widths.prove_mapping((ROOT/old).read_text(),changed)

@pytest.mark.parametrize('i',[0,1])
def test_width_inverse_rejects_zero_spelling_or_sign_change(i):
    _,_,new,_=widths.COPIES[i]
    changed=(ROOT/new).read_text().replace("16960'd0","16960'sd0")
    with pytest.raises(ValueError):widths.inverse(changed,i)

def test_ancestor_source_census_and_caps_and_mutants_unchanged():
    assert PLAN['caps']==PRIOR['caps'] and PLAN['tool']==PRIOR['tool']
    for i,(a,b) in enumerate(zip(PRIOR['modes'],PLAN['modes'])):
        old,oldtop,new,newtop=widths.COPIES[i]
        assert a['parameters']==b['parameters'] and a['mutants']==b['mutants']
        assert b['argv']==[x.replace(oldtop,newtop).replace(old,new) for x in a['argv']]
        assert {k:v for k,v in a['source_sha256'].items() if k!=old}=={k:v for k,v in b['source_sha256'].items() if k!=new}
        text=(ROOT/new).read_text()
        for m in b['mutants']:
            assert text.count(m['find'])==1 and m['timeout_seconds']==30
    assert len(PLAN['modes'][0]['source_sha256'])==124 and len(PLAN['modes'][1]['source_sha256'])==130

def test_prior_go_and_pending_new_go_inert():
    old=ROOT/'results/rtl/observer_resource_lint_execution_d1b55a45_20261002/GO.json'
    for g in [json.loads(old.read_bytes()),json.loads((OUT/'GO.template.json').read_bytes())]:
        with pytest.raises(ValueError):runner.require_go(DATA,g)

@pytest.mark.parametrize('mutation',[
 lambda p:p['modes'][0]['argv'].append('-Wno-WIDTH'),
 lambda p:p['caps'].update(memory_bytes=65*1024**3),
 lambda p:p['modes'][1]['parameters'].update(CKV_SELECTED=0),
 lambda p:p['modes'][0]['parameters'].update(SUN=16),
])
def test_warning_waiver_caplift_or_wrong_geometry_rejected(mutation):
    p=copy.deepcopy(PLAN);mutation(p)
    with pytest.raises(ValueError):runner.validate_plan(p)

def test_source_authority_declaration_mutation_rejected():
    assert widths.declaration_width('wire [3:0] e_go, e_ready, e_idle, e_fault;', 'e_fault')[0]==4
    with pytest.raises(ValueError):widths.declaration_width('wire e_fault;\nwire [3:0] e_fault;', 'e_fault')

def test_missing_go_rejects_before_scratch(tmp_path):
    scratch=tmp_path/'scratch'
    with pytest.raises(ValueError):runner.execute(ROOT,OUT/'plan.json',OUT/'GO.template.json',scratch)
    assert not scratch.exists()

def test_plan_only_cli():
    result=subprocess.run([sys.executable,str(ROOT/'tools/run_observer_explicit_width_lint.py'),'--plan',str(OUT/'plan.json')],capture_output=True,text=True,timeout=10)
    assert result.returncode==0 and 'PLAN ONLY' in result.stdout

def test_plan_generator_cannot_overwrite_existing_evidence():
    before=(OUT/'classification.json').read_bytes();plan=(OUT/'plan.json').read_bytes()
    result=subprocess.run([sys.executable,str(ROOT/'tools/plan_observer_explicit_width_gate.py')],cwd=ROOT,capture_output=True,text=True,timeout=10)
    assert result.returncode!=0 and 'FileExistsError' in result.stderr
    assert (OUT/'classification.json').read_bytes()==before and (OUT/'plan.json').read_bytes()==plan
