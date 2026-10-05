import copy
import pytest
from tools import w16_crom_stage_catalog_binding as S

def operand_fixture():
 source=dict(operand='b',tensor='fixture',kind='checkpoint_CROM',original_encoded_base=100,outer_stride=4,inner_stride=1,half_inner=True,
  source_valid=True,provenance=dict(kind='synthetic_test_only'))
 canonical=dict(operand='b',tensor='fixture',kind='checkpoint_CROM',base=100,outer_stride=4,inner_stride=1,half_inner=True)
 return source,canonical

def test_half_axis_relocation_preserves_exact_lane_destinations():
 source,c=operand_fixture();m={100:0,101:1,104:4,105:5}
 r=S.bind_operand(source,c,{},[[(0,0),(0,1),(0,2),(0,3),(1,0),(1,2)]],m,1)
 assert r['exact_same_stride_translation'] and r['destination_uses']==6
 assert r['bursts'][0]['operand_lane_local_address_SHA256']==S.digest([[1,0,0],[1,1,0],[1,2,1],[1,3,1],[1,4,4],[1,5,5]])

def test_dense_collapse_cannot_silently_preserve_stride():
 source,c=operand_fixture()
 r=S.bind_operand(source,c,{},[[(0,0),(1,0)]],{100:0,104:1},0)
 assert not r['exact_same_stride_translation'] and 'REFUSED' in r['compiler_action']

@pytest.mark.parametrize('mutant',['missing_address','wrong_axis','stride'])
def test_refuse_lost_or_changed_source_reference(mutant):
 source,c=operand_fixture();m={100:0,101:1}
 if mutant=='missing_address':m={101:0}
 elif mutant=='wrong_axis':c['operand']='c'
 else:c['outer_stride']=5
 with pytest.raises(ValueError):S.bind_operand(source,c,{},[[(0,0),(0,2)]],m,0)

def test_duplicate_stage_union_is_rejected():
 with pytest.raises(ValueError):S.dense_map(dict(ranges=[[1,4],[3,5]],unique_words=5))

def test_actual_fourrank_stage_catalog_correspondence_and_unpriced_calendar():
 r=S.build()
 assert r['maximum_stage_words']==33648 and len(r['ranks'])==4
 assert not r['old45bank_calendar_transferred'] and r['physical_bank_count'] is None
 assert len(r['retained_L14_product_pins'])==4
 for rank in r['ranks']:
  assert rank['PCs_bound']==491 and rank['destination_uses_bound']==549760
  assert len(rank['stages'])==41
  l1=next(s for s in rank['stages'] if s['layer']==1)
  assert l1['invalid_source_words']==20480 and not l1['all_source_values_available']
  l14=next(s for s in rank['stages'] if s['layer']==14)
  assert l14['words']==33648 and l14['all_source_values_available']
  for stage in rank['stages']:
   assert stage['actual_bank_count'] is None and not stage['catalogue_recompiled']
   for c in stage['commands']:
    assert c['earliest_consumer_issue_tick'] is None and c['future_local_bank_waves'] is None
