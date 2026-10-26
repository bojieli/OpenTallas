"""Interior pin removal preserves source nets and refuses truncation."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bind
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import die_port_bind as D

def variant(width=35):
    return D.parse_modules(f'module v(input wire [{width-1}:0] am, input wire clk); endmodule','fixture.sv')[0]

def test_astk_g_removal_preserves_valid_and_all_data():
    ports={'am':list(range(100,136)),'clk':[42]}
    selected=bind.variant_port_bits(ports,variant(),{}, {'am':[0]+list(range(2,36))})
    assert selected['am']==[100]+list(range(102,136))
    assert ports['am']==list(range(100,136))
    # Wrong contiguous truncation would retain g and drop the data MSB.
    assert selected['am']!=ports['am'][:35]

def test_noncontiguous_output_pins_keep_their_actual_nets():
    v=D.parse_modules('module v(output wire [2:0] so);endmodule','fixture.sv')[0]
    assert bind.variant_port_bits({'so':[20,21,22,23,24]},v,{}, {'so':[0,2,4]})=={'so':[20,22,24]}

@pytest.mark.parametrize('mapping',[
    {'am':list(range(35))[:-1]+[0]},
    {'am':list(range(34))+[36]},
    {'am':[-1]+list(range(34))},
    {'am':[True]+list(range(1,35))},
    {'am':list(range(34))},
    {'missing':[0]},
    {},
])
def test_bad_mapping_fails_closed(mapping):
    with pytest.raises(bind.BindError):
        bind.variant_port_bits({'am':list(range(36)),'clk':[42]},variant(),{},mapping)
