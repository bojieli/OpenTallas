import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_crom_finite_prefetch as C

def test_strip_wave_conflicts_and_finite_landing():
    a=set(range(1808,1808+1024))
    w=C.bank_waves(a)
    assert len(w)==8 and set().union(*w)==a
    assert all(len(x)<=135 for x in w)
    assert all(max((x//3)//45 for x in a)<4096 for _ in [0])

def test_credit_release_waits_for_receiver_and_reverse():
    x=C.credit_calendar(354,2)
    y=C.credit_calendar(354,128)
    assert x['last_cache_write_and_reverse_credit_tick']>y['last_cache_write_and_reverse_credit_tick']
    assert x['last_cache_write_and_reverse_credit_tick']>354*3
    assert not x['actual_sink_stall_bound']
    import pytest
    with pytest.raises(ValueError):C.credit_calendar(1,0)

def test_actual_cold_cache_and_ports_not_capacity_credit():
    r=C.build()
    assert r['commands_per_rank']==491 and r['gamma_commands_per_rank']==81
    assert sum(x['coefficient_reads'] for x in r['commands'])==549760
    assert r['staging']['gamma_FP32_bits']==327680
    assert r['staging']['generic_two_operand_doublebuffer_bits']==131072
    assert r['fill_port']['payload_FP32_bits']==512
    assert r['staging']['no_all_layer_reuse']
    assert r['bank_placement']['ports_per_bank']==1
    assert not r['hardware_build_ready'] and r['full_operator_critical_path_ticks'] is None
