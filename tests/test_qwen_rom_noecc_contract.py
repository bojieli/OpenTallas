import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_noecc_contract import payload_word,contract


def test_payload_exact_copy_and_no_parity_bits_for_all_bit_positions():
    words=[0,(1<<256)-1]+[1<<bit for bit in range(256)]
    for word in words:
        packed=payload_word(word)
        assert packed & ((1<<256)-1)==word
        assert packed>>256==0
        assert int(f'{packed:067x}',16)==word
    for word in [-1,1<<256]:
        with pytest.raises(ValueError):payload_word(word)


def test_only_explicit_projection_surcharge_removed_not_physical_geometry():
    c=contract();s=c['fixed_Qwen_shape'];m=c['model_owner_delta']
    assert s['physical_allocated_bits']-s['payload_capacity_bits']==409600
    assert m['old_projection_multiplier']*m['affected_storage_projection_ratio']==1
    assert c['actual_decoder_removed']==0 and c['physical_macro_area_credit']==0
    assert not c['new_macro_ready'] and not c['PnR_admitted']
    assert not c['policy']['KV_SRAM_changed'] and not c['policy']['HBM_changed']
    assert not c['policy']['configuration_ROM_ECC_required']
    assert c['policy']['descriptor_validity_preserved'] and c['policy']['address_bounds_preserved']
    assert c['policy']['descriptor_identity_preserved'] and c['policy']['arithmetic_contract_preserved']
    assert c['policy']['mutable_control_state_protection_preserved']
    assert c['policy']['link_protection_preserved'] and c['policy']['pinned_jobs_unchanged']
