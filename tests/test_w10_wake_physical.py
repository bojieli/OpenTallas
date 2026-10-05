"""Physical admission detects collapsed wake clones and preserves the ROM timing contract."""
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from w10_wake_physical import mapped_guard
from w10_wake_flow import overlay, EXPECTED


def netlist(tmp_path,kind='valid'):
    text=''
    for i in range(8):
        text+=f'  DFFHQNx1_ASAP7_75t_R wake{i} (\n    .CLK(clk), .D(next), .QN(w{i})\n  );\n'
        ena='go' if kind=='raw_go' else ('w0' if kind=='merged' else f'w{i}')
        text+=f'  ICGx1_ASAP7_75t_R gate{i} (\n    .CLK(clk), .ENA({ena}), .GCLK(g{i}), .SE(zero)\n  );\n'
    for i in range(3 if kind=='small' else 4):
        text+=f'  ot_rom_4096x274_m8 rom{i} (\n    .clk(g{i+4}), .ce_in(issue)\n  );\n'
    path=tmp_path/'mapped.v';path.write_text(text);return path


def test_distinct_registered_leaf_drivers(tmp_path):
    r=mapped_guard(netlist(tmp_path),'q')
    assert r['icg_count']==8 and len(r['distinct_wake_flops'])==8


@pytest.mark.parametrize('kind',['raw_go','merged','small'])
def test_reject_unsafe_structure(tmp_path,kind):
    with pytest.raises(ValueError):mapped_guard(netlist(tmp_path,kind),'q')


def test_reject_undersized_column(tmp_path):
    with pytest.raises(ValueError):mapped_guard(netlist(tmp_path),'column')


@pytest.mark.parametrize('pin,old,new', [('CLK','clk','other_clk'),('D','next','different_enable')])
def test_reject_functional_or_clock_perturbation(tmp_path,pin,old,new):
    p=netlist(tmp_path)
    p.write_text(p.read_text().replace(f'.{pin}({old})',f'.{pin}({new})',1))
    with pytest.raises(ValueError):mapped_guard(p,'q')


def test_existing_rom_contract_only(tmp_path):
    assert overlay(ROOT/'physical/abi3/w10_wake_pp_multicycle.sdc')==EXPECTED
    path=tmp_path/'bad.sdc';path.write_text('\n'.join(EXPECTED)+'\nset_false_path -from [all_inputs]\n')
    with pytest.raises(ValueError):overlay(path)
