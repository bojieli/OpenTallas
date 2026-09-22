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
