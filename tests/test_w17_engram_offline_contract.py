import subprocess
import pytest
from tools.w17_engram_offline_contract import audit,build

def test_offline_authority_and_capacity():
    r=build()
    assert not r['runtime_initializer_required'] and not r['mutable_overlay_required']
    c=r['physical_composition']
    assert c['total_logical64_words_per_rank']==508800+2*20480
    assert c['candidate_capacity']==45*4096*3
    assert c['candidate_spare_before_padding']==3200
    assert not r['hardware_admission'] and r['full_token_cycles'] is None

def test_activation_and_consumer_substitution_reject():
    s=subprocess.check_output(['git','show','d2c28c279:tools/hdc_program_v41.py']).decode()
    with pytest.raises(ValueError):audit(s.replace('lw(L, "engram.q_weight")','activation(L, "engram.q_weight")'))
    with pytest.raises(ValueError):audit(s.replace('b_src=I.SRC_CLO,\n                b_base=lay.cb[(L, "ewgt")]','b_src=I.SRC_VM,\n                b_base=lay.cb[(L, "ewgt")]'))
