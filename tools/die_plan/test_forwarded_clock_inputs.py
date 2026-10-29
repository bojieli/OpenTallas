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


def test_multiple_export_taps_parse_and_forward_distinct_clocks(tmp_path):
    """A tap inserted before a later port must not comment out its comma."""
    import shutil
    import subprocess
    iv = shutil.which("iverilog")
    vv = shutil.which("vvp")
    if not iv or not vv:
        pytest.skip("iverilog/vvp required for executable generated-header regression")
    p, t = physical_vehicle()
    pp = copy.deepcopy(p["ports"][0]); pp.update(id="P2")
    pp["src"]["bus"] = "z"; pp["dst"]["bus"] = "y2"; p["ports"].append(pp)
    tp = copy.deepcopy(t["ports"][0]); tp.update(port="P2", lane="L2"); t["ports"].append(tp)
    cpin = copy.deepcopy(p["partition_types"]["A"]["buses"][0]); cpin["name"]="fclk_out_z"
    p["partition_types"]["A"]["buses"].append(cpin)
    for name in ("y2", "fclk_in_y2", "landing_ready_y2", "landing_fault_y2"):
        q=copy.deepcopy(next(x for x in p["partition_types"]["B"]["buses"] if x["name"]==name.replace("y2","y")))
        q["name"]=name; p["partition_types"]["B"]["buses"].append(q)
    p["partition_types"]["A"]["clock"]["landing_contract"]["pins"].append(dict(
        name="fclk_out_z",dir="out",kind="clock",layer="M8",xy_um=[799,3.5],source_clock_port="clk_t2"))
    source=A.replace(" output wire [4:0] x", " output wire [4:0] z,\n output wire [4:0] x").replace(" assign x = 0;"," assign x = 0; assign z = 0;")
    emitted=Landings(p,t).type_rtl("A",source)
    assert "assign fclk_out_x = clk_t3;" in emitted and "assign fclk_out_z = clk_t2;" in emitted
    bench="""module tb;
reg clk=0, c2=0, c3=0; wire fx,fz; wire [4:0] x,z;
a_mod u(.clk(clk),.clk_t2(c2),.clk_t3(c3),.fclk_out_x(fx),.fclk_out_z(fz),.x(x),.z(z));
initial begin
 #1; c2=1; #1; if(fz!==1 || fx!==0 || x!==0 || z!==0) $fatal(1,"c2 forwarding");
 c3=1; c2=0; #1; if(fx!==1 || fz!==0) $fatal(1,"c3 forwarding");
 clk=1; #1; if(fx!==1 || fz!==0) $fatal(1,"data clock changed export");
 $display("CLOCK_EXPORT_PASS"); $finish;
end
endmodule
"""
    def compile_run(label,rtl):
        f=tmp_path/(label+".sv");f.write_text(rtl+"\n"+bench);exe=tmp_path/label
        cp=subprocess.run([iv,"-g2012","-s","tb","-o",str(exe),str(f)],capture_output=True,text=True)
        if cp.returncode:return cp,None
        return cp,subprocess.run([vv,str(exe)],capture_output=True,text=True)
    cp,r=compile_run("normal",emitted)
    assert cp.returncode==0,cp.stderr
    assert r.returncode==0 and "CLOCK_EXPORT_PASS" in r.stdout,r.stdout+r.stderr
    # Exact old defect: the comma after this input becomes part of its line comment.
    legacy=emitted.replace("/* planned physical tap: forwarded-clock export only */", "// planned physical tap: forwarded-clock export only")
    cp,_=compile_run("commented_comma",legacy)
    assert cp.returncode!=0
    # A parse-only regression would miss a real wrong export-clock connection.
    cp,r=compile_run("wrong_clock",emitted.replace("assign fclk_out_z = clk_t2;", "assign fclk_out_z = clk_t3;"))
    assert cp.returncode==0 and r.returncode!=0
