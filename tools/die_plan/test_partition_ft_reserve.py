import copy
import json
from pathlib import Path
import pytest
from tools.die_plan import schema, partition_ft_reserve as F


def plan(share=.5, duplicate=False, flip=False):
    raw=json.loads((Path(schema.__file__).parent/'examples/tiny_plan.json').read_text())
    raw['ports']=[];raw['lanes']=[]
    raw['partitions']=raw['partitions'][:1]
    typ=raw['partitions'][0]['type'];t=raw['partition_types'][typ]
    t['hard_cores']=[];t['hard']=False
    t['die_ft_bands']=[dict(dir='EW',span_um=[0,t['outline_um'][1]],layers=['M4'],die_share=share)]
    if duplicate:
        p=copy.deepcopy(raw['partitions'][0]);p['name']='copy';p['origin_um'][0]+=t['outline_um'][0]
        if flip:p['orient']='MX'
        raw['partitions'].append(p)
    return schema.Plan(raw),typ


def inside(rows, x,y):
    return any(r['rect'][0]<x<r['rect'][2] and r['rect'][1]<y<r['rect'][3] for r in rows)


def test_default_is_unchanged_and_half_band_blocks_die_owned_half():
    P,typ=plan();P.types[typ].pop('die_ft_bands')
    assert F.reservation(P,typ) is None and F.tcl(None)==''
    P,typ=plan();r=F.reservation(P,typ)
    assert inside(r['rectangles_um'],20,2)
    assert not inside(r['rectangles_um'],20,8)
    assert 'odb::dbObstruction_create' in F.tcl(r)
    assert r['instances']==['pa']


def test_full_die_band_physically_excludes_partition_route():
    P,typ=plan(1)
    r=F.reservation(P,typ)
    w,h=P.types[typ]['outline_um']
    assert sum((z['rect'][2]-z['rect'][0])*(z['rect'][3]-z['rect'][1]) for z in r['rectangles_um'])==pytest.approx(w*h)


def test_same_canonical_phase_is_shared_but_flipped_phase_fails():
    P,typ=plan(duplicate=True)
    assert len(F.reservation(P,typ)['instances'])==2
    P,typ=plan(duplicate=True,flip=True)
    with pytest.raises(ValueError,match='transformed FT maps differ'):F.reservation(P,typ)


def test_exact_complement_never_double_owns_die_tracks():
    P,typ=plan()
    from tools.die_plan import die_trial as D
    _,regs=D.band_region_adjust(P,.75)
    die_obstacles=[dict(rect=list(r)) for L,*r in D.band_share_obs(P,regs) if L=='M4']
    own=F.reservation(P,typ)['rectangles_um']
    # Explicit witness: a fraction-only/global capacity adjustment has no such
    # pointwise partition/die ownership guarantee.
    for x in (20,50,100):
        for y in (2,8,12,18,23,29):
            assert inside(own,x,y)==(not inside(die_obstacles,x,y))


def test_clock_pg_layers_cannot_be_admitted_as_ft_signal_share():
    P,typ=plan();P.types[typ]['die_ft_bands'][0]['layers']=['M8']
    with pytest.raises(ValueError,match='lower signal'):F.reservation(P,typ)


def test_other_placed_type_layer_default_is_reserved_in_this_opted_in_type():
    P,typ=plan()
    other=copy.deepcopy(P.raw['partitions'][0]);other.update(name='other',type='other')
    other['origin_um']=[P.types[typ]['outline_um'][0],0]
    P.raw['partitions'].append(other)
    P.raw['partition_types']['other']=copy.deepcopy(P.types[typ])
    P.raw['partition_types']['other']['module']='other_module'
    P.raw['partition_types']['other']['die_ft_bands']=[dict(
        dir='NS',span_um=[0,P.types[typ]['outline_um'][0]],layers=['M7'],die_share=.5)]
    P=schema.Plan(P.raw)
    r=F.reservation(P,typ)
    assert {row['layer'] for row in r['rectangles_um']}=={'M4','M7'}
    own=[row for row in r['rectangles_um'] if row['layer']=='M7']
    # The M7 band is in the neighbour; this type still owes the die its
    # default quarter of each global gcell on M7.
    assert inside(own,2,20)
    assert not inside(own,8,20)
    from tools.die_plan import die_trial as D
    _,regs=D.band_region_adjust(P,.75)
    blocked=[dict(rect=list(rect)) for layer,*rect in D.band_share_obs(P,regs) if layer=='M7']
    for x in (2,8,12,18,23,29):
        for y in (20,50,100):
            assert inside(own,x,y)==(not inside(blocked,x,y))


