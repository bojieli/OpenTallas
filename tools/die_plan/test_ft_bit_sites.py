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


def _packed_column(n=13, pitch=0.0844, x=30.24, y=1082.9376):
    return dict(name='cws1', width=n - 1, stations=2, bit_site_cell_um=[1.404, .27],
                bit_sites_um=[[[x, round(y + i * pitch, 4)] for i in range(n)]])


def test_footprint_conflicts_finds_subrow_pitch_and_x_step():
    from ft_bit_sites import footprint_conflicts
    assert footprint_conflicts([GOOD], (4.32, 4.32)) == []
    assert len(footprint_conflicts([_packed_column()], (0.0, 0.0))) == 8       # 13 bits in 5 rows
    xs = dict(GOOD, bit_sites_um=[[[4.32, 4.32], [4.374, 4.32]]])      # 0.054 um apart in one row
    assert footprint_conflicts([xs], (4.32, 4.32)) == [('ft0,0,0', 'ft0,0,1')]
    fixed = [('ist:a,0,0', 6.48, 4.32, 1.404, .27)]
    assert footprint_conflicts([GOOD], (4.32, 4.32), fixed=fixed) == [('ist:a,0,0', 'ft0,0,1')]


def test_legalize_spreads_packed_column_onto_rows_and_snap_accepts_it():
    from ft_bit_sites import footprint_conflicts, legalize_slots, snap_slots
    slot = _packed_column()
    with pytest.raises(ValueError, match='snap to one site'):
        snap_slots([slot], (0.0, 0.0))
    out, moves = legalize_slots([slot], (0.0, 0.0), (0.0, 0.0, 200.0, 1200.0))
    assert footprint_conflicts(out, (0.0, 0.0)) == []
    snap_slots(out, (0.0, 0.0))                                            # no collision any more
    rows = sorted(round(y / .27) for _, y in out[0]['bit_sites_um'][0])
    assert len(set(rows)) == 13                                            # one bit per row of the column
    assert len(moves) == 8 and max(m[3] for m in moves) <= 13 * 0.27
    assert slot['bit_sites_um'][0][1] == [30.24, 1083.022]                # input not mutated
    assert out[0]['bit_sites_um'][0][0] == slot['bit_sites_um'][0][0]     # a free site stays exactly as planned


def test_legalize_avoids_blocks_core_edge_and_fixed_sites():
    from ft_bit_sites import footprint_conflicts, legalize_slots
    slot = dict(GOOD, bit_sites_um=[[[4.32, 4.32], [4.32, 4.32]]])
    block = (0.0, 4.59, 100.0, 100.0)                                      # everything above row 4.32 blocked
    fixed = [('ist:a,0,0', 5.724, 4.32, 1.404, .27)]                       # right neighbour taken
    out, moves = legalize_slots([slot], (4.32, 4.32), (4.32, 4.32, 100.0, 100.0), blocks=[block], fixed=fixed)
    (lab, _, to, _), = moves
    assert lab == 'ft0,0,1' and to[1] == 4.32 and to[0] >= 5.724 + 1.404 - 1e-6
    assert footprint_conflicts(out, (4.32, 4.32), fixed=fixed) == []
    with pytest.raises(ValueError, match='no free grid site'):
        legalize_slots([slot], (4.32, 4.32), (4.32, 4.32, 5.9, 4.59))
