from types import SimpleNamespace
import pytest
import reset_tree as R


def fixture(monkeypatch, points):
    t={'outline_um':[300,300], 'reset':{'relay_route':'core_free_bbox'},
       'hard_cores':[{'inst':'macro','origin_um':[20,20],'outline_um':[60,60]}]}
    p=SimpleNamespace(types={'t':t},reset={})
    monkeypatch.setattr(R,'_taps',lambda p,tn:[(f'clk{i}',*q) for i,q in enumerate(points)])
    monkeypatch.setattr(R,'in_pin',lambda p,tn:(5,5))
    monkeypatch.setattr(R,'out_pins',lambda p,tn:[])
    monkeypatch.setattr(R,'core_reset_targets',lambda p,tn:[])
    monkeypatch.setattr(R,'walls',lambda p,tn:[])
    return p,t


def test_clear_L_alone_does_not_prevent_resizer_core_corner():
    boxes=[(20,20,80,80)]
    assert R._edge_ok((5,5),(95,95),boxes)
    assert not R._bbox_edge_ok((5,5),(95,95),boxes)


def test_core_free_routes_keep_existing_release_depth(monkeypatch):
    p,t=fixture(monkeypatch,[(95,95),(285,285)])
    tree=R._wf_type_tree(p,'t')
    assert tree['depth']==tree['native_depth']==2
    xy={'rst_root_n':tree['root']}
    for r in tree['relays']:
        assert R._bbox_edge_ok(xy[r['d']],r['xy'],R.blockages(t))
        xy[r['q']]=r['xy']
    assert {r['depth'] for r in tree['relays'] if r['tap'] is not None}=={2}


def test_deeper_control_route_is_rejected_not_silently_retimed(monkeypatch):
    p,t=fixture(monkeypatch,[(95,95)])
    with pytest.raises(R.ResetError,match='explicit boot/cycle proposal required'):
        R._wf_type_tree(p,'t')


def test_declared_existing_depth_is_not_shortened_after_new_tap_inventory(monkeypatch):
    p,t=fixture(monkeypatch,[(95,95),(285,285)])
    t['reset']['relay_route_depth']=3
    tree=R._wf_type_tree(p,'t')
    assert tree['native_depth']==2
    assert tree['depth']==tree['contract_depth']==3
    assert {r['depth'] for r in tree['relays'] if r['tap'] is not None}=={3}