def test_unplaced_type_band_does_not_add_an_unreal_global_layer():
    P,typ=plan()
    P.raw['partition_types']['unplaced']=copy.deepcopy(P.types[typ])
    P.raw['partition_types']['unplaced']['die_ft_bands'][0]['layers']=['M7']
    P=schema.Plan(P.raw)
    assert {row['layer'] for row in F.reservation(P,typ)['rectangles_um']}=={'M4'}


def test_no_band_type_remains_unchanged_even_with_global_bands():
    P,typ=plan()
    other=copy.deepcopy(P.types[typ]);other.pop('die_ft_bands')
    P.types['no_bands']=other
    assert F.reservation(P,'no_bands') is None


def test_row_bridge_only_when_m4_band_spans_width():
    """DIE-HBM-90 11-07 (q_spu0/q_spu1 PDN-0179): a full-width M4 reservation band leaves the rows under it with no
    M2->M5 via; the PDN then gets M3 + M4 bridge straps. Without such a band nothing changes."""
    P,typ=plan();w,h=P.types[typ]['outline_um'];r=F.reservation(P,typ)
    assert F.blocks_rows(r,w)
    t=F.row_bridge_tcl(r,w)
    for line in ('-layer {M3} -width {0.09}','-layer {M4} -width {0.12}','-layers {M2 M3}','-layers {M3 M4}','-layers {M4 M5}'):
        assert line in t
    assert F.row_bridge_tcl(None,w)=='' and not F.blocks_rows(None,w)
    part={'type':typ,'rectangles_um':[dict(layer='M4',rect=[0,0,w/2,1]),dict(layer='M5',rect=[0,0,w,1])]}
    assert not F.blocks_rows(part,w) and F.row_bridge_tcl(part,w)==''


def _street_receipt():
    # q_b013 geometry (DIE-HBM-91 11-08): full-width M4 street band 103.68 um tall, full-width M6 block over it,
    # a thin q_spu0-like 2.7-um M4 band and a partial M5 strip.
    return {'rectangles_um': [dict(layer='M4', rect=[0.0, 1028.16, 552.96, 1131.84]),
                              dict(layer='M6', rect=[0.0, 943.92, 552.96, 2912.22]),
                              dict(layer='M4', rect=[0.0, 4.32, 552.96, 7.02]),
                              dict(layer='M5', rect=[25.38, 1028.16, 28.08, 1131.84])]}


def test_tall_full_width_pdn_band_keeps_strap_windows_on_the_stripe_grid():
    r = _street_receipt()
    w = F.pdn_windows(r, 552.96)
    m4 = [x for x in w if x[0] == 'M4']; m6 = [x for x in w if x[0] == 'M6']
    assert m4 and m6
    for L, lo, hi in w:
        off, wd, sp, pitch = F.PDN_WIN_STRIPES[L]
        s = lo + F.PDN_WIN_MARGIN
        assert ((s - 4.32 - off) / pitch) == pytest.approx(round((s - 4.32 - off) / pitch), abs=1e-6)
        assert hi - lo == pytest.approx(2 * wd + sp + 2 * F.PDN_WIN_MARGIN)
    assert all(1028.16 + 4.32 <= lo and hi <= 1131.84 - 4.32 for _, lo, hi in m4)
    assert len(m4) == 4 and len(m6) == 91


def test_obstructions_cover_receipt_minus_windows_and_thin_bands_unchanged():
    r = _street_receipt()
    rows = F.obstruction_rows(r, 552.96)
    area = lambda q: (q[2] - q[0]) * (q[3] - q[1])
    win = sum((hi - lo) * 552.96 for _, lo, hi in F.pdn_windows(r, 552.96))
    assert sum(area(q) for _, q in rows) == pytest.approx(sum(area(x['rect']) for x in r['rectangles_um']) - win)
    assert ('M4', [0.0, 4.32, 552.96, 7.02]) in rows and ('M5', [25.38, 1028.16, 28.08, 1131.84]) in rows
    thin = {'rectangles_um': [dict(layer='M4', rect=[0.0, 4.32, 552.96, 7.02])]}
    assert F.pdn_windows(thin, 552.96) == [] and 'pdn_windows' not in F.tcl(thin)
    assert 'pdn_windows=95' in F.tcl(r)



