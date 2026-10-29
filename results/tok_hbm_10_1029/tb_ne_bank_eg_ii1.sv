`timescale 1ps/1ps
module tb;
reg clk=0; always #416.5 clk=~clk;
reg rst_n=0;
reg [561:0] wq=0;
reg wslot_v=0;
wire [275:0] eg;
wire [17:0] status;
integer nseen=0,consecutive=0,maxconsecutive=0,lastseen=-100,edge_n=0;
reg [255:0] lastdata=0;
ot_vms_bank_q0_faces_body #(.RG(5),.WG(2),.EG_WIDE(1)) dut(
.clk(clk),.rst_n(rst_n),.clk_n(clk),.clk_s(clk),.clk_e(clk),.clk_w(clk),
.clk_macro0(clk),.clk_macro1(clk),.clk_macro2(clk),.bid(3'd7),.sid(2'd2),
.rslot_v(1'b0),.rslot(3'd0),.wslot_v(wslot_v),.wslot(3'd0),.rq(85'd0),.rr(),
.wq(wq),.wq_done(),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
.xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(eg),.pq(285'd0),.pr(),.status(status));
always @(posedge clk) begin
 edge_n=edge_n+1;
 #10;
 if(eg[275])begin
  nseen=nseen+1;
  if(eg[263:8]!==256'(nseen))$fatal(1,"wrongpayload %d expected %d",eg[263:8],nseen);
  if(edge_n==lastseen+1)consecutive=consecutive+1;else consecutive=1;
  if(consecutive>maxconsecutive)maxconsecutive=consecutive;
  lastseen=edge_n;
 end
end
initial begin
 repeat(4)@(negedge clk);rst_n=1;
 repeat(8)@(negedge clk);
 for(integer i=1;i<=24;i=i+1)begin
  @(negedge clk);wslot_v=1;wq={281'd0,1'b1,16'h8007,256'(i),8'hff};
 end
 @(negedge clk);wslot_v=0;wq=0;
 repeat(24)@(negedge clk);
 if(nseen!=24||maxconsecutive!=24||status[17])$fatal(1,"seen%d consecutive%d status%h",nseen,maxconsecutive,status);
 $display("EG_II1_PASS seen=%0d consecutive=%0d status=%h; proposedII2cannotretainall24",nseen,maxconsecutive,status);
 $finish;
end
endmodule
