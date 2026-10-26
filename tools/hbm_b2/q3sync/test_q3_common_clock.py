import importlib.util
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import q3_common_clock as C


def test_native_clock_expression_rejects_phase_logic_and_constants():
    assert C.native_expr('{clk_link[4],clk_link[3:0]}')=={'clk_link'}
    for text in ['~clk_arg',"1'b0",'clk_arg&enable','clk_link[15]','clk_pair[0]']:
        with pytest.raises(ValueError):C.native_expr(text)


def test_ansi_port_inventory_preserves_literal_vector_shape():
    p=C.ports('module m(input wire [4:0] a,output signed [2:0][3:0] y);endmodule','m')
    assert [x['width']for x in p]==[5,12]
    assert p[1]['signed']=='signed'
    with pytest.raises(ValueError):C.ports('module m #(parameter N=3)(input clk);endmodule','m')


def test_native_bit_id_negative_control(tmp_path):
    m={'cores':{'edge':{'clocks':[{'name':'arg_clk','width':1}]}}}
    (tmp_path/'m.json').write_text(json.dumps(m))
    n={'modules':{'native_clock_alias_probe':{'ports':{'clk':{'bits':[2]}},'cells':{'edge':{'connections':{'arg_clk':[2]}}}}}}
    p=tmp_path/'n.json';p.write_text(json.dumps(n));assert C.check_bits(p,tmp_path/'m.json')['clock_bits']==1
    n['modules']['native_clock_alias_probe']['cells']['edge']['connections']['arg_clk']=[3]
    p.write_text(json.dumps(n))
    with pytest.raises(ValueError,match='phase mismatch'):C.check_bits(p,tmp_path/'m.json')


def test_nonclock_bit_identity_refuses_wrong_data_or_extra_cell(tmp_path):
    m={'cores':{'edge':{'wrapper':'outer','top':'inner','clocks':[{'name':'arg_clk','width':1}],'data_ports':[{'name':'fault','width':1}]}}}
    mp=tmp_path/'m.json';mp.write_text(json.dumps(m))
    x={'modules':{'outer':{'ports':{'clk':{'bits':[2]},'fault':{'bits':[3]}},'cells':{'u_core':{'type':'inner','connections':{'arg_clk':[2],'fault':[3]}}}}}}
    p=tmp_path/'x.json';p.write_text(json.dumps(x));assert C.check_adapter(p,mp,'edge')['nonclock_bits']==1
    x['modules']['outer']['cells']['u_core']['connections']['fault']=[4];p.write_text(json.dumps(x))
    with pytest.raises(ValueError,match='data/valid/fault/reset'):C.check_adapter(p,mp,'edge')
