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
    starts = [lo + F.PDN_WIN_MARGIN + F._pair_shift(wd) for _, lo, _, _ in w]    # first strap centre on the stripe grid
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


def _comb_receipt():
    # q_b002 pocket: columns 2.7 wide under the tooth row, tooth 47.25-54.0 x 2607.12-2617.92, gap strap at x 49.584
    return {'rectangles_um': [dict(layer='M5', rect=[51.3, 2514.24, 54.0, 2607.12]),
                              dict(layer='M5', rect=[47.25, 2607.12, 54.0, 2617.92])]}


def test_comb_tooth_keeps_window_at_gap_strap_only():
    r = _comb_receipt()
    w = F.pdn_windows_comb(r)
    assert [(L, a, b) for L, a, b, _ in w] == [('M5', 49.434, 50.046)]   # strap 53.904 is on the column
    rows = F.obstruction_rows(r, 380.16)
    assert ('M5', [47.25, 2607.12, 49.434, 2617.92]) in rows and ('M5', [50.046, 2607.12, 54.0, 2617.92]) in rows


def test_short_tooth_unchanged():
    r = {'rectangles_um': [dict(layer='M5', rect=[47.25, 2607.12, 54.0, 2615.76])]}   # 8.64 tall
    assert F.pdn_windows_comb(r) == []
    assert F.obstruction_rows(r, 380.16) == [('M5', [47.25, 2607.12, 54.0, 2615.76])]


def test_tall_column_never_windowed():
    r = {'rectangles_um': [dict(layer='M5', rect=[18.9, 0.0, 21.6, 2903.04])]}
    assert F.pdn_windows_comb(r) == []



def _gap_receipt(own_rows=True):
    """q_b011 shape: 6.048-um M5 column between two macros with its own M4 rows, closed by M5 street rows on both ends,
    plus a plain 2.7-um FT column with no own rows."""
    R = [dict(layer='M5', rect=[123.552, 2989.44, 129.6, 3276.72]),
         dict(layer='M5', rect=[124.74, 3276.72, 129.6, 3279.744]),
         dict(layer='M5', rect=[124.74, 3279.744, 246.24, 3287.52]),
         dict(layer='M5', rect=[124.74, 2978.208, 246.24, 2985.12]),
         dict(layer='M5', rect=[120.69, 2985.12, 246.24, 2989.44]),
         dict(layer='M5', rect=[5.94, 0.0, 8.64, 4320.0])]
    if own_rows:
        R += [dict(layer='M4', rect=[123.552, 3000.0 + 10.8 * k, 129.6, 3002.7 + 10.8 * k]) for k in range(5)]
    return dict(rectangles_um=R)


def test_gap_column_gets_m5_window_through_end_rows_and_m6_fill():
    r = _gap_receipt()
    w = F.pdn_windows_col(r)
    assert {(a, b) for _, a, b, _ in w} == {(127.194, 127.806)}
    hit = {rr for _, _, _, rr in w}
    assert (123.552, 2989.44, 129.6, 3276.72) in hit and (124.74, 3279.744, 246.24, 3287.52) in hit
    assert (120.69, 2985.12, 246.24, 2989.44) in hit and (5.94, 0.0, 8.64, 4320.0) not in hit
    assert F.pdn_col_fill(r) == [('M6', [123.552, 2989.44, 129.6, 3276.72])]
    rows = F.obstruction_rows(r)
    assert ('M6', [123.552, 2989.44, 129.6, 3276.72]) in rows
    assert not any(L == 'M5' and q[0] < 127.5 < q[2] and q[1] < 3100 < q[3] for L, q in rows)
    assert any(L == 'M5' and q == [123.552, 2989.44, 127.194, 3276.72] for L, q in rows)
    assert all(q[2] > q[0] for _, q in rows)
    assert 'pdn_windows_col=5 col_fill_m6=1' in F.tcl(r)


