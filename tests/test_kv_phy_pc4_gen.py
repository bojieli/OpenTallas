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


def test_single_core_face(tmp_path):
    sheet=P.generate(tmp_path,316.008,1511.28,faces=('E','E','E','E'))
    assert {p['face'] for p in sheet['pins'].values()} == {'E'}
    ys=sorted(p['rect_um'][1] for p in sheet['pins'].values())
    assert all(b-a > .15 for a,b in zip(ys,ys[1:])) and len(ys) == 2502
    assert P.generate(tmp_path/'d',432,760.32)['pins']['clk']['face'] == 'W'
    with pytest.raises(ValueError,match='faces'):
        P.generate(tmp_path/'x',432,760.32,faces=('E','E'))
