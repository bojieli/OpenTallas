"""Exercise literal retained source fragments, including four-state enables."""
from pathlib import Path
import subprocess,re
import pytest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'rtl/hdc/ot_qwen_rom_tile_context_candidate_r3_retained.sv'

def test_defaultoff_names_and_actual_library_polarity():
 s=SOURCE.read_text()
 assert s.count('parameter integer ROM_REPLICA_CELL_RETENTION = 0')==2
 assert '.ROM_REPLICA_CELL_RETENTION(ROM_REPLICA_CELL_RETENTION)' in s
 assert s.count('(* keep = 1, dont_touch = 1 *) DFFASRHQNx1_ASAP7_75t_R')==2
 lib=(ROOT/'results/uarch/qwen_rom_bank5_control_20261002/fulltile_terminal_r1/inputs/18_asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib').read_text()
 cell=lib[lib.index('cell (DFFASRHQNx1_ASAP7_75t_R)'):lib.index('cell (DFFHQNx1_ASAP7_75t_R)')]
 for literal in ['next_state : "!D"','preset : "!RESETN"','clear : "!SETN"']:
  assert literal in cell

@pytest.mark.parametrize('include_z',[False,True])
@pytest.mark.parametrize('distribution',[0,1])
def test_literal_retained_fragments_fourstate(tmp_path,include_z,distribution):
 s=SOURCE.read_text()
 parts=s.split('if (ROM_REPLICA_CELL_RETENTION != 0) begin : g_retained')[1:]
 assert len(parts)==2
 read=parts[0].split('end else begin : g_inferred')[0]
 mask=parts[1].split('end else begin : g_inferred')[0]
 # Testbench primitive model follows the captured Liberty state equations;
 # it is test-only and never replaces physical library cells in synthesis.
 text='''module DFFASRHQNx1_ASAP7_75t_R(input CLK,D,RESETN,SETN,output reg QN);
 always @(posedge CLK or negedge RESETN or negedge SETN)
 if (!RESETN) QN<=1'b1; else if (!SETN) QN<=1'b0; else QN<=!D;
 endmodule
 module tb;
 localparam ROM_CONTROL_DISTRIBUTION=1,b=0,p=0,chunk=0;
 reg clk=0,bank_reset_n=0,mask_reset_n=0,wrom_re=0;
 reg [84:0] distributed_strobe_n=0;reg [79:0] distributed_hold_term=0;
 reg [4:0] code_rd_bank=0,code_sel_q=0;
 wire read_q,local_sel;
 generate begin:g_read
 '''+read+''' end begin:g_mask
 '''+mask+''' end endgenerate
 reg ref_read,ref_mask;
 always @(posedge clk or negedge bank_reset_n)
 if(!bank_reset_n) ref_read<=0;else ref_read<=wrom_re;
 always @(posedge clk or negedge mask_reset_n)
 if(!mask_reset_n) ref_mask<=0;
 else if(ROM_CONTROL_DISTRIBUTION != 0) begin
 if(!distributed_strobe_n[1]) ref_mask<=distributed_hold_term[0];
 end else if(code_rd_bank[0]) ref_mask<=code_sel_q[0];
 integer i,j,k;
 task tick;begin #1;clk=1;#1;
 if(read_q!==ref_read || local_sel!==ref_mask) $fatal(1,"literal mismatch");
 clk=0;#1;end endtask
 initial begin
 tick;bank_reset_n=1;mask_reset_n=1;
 for(i=0;i<4;i=i+1) for(j=0;j<4;j=j+1) for(k=0;k<4;k=k+1) begin
 case(i) 0:distributed_strobe_n[1]=0;1:distributed_strobe_n[1]=1;2:distributed_strobe_n[1]=1'bx;3:distributed_strobe_n[1]=1'bz;endcase
 case(j) 0:distributed_hold_term[0]=0;1:distributed_hold_term[0]=1;2:distributed_hold_term[0]=1'bx;3:distributed_hold_term[0]=1'bz;endcase
 case(k) 0:wrom_re=0;1:wrom_re=1;2:wrom_re=1'bx;3:wrom_re=1'bz;endcase
 code_rd_bank[0]=!distributed_strobe_n[1];code_sel_q[0]=distributed_hold_term[0];tick;
 end
 mask_reset_n=0;bank_reset_n=0;#1;
 if(read_q!==ref_read || local_sel!==ref_mask) $fatal(1,"asyncreset mismatch");
 tick;
 $display("PASS_LITERAL_RETAINED_CELL_FOURSTATE_64_COMBINATIONS");$finish;
 end endmodule'''
 text=text.replace('ROM_CONTROL_DISTRIBUTION=1',f'ROM_CONTROL_DISTRIBUTION={distribution}')
 if not include_z:text=text.replace('i<4','i<3').replace('j<4','j<3').replace('k<4','k<3').replace('64_COMBINATIONS','27_COMBINATIONS')
 f=tmp_path/'literal.sv';f.write_text(text)
 subprocess.run(['iverilog','-g2012','-s','tb','-o',str(tmp_path/'sim'),str(f)],check=True,capture_output=True)
 r=subprocess.run(['vvp',str(tmp_path/'sim')],capture_output=True,text=True)
 if include_z:
  # Physical inverted-Q FF cannot preserve a high-impedance stored value.
  # Keep this failed literal contract explicit; this candidate is unadopted.
  assert r.returncode!=0 and 'literal mismatch' in r.stdout
 else:
  assert r.returncode==0 and 'PASS_LITERAL_RETAINED_CELL_FOURSTATE' in r.stdout