def _edge_receipt():
    """q_su20 a7 shape: 2004.48-um outline (full-width M4 row), the die M5 column 1995.84-2002.32 beside macro p0 crossing
    the core edge 2000.16 with its own 8.64-um M4 rows to the outline, plus the same column moved inside the core."""
    R = [dict(layer='M4', rect=[0.0, 220.32, 2004.48, 223.02])]
    for x0, x1, rx1 in ((1995.84, 2002.32, 2004.48), (1000.08, 1006.56, 1008.72)):
        R.append(dict(layer='M5', rect=[x0, 233.28, x1, 544.32]))
        R += [dict(layer='M4', rect=[x0, 241.92 + 10.8 * k, rx1, 244.62 + 10.8 * k]) for k in range(28)]
    return dict(rectangles_um=R)


def test_outline_edge_column_is_not_a_macro_gap():
    # DIE-HBM-97/SUPDN: an edge column window turned the core-edge pocket into 141 serial pdngen repair rounds (50 GB OOM)
    r = _edge_receipt()
    hit = {rr for _, _, _, rr in F.pdn_windows_col(r)}
    assert (1995.84, 233.28, 2002.32, 544.32) not in hit                # edge column: no window, no M6 fill
    assert (1000.08, 233.28, 1006.56, 544.32) in hit                    # interior column: unchanged rule
    assert F.pdn_col_fill(r) == [('M6', [1000.08, 233.28, 1006.56, 544.32])]
    rows = F.obstruction_rows(r)
    assert ('M5', [1995.84, 233.28, 2002.32, 544.32]) in rows           # edge column stays whole
    left = dict(rectangles_um=[dict(layer=x['layer'], rect=[2004.48 - x['rect'][2], x['rect'][1],
                                                              2004.48 - x['rect'][0], x['rect'][3]])
                               for x in r['rectangles_um']])            # mirrored: left outline edge
    assert (2.16, 233.28, 8.64, 544.32) not in {rr for _, _, _, rr in F.pdn_windows_col(left)}


def test_plain_columns_without_own_rows_unchanged():
    r = _gap_receipt(own_rows=False)
    assert F.pdn_windows_col(r) == [] and F.pdn_col_fill(r) == []
    assert F.obstruction_rows(r) == [(x['layer'], x['rect']) for x in r['rectangles_um']]
    assert 'pdn_windows_col' not in F.tcl(r)


def test_tall_macro_bounded_band_is_windowed():
    # q_b100__physical_v1: M6 band 0-259.2 x 423-527 of a 734.4 outline (bounded by macros, not full width)
    r = {'rectangles_um': [dict(layer='M6', rect=[0.0, 423.0, 259.2, 527.0])]}
    w = F.pdn_windows(r, 734.4)
    assert w and all(L == 'M6' and 423.0 + 4.32 <= a and b <= 527.0 - 4.32 for L, a, b in w)
    thin = {'rectangles_um': [dict(layer='M6', rect=[0.0, 423.0, 259.2, 430.0])]}      # not tall: unchanged
    assert F.pdn_windows(thin, 734.4) == []
    narrow = {'rectangles_um': [dict(layer='M6', rect=[0.0, 423.0, 60.0, 527.0])]}     # < PDN_WIN_PARTIAL_MIN_UM
    assert F.pdn_windows(narrow, 734.4) == []


def _strip_receipt():
    """q_b101_nw y 298.9-311.0: a strip of three stacked wide M4 rows under partial-width M6 rows, M5 teeth inside it and
    one M5 column piece entering it from below."""
    R = [dict(layer='M4', rect=[2.16, 298.944, 492.48, 306.72]),
         dict(layer='M4', rect=[0.0, 306.72, 492.48, 309.42]),
         dict(layer='M4', rect=[2.16, 309.42, 492.48, 311.04]),
         dict(layer='M6', rect=[2.16, 290.0, 492.48, 306.72]),
         dict(layer='M6', rect=[0.0, 306.72, 492.48, 309.42]),
         dict(layer='M6', rect=[2.16, 309.42, 492.48, 328.32]),
         dict(layer='M5', rect=[347.76, 298.944, 350.46, 306.72]),
         dict(layer='M5', rect=[358.56, 295.92, 361.26, 306.72]),
         dict(layer='M5', rect=[358.56, 306.72, 365.31, 311.04]),
         dict(layer='M5', rect=[358.56, 8.64, 362.88, 295.92])]
    return dict(rectangles_um=R)


