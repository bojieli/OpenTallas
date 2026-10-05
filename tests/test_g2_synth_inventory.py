"""Inventory acceptance must reject dropped memories and wrong feature modes."""
import copy
from tools.audit_g2_synth_inventory import audit


def fixture():
    return ({'modules': {'ot_a3_g2_cluster': {
        'parameter_default_values': {'RUNTIME_OPERANDS': '1'},
        'cells': {'bank': {'type': 'fakeram_512x128'},
                  'lookup': {'type': '$mem_v2', 'parameters': {
                      'WIDTH': '11', 'SIZE': '10000', 'RD_PORTS': '1', 'WR_PORTS': '0'}}}}}},
            {'argv': ['--param', 'RUNTIME_OPERANDS=1'],
             'expected_memory_instances': {'fakeram_512x128': 1}, 'expected_memory_bits': 65536})


def test_inventory_accepts_rom_but_not_writable_replacement():
    net, config = fixture()
    assert audit(net, config)['status'] == 'pass'
    net['modules']['ot_a3_g2_cluster']['cells']['lookup']['parameters']['WR_PORTS'] = '1'
    assert audit(net, config)['status'] == 'fail'


def test_inventory_rejects_missing_bank_and_disabled_runtime():
    net, config = fixture()
    missing = copy.deepcopy(net)
    del missing['modules']['ot_a3_g2_cluster']['cells']['bank']
    assert audit(missing, config)['status'] == 'fail'
    net['modules']['ot_a3_g2_cluster']['parameter_default_values']['RUNTIME_OPERANDS'] = '0'
    assert audit(net, config)['status'] == 'fail'


def test_inventory_rejects_unflattened_unknown_logic():
    net, config = fixture()
    net['modules']['ot_a3_g2_cluster']['cells']['unknown'] = {'type': 'unresolved_bank'}
    assert audit(net, config)['status'] == 'fail'


def test_inventory_derives_capacity_and_rejects_wrong_bit_budget():
    net, config = fixture()
    assert audit(net, config)['observed_macro_bits'] == 512 * 128
    config['expected_memory_bits'] += 1
    result = audit(net, config)
    assert result['status'] == 'fail'
    assert 'macro bit capacity differs from configuration' in result['issues']


def test_inventory_refuses_unknown_capacity_even_when_count_matches():
    net, config = fixture()
    net['modules']['ot_a3_g2_cluster']['cells']['bank']['type'] = 'fakeram_custom'
    config['expected_memory_instances'] = {'fakeram_custom': 1}
    result = audit(net, config)
    assert result['status'] == 'fail'
    assert result['observed_macro_bits'] is None


def test_inventory_counts_multiple_macro_geometries():
    net, config = fixture()
    net['modules']['ot_a3_g2_cluster']['cells']['other'] = {'type': 'fakeram_256x128'}
    config['expected_memory_instances']['fakeram_256x128'] = 1
    config['expected_memory_bits'] += 256 * 128
    result = audit(net, config)
    assert result['status'] == 'pass'
    assert result['observed_macro_bits'] == (512 + 256) * 128
