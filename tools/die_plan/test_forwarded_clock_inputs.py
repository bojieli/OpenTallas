"""Opaque logical leaves must preserve planned, distinct clock-export input taps."""
import copy
import json
import re
from pathlib import Path
import pytest
from clock_landings import Landings, LandingError
from test_clock_landings import vehicle
import bind


def physical_vehicle():
    p,t=vehicle()
    for typ in p['partition_types'].values():typ['outline_um']=[800,800]
    p['partitions'][1]['origin_um']=[810,0]
    t['regions'][0]['box_um']=[0,0,800,800];t['regions'][1]['box_um']=[810,0,1610,800]
    p['die']=dict(name='tapdie',outline_um=[1610,800],reach_um=405)
    p['lanes']=[]
    p['partition_types']['A']['clock']=dict(landing_contract=dict(forwarded_clock_only_inputs=True,pins=[dict(name='fclk_out_x',dir='out',kind='clock',layer='M8',xy_um=[799,1.5],source_clock_port='clk_t3'),dict(name='fclk_out_unused',dir='out',kind='clock',layer='M8',xy_um=[799,2.5],source_clock_port='clk_t2')]))
    return p,t


A='module a_mod (\n input wire clk,\n output wire [4:0] x\n);\n assign x = 0;\nendmodule\n'
B='module b_mod (\n input wire clk,\n input wire [4:0] y\n);\n wire rst_n,rst_n_t0,rr_parent,run;\n ot_dp_rgate u_rrl_0 (.clk(clk),.d(rr_parent),.run(run),.q(rst_n_t0));\n wire[4:0] y_q;\n assign y_q = y;\nendmodule\n'


def test_declared_export_tap_and_parent_connection():
    p,t=physical_vehicle();c=Landings(p,t)
    aa=c.type_rtl('A',A);c.type_rtl('B',B)
    assert 'input wire clk_t3' in aa
    assert 'assign fclk_out_x = clk_t3;' in aa
    assert 'input wire clk_t2' not in aa  # unused contract entry must not add a port
    assert 'assign x = 0;' in aa
    top='module tapdie (clk_core,rst_n);\n input wire clk_core;\n input wire rst_n;\n    a_mod a (\n        .clk(clk_core),\n        .x(w)\n    );\n    b_mod b (\n        .clk(clk_core),\n        .y(w)\n    );\nendmodule\n'
    out=c.top_rtl(top)
    assert '.clk_t3(clk_region_r0)' in out
    assert c.manifest()['forwarded_clock_only_inputs']=={'A':['clk_t3']}


def test_no_optin_preserves_fail_closed_contract():
    p,t=physical_vehicle();del p['partition_types']['A']['clock']['landing_contract']['forwarded_clock_only_inputs']
    with pytest.raises(LandingError,match='not an input port'):Landings(p,t).type_rtl('A',A)


def test_unknown_physical_tap_rejected():
    p,t=physical_vehicle();p['partition_types']['A']['clock']['landing_contract']['pins'][0]['source_clock_port']='clk_t99'
    with pytest.raises(LandingError,match='not a planned physical tap'):Landings(p,t).type_rtl('A',A)


def test_existing_clock_input_not_duplicated():
    p,t=physical_vehicle();c=Landings(p,t);out=c.type_rtl('A',A.replace(' input wire clk,',' input wire clk,\n input wire clk_t3,'))
    assert out.count('input wire clk_t3')==1
    assert c.forwarded_clock_only_inputs=={}


def test_kit_rtl_connects_bound_planned_tap_once(tmp_path):
    p,_=physical_vehicle();p['partitions']=p['partitions'][:1];p['partition_types']={'A':p['partition_types']['A']};p['partition_types']['A']['buses']=[];p['ports']=[]
    p['asbuilt']=dict(base=str(tmp_path),files=[],rtl_roots=[],prefer=[])
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(p));out=tmp_path/'out';rtl=out/'rtl';rtl.mkdir(parents=True)
    bf=rtl/'a_mod.sv';bf.write_text('module a_mod (\n input wire clk,\n input wire arst_n,\n input wire clk_t3,\n output wire fclk_out_x\n);\n assign fclk_out_x=clk_t3;\nendmodule\n')
    (rtl/'bind_cells.sv').write_text('// no bound cells in this clock-only fixture\n')
    (rtl/'tapdie_bound_top.sv').write_text('module tapdie_bound_top;\n    a_mod a (\n        .clk(clk_core),\n        .arst_n(rst_n),\n        .clk_t3(clk_core),\n        .fclk_out_x(fclk_out_x)\n    );\nendmodule\n')
    (out/'bind_report.json').write_text(json.dumps(dict(types={'A':dict(module='a_mod')},extra_lib=[],files=[str(bf)])))
    kit=tmp_path/'kit'
    assert bind.main(['kit-rtl',str(plan),'--out',str(out),'--type','A','--kit',str(kit)])==0
    text=(kit/'a_mod.sv').read_text()
    assert len(re.findall(r'input\s+wire\s+clk_t3\b',text))==1
    assert text.count('.clk_t3(clk_t3)')==1