def test_stacked_m4_strip_gets_one_m6_window_and_m5_windows():
    r = _strip_receipt()
    st = []
    assert F.pdn_windows_strip(r, 734.4, strips=st) == [('M6', 299.898, 300.87)]
    assert st == [(0.0, 298.944, 492.48, 311.04)]                  # the three rows merged into one strip
    m5 = F.pdn_windows_strip_m5(r, 734.4)
    hit = {rr for *_, rr in m5}
    assert (358.56, 295.92, 361.26, 306.72) in hit                 # mostly inside the strip
    assert (358.56, 306.72, 365.31, 311.04) in hit and (347.76, 298.944, 350.46, 306.72) in hit
    assert (358.56, 8.64, 362.88, 295.92) not in hit               # the column below is untouched
    assert ('M5', 360.474, 361.086, (358.56, 295.92, 361.26, 306.72)) in m5
    rows = F.obstruction_rows(r, 734.4)
    assert ('M5', [358.56, 8.64, 362.88, 295.92]) in rows
    m6 = [q for L, q in rows if L == 'M6']
    assert not any(q[1] < 300.87 - 1e-9 and q[3] > 299.898 + 1e-9 for q in m6)       # the partial M6 row is cut
    assert all(q[2] > q[0] and q[3] > q[1] for _, q in rows)


def test_strip_not_under_m6_unchanged():
    r = {'rectangles_um': [dict(layer='M4', rect=[2.16, 298.944, 492.48, 306.72]),
                           dict(layer='M5', rect=[347.76, 298.944, 350.46, 306.72])]}
    assert F.pdn_windows_strip(r, 734.4) == [] and F.pdn_windows_strip_m5(r, 734.4) == []
    assert F.obstruction_rows(r, 734.4) == [(x['layer'], x['rect']) for x in r['rectangles_um']]


def test_isolated_m6_stack_without_m4_gets_strip_window():
    # q_b102__physical_v1 core bottom: two abutting wide M6 rows, no M4 under them
    r = {'rectangles_um': [dict(layer='M6', rect=[0.0, 4.32, 466.56, 7.02]),
                           dict(layer='M6', rect=[19.44, 7.02, 246.24, 11.07])]}
    assert F.pdn_windows_strip(r, 708.48) == [('M6', 6.138, 7.11)]


def test_m6_stack_part_of_taller_stack_gets_no_strip_window():
    r = {'rectangles_um': [dict(layer='M6', rect=[0.0, 4.32, 466.56, 7.02]),
                           dict(layer='M6', rect=[0.0, 7.02, 466.56, 11.07]),
                           dict(layer='M6', rect=[0.0, 11.07, 466.56, 30.0])]}
    assert F.pdn_windows_strip(r, 708.48) == []


def test_column_with_slightly_wider_own_rows_gets_windows():
    R = [dict(layer='M5', rect=[574.29, 0.0, 578.88, 290.304])]
    R += [dict(layer='M4', rect=[572.832, y, 578.88, y + 2.7]) for y in (58.32, 69.12, 79.92)]
    assert [w[:3] for w in F.pdn_windows_col({'rectangles_um': R})] == [('M5', 576.474, 577.086)]
    R2 = [dict(layer='M5', rect=[5.94, 0.0, 8.64, 290.304])]       # street rows, 3.2x the column width
    R2 += [dict(layer='M4', rect=[0.0, y, 8.64, y + 2.7]) for y in (58.32, 69.12, 79.92)]
    assert F.pdn_windows_col({'rectangles_um': R2}) == []


def test_sliver_close_tcl_emitted():
    r = {'rectangles_um': [dict(layer='M6', rect=[572.832, 58.32, 578.88, 65.07])]}
    t = F.tcl(r)
    assert 'm6_sliver_close' in t and 'round(0.384*$ot_ft_dbu)' in t
    assert t.index('dbObstruction_create $ot_ft_blk $ot_ft_layer') < t.index('m6_sliver_close')


