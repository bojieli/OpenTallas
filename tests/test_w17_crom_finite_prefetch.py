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
    no_return_wire=C.credit_calendar(354,2,reverse_route=0)
    assert x['last_cache_write_and_reverse_credit_tick']>no_return_wire['last_cache_write_and_reverse_credit_tick']
    one=C.credit_calendar(1,2)
    zero=C.credit_calendar(1,2,reverse_route=0)
    assert one['last_cache_write_and_reverse_credit_tick']-zero['last_cache_write_and_reverse_credit_tick']==75*3
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
    assert r['compiler_control_storage']['selector_bits']==8
    assert r['compiler_control_storage']['fill_selector_bits_per_entry']==151
    assert r['compiler_control_storage']['total4096x274_macros']==16
    assert r['selector_control_exactness']['maximum_actual_selector']==134
    assert r['selector_control_exactness']['old7bit_alias_uses']>0
    assert not r['selector_control_exactness']['actual_compiled_control_image_bound']
    assert r['compiled_software_catalog']['counts_match_current_calendar']
    assert r['compiled_software_catalog']['metadata_roundtrip_uses_per_rank']==549760
    assert not r['compiled_software_catalog']['runtime_tags_credits_ports_and_contextual_SSFF_bound']
    assert r['compiled_software_catalog']['immutable_source_guard_software_closed']
    assert r['compiled_software_catalog']['original_catalog_artifacts_hashes_verified_unchanged']
    assert r['compiled_software_catalog']['compiler_sha256']=='a8417b23f889f0225f574b13674be01ae38e2d89963a1f8102d90064453dc470'

def test_high_selector_negative_preserves_actual_first_gamma_alias():
    landing=next(sorted(wave) for wave in C.bank_waves(set(range(1808,1808+1024)))
                 if len(wave)>128 and sorted(wave)[128]==2069)
    assert landing[128]==2069 and landing[128 & 127]==1941
    assert all((index & 255)==index for index in range(135))
    assert all((index & 127)!=index for index in range(128,135))
