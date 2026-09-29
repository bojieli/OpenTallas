"""Exercise the tile's actual streamer parameter binding and image ABI.

This is a boundary test, not a full die memory allocation or token result.
"""
import re
import subprocess
from pathlib import Path
import numpy as np
import pytest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from tools import hdc_program_v41 as P
from tools import hdc_qstream_descriptor as D

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('full', [0, 1])
def test_actual_tile_streamer_profile(tmp_path, full):
    tile = (ROOT/'rtl/chip/ot_chip_v41x_tile.sv').read_text()
    params = re.search(r'ot_hdc_qstream #(.*?) u_qs', tile, re.S)
    # Retain the actual instance's parameter expression and declarations.
    if params is None:
        params = re.search(r'ot_hdc_qstream #(.*?)\)\s*\(\s*\.clk', tile, re.S)
        prefix = 'ot_hdc_qstream #' + params.group(1) + ')'
    else:
        prefix = 'ot_hdc_qstream #' + params.group(1)
    decls = []
    for name in ('qlist', 'l_q'):
        decls.append(re.search(r'reg\s*\[[^;]+\]\s*'+name+r'\b[^;]*;', tile).group())
    source = '''module test;
localparam FULL_SHAPE=%d, AW=FULL_SHAPE?30:24, NW=FULL_SHAPE?21:16;
localparam QLIST_BITS=FULL_SHAPE?160:128, BL=16, QLB=272, LWIN=3, LAW=2, NPC_W=8;
%s
%s dut();
initial begin
if ($bits(l_q)!=(FULL_SHAPE?160:128) || $bits(qlist[0])!=$bits(l_q)) $fatal;
if (dut.FULL_SHAPE!=FULL_SHAPE || dut.HAW!=AW || dut.LIST_BITS!=$bits(l_q) || dut.NW!=NW) $fatal;
$display("TILE_FETCH_PROFILE_PASS");$finish;
end
endmodule
''' % (full, '\n'.join(decls), prefix)
    (tmp_path/'test.sv').write_text(source)
    subprocess.run(['iverilog','-g2012','-s','test','-o',str(tmp_path/'sim'),
                    str(ROOT/'rtl/hdc/hbm/ot_hdc_qstream.sv'),str(tmp_path/'test.sv')],check=True,capture_output=True)
    out=subprocess.run(['vvp',str(tmp_path/'sim')],check=True,capture_output=True,text=True)
    assert 'TILE_FETCH_PROFILE_PASS' in out.stdout

@pytest.mark.parametrize('profile', ['reduced','full_shape'])
def test_image_writer_selects_fetch_abi(tmp_path, monkeypatch, profile):
    entry=dict.fromkeys(D.FIELDS,0)
    entry.update(n=65536 if profile=='full_shape' else 8,
                 hbm=(1<<29) if profile=='full_shape' else 7,
                 rom=(1<<26) if profile=='full_shape' else 3)
    class Layout:
        qcodes=[0]
    monkeypatch.setattr(P,'qe_hbm_image',lambda lay: ([0],[0]))
    monkeypatch.setattr(P,'qe_fetch_list',lambda *args: [entry])
    monkeypatch.setattr(P,'qe_word_formats',lambda lay: np.array([0]))
    P.write_hbm_images(tmp_path,Layout(),[],profile=profile)
    lines=(tmp_path/'qlist.hex').read_text().splitlines()
    assert all(len(line)==D.BITS[profile]//4 for line in lines)
    assert [int(line,16) for line in lines]==D.encode_list([entry],profile)
    assert D.decode(int(lines[0],16),profile)==entry