def _wide_m7_receipt():
    # q_su21 geometry (DIE-HBM-92-SU 11-08): a 251.1-um M7 block over the left SU lane1 macro column, a thin
    # 2.7-um M7 band and an M6 band.
    return {'rectangles_um': [dict(layer='M7', rect=[0.0, 4.32, 251.1, 1555.2]),
                              dict(layer='M7', rect=[10.8, 0.0, 13.5, 4.32]),
                              dict(layer='M6', rect=[0.0, 1019.52, 1892.16, 1022.22])]}


def test_wide_m7_band_keeps_every_second_strap_from_the_band_edge():
    r = _wide_m7_receipt()
    w = F.pdn_windows_v(r)
    off, wd, sp, pitch = F.PDN_WIN_STRIPES_V['M7']
    starts = [lo + F.PDN_WIN_MARGIN for _, lo, _, _ in w]
    for s in starts:
        assert ((s - 4.32 - off) / pitch) == pytest.approx(round((s - 4.32 - off) / pitch), abs=1e-6)
    assert starts[0] == pytest.approx(4.32 + off)                 # first strap inside the band: the edge channel
    assert all(b - a == pytest.approx(F.PDN_WIN_EVERY_V * pitch) for a, b in zip(starts, starts[1:]))
    assert all(x[3] == (0.0, 4.32, 251.1, 1555.2) for x in w) and len(w) == 14


def test_wide_m7_obstructions_cover_receipt_minus_windows():
    r = _wide_m7_receipt()
    rows = F.obstruction_rows(r, 1892.16)
    area = lambda q: (q[2] - q[0]) * (q[3] - q[1])
    win = sum((hi - lo) * (1555.2 - 4.32) for _, lo, hi, _ in F.pdn_windows_v(r))
    assert sum(area(q) for _, q in rows) == pytest.approx(sum(area(x['rect']) for x in r['rectangles_um']) - win)
    assert ('M7', [10.8, 0.0, 13.5, 4.32]) in rows and ('M6', [0.0, 1019.52, 1892.16, 1022.22]) in rows
    assert F.pdn_windows_v({'rectangles_um': [dict(layer='M7', rect=[0.0, 0.0, 8.0, 100.0])]}) == []



def _stacked_m6_receipt():
    # q_su30__physical_v1 (DIE-HBM-92-SU 11-08): a tall M6 block given as abutting 8.1 / 2.7 um rows that end
    # alternately at x 2062.8 and 2064.96 (outline 2064.96).
    rows, y, k = [], 1429.92, 0
    while y < 1555.2 - 1e-6:
        h = 2.7 if k % 2 == 0 else 8.1
        y1 = min(1555.2, round(y + h, 3))
        rows.append(dict(layer='M6', rect=[0.0, y, 2064.96 if k % 2 == 0 else 2062.8, y1]))
        y, k = y1, k + 1
    return {'rectangles_um': rows}


def test_stacked_rows_merge_into_one_tall_band_with_windows():
    r = _stacked_m6_receipt()
    w = F.pdn_windows(r, 2064.96)
    assert w and all(L == 'M6' for L, _, _ in w)
    assert all(1429.92 + 4.32 <= lo and hi <= 1555.2 - 4.32 for _, lo, hi in w)
    rows = F.obstruction_rows(r, 2064.96)
    area = lambda q: (q[2] - q[0]) * (q[3] - q[1])
    for _, lo, hi in w:            # no obstruction left inside a window
        assert not any(q[1] < hi - 1e-9 and q[3] > lo + 1e-9 for _, q in rows)
    lost = sum(area(x['rect']) for x in r['rectangles_um']) - sum(area(q) for _, q in rows)
    assert 0 < lost <= sum((hi - lo) * 2064.96 for _, lo, hi in w) + 1e-6
