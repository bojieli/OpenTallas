`timescale 1ns/1ps
module tb_ctl;
 parameter integer MUT=0;
 reg clk=0,rst=0;always #1 clk=~clk;
 reg[11:0]d=0;always @(negedge clk)d<=$urandom;
 wire[1199:0]q;wire[11:0]refq;wire rc;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) r0(.clk(clk),.rst_n_in(rst),.rst_n(rc));
 ot_hdc_delay #(.W(12),.D(4),.RESET(1)) refdut(.clk(clk),.rst_n(rc),.d(d),.q(refq));
 ot_qkh_ctl_tree4 #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst),.d(d),.q(q));
 integer errors=0,checks=0,i;
 always @(posedge clk)begin #0.1;checks=checks+1;if($time>4 && q!=={100{refq}})errors=errors+1;end
 initial begin
 #0.3;rst=1;#0.2;rst=0;
 for(i=0;i<200;i=i+1)begin #5.7;rst=1;#31.3;rst=0;#0.1;if(q!=={100{refq}})errors=errors+1;end
 #10;
 if(errors==0)$display("CTL_TREE4 PASS checks=%0d mut=%0d",checks,MUT);
 else begin $display("CTL_TREE4 FAIL errors=%0d checks=%0d mut=%0d",errors,checks,MUT);$fatal;end
 $finish;
 end
endmodule
