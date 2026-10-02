import importlib.util,itertools
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'tools/dsrom_PAR2_clean_terminal_model.py'
S=importlib.util.spec_from_file_location('clean',P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
@pytest.fixture(scope='module')
def model():return M.build()
@pytest.mark.parametrize('k',[256,272])
def test_clean_raw_equals_source_decoder(k):
    for d in [0,(1<<k)-1,*[1<<j for j in range(k)]]:
        cw=M.encode(d,k);assert M.check_word(cw,k)[2]
        assert M.source_decoder(cw,k)==(d,False,False)
@pytest.mark.parametrize('k',[256,272])
def test_every_single_bit_correction_is_held_not_clean(k):
    data=(1<<k)-1;cw=M.encode(data,k)
    for b in range(k+10):
        bad=cw^(1<<b);assert not M.check_word(bad,k)[2]
        assert M.source_decoder(bad,k)==(data,True,False)
@pytest.mark.parametrize('k',[256,272])
def test_every_double_bit_fault_refuses_clean(k):
    cw=M.encode(0,k)
    for a,b in itertools.combinations(range(k+10),2):
        bad=cw^(1<<a)^(1<<b);assert not M.check_word(bad,k)[2]
        assert M.source_decoder(bad,k)[2]
def test_measured_corrector_not_free_or_pipeline(model):
    a,b=model['decoder_entries'];assert a['full_corrector_held_intervals_lower_bound_no_wire_setup_or_clockq']==4
    assert b['full_corrector_held_intervals_lower_bound_no_wire_setup_or_clockq']==3
    assert model['direct_rawmacro_plus_fullK256_held_lower_bound_intervals']==5
    assert all(d['detector_mapped_delay_unmeasured'] and not d['registered_hold_closed'] for d in [a,b])
def test_finite_exception_and_no_free_nonce_storage(model):
    f=model['finite_witness'];assert f['all_words_repair_counterfactual_schedule']['raw_prefetch_terminal_tick']>f['clean_schedule']['raw_prefetch_terminal_tick']
    assert f['clean_schedule']['accepted_reads']==800 and f['clean_schedule']['final_read_debt']==0
    assert model['buffer_and_fence']['gather_full_packet_bits']==90
    assert model['area']['extra_inline_bits']==512 and model['area']['added_FF50_policy_mm2']>0
    assert not model['admission']['fulltile_PR'] and not model['admission']['normal_latency_calibrated']
    assert not model['encoding_contract']['current_physical_FP4_encoder_placement_proven']
