"""Parameterized soft leaf ABIs retain dimensions, latency and string parameters."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bind_elab as E
import bind_slang_abi as ABI


def sources(tmp_path):
    leaf=tmp_path/'leaf.sv'
    leaf.write_text('''module leaf #(parameter integer W=595,D=2,parameter LABEL="001",parameter string TAG="source")
(input clk,input [W-1:0] i,output [W-1:0] q);
reg [W-1:0] p[0:D-1];integer k;
always @(posedge clk) begin p[0]<=i;for(k=1;k<D;k=k+1)p[k]<=p[k-1];end
assign q=p[D-1] ^ (LABEL=="right" ? {{(W-1){1'b0}},1'b1}: {W{1'b0}});
endmodule
''')
    top=tmp_path/'top.sv'
    top.write_text('''module top(input clk,input [667:0] i,output [594:0] a,output [667:0] b);
leaf #(.W(595),.D(2),.LABEL("001"),.TAG("001")) u_a(.clk(clk),.i(i[594:0]),.q(a));
leaf #(.W(668),.D(5),.LABEL("right"),.TAG("right_tag")) u_b(.clk(clk),.i(i),.q(b));
endmodule
''')
    return leaf,top


def test_parser_multiple_parameters_and_localparam():
    assert ABI._parameters('module m #(parameter W=4,D=2,parameter string LABEL="x,y",localparam A=4)(input i);','')==['W','D','LABEL']
    with pytest.raises(ValueError,match='type parameters'):
        ABI._parameters('module m #(parameter type T=logic)(input i);','')


def test_private_body_and_structural_parent_rejected(tmp_path):
    leaf,_=sources(tmp_path)
    with pytest.raises(ValueError,match='private body is forbidden'):
        ABI.stage([str(leaf)],set(),['leaf'],tmp_path/'stage',E.MOD_RE,E._strip,E._match)
    with pytest.raises(ValueError,match='structural parents'):
        ABI.stage([str(leaf)],{'leaf'},['leaf'],tmp_path/'stage',E.MOD_RE,E._strip,E._match)


def test_numeric_string_parameters_and_native_latency(tmp_path,monkeypatch):
    exe=shutil.which('yosys')
    if not exe:pytest.skip('native Yosys/Slang unavailable')
    monkeypatch.setenv('OT_BIND_YOSYS',exe)
    leaf,top=sources(tmp_path)
    ab={'top':'top','frontend':'slang','netlist':[str(top)],'files':[str(leaf)],'rtl_roots':[]}
    E.elab(ab,tmp_path,tmp_path/'before',mem_gb=4)
    before=json.loads((tmp_path/'before/asbuilt.json').read_text())
    assert len(before['modules']['top']['cells']['u_b']['connections']['q'])==595
    assert sum(isinstance(b,str) for b in before['modules']['top']['ports']['b']['bits'])==73
    ab['slang_parameterized_blackboxes']=['leaf']
    rec=E.elab(ab,tmp_path,tmp_path/'after',mem_gb=4)
    j=json.loads((tmp_path/'after/asbuilt.json').read_text());m=j['modules']['top']
    assert rec['parameterized_interface_restore']=={'masters':['leaf'],'specialized_modules':2,'instances':2}
    assert {n:len(c['connections']['q']) for n,c in m['cells'].items()}=={'u_a':595,'u_b':668}
    assert all(not isinstance(b,str) for b in m['ports']['b']['bits'])
    F=E.flatten(j,'top')
    params={c.path:c.params for c in F.cells}
    assert E._pval(m['cells']['u_a']['parameters']['LABEL'])[1]==int.from_bytes(b'001','big')
    assert params['u_a']['TAG']=='"001"'
    assert params['u_b']['TAG']=='"right_tag"'
    assert E._pval(m['cells']['u_b']['parameters']['LABEL'])[1]==int.from_bytes(b'right','big')
    assert E._pval(m['cells']['u_a']['parameters']['D'])[1]==2
    assert E._pval(m['cells']['u_b']['parameters']['D'])[1]==5
    assert all(c.module=='leaf' for c in F.cells)
    assert all(not j['modules'][c['type']].get('cells') for c in m['cells'].values())
    if not shutil.which('iverilog') or not shutil.which('vvp'):pytest.skip('iverilog/vvp unavailable')
    simleaf=tmp_path/'leaf_sim.sv'
    simleaf.write_text(leaf.read_text().replace('parameter string TAG','parameter TAG'))
    bound=[]
    for module,mutant in [('bound',False),('bound_mut',True)]:
        lines=[f'module {module}(input clk,input [667:0]i,output [594:0]a,output [667:0]b);']
        for name,p in params.items():
            p=dict(p)
            if mutant and name=='u_b':p['D']="32'd4"
            arguments=','.join(f'.{k}({v})' for k,v in p.items())
            inp='i[594:0]' if name=='u_a' else 'i';out='a' if name=='u_a' else 'b'
            lines.append(f'leaf #({arguments}) {name}(.clk(clk),.i({inp}),.q({out}));')
        lines.append('endmodule');bound+=lines
    (tmp_path/'bound.sv').write_text('\n'.join(bound))
    (tmp_path/'tb.sv').write_text('''module tb;
reg clk=0;reg[667:0]i=0;wire[594:0]ga,ba,ma;wire[667:0]gb,bb,mb;integer t,k,hits=0,activity=0;
top g(clk,i,ga,gb);bound b(clk,i,ba,bb);bound_mut m(clk,i,ma,mb);
initial begin
for(t=0;t<200;t=t+1)begin
clk=0;for(k=0;k<668;k=k+1)i[k]=$random;#2;clk=1;#1;
if(t>10)begin
if({ga,gb}!=={ba,bb})$fatal(1,"ABI latency/string mismatch");
if(mb!==gb)hits=hits+1;if(gb!==0)activity=activity+1;
end
#2;
end
if(hits<180||activity<180)$fatal(1,"vacuous or mutant not caught");
$display("ABI_LOCKSTEP_PASS checks189 mutant_hits%0d",hits);$finish;end
endmodule
''')
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim'),str(simleaf),str(top),str(tmp_path/'bound.sv'),str(tmp_path/'tb.sv')],check=True,capture_output=True,text=True)
    run=subprocess.run(['vvp',str(tmp_path/'sim')],check=True,capture_output=True,text=True)
    assert 'ABI_LOCKSTEP_PASS checks189 mutant_hits189' in run.stdout
