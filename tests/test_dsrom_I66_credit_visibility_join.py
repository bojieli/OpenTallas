import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('creditjoin', Path(__file__).resolve().parents[1] / 'tools/dsrom_I66_credit_visibility_join.py')
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)


def case(credit_offset=7):
    return [{'kind': kind, 'row': r, 'time': str(10*r+t)} for r in range(576)
            for kind, t in [('read_accept_reserved', 0), ('consumer_accept', 3), ('home_visible', 5), ('credit_return_capture', credit_offset)]]


def leases():
    return {r: {'owner': 'frozen-context/VM-output', 'address': 1000+r,
                'reserved_before': -1, 'released_after': 10*r+6} for r in range(576)}


def test_visibility_anchored_credit():
    assert M.check(case(), 2)['downstream_transfers'] == 0


def test_delivery_anchored_credit_needs_distinct_downstream_lease():
    with pytest.raises(ValueError, match='visibility'): M.check(case(5), 2)
    assert M.check(case(5), 2, leases())['downstream_transfers'] == 576


@pytest.mark.parametrize('fault', ['alias', 'late_reserve', 'early_release', 'missing', 'zero_delay', 'duplicate'])
def test_bad_ownership_transfer(fault):
    data, lease, delay = case(5), leases(), 2
    if fault == 'alias': lease[1]['address'] = lease[0]['address']
    if fault == 'late_reserve': lease[0]['reserved_before'] = 0
    if fault == 'early_release': lease[0]['released_after'] = 5
    if fault == 'missing': del lease[0]
    if fault == 'zero_delay': delay = 0
    if fault == 'duplicate': data.append(data[0])
    with pytest.raises(ValueError): M.check(data, delay, lease)
