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