def test_m4_m6_reservations_are_disjoint_rows_and_exact_complements():
    """DIE-HBM-97 11-09: a band on both H layers reserves M4 and M6 in different parts of each gcell row (no row of
    the partition loses both), each layer still the exact complement of the die obstructions."""
    P,typ=plan()
    P.types[typ]['die_ft_bands'][0]['layers']=['M4','M6']
    P=schema.Plan(P.raw)
    from tools.die_plan import die_trial as D
    _,regs=D.band_region_adjust(P,.75)
    rows=F.reservation(P,typ)['rectangles_um']
    own={L:[r for r in rows if r['layer']==L] for L in ('M4','M6')}
    blocked={L:[dict(rect=list(rect)) for layer,*rect in D.band_share_obs(P,regs) if layer==L] for L in ('M4','M6')}
    ys=[i*0.27+0.135 for i in range(80)]
    for L in ('M4','M6'):
        for x in (20,50,100):
            for y in ys:
                assert inside(own[L],x,y)==(not inside(blocked[L],x,y))
    for x in (20,50,100):
        assert not any(inside(own['M4'],x,y) and inside(own['M6'],x,y) for y in ys)
    a4=sum((r['rect'][2]-r['rect'][0])*(r['rect'][3]-r['rect'][1]) for r in own['M4'])
    a6=sum((r['rect'][2]-r['rect'][0])*(r['rect'][3]-r['rect'][1]) for r in own['M6'])
    assert a4==pytest.approx(a6)


# Mock odb for SLIVER_TCL: blocks + obstructions in um (dbu 1000), returns the M6 fills it creates.
_MOCK_ODB = r'''
namespace eval ord {}; namespace eval odb {}
set ::made {}
proc ord::get_db_tech {} { return mtech }
proc mtech {m L} { return L_$L }
proc mbox {kind x0 y0 x1 y1 {L {}}} {
  set n box[incr ::nbox]
  proc $n {m} "switch \$m {xMin {return $x0} yMin {return $y0} xMax {return $x1} yMax {return $y1} getTechLayer {return {$L}}}"
  return $n
}
proc mwrap {bb} { set n w[incr ::nbox]; proc $n {m} "if {\$m eq {getBBox}} {return $bb}; if {\$m eq {getMaster}} {return mmaster}"; return $n }
proc mmaster {m} { return 1 }
proc odb::dbObstruction_create {blk L x0 y0 x1 y1} { lappend ::made [list $L $x0 $y0 $x1 $y1] }
proc mblk {m} { if {$m eq {getInsts}} { return $::insts }; if {$m eq {getCoreArea}} { return $::core }; return $::obss }
set ot_ft_blk mblk; set ot_ft_dbu 1000
set ::insts {}; set ::obss {}; set ::core [mbox c 4320 4320 829440 4315680]
proc um {v} { return [expr {round($v*1000)}] }
foreach b $::B { lassign $b x0 y0 x1 y1; lappend ::insts [mwrap [mbox i [um $x0] [um $y0] [um $x1] [um $y1]]] }
foreach o $::O { lassign $o L x0 y0 x1 y1; lappend ::obss [mwrap [mbox o [um $x0] [um $y0] [um $x1] [um $y1] L_$L]] }
'''


def _sliver_fills(blocks, obs):
    import shutil, subprocess
    if not shutil.which('tclsh'):
        pytest.skip('tclsh not installed')
    tl = lambda rows: '{' + ' '.join('{' + ' '.join(str(v) for v in r) + '}' for r in rows) + '}'
    src = f'set ::B {tl(blocks)}\nset ::O {tl(obs)}\n' + _MOCK_ODB + F.sliver_tcl() + \
        '\nforeach m $::made { puts "FILL [lindex $m 0] [lrange $m 1 end]" }\n'
    out = subprocess.run(['tclsh'], input=src, capture_output=True, text=True, check=True).stdout
    fills = sorted(tuple(round(int(v) / 1000, 3) for v in l.split()[2:]) for l in out.splitlines() if l.startswith('FILL L_M6'))
    return fills, out


def test_m6_gap_to_macro_under_reserved_m7_is_closed():
    """DIE-HBM-97 11-09 q_b010 x 127.44-129.6: M6 rows of a macro-gap column end 2.16 um short of the macro, M7 reserved
    over the gap -> the M6 strap piece there has no M7 landing (PDN-0178/0179).  Without M7 above, the gap is kept."""
    blk = [(129.6, 2989.44, 235.872, 3279.744)]
    row = ('M6', 123.552, 3259.17, 127.44, 3263.22)
    fills, out = _sliver_fills(blk, [row, ('M7', 127.44, 0.0, 130.14, 4320.0)])
    assert fills == [(127.44, 3259.17, 129.6, 3263.22)] and 'm6_no_m7_close=1' in out
    fills, out = _sliver_fills(blk, [row, ('M7', 127.44, 0.0, 128.5, 4320.0)])      # M7 free over part of the gap
    assert fills == [] and 'm6_sliver_close=0' in out


