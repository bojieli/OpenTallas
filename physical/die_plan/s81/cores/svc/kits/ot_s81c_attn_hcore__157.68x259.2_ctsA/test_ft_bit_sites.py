import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ft_bit_sites import table, validate_slot

GOOD = dict(name='ft0', width=1, stations=2, bit_site_cell_um=[1.404, .27],
            bit_sites_um=[[[4.32, 4.32], [6.48, 4.32]]])

def test_serializes_epoch_and_internal_stage_one():
    text = table([GOOD])
    assert 'dict set ff_bit_sites {ft0,1,0} {4.32 4.32}' in text
    assert 'dict set ff_bit_sites {ft0,1,1} {6.48 4.32}' in text
    assert 'ft0,0,' not in text

def test_legacy_has_no_explicit_slots():
    assert table([dict(name='old', width=1)]) == table([])

@pytest.mark.parametrize('change', [lambda s:s['bit_sites_um'][0].pop(),
    lambda s:s.update(stations=3),lambda s:s.pop('bit_site_cell_um'),
    lambda s:s['bit_sites_um'][0][0].__setitem__(0,float('nan'))])
def test_rejects_incomplete_or_nonphysical_sites(change):
    slot=copy.deepcopy(GOOD);change(slot)
    with pytest.raises(ValueError):validate_slot(slot)
