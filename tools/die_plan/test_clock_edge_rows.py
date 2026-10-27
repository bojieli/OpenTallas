import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
import schema as S
EX=json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text())
def plan(edges=None):
    t=dict(outline_um=[100.,100.],clock={'tap_um':[50.,50.]})
    if edges is not None:t['clock']['tap_edge_y_um']=edges
    return SimpleNamespace(types={'b':t},budgets={})
def test_small_type_honors_explicit_two_edges():
    assert S._grid_taps(plan([10.,90.]),'b')==[('clk',50.,10.),('clk_t1',50.,90.)]
def test_default_small_type_keeps_its_tap():
    assert S._grid_taps(plan(),'b')==[('clk',50.,50.)]
def test_edge_rows_validate_and_reject_outside():
    p=copy.deepcopy(EX);tn=next(iter(p['partition_types']));t=p['partition_types'][tn]
    t.setdefault('clock',{})['tap_edge_y_um']=[1.,t['outline_um'][1]-1.]
    assert not S.validate(p)
    t['clock']['tap_edge_y_um']=[t['outline_um'][1]+1.]
    assert any('outside outline' in x for x in S.validate(p))
def test_negative_edge_row_rejected():
    p=copy.deepcopy(EX);tn=next(iter(p['partition_types']));p['partition_types'][tn].setdefault('clock',{})['tap_edge_y_um']=[-1.]
    assert S.validate(p)
