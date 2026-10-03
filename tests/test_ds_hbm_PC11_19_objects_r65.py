from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_PC11_19_objects_r65 as R


def native(words):
    code=[dict(dst='a',op='CONST',src=[],shape=[6],attrs={'dtype':'F32'}),
          dict(dst='b',op='F2I',src=['a'],shape=[6],attrs={})]
    n={'instructions':[dict(pc=0,rank_bindings=[{'rank':0,'template':'t'}],
       writes=[{'version':'ids','home_indices':[0],'native_result_binding':{'result':'ids'}}])],
       'templates':{'t':{'code':code,'outputs':{'ids':'b'}}}}
    return n,[{'rank_group':[0],'word_count':words}]


def test_I64_output_requires_two_U32_words_per_element():
    n,h=native(12);rows,faults=R.output_rows(n,h,stop=0)
    assert not faults and rows[0]['dtype']=='int64' and rows[0]['bytes']==48
    assert R.object_model(rows)['produced_payload_bytes_no_release_credit']==48


def test_four_byte_generic_expansion_refused_without_padding():
    n,h=native(6);rows,faults=R.output_rows(n,h,stop=0)
    assert len(faults)==1 and faults[0]['physical_home_bytes']==24
    assert rows[0]['bytes']==48 and rows[0]['cache_release_credit_bytes']==0
    assert h[0]['word_count']==6


def test_unimplemented_dtype_operation_never_zero_cost():
    n,h=native(12);n['templates']['t']['code'][-1]['op']='UNKNOWN'
    with pytest.raises(ValueError,match='unpriced'):R.output_rows(n,h,stop=0)


def test_old_cold_objects_and_addressed_readback_are_separate():
    n,h=native(12);rows,_=R.output_rows(n,h,stop=0);v=R.object_model(rows)
    assert v['old_and_cold_cache_object_upper_bytes']==2*v['one_producer_cache_object_upper_bytes']
    assert v['publication_scatter_and_readback_workspace_upper_bytes']>48
    assert v['physical_RF_mirror_data_not_doublecounted_as_cache']
