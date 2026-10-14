`timescale 1ns/1ps
module tb_hbm_norm_sum_node;
`ifndef NMUT
`define NMUT 0
`endif
 reg clk=0;always #1 clk=~clk;
 reg rst_n=0,go=0,lready=0,rready=0;reg[31:0]ld=0,rd=0;
 wire ready,pub,fault;wire[31:0]data;
 ot_hbm_norm_sum_node #(.MUT(`NMUT))dut(.clk(clk),.rst_n(rst_n),.go(go),.left_ready(lready),.right_ready(rready),.left_data(ld),.right_data(rd),.ready(ready),.published(pub),.fault(fault),.data(data));
 integer errors=0,checks=0,t,pubs=0;
 always @(negedge clk)if(pub)pubs=pubs+1;
 task automatic run(input[31:0]a,b,golden,input integer delay_right);
  integer p0;begin
   // GO must flush old held readiness before new independent child arrivals.
   @(negedge clk);go=1;@(negedge clk);go=0;lready=0;rready=0;
   repeat(4)@(negedge clk);ld=a;rd=b;lready=1;p0=pubs;
   repeat(delay_right)@(negedge clk);rready=1;t=0;
   while(!ready&&t<50)begin @(negedge clk);t=t+1;end
   if(!ready||fault||data!==golden)begin errors=errors+1;$display("ERR node expected %h got %h ready %0d fault %0d",golden,data,ready,fault);end
   // Source payload changes after issue must not alter the retained result.
   ld=32'h42f60000;rd=32'h3e800000;repeat(5)@(negedge clk);
   if(data!==golden||pubs-p0!=1)begin errors=errors+1;$display("ERR publication count or retained data");end
   checks=checks+1;
  end
 endtask
 task automatic abort_inflight;
  integer p0;begin
   @(negedge clk);go=1;lready=0;rready=0;@(negedge clk);go=0;
   repeat(10)@(negedge clk);ld=32'h3f800000;rd=32'h40000000;lready=1;rready=1;
   repeat(3)@(negedge clk);go=1;@(negedge clk);go=0;lready=0;rready=0;p0=pubs;
   // No result from the previous epoch may publish after a row clear.
   repeat(10)begin @(negedge clk);if(ready||pub)begin errors++;$display("ERR aborted node published stale sum");end end
   ld=32'h40e00000;rd=32'h41100000;lready=1;rready=1;t=0;
   while(!ready&&t<50)begin @(negedge clk);t++;end
   if(!ready||fault||data!==32'h41800000||pubs-p0!=1)begin errors++;$display("ERR node restart expected16 got %h pubs %0d",data,pubs-p0);end
   checks++;
  end
 endtask
 initial begin
  repeat(3)@(negedge clk);rst_n=1;repeat(6)@(negedge clk);
  run(32'h3fc00000,32'h40100000,32'h40700000,0);
  run(32'h3f800000,32'h3f800000,32'h40000000,5);
  run(32'h00000000,32'h40800000,32'h40800000,2);
  run(32'h3e800000,32'h3f000000,32'h3f400000,3);
  abort_inflight();
  $display("NORM_SUM_NODE cases=%0d errors=%0d",checks,errors);
  if(errors==0)$display("NORM_SUM_NODE PASS");else $display("NORM_SUM_NODE FAIL");
  $finish;
 end
endmodule
