import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_fulltile_downstream_graph import Graph,boolean,variables

def test_liberty_boolean_operators_exhaustive():
    a,b,c=variables(3);u=(1<<8)-1
    assert boolean('(!A * B) + (C)',dict(A=a,B=b,C=c),u)==((u^a)&b)|c

def test_unrecognized_function_refused():
    with pytest.raises(ValueError):boolean('A and B',dict(A=1,B=0),1)

def fixture(function='A * B'):
    lib='cell (AND) { pin (Y) { function : "'+function+'"; } }'
    net={'cells':{'merge':{'type':'AND','port_directions':{'A':'input','B':'input','Y':'output'},'connections':{'A':[1],'B':[2],'Y':[3]}}}}
    return Graph(net,lib)

def test_actual_gate_function_and_wrong_polarity_detected():
    a,b=variables(2);u=15
    assert fixture().eval(3,{1:a,2:b},u,{})==a&b
    assert fixture('!A * B').eval(3,{1:a,2:b},u,{})!=a&b

def test_missing_boundary_refused():
    with pytest.raises(KeyError):fixture().eval(3,{1:3},15,{})

def test_sequential_boundary_cannot_be_zero_filled():
    net={'cells':{'ff':{'type':'DFF','port_directions':{'D':'input','Q':'output'},'connections':{'D':[1],'Q':[2]}}}}
    with pytest.raises(ValueError,match='unbound sequential'):Graph(net,'').eval(2,{},15,{})
