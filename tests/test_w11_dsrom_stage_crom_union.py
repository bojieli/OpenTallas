import copy
import pytest
import w11_dsrom_stage_crom_union as U

@pytest.fixture(scope='module')
def result(): return U.build()

def test_all_stage_rank_operand_coverage(result):
    for r in result['ranks']:
        assert len(r['stages'])==41 and r['command_count']==491
        assert r['bound_operand_count']==729 and r['generated_operand_count']==2
        assert r['global_unique_words']==r['sum_stage_unique_words']==549760
        assert not r['crossstage_address_copies'] and not r['crossstage_tensor_copies']
        assert r['max_stage_words']==33648

def test_invalid_generated_source_and_global_constant(result):
    for r in result['ranks']:
        stages={s['layer']:s for s in r['stages']}
        assert stages[1]['unique_words']==33008
        assert stages[1]['L1invalid_ranges']==[[508800,529280]]
        assert stages[1]['invalid_words']==20480
        assert stages[14]['unique_words']==33648 and stages[14]['invalid_words']==0
        assert stages['head']['unique_words']==5120
        assert {o['tensor'] for s in r['stages'] for o in s['global_constant_operands']}=={'norm.weight'}
    assert not result['geometry_credit'] and not result['hardware_admission']

@pytest.mark.parametrize('mutation',['empty','predicate','range','tensor'])
def test_mutable_demand_rejected(mutation):
    d,_=U.load(U.DEMAND,True);x=copy.deepcopy(d)
    if mutation=='empty': x['ranks'][0]['records']=[]
    if mutation=='predicate': x['ranks'][0]['records'][0]['pred']^=1
    if mutation=='range': x['ranks'][0]['records'][0]['operand_demands'][0]['unique_address_ranges'][0][0]+=1
    if mutation=='tensor': x['ranks'][0]['records'][0]['operand_demands'][0]['tensor']='norm.weight'
    with pytest.raises(ValueError,match='immutable'): U.build(x)