def test_m6_hole_between_rows_under_reserved_m7_is_closed():
    """DIE-HBM-97 11-09 q_b010 x 591.84-602.64 y 2913.57-2917.62: a hole between two M6 FT rows under M7 reserved by two
    abutting-or-overlapping M7 rects (588.006-604.314) -> closed; with an M7 strap window over the hole -> kept."""
    rows = [('M6', 483.84, 2913.57, 591.84, 2917.62), ('M6', 602.64, 2913.57, 710.64, 2917.62)]
    m7 = [('M7', 588.006, 4.32, 596.0, 4320.0), ('M7', 596.0, 4.32, 604.314, 4320.0)]
    fills, out = _sliver_fills([], rows + m7)
    assert fills == [(591.84, 2913.57, 602.64, 2917.62)] and 'm6_no_m7_close=1' in out
    win = [('M7', 588.006, 4.32, 595.0, 4320.0), ('M7', 596.0, 4.32, 604.314, 4320.0)]   # window 595-596
    assert _sliver_fills([], rows + win)[0] == []


def test_m6_pocket_between_macros_with_half_landing_pair_is_closed():
    """DIE-HBM-97 11-09 q_b010__physical_v1 (VSS channel x 466.6-477.3): macro h1 ends 469.152, macro u_ra starts 483.84,
    M7 reserved 467.046-483.354 with a strap window 483.354-484.326 that lands only the first strap of the pair inside
    the pocket (the second is over u_ra) and is narrower than a pair -> closed.  With M7 free (repairable) -> kept."""
    blk = [(250.56, 3135.936, 469.152, 3323.424), (483.84, 2920.32, 590.112, 3210.624)]
    m7 = [('M7', 449.766, 4.32, 466.074, 4320.0), ('M7', 467.046, 4.32, 483.354, 4320.0),
          ('M7', 484.326, 4.32, 498.96, 4320.0)]
    fills, out = _sliver_fills(blk, m7)
    assert fills == [(469.152, 3135.936, 483.84, 3210.624)] and 'm6_no_m7_close=1' in out
    assert _sliver_fills(blk, [])[0] == []


def test_m6_gap_where_both_nets_land_is_kept():
    blk = [(129.6, 2989.44, 235.872, 3279.744)]
    fills, out = _sliver_fills(blk, [('M6', 100.0, 3259.17, 110.0, 3263.22), ('M7', 100.0, 0.0, 120.0, 4320.0)])
    assert fills == [] and 'm6_sliver_close=0' in out          # pair at 120.768 lands clear of the M7 rect


def test_m6_sliver_at_macro_edge_still_closed_without_m7():
    fills, out = _sliver_fills([(579.012, 0.0, 700.0, 300.0)], [('M6', 572.832, 58.32, 578.88, 65.07)])
    assert fills == [(578.88, 58.32, 579.012, 65.07)] and 'm6_no_m7_close=0' in out


def _pocket_receipt(x0=0.0, x1=25.92, width=786.24, own=4, m6=True):
    rows=[dict(layer='M4',rect=[0.0,4.32,width,7.02])]
    y=25.92
    for _ in range(own):
        rows.append(dict(layer='M4',rect=[x0,y,x1,y+2.7]));y+=10.8
    rows.append(dict(layer='M5',rect=[x0,17.28,x1,285.12]))
    if m6:rows.append(dict(layer='M6',rect=[x0,23.22,x1,25.92]))
    return dict(rectangles_um=rows)


def test_wide_edge_pocket_keeps_one_middle_m5_window():
    # q_b001__physical_v1 a11: the outline-to-macro strip, M5 reserved whole, M4 rows of its own x extent
    r=_pocket_receipt()
    assert F.pdn_windows_edge_pocket(r)==[('M5',14.874,15.486,(0.0,17.28,25.92,285.12))]
    m5=sorted(q for L,q in F.obstruction_rows(r) if L=='M5')
    assert m5==[[0.0,17.28,14.874,285.12],[15.486,17.28,25.92,285.12]]
    assert 'pdn_windows_edge_pocket=1' in F.tcl(r)


