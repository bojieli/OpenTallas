from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from qc_su_plan_cut import pins_for_cut


def test_real_consumer_pin_slots_and_control_clearance():
    source='    wire [1:0] w_u_lrly0_a;\n    wire w_u_lrly0_b;\n    ot_dp_st #(.W(2)) u_bout_x_su_c_o (.d(w_u_lrly0_a), .ea(rst_n));\n    ot_dp_st #(.W(1)) u_bout_x_ctl_o (.d(w_u_lrly0_b), .ea(rst_n));\n'
    old=[dict(name='c_i[0]',layer='M4',x=.096,y=10),dict(name='c_o[0]',layer='M4',x=.096,y=20),dict(name='c_o[1]',layer='M4',x=.096,y=21),dict(name='ctl_o[0]',layer='M5',x=30,y=49.904)]
    report=dict(input_bits=1,outputs=[dict(name='w_u_lrly0_a',bit=0),dict(name='w_u_lrly0_a',bit=1),dict(name='w_u_lrly0_b',bit=0)])
    ps,roles=pins_for_cut(old,report,source,[50,50])
    assert roles==dict(c_o=2,ctl_o=1)
    assert [(p['x'],p['y']) for p in ps[:4]]==[(p['x'],p['y']) for p in old]
    assert [p['name'] for p in ps]==['c_i[0]','c_o[0]','c_o[1]','c_o[2]','clk','rst_n']
    report['outputs'].append(dict(name='w_u_unknown',bit=0))
    with pytest.raises(ValueError,match='no approved'):
        pins_for_cut(old,report,source,[50,50])
