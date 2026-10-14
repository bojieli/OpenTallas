import json
from pathlib import Path

from hbm_sm_global_pack_1013 import intersect, subtract, template, validate
from hbm_sm_real_pin_audit_1013 import pinmap, transform

ROOT=Path(__file__).resolve().parents[1]


def test_adjacent_lef_pins_are_all_read():
    # A consuming END newline silently dropped every second pin in an earlier
    # draft and understated both reach and congestion by almost one half.
    s='\nPIN a\n DIRECTION INPUT ;\n PORT\n LAYER M5 ;\n RECT 0 0 1 1 ;\n END\nEND a\nPIN b\n DIRECTION OUTPUT ;\n PORT\n LAYER M5 ;\n RECT 2 2 3 3 ;\n END\nEND b\n'
    assert pinmap(s)=={'a':[.5,.5],'b':[2.5,2.5]}


def test_whole_layout_mirror_preserves_distances():
    a={'at_um':[43.2,766.8],'size_um':[302.4,157.68],'orient':'R0'}
    b={'at_um':[630.72-43.2-302.4,766.8],'size_um':[302.4,157.68],'orient':'MY'}
    pa=transform(a,[.042,139.548]);pb=transform(b,[.042,139.548])
    assert abs(pa[0]+pb[0]-630.72)<1e-6
    assert pa[1]==pb[1]


def test_real_native_template_preserves_35_children():
    c=json.load(open(ROOT/'results/arch/hbm_native_1013/sm/component.json'))
    g=json.load(open(ROOT/'results/arch/hbm_native_1013/sm_compaction/real_pin_geometry_candidate.json'))
    n=template(c,g)
    assert len(n['children'])==35
    assert abs(n['outline_um'][1]-2272.32)<1e-6
    assert [x['instance'] for x in n['children']]==[x['instance'] for x in c['children']]
    for before,after in zip(c['children'],n['children']):
        assert before['view_lef']==after['view_lef']
        if '_tile_' not in before['logical_module']:
            assert before==after


def test_fixed_overlap_cannot_be_claimed_legal():
    r=[{'name':'a','at_um':[0,0],'size_um':[10,10]}, {'name':'b','at_um':[9,0],'size_um':[10,10]}]
    assert not validate(r,20,20)['legal']
    r[1]['at_um']=[10,0]
    assert validate(r,20,20)['legal']


def test_subtract_does_not_leave_obstacle_in_free_space():
    b=[4,4,6,6]
    free=subtract([[0,0,10,10]],b)
    assert all(not intersect(f,b)for f in free)
    assert len(free)==4
