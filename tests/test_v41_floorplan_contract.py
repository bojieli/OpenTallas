import copy
import pytest
from tools.v41_floorplan_contract import build, validate


def test_reservations_partition_die_without_claiming_fit():
    d = validate(build())
    assert len([r for r in d['regions'] if r['kind'] == 'compute']) == 4
    assert d['clock_hz_verified'] is None


@pytest.mark.parametrize('failure', ['overlap', 'outside', 'rate', 'fit'])
def test_reject_invalid_geometry_or_unsupported_claim(failure):
    d = copy.deepcopy(build())
    if failure == 'overlap':
        d['regions'][1] = dict(d['regions'][0])
    elif failure == 'outside':
        d['regions'][0]['x_mm'] = -1
    elif failure == 'rate':
        d['token_rate'] = 8000
    else:
        d['macro_packing_verified'] = True
    with pytest.raises(AssertionError):
        validate(d)