def test_east_edge_pocket_window_stays_in_core():
    w=829.44
    r=_pocket_receipt(806.112,w,w)
    wins=F.pdn_windows_edge_pocket(r)
    assert len(wins)==1 and wins[0][2]<=w-F.PDN_CORE_INSET


def test_edge_pocket_rule_leaves_other_columns_whole():
    interior=_pocket_receipt(469.152,483.84)                      # between macros, not at the outline
    no_rows=_pocket_receipt(own=1)                                # street, no own M4 rows
    too_wide=_pocket_receipt(0.0,138.24)                          # not a measured failing form
    narrow=_pocket_receipt(0.0,6.48)                              # the 4.32-um core margin: edge-column rule
    for r in (interior,no_rows,too_wide,narrow):
        assert F.pdn_windows_edge_pocket(r)==[]
    assert 'pdn_windows_edge_pocket' not in F.tcl(interior)


def _macro_street_receipt(rows):
    return dict(rectangles_um=[dict(layer='M4', rect=list(r)) for r in rows])


STREET_BOXES = [(25.92, 1105.92, 276.48, 1373.76), (25.92, 1382.4, 276.48, 1650.24)]


def test_street_window_lands_on_m4_strap_inside_one_row():
    r = _macro_street_receipt([(0, 1373.76, 453.6, 1375.92), (0, 1375.92, 457.92, 1378.62), (0, 1378.62, 453.6, 1382.4)])
    assert F.pdn_windows_street(r, boxes=STREET_BOXES) == [('M4', 1380.09, 1380.702)]
    rows = [q for L, q in F.obstruction_rows(r, 457.92, macro_boxes=STREET_BOXES) if L == 'M4']
    assert [0, 1378.62, 453.6, 1380.09] in rows and [0, 1380.702, 453.6, 1382.4] in rows


def test_no_street_window_without_macros_or_when_m4_open_or_already_cut():
    full = _macro_street_receipt([(0, 1373.76, 457.92, 1382.4)])
    assert F.pdn_windows_street(full) == [] and F.pdn_windows_street(None, boxes=STREET_BOXES) == []
    assert F.obstruction_rows(full, 457.92) == [('M4', [0, 1373.76, 457.92, 1382.4])]
    opened = _macro_street_receipt([(0, 1373.76, 457.92, 1376.0), (0, 1379.0, 457.92, 1382.4)])
    assert F.pdn_windows_street(opened, boxes=STREET_BOXES) == []
    assert F.pdn_windows_street(full, boxes=STREET_BOXES, existing=[('M4', 1376.0, 1376.6)]) == []


def test_tcl_unchanged_without_macro_boxes_and_counts_street_windows():
    full = _macro_street_receipt([(0, 1373.76, 457.92, 1382.4)])
    assert 'pdn_windows_street' not in F.tcl(full)
    assert 'pdn_windows_street=1' in F.tcl(full, STREET_BOXES)


# q_b102 street 445.824-449.28 between hcol macros k2h0 and k2h1: M6 over the lower 1.296 um, M4 over the rest, M5 teeth
# over the upper part, and a full-width M4 band elsewhere (row bridge on).
M5_STREET_BOXES = [(241.92, 155.52, 460.512, 445.824), (241.92, 449.28, 460.512, 636.768)]


def _m5_street_receipt(teeth=True, m6=True):
    rows = [('M4', [235.872, 447.12, 466.56, 449.28]), ('M4', [0, 1000.0, 708.48, 1002.16])]
    if m6:
        rows.append(('M6', [235.872, 445.824, 708.48, 447.12]))
    if teeth:
        rows.append(('M5', [239.76, 447.12, 460.512, 449.28]))
    return dict(rectangles_um=[dict(layer=L, rect=r) for L, r in rows])


def test_m5_island_in_street_gets_one_m6_window():
    r = _m5_street_receipt()
    assert F.pdn_windows_street(r, boxes=M5_STREET_BOXES) == [('M6', 446.778, 447.75)]
    rows = [q for L, q in F.obstruction_rows(r, 708.48, macro_boxes=M5_STREET_BOXES) if L == 'M6']
    assert rows == [[235.872, 445.824, 708.48, 446.778]]
    assert 'pdn_windows_street=1' in F.tcl(r, M5_STREET_BOXES)


