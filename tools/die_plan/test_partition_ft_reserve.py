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
