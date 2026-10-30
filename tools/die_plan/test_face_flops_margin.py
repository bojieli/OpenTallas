"""N/S face search covers pins in both core margins without silently dropping FFs."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC=Path(__file__).with_name('face_flops.tcl').read_text()
pytestmark=pytest.mark.skipif(shutil.which('tclsh') is None,reason='tclsh unavailable')


def scan(pins,occupied=''):
    start=SRC.index('      # Face pins may lie in the core margin.')
    end=SRC.index('\n    }\n    if {!$placed}',start)
    branch=SRC[start:end]
    script='''set ff_x0 4320;set ff_x1 388800;set ff_y0 4320;set ff_y1 172800
set ff_cpitch 2160;set ff_rh 270;set w 1080;set face N;set ff_occ {};set ff_miss 0
'''+occupied+'\nforeach px {'+' '.join(map(str,pins))+'} {\n'+branch+'''
if {!$placed} {error "unplaced margin pin $px"}
puts "LOC $px $c $cx $cy"
}
'''
    cp=subprocess.run(['tclsh'],input=script,capture_output=True,text=True,check=True)
    assert not cp.stderr,cp.stderr
    return [tuple(map(int,x)) for x in re.findall(r'LOC (\d+) (\d+) (\d+) (\d+)',cp.stdout)]


def test_actual_rn_129_to_135_margin_positions_all_find_distinct_firm_sites():
    pins=[924,1116,1308,1500,1692,1884,2076]
    rows=scan(pins)
    assert len(rows)==7 and len({(x,y) for _,_,x,y in rows})==7
    assert all(4320<=x and x+1080<=388800 for _,_,x,_ in rows)
    assert {col for _,col,_,_ in rows}<={0,1}


def test_upper_margin_uses_last_legal_column_and_skips_occupied_site():
    rows=scan([388900,390000,395000], 'dict set ff_occ "N,0,177" 1')
    assert len(rows)==3 and all(0<=c<=177 for _,c,_,_ in rows)
    assert len({(x,y) for _,_,x,y in rows})==3
    assert all(x+1080<=388800 for _,_,x,_ in rows)


def test_interior_starting_column_keeps_previous_coordinate():
    rows=scan([194400])
    assert rows[0][1:]==(88,194400,172530)
