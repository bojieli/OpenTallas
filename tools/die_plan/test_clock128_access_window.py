"""Physical host boundaries can require an L-drop even on a short clock leg."""
from test_clock128_r7 import C, _router, _tree


def test_abutting_host_windows_get_separate_m8_pin_jogs():
    M,cells,_=_tree()
    cells['H1']['y']=21.08
    nets=[dict(name='boundary',drv='D',loads=['H1'])]
    baseline=C.fixed_wires(M,cells,nets,1.62,.27,off=0.,router=_router(),pin_stack=True,l_drops=True)[0]
    assert not any(s[0]=='M9' for s in baseline['segs'])
    windows={('D','Y'):(20.02,20.25),('H1','A'):(21.10,21.30)}
    router=_router()
    def bound(net,what):
        key=('D','Y') if what=='trunk' else ('H1','A')
        return windows[key]
    router.access_window=bound
    router.riser_legal=lambda cell,pin,y:windows[(cell,pin)][0]<=y<=windows[(cell,pin)][1]
    result=C.fixed_wires(M,cells,nets,1.62,.27,off=0.,router=router,pin_stack=True,l_drops=True)[0]
    assert any(s[0]=='M9' for s in result['segs'])
    for stack in result['stacks']:
        lo,hi=windows[(stack['cell'],stack['pin'])]
        assert lo<=stack['riser_from'][1]<=hi
    assert next(s for s in result['stacks'] if s['cell']=='H1').get('drop')


def test_absent_access_contract_keeps_existing_routes():
    M,cells,nets=_tree()
    first=C.fixed_wires(M,cells,nets,1.62,.27,router=_router(),pin_stack=True,l_drops=True)
    router=_router();router.access_window=None;router.riser_legal=None
    second=C.fixed_wires(M,cells,nets,1.62,.27,router=router,pin_stack=True,l_drops=True)
    assert first==second


def test_impossible_actual_window_fails_before_route():
    M,cells,nets=_tree();router=_router()
    router.access_window=lambda net,what:(20.2,20.1)
    try:C.fixed_wires(M,cells,nets,1.62,.27,router=router,pin_stack=True,l_drops=True)
    except C.PlanError as failure:assert any(r['kind']=='no_clock_track' for r in failure.rows)
    else:raise AssertionError('impossible pin access window was accepted')


def test_m6_backbone_column_keeps_cell_pin_and_body_fixed():
    import copy
    M,cells,nets=_tree();before=copy.deepcopy(cells);r=_router()
    def column(cell,pin,actual):
        return (actual[0]+.08,actual[1]) if (cell,pin)==('H1','A') else actual
    r.stack_backbone_xy=column
    wires=C.fixed_wires(M,cells,nets,1.62,.27,off=0.,router=r,pin_stack=True,l_drops=True)
    assert cells==before
    s=next(s for w in wires for s in w['stacks'] if (s['cell'],s['pin'])==('H1','A'))
    actual=C.pin_xy(cells,'H1','A',.27)
    assert s['m6_entry_xy']==list(actual)
    assert abs(s['xy'][0]-actual[0]-.08)<1e-8 and s['xy'][1]==actual[1]
