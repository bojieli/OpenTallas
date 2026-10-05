"""Actual manifest limits; no physical image or historical PASS transfer."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w11_dsrom_full_tp_program_contract as C

def test_actual_manifest_and_execution_refusal():
    c=C.constant_writer_contract()
    assert c['source']['commit']==C.MAIN_BINDING_PIN
    assert c['final_norm']['output_words_per_reference_view']==5120
    assert c['final_norm']['current_fullprogram_image_binding'] is None
    assert c['CROM']['HC_scale_output_words']==sum(c['CROM']['HC_scale_repeat_counts'])==24
    assert c['CROM']['sink_words_per_rank']==16
    assert c['wo_a_existing_producer']['reference_bank_word_bits']==32
    assert c['wo_a_existing_producer']['reference_address_count']==131072
    assert c['head']['candidate_vocab_quarter_WROM_words']==2585600
    assert c['vocabulary_mapping']['capacity_deficit_words']==2061312
    assert not c['vocabulary_mapping']['address_truncation_allowed']
    with pytest.raises(ValueError,match='unbound'):C.require_actual_constant_writer_binding(c)

def test_all_vocabulary_addresses_exact_no_alias_or_truncation():
    for token in range(129280):
        a=C.vocabulary_address(token)
        assert a['logical_rank']*32320+a['local_row']==token
        assert a['word_end_exclusive']-a['word_start']==80
        assert 0<=a['word_start']<a['word_end_exclusive']<=2585600
        assert a['actual_owner'] is None
    assert C.vocabulary_address(32319)['word_end_exclusive']==2585600
    assert C.vocabulary_address(32320)['word_start']==0
    assert C.vocabulary_address(129279)['logical_rank']==3

@pytest.mark.parametrize('token',[-1,129280,True,1.5])
def test_invalid_token_rejected(token):
    with pytest.raises(ValueError):C.vocabulary_address(token)
