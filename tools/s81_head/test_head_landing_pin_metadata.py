import copy
import json
import pytest
from head_landing_pin_metadata import derive, sha


def fixture():
    old = [dict(bus='data', bit=0, face='W', x=0, y=5, layer='M4', retained='exact')]
    rows = [dict(name='data[0]', layer='M4', x=.1, y=5),
            dict(name='cland_ready', layer='M7', x=3, y=4),
            dict(name='strap_ca_k[0]', layer='M5', x=7, y=8),
            dict(name='clk_t1', layer='M7', x=6, y=6)]
    plan = dict(schema='opentallas.die_plan.partition_plan_pins.v1', die='s81_head', type='hd_host_n', pins=rows)
    raw = json.dumps(plan).encode()
    freeze = dict(schema='opentallas.partition_freeze.v1', die='s81_head', type='hd_host_n', pins=4,
                  pins_sha256=sha(raw), outline_um=[10, 10])
    bind = [dict(bus='data', bit=0), dict(bus='cland_ready'), dict(bus='strap_ca_k', bit=0), dict(bus='clk_t1')]
    wrapper = 'module host(input [0:0] data, input cland_ready, input [0:0] strap_ca_k, input clk_t1); endmodule'
    return [old, plan, freeze, bind, wrapper, 'host', raw]


def test_restore_all_source_declarations_without_observed_pin_input():
    args = fixture(); original = copy.deepcopy(args[0]); result, receipt = derive(*args)
    assert args[0] == original and result[:len(original)] == original
    assert receipt['appended_rows'] == 2 and receipt['audit_rows'] == 3
    assert receipt['existing_interior_exclusions'] == ['clk_t1']
    assert {p['bus'] for p in result[1:]} == {'cland_ready', 'strap_ca_k'}
    assert all(p['face'] == 'island' for p in result[1:])


def test_refuse_changed_source_hash_or_wrapper_or_bind():
    for index, value, reason in [(6, b'changed', 'hash'),
                                  (4, 'module host(input data); endmodule', 'ABI'),
                                  (3, [], 'port-bind')]:
        args = fixture(); args[index] = value
        with pytest.raises(ValueError, match=reason): derive(*args)


def test_refuse_unrelated_plan_and_undeclared_old_pin():
    args = fixture(); args[2]['die'] = 'other'
    with pytest.raises(ValueError, match='identity'): derive(*args)
    args = fixture(); args[0].append(dict(bus='observed_extra', layer='M4', x=1, y=1, face='island'))
    with pytest.raises(ValueError, match='undeclared'): derive(*args)
