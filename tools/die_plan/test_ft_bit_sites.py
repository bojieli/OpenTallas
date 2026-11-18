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


def test_explicit_stage_zero_serializes_all_payload_and_epoch_sites():
    slot = copy.deepcopy(GOOD)
    slot.update(explicit_stage0=True)
    slot['bit_sites_um'].insert(0, [[8.64, 4.32], [10.8, 4.32]])
    text = table([slot])
    assert 'dict set ff_bit_sites {ft0,0,0} {8.64 4.32}' in text
    assert 'dict set ff_bit_sites {ft0,0,1} {10.8 4.32}' in text
    assert 'dict set ff_bit_sites {ft0,1,0} {4.32 4.32}' in text
    slot['explicit_stage0'] = False
    with pytest.raises(ValueError, match='explicit_stage0'):
        validate_slot(slot)


def test_explicit_stage_zero_keeps_legacy_internal_only_table_identical():
    slot = copy.deepcopy(GOOD)
    slot['explicit_stage0'] = True
    assert table([slot]) == table([GOOD])


def test_snap_moves_offgrid_stage_onto_core_grid():
    from ft_bit_sites import snap_slots
    slot = copy.deepcopy(GOOD)
    slot['bit_sites_um'] = [[[82.9376, 176.8544], [82.9376, 177.1244]]]
    out, moved = snap_slots([slot, dict(name='old', width=1)], (4.32, 4.32))
    assert moved == 2
    assert out[0]['bit_sites_um'] == [[[82.944, 176.85], [82.944, 177.12]]]
    assert out[1] == dict(name='old', width=1)
    assert slot['bit_sites_um'][0][0] == [82.9376, 176.8544]


def test_snap_keeps_ongrid_sites_and_refuses_collisions():
    from ft_bit_sites import snap_slots
    out, moved = snap_slots([GOOD], (4.32, 4.32))
    assert moved == 0 and out[0]['bit_sites_um'] == GOOD['bit_sites_um']
    slot = copy.deepcopy(GOOD)
    slot['bit_sites_um'] = [[[4.32, 4.32], [4.33, 4.33]]]
    with pytest.raises(ValueError, match='snap to one site'):
        snap_slots([slot], (4.32, 4.32))
