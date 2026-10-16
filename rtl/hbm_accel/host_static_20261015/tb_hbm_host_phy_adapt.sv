`timescale 1ns/1ps
// Bench: ot_hbm_host_phy_adapt framing (487-b endpoint word <-> 512-b UCIe beat, reserved lanes zero),
// 1-edge latency each way, reserved-lane check gated by link-live st[1], session pin flop. MUT 1/2 must FAIL.
module tb_hbm_host_phy_adapt;
parameter integer MUT=0;
reg clk=0,rst_n=0; always #1 clk=~clk;
integer errors=0,checks=0,i;
task chk(input c,input [8*64-1:0] w); begin checks=checks+1; if(!c) begin errors=errors+1; $display("FAIL %0s t=%0t",w,$time); end end endtask
reg [486:0] ep_tx=0; reg [511:0] phy_rx=0; reg [1:0] st=0; reg [23:0] sp=24'h5e551d;
wire [511:0] phy_tx; wire [486:0] ep_rx; wire [23:0] session; wire pad_fault,phy_fault;
ot_hbm_host_phy_adapt #(.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.ep_tx(ep_tx),.phy_tx(phy_tx),.phy_rx(phy_rx),.phy_st(st),.ep_rx(ep_rx),
 .session_pad(sp),.session(session),.pad_fault(pad_fault),.phy_fault(phy_fault));
reg [486:0] t_prev; reg [511:0] r_prev;
initial begin
 repeat(3) @(posedge clk); rst_n=1;
 for(i=0;i<200;i=i+1) begin
  @(negedge clk); t_prev=ep_tx; r_prev=phy_rx;
  ep_tx={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
  phy_rx={25'd0,ep_tx^487'h1234567}; if(i==50) phy_rx[500]=1'b1;   // reserved lane set while link not live: ignored
  @(posedge clk); #0.1;
  chk(phy_tx=={25'd0,ep_tx},"tx framed, reserved lanes zero, 1 edge");
  chk(ep_rx==phy_rx[486:0],"rx word, 1 edge");
 end
 chk(!pad_fault,"reserved lanes ignored before link live");
 chk(session==24'h5e551d,"session pin flop");
 @(negedge clk); st=2'b10; phy_rx[505]=1; repeat(4) @(posedge clk);
 chk(pad_fault,"reserved lane fault when link live");
 @(negedge clk); st=2'b11; repeat(3) @(posedge clk); chk(phy_fault,"rate-match fault");
 if(errors==0) $display("PASS host phy adapt checks=%0d",checks); else $display("FAIL errors=%0d checks=%0d",errors,checks);
 $finish;
end
endmodule
