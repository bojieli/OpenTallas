#!/usr/bin/env python3
"""Regression: initialization commands are part of a face shell's live interface."""
import importlib.util, subprocess, sys, tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('fs', Path(__file__).with_name('face_shell.py'))
fs=importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)
 src=p/'core.sv'; src.write_text('''module core(input clk, input ld, input [7:0] x, output [7:0] y);
 reg [7:0] off;
 always @(posedge clk) if(ld) off <= 0;
 assign y=x+off;
 endmodule
''')
 rep=fs.analyze([src],'core',workdir=p/'analyze')
 assert 'ld' not in rep['unread_in'], rep
 widths,dirs=rep['port_width'],rep['port_dirs']
 keep,dropped,_=fs.drop_plan(widths,dirs,rep['unread_in'],{'clk'})
 assert keep['ld']==1 and not dropped
 shell=fs.emit_shell('shell','core',{},widths,dirs,keep,{'clk'},'clk')
 (p/'cell.sv').write_text(fs.CELL_SV)
 tb='''module tb;
 reg clk=0; always #5 clk=~clk;
 reg ld=0; reg [7:0] x=0;
 wire [7:0] got,ref_y; reg ref_ld; reg [7:0] ref_x,expect_y;
 shell dut(clk,ld,x,got);
 always @(posedge clk) begin ref_ld<=ld;ref_x<=x;expect_y<=ref_y;end
 core gold(clk,ref_ld,ref_x,ref_y);
 integer c;
 initial begin
 for(c=0;c<160;c=c+1) begin
 @(negedge clk);ld=(c<3 || c%23==0);x=(c*31+7)%256;
 @(posedge clk);#1;
 if(c>5 && got !== expect_y) $fatal(1,"boot mismatch cycle%0d got%h expected%h",c,got,expect_y);
 end
 $display("PASS initialization lockstep154checks");$finish;
 end
 endmodule
'''
 (p/'tb.sv').write_text(tb)
 for mutant in [False,True]:
  (p/'shell.sv').write_text(shell.replace('.ld(ld__fq)',".ld(1'b0)") if mutant else shell)
  subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(src),str(p/'cell.sv'),str(p/'shell.sv'),str(p/'tb.sv')],check=True)
  r=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True)
  print(('MUTANT' if mutant else 'NORMAL'),r.returncode,r.stdout.strip())
  assert (r.returncode!=0)==mutant
 print('PASS init port retained; boot lockstep; tied-low initialization mutant caught; cycle delta0')
