import copy
import pytest
import w11_dsrom_stage_crom_relocation as R

@pytest.fixture(scope='module')
def result(): return R.build()

def test_all_rank_exact_base_only_relocation(result):
    for rank in result['ranks']:
        assert rank['CROM_command_count']==491 and rank['source_operand_count']==731
        assert len(rank['stages'])==41 and not rank['runnable']
        for s in rank['stages']:
            assert len(s['candidate_homes'])==3
            assert all(b['stride_and_half_unchanged'] and b['published_base'] is None for b in s['bindings'])
        stages={s['layer']:s for s in rank['stages']}
        assert stages[1]['invalid_local_ranges']==[[12528,33008]]
        assert stages[14]['invalid_local_ranges']==[]
        assert next(b for b in stages[14]['bindings'] if b['tensor']=='L14.engram.q_times_k')['diagnostic_local_base']==13168
    assert result['publication_blocked'] and not result['image_admission']
    assert result['adopted_geometry'] is None and not result['actual_service_bound']

def test_invalid_source_blocks_actual_publication():
    with pytest.raises(ValueError,match='L1 invalid'): R.require_publication()

@pytest.mark.parametrize('mutation',['validity','catalog','empty','geometry'])
def test_counterfeit_stage_model_cannot_publish(mutation):
    models,_=R.authorities();x=copy.deepcopy(models)
    if mutation=='validity': x[6]['rank_values'][0]['homes'][1]['source_invalid_words']=0
    if mutation=='catalog': x[6]['stages'][0]['request_catalog_word_SHA256']='0'*64
    if mutation=='empty': x[6]['rank_values']=[]
    if mutation=='geometry': x[6]['regular_element']['readonly_banks_per_home']=3
    with pytest.raises(ValueError,match='immutable'): R.build(x)
    with pytest.raises(ValueError,match='immutable'): R.require_publication(x)
