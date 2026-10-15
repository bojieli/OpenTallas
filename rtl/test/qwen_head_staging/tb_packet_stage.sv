`timescale 1ns/1ps
module tb_packet_stage;
 parameter integer W=519,MUT=0;
 reg clk=0,rst_n=0;
 always #0.416667 clk=~clk;
 reg [W-1:0] d=0;
 wire [W-1:0] mid,qa,qb,oa,ob;
`ifdef QKH_PACKET_DUT
 `QKH_PACKET_DUT #(.MUT(MUT)) ingress(.clk(clk),.rst_n(rst_n),.d(d),.q(mid));
 localparam integer FORK_MUT=0;
`else
 ot_qkh_packet_pipe #(.W(W)) ingress(.clk(clk),.rst_n(rst_n),.d(d),.q(mid));
 localparam integer FORK_MUT=MUT;
`endif
 ot_qkh_packet_fork2 #(.W(W),.MUT(FORK_MUT)) fork_stage(.clk0(clk),.clk1(clk),.rst_n(rst_n),.d(mid),.q0(qa),.q1(qb));
 ot_qkh_packet_pipe #(.W(W)) leaf_a(.clk(clk),.rst_n(rst_n),.d(qa),.q(oa));
 ot_qkh_packet_pipe #(.W(W)) leaf_b(.clk(clk),.rst_n(rst_n),.d(qb),.q(ob));
 reg [W-1:0] hist0=0,hist1=0,hist2=0;
 integer n,b,age=0,checks=0,errors=0;
 task step(input integer seq);
 begin
   @(negedge clk);
   for(b=0;b<W;b=b+1) d[b]=(((seq+1)*(b+3))^(seq>>(b%13))^(b>>2))&1;
   @(posedge clk);
   if(!rst_n) begin age=0;hist0=0;hist1=0;hist2=0;end
   else begin age=age+1;hist2=hist1;hist1=hist0;hist0=d;end
   #0.001;
   if(age>=6) begin
     checks=checks+2*W;
     if(oa!==hist2) begin errors=errors+1;if(errors<4)$display("stage mismatch branch0 age=%0d",age);end
     if(ob!==hist2) begin errors=errors+1;if(errors<4)$display("stage mismatch branch1 age=%0d",age);end
   end
   if(age<4 && (mid!==0 || qa!==0 || qb!==0 || oa!==0 || ob!==0)) begin
     errors=errors+1;if(errors<4)$display("reset window mismatch age=%0d",age);
   end
 end endtask
 initial begin
   repeat(4) step(0);
   rst_n=1;
   for(n=0;n<2048;n=n+1) step(n);
   rst_n=0;
   repeat(4) step(0);
   rst_n=1;
   for(n=0;n<2048;n=n+1) step(n+5000);
   if(errors)$display("FAIL qkh_packet_stage W=%0d checks=%0d errors=%0d",W,checks,errors);
   else $display("PASS qkh_packet_stage W=%0d checks=%0d fixed_data_edges=3 reset_release_edges=3",W,checks);
   $finish;
 end
endmodule
