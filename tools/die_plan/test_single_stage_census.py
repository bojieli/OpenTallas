"""Real tiny OpenSTA fixtures: no timing-path pruning can turn internal sequential structure into a single stage."""
import re
import shutil
import subprocess
from pathlib import Path
import pytest

HERE=Path(__file__).resolve().parent
STA=shutil.which('sta')


def run(tmp_path, body, extra='', propagated=True):
    if not STA:pytest.skip('OpenSTA unavailable')
    (tmp_path/'tiny.v').write_text('module tiny(input clk,input clk2,input a,input b,output q0,output q1);\n'+body+'\nendmodule\n')
    script=f'''read_liberty {{{HERE/'examples/single_stage/tiny.lib'}}}
read_verilog {{{tmp_path/'tiny.v'}}}
link_design tiny
create_clock -name clk -period 1 [get_ports clk]
{extra}
'''
    if propagated:script+='set_propagated_clock [all_clocks]\n'
    script+=f'source {{{HERE/"single_stage_census.tcl"}}}\nputs "CENSUS [ot_ss_census]"\nexit\n'
    (tmp_path/'run.tcl').write_text(script)
    p=subprocess.run([STA,'-exit',str(tmp_path/'run.tcl')],text=True,capture_output=True)
    assert p.returncode==0,p.stdout+p.stderr
    row=next(l for l in p.stdout.splitlines() if l.startswith('CENSUS '))
    return {k:int(re.search(rf'\b{k} (\d+)',row)[1]) for k in ('done','registers','clocked','missing_clock','missing_arrival','internal_pairs_any','data_pins')},row


PORTS='DFF u0(.CK(clk),.D(a),.Q(q0));DFF u1(.CK(clk),.D(b),.Q(q1));'


def test_real_independent_port_registers_have_zero_internal_pairs(tmp_path):
    c,row=run(tmp_path,PORTS)
    assert c==dict(done=1,registers=2,clocked=2,missing_clock=0,missing_arrival=0,internal_pairs_any=0,data_pins=2)
    assert 'status PASS' in row


def test_disabled_false_path_mutant_still_counts_internal_pair(tmp_path):
    body='wire w;DFF u0(.CK(clk),.D(a),.Q(q0));BUF z(.A(q0),.Y(w));DFF u1(.CK(clk),.D(w),.Q(q1));'
    c,row=run(tmp_path,body,'set_false_path -from [get_cells u0] -to [get_cells u1]\nset_disable_timing -from A -to Y [get_cells z]')
    assert c['internal_pairs_any']==1 and 'status FAIL' in row


def test_unclocked_register_mutant_is_not_omitted(tmp_path):
    c,row=run(tmp_path,PORTS.replace('u1(.CK(clk)','u1(.CK(clk2)'))
    assert c['registers']==2 and c['clocked']==1 and c['missing_clock']==1 and 'status FAIL' in row


def test_interclock_data_pair_mutant_is_not_filtered(tmp_path):
    body='DFF u0(.CK(clk),.D(a),.Q(q0));DFF u1(.CK(clk2),.D(q0),.Q(q1));'
    c,row=run(tmp_path,body,'create_clock -name clk2 -period 1 [get_ports clk2]\nset_clock_groups -asynchronous -group clk -group clk2')
    assert c['clocked']==2 and c['internal_pairs_any']==1 and 'status FAIL' in row


def test_missing_propagated_arrivals_blocks_single_stage(tmp_path):
    c,row=run(tmp_path,PORTS,propagated=False)
    assert c['missing_arrival']==2 and 'status FAIL' in row