def test_m5_street_without_island_gets_no_m6_window():
    # M5 pieces reach the free M6 strap above the reserved row, or M6 is not reserved in the street at all
    for r in (_m5_street_receipt(teeth=False), _m5_street_receipt(m6=False)):
        assert [w for w in F.pdn_windows_street(r, boxes=M5_STREET_BOXES) if w[0] == 'M6'] == []
    r = _m5_street_receipt()
    assert F.pdn_windows_street(r, boxes=M5_STREET_BOXES, existing=[('M6', 446.778, 447.75)]) == []
    assert 'pdn_windows_street' not in F.tcl(r)


# q_b002 a10 (plan p11t_taps_cyc): M5 reserved everywhere except over the hard cores -> M5 strap windows on one global
# every-4th-strap grid, aligned through stacked rects; types with free M5 outside the cores are unchanged.
M5_FULL_BOXES = [(17.28, 20.0, 51.84, 80.0)]


def _m5_full_receipt(right=True):
    rows = [('M5', [0, 0, 60.0, 20.0]), ('M5', [0, 20.0, 17.28, 80.0]), ('M5', [0, 80.0, 60.0, 100.0])]
    if right:
        rows.append(('M5', [51.84, 20.0, 60.0, 80.0]))
    return dict(rectangles_um=[dict(layer=L, rect=r) for L, r in rows])


def test_m5_wholly_reserved_gets_aligned_strap_windows():
    r = _m5_full_receipt()
    wins = F.pdn_windows_m5_full(r, boxes=M5_FULL_BOXES)
    assert sorted({(a, b) for _, a, b, _ in wins}) == [(6.234, 6.846), (14.874, 15.486), (23.514, 24.126), (40.794, 41.406),
                                                     (53.754, 54.366)]   # grid k%4 + the strap clear of each core edge
    assert sorted((rr, a) for _, a, _, rr in wins if a == 6.234) == [((0, 0, 60.0, 20.0), 6.234), ((0, 20.0, 17.28, 80.0), 6.234),
                                                                    ((0, 80.0, 60.0, 100.0), 6.234)]
    assert not any(rr == (51.84, 20.0, 60.0, 80.0) for _, _, _, rr in wins)        # no wider than PDN_WIN_MIN
    rows = [q for L, q in F.obstruction_rows(r, 60.0, macro_boxes=M5_FULL_BOXES) if L == 'M5']
    assert [0, 20.0, 6.234, 80.0] in rows and [6.846, 20.0, 14.874, 80.0] in rows and [15.486, 20.0, 17.28, 80.0] in rows
    assert 'pdn_windows_m5_full=12' in F.tcl(r, M5_FULL_BOXES)


def test_m5_with_free_area_or_without_boxes_is_unchanged():
    free = _m5_full_receipt(right=False)
    assert F.pdn_windows_m5_full(free, boxes=M5_FULL_BOXES) == []
    assert F.pdn_windows_m5_full(_m5_full_receipt()) == []
    assert 'pdn_windows_m5_full' not in F.tcl(_m5_full_receipt())
    assert F.tcl(free, M5_FULL_BOXES) == F.tcl(free)


# DIE-HBM-PDN-1 11-11 (q_b011__physical_v1 PDN-0179): M5 reserved over a whole strip beside the hard cores while the type keeps
# free M5 elsewhere.  The strip's M4 gaps (FT rows leave 2.7 um every 10.8) get M4 bridge straps with no M5 above them.
STARVED_BOXES = [(25.92, 17.28, 276.48, 285.12)]


def _starved_receipt(strip_top=285.12, gap=True):
    rows = [('M5', [276.48, 17.28, 380.16, strip_top]), ('M5', [0, 300.0, 100.0, 400.0]), ('M4', [0, 300.0, 100.0, 400.0])]
    y = 17.28
    while y + 8.1 <= strip_top + 1e-9:
        rows.append(('M4', [235.872, y, 380.16, y + (8.1 if gap else 10.8)]))
        y += 10.8
    return dict(rectangles_um=[dict(layer=L, rect=r) for L, r in rows])


