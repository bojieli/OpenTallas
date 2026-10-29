"""Modeled PHY must cover every actual port; clock forwarding is not a data FF."""
import re
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/qwen_kv_die'))
import phy_pc4_gen as P


def test_actual_ports_and_corner_arcs(tmp_path):
    sheet=P.generate(tmp_path,432,760.32)
    d=tmp_path/P.NAME
    expected={'clk','rst_n'} | {f'{n}{k}[{b}]' for k in range(4) for n,w in [('po',328),('pi',289),('fh',4),('rh',4)] for b in range(w)}
    assert set(sheet['pins']) == expected
    lef=(d/f'{P.NAME}.lef').read_text()
    assert set(re.findall(r'^ PIN (\S+)',lef,re.M)) == expected | {'VDD','VSS'}
    for corner in ['tt','ff']:
        lib=(d/f'{P.NAME}_{corner}.lib').read_text()
        assert lib.count('timing_type : combinational;') == 8
        assert lib.count('timing_type : rising_edge;') == 4
        assert lib.count('timing_type : setup_rising;') == 5
        assert 'MODELED' in lib
    for p in sheet['pins'].values():
        a,b,c,d=p['rect_um']
        assert 0 <= a < c <= 432 and 0 <= b < d <= 760.32
    assert sheet['cycles_added'] == 0 and sheet['grade'] == 'MODELED'


def test_no_impossible_pin_wall(tmp_path):
    with pytest.raises(ValueError,match='cannot fit'):
        P.generate(tmp_path,40,40)


def test_explicit_layout_complete_and_no_pin_shorts(tmp_path):
    sheet=P.generate(tmp_path/'base',432,760.32)
    layout={'pins':{n:dict(layer=p['layer'],face=p['face'],rects_um=p['access_rects_um']) for n,p in sheet['pins'].items()},'obstruction_layers':[1,2,3]}
    got=P.generate(tmp_path/'native',432,760.32,layout)
    assert got['pins'] == sheet['pins']
    del layout['pins']['rst_n']
    with pytest.raises(ValueError,match='exactly every'):
        P.generate(tmp_path/'missing',432,760.32,layout)
    layout['pins']['rst_n']=layout['pins']['clk']
    with pytest.raises(ValueError,match='overlapping modeled pins'):
        P.generate(tmp_path/'shorted',432,760.32,layout)
