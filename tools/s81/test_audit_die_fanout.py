import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_die_fanout import audit


def test_fanout_keeps_unknown_direction_and_branch_vs_pair_difference():
    def inst(n,x):return [n,'m','hub','','',x,0,10,10,'R0']
    m=dict(insts=[inst('middle',500),inst('left',0),inst('right',1000)],ports={},real_masters=[],buses=[
        ['three','hub',32,[['middle','o'],['left','i'],['right','i']]],
        ['clock','clock',1,[['middle','ck'],['left','ck'],['right','ck']]],
        ['unresolved','hub',4,[['middle','x'],['left','i'],['missing','i']]],
        ['p2p','hub',1,[['left','x'],['right','y']]],
    ])
    d=audit(m);assert d['multi_terminal_bus_count']==d['emitted_rows']==3
    r=next(r for r in d['rows'] if r['bus']=='three')
    assert r['first_endpoint_branch_um']==500
    assert r['max_terminal_separation_um']==1000
    assert r['first_endpoint_same_pair_box_gap_lower_bound_um']==490
    assert r['endpoint_anchor_gaps']==3 and r['age'].startswith('UNPROVED')
    assert d['categories']['clock']['buses']==1
    assert d['categories']['data_or_control']['age_qualified']==0
    assert d['unresolved_endpoints']==[dict(bus='unresolved',inst='missing',port='i')]


def test_actual_rtl_driver_can_be_last_without_inventing_direction():
    m=dict(insts=[[n,'m','hub','','',x,0,10,10,'R0']for n,x in [('a',0),('b',500),('driver',2000)]],ports={},buses=[
        ['real','hub',8,[['a','i','in'],['b','i','in'],['driver','o','out']]],
        ['mixed','hub',8,[['a','i','in'],['b','i','io'],['driver','o','mixed']]],
    ])
    d=audit(m);rows={r['bus']:r for r in d['rows']}
    assert rows['real']['rtl_driver']==['driver','o']
    assert rows['real']['rtl_driver_branch_um']==2000
    assert rows['real']['rtl_driver_same_pair_box_gap_lower_bound_um']==1990
    assert rows['mixed']['rtl_driver'] is None
    assert d['categories']['data_or_control']['rtl_direction_resolved']==1