def test_starved_m5_strip_with_m4_gaps_gets_local_windows():
    r = _starved_receipt()
    assert not F._m5_wholly_reserved(r, 380.16, STARVED_BOXES)
    wins = F.pdn_windows_m5_full(r, 380.16, boxes=STARVED_BOXES)
    assert wins and {rr for _, _, _, rr in wins} == {(276.48, 17.28, 380.16, 285.12)}
    assert sorted({(a, b) for _, a, b, _ in wins}) == [(278.394, 279.006), (282.714, 283.326), (299.994, 300.606), (317.274, 317.886),
                                                (334.554, 335.166), (351.834, 352.446), (369.114, 369.726)]   # core-edge straps + the k%4 grid
    rows = [q for L, q in F.obstruction_rows(r, 380.16, macro_boxes=STARVED_BOXES) if L == 'M5' and q[1] == 17.28]
    assert [276.48, 17.28, 278.394, 285.12] in rows and [279.006, 17.28, 282.714, 285.12] in rows
    assert f'pdn_windows_m5_full={len(wins)}' in F.tcl(r, STARVED_BOXES)


def test_m5_strip_without_m4_gap_short_or_without_boxes_is_unchanged():
    assert F.pdn_windows_m5_full(_starved_receipt(gap=False), 380.16, boxes=STARVED_BOXES) == []      # M4 reserved whole: no strap piece
    assert F.pdn_windows_m5_full(_starved_receipt(strip_top=30.0), 380.16, boxes=STARVED_BOXES) == []   # a short row is a street / tooth
    assert F.pdn_windows_m5_full(_starved_receipt(), 380.16) == []
    assert F.tcl(_starved_receipt()) == F.tcl(_starved_receipt(), None)
    assert 'pdn_windows_m5_full' not in F.tcl(_starved_receipt(gap=False), STARVED_BOXES)


# q_b103 street 195.74-207.36 (11.62 um, over the 8.64 limit of q_b102's 3.456-um street) between hcol h1 and the h0 ra/rb row:
# M6 reserved 196.02-198.72, M4 198.72-201.42 and a 0.648-um row at 196.128, M5 comb teeth from 198.72 up.
B103_BOXES = [(8.64, 8.26, 227.232, 195.74), (8.64, 207.36, 114.912, 497.66), (120.96, 207.36, 227.232, 497.66)]


def _b103_street_receipt():
    rows = [('M4', [0, 198.72, 239.76, 201.42]), ('M4', [12.96, 196.128, 228.96, 196.776]), ('M6', [0, 196.02, 241.92, 198.72])]
    rows += [('M5', [23.76 + 10.8 * k, 198.72, 25.11 + 10.8 * k, 207.36]) for k in range(20)]
    return dict(rectangles_um=[dict(layer=L, rect=r) for L, r in rows])


def test_11_62_um_street_island_gets_m6_window():
    r = _b103_street_receipt()
    assert F.pdn_windows_street(r, boxes=B103_BOXES) == [('M6', 196.218, 197.19)]
    wide = [(8.64, 8.26, 227.232, 195.74), (8.64, 195.74 + 17.4, 227.232, 497.66)]
    assert F.pdn_windows_street(r, boxes=wide) == []                                   # a 17.4-um gap is no street


def test_short_rows_stacked_on_a_starved_strip_carry_its_windows_on():
    # the closing row of the strip (8.64 um) gets the strip's grid windows; a 2.16-um sliver and a row far wider than the strip do not
    r = _starved_receipt()
    r['rectangles_um'] += [dict(layer='M5', rect=[272.16, 285.12, 380.16, 293.76]), dict(layer='M5', rect=[235.872, 293.76, 380.16, 295.92]),
                           dict(layer='M5', rect=[164.16, 295.92, 380.16, 304.56])]
    wins = F.pdn_windows_m5_full(r, 380.16, boxes=STARVED_BOXES)
    rr = {w[3] for w in wins}
    assert (272.16, 285.12, 380.16, 293.76) in rr and (235.872, 293.76, 380.16, 295.92) not in rr and (164.16, 295.92, 380.16, 304.56) not in rr
    strip = sorted((a, b) for _, a, b, q in wins if q == (276.48, 17.28, 380.16, 285.12))
    assert sorted((a, b) for _, a, b, q in wins if q == (272.16, 285.12, 380.16, 293.76)) == strip
