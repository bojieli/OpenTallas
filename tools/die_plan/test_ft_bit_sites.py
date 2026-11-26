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


# FT-SITE-SNAP / FT-SITE-OFFCORE (S81-OWN-LEAF 11-24): core_box clamps into CORE_AREA rows and de-collides
BOX = (4.32, 4.32, 100.0, 100.0)


def _slot(sites, w=1):
    return dict(name='ft0', width=w, stations=2, bit_site_cell_um=[1.404, .27], bit_sites_um=[sites])


def test_core_box_keeps_free_inside_sites_identical():
    from ft_bit_sites import snap_slots
    legacy, n0 = snap_slots([GOOD], (4.32, 4.32))
    out, n1 = snap_slots([GOOD], (4.32, 4.32), core_box=BOX)
    assert out == legacy and n0 == n1 == 0


def test_core_box_moves_colliding_bit_to_nearest_free_site():
    from ft_bit_sites import snap_slots
    s = _slot([[77.76, 212.76 - 200], [77.76, 12.77]])        # both snap to one grid point (t41 ft0,2,151 / 221 class)
    with pytest.raises(ValueError, match='snap to one site'):
        snap_slots([s], (4.32, 4.32))
    out, moved = snap_slots([s], (4.32, 4.32), core_box=BOX)
    a, b = out[0]['bit_sites_um'][0]
    assert a == [77.76, 12.69] and b != a
    assert abs(b[0] - a[0]) + abs(b[1] - a[1]) <= 0.27 + 1e-9    # one row away (y is the cheap axis)
    assert moved == 2


def test_core_box_clamps_offcore_margin_sites_onto_core_rows():
    from ft_bit_sites import snap_slots, site_findings
    s = _slot([[62.64, 4.05], [62.64, 3.24]])                   # t40 ft1,1,183 class: below CORE_AREA y0 4.32
    assert site_findings([s], BOX)['offcore'] == 2
    out, moved = snap_slots([s], (4.32, 4.32), core_box=BOX)
    ys = sorted(xy[1] for xy in out[0]['bit_sites_um'][0])
    assert ys[0] == 4.32 and all(y >= 4.32 for y in ys)
    assert site_findings(out, BOX) == dict(offcore=0, collide=0, sample=[])
    x1 = max(xy[0] for xy in out[0]['bit_sites_um'][0])
    assert x1 + 1.404 <= BOX[2]


def test_core_box_clamps_top_right_inside_the_cell_footprint():
    from ft_bit_sites import snap_slots
    s = _slot([[99.9, 99.9], [99.9, 99.6]])
    out, _ = snap_slots([s], (4.32, 4.32), core_box=BOX)
    for x, y in out[0]['bit_sites_um'][0]:
        assert x + 1.404 <= BOX[2] + 1e-6 and y + 0.27 <= BOX[3] + 1e-6


def test_core_box_moved_bits_avoid_blocks_and_refuse_when_full():
    from ft_bit_sites import snap_slots
    s = _slot([[10.8, 10.8], [10.8, 10.8]])
    blk = (0.0, 10.9, 200.0, 200.0)                              # everything above the first row blocked
    out, _ = snap_slots([s], (4.32, 4.32), core_box=BOX, blocks=[blk])
    b = out[0]['bit_sites_um'][0][1]
    assert b[1] + 0.27 <= 10.9 + 1e-6 or b[1] >= 200
    tiny = (4.32, 4.32, 4.32 + 1.404, 4.32 + 0.27)               # one site only
    with pytest.raises(ValueError, match='move the station inward'):
        snap_slots([_slot([[4.32, 4.32], [4.32, 4.32]])], (4.32, 4.32), core_box=tiny)


def test_pre_ftsite_reports_offcore_and_collisions_warn_only(tmp_path):
    import json as _json
    import plan_gate_pre as G
    t = dict(outline_um=[100.0, 100.0], ft_slots=[_slot([[62.64, 4.05], [62.64, 3.24]]),
                                                  dict(_slot([[20.0, 20.0], [20.005, 20.0]]), name='ft1')])
    ok = dict(outline_um=[100.0, 100.0], ft_slots=[GOOD])
    p = tmp_path / 'plan.json'
    p.write_text(_json.dumps({'die': 's81', 'partition_types': {'leaf_bad': t, 'leaf_ok': ok}}))
    out = G.check_ftsite(str(p))
    assert not [x for x in out if x.startswith('FAIL')]
    assert out[0].startswith('WARN FTSITE leaf_bad: 2 explicit FT bit site(s) off CORE_AREA, 1 on an already used grid point')
    assert out[-1].startswith('WARN FTSITE-SUMMARY 1 type(s), 2 off-core and 1 colliding')
    assert 'FTSITE' in G.CLASSES


def test_legalize_repairs_blocked_singletons_before_and_after_snap():
    from ft_bit_sites import legalize_slots, snap_slots

    # Neither site shares grid occupancy with another register.  The first
    # cell hits the moved SRAM at its raw x only, the second only after snap.
    slot = _slot([[10.013, 10.80], [20.001, 13.50]])
    blocks = [(11.402, 10.8, 15.0, 11.07), (19.0, 13.50, 20.0, 13.77)]
    out, moves = legalize_slots([slot], (0.0, 0.0), (0.0, 0.0, 100.0, 100.0), blocks=blocks)
    assert len(moves) == 2
    snapped, _ = snap_slots(out, (0.0, 0.0))
    for sites in (out[0]["bit_sites_um"][0], snapped[0]["bit_sites_um"][0]):
        for x, y in sites:
            assert all(x + 1.404 <= left or right <= x or y + 0.27 <= bottom or top <= y
                       for left, bottom, right, top in blocks)
