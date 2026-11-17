import copy
import pytest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from direct_frame_links import direct_frame_links

def fixture():
    return {'a':dict(master='col_h10_l4_lp_asb_x',conns={'xo':'pf_xo_test'}),
            'b':dict(master='col_h9_l4_lp_asb_x',conns={'x':'pf_xo_test'})},'wire [1103:0] pf_xo_test;'

def test_direct_selected_frame_word_keeps_actual_endpoints():
    inst,text=fixture();p=direct_frame_links(inst,text)['pf_xo_test']
    assert p['src']==[('a','xo')] and p['dst']==[('b','x')]
    assert p['age_edges']==0 and p['stations']==0 and p['width']==1104
    assert p['source_identity'].startswith('exact selected top')

@pytest.mark.parametrize('mutant', ['width','slice','fanout','assign','port','master'])
def test_direct_frame_wire_mutants_fail_closed(mutant):
    inst,text=fixture()
    if mutant=='width':text=text.replace('1103','275')
    if mutant=='slice':inst['b']['conns']['x']='pf_xo_test[275:0]'
    if mutant=='fanout':inst['c']=copy.deepcopy(inst['b'])
    if mutant=='assign':text+='assign pf_xo_test=other;'
    if mutant=='port':inst['a']['conns']={'ret':'pf_xo_test'}
    if mutant=='master':inst['a']['master']='legacy_frame'
    with pytest.raises(ValueError):direct_frame_links(inst,text)
