from pathlib import Path
import shutil
import subprocess
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qc_su_lane_cut import cut


def fixture():
    text = 'module original(input wire clk, input wire rst_n, input wire [7:0] x, output wire [7:0] y);\n    wire [7:0] x_q;\n    assign x_q=x;\n'
    names = ['exp', 'rsq', 'head', 'rcp', 'lrly']
    for k in names:
        text += f'    wire [7:0] w_u_{k}0_y;\n'
    for i, k in enumerate(names):
        src = 'x_q' if i == 0 else f'w_u_{names[i-1]}0_y'
        text += f'    // as-built root.u_{k}0\n    leaf u_u_{k}0 (\n        .clk(clk),\n        .rst_n(rst_n),\n        .x({src}),\n        .y(w_u_{k}0_y)\n    );\n'
    return text + '    assign y=w_u_lrly0_y;\nendmodule\n'


def test_exact_group_lockstep_and_mutant(tmp_path):
    if not shutil.which('iverilog'):
        pytest.skip('iverilog unavailable')
    source = fixture()
    rtl, frame, report = cut(source, 0)
    assert (report['input_bits'], report['output_bits'], report['added_cycles']) == (8, 8, 0)
    leaf = '''module leaf(input clk,rst_n,input [7:0] x,output reg [7:0] y);
    always @(posedge clk) if(!rst_n) y<=0; else y<={x[6:0],x[7]}^8'h49;
    endmodule
    '''
    tb = '''module tb;
    reg clk=0,rst_n=0; reg[7:0] x=0; wire[7:0] a,b;
    original ref0(clk,rst_n,x,a); grouped dut(clk,rst_n,x,b);
    always #5 clk=~clk;
    integer i;
    initial begin
      repeat(3) @(negedge clk); rst_n=1;
      for(i=0;i<256;i=i+1) begin x=i; @(negedge clk); if(a!==b) $fatal(1,"cut differs at %0d",i); end
      $display("LOCKSTEP PASS256"); $finish;
    end endmodule
    '''
    def run(core, name):
        p=tmp_path/(name+'.sv')
        p.write_text(leaf+source+frame.replace('module original(', 'module grouped(')+core+tb)
        exe=tmp_path/name
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(p)],check=True,capture_output=True,text=True)
        return subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    good=run(rtl,'good')
    assert good.returncode == 0 and 'LOCKSTEP PASS256' in good.stdout
    bad=run(rtl.replace('assign x_q[0] = c_i[0];','assign x_q[0] = c_i[1];'),'mutant')
    assert bad.returncode != 0 and 'cut differs' in bad.stdout


def test_missing_leaf_rejected():
    with pytest.raises(ValueError,match='exactly five'):
        cut(fixture().replace('u_u_rcp0','u_u_other0'),0)


def test_bound_head_alignment_contract():
    source=fixture().replace('leaf u_u_head0 (', 'leaf #(.MEMORY_ALIGNMENT(3)) u_u_head0 (')
    _,_,r=cut(source,0,memory_alignment=3)
    assert r['memory_alignment']==3
    with pytest.raises(ValueError,match='regenerate the canonical bind'):
        cut(source.replace('MEMORY_ALIGNMENT(3)','MEMORY_ALIGNMENT(0)'),0,memory_alignment=3)
    with pytest.raises(ValueError,match='regenerate the canonical bind'):
        cut(fixture(),0,memory_alignment=3)
