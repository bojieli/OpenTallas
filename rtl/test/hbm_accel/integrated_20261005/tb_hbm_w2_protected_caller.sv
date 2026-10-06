`timescale 1ns/1ps
// Actual caller output cut versus unchanged predecessor, using the four
// canonical R2 rows. This gate has root POR only; no parent warm claim.
module tb_hbm_w2_protected_caller;
 reg clk=0;always #0.416666666667 clk=~clk;
 reg por_n=0,cv=0,start=0;reg [7:0] row=0;reg [255:0] cy=0;
 wire [1:0] ready,rv,fault;wire [7:0] rr[0:1];wire [31:0] op[0:1];wire [255:0] data[0:1];
 reg [255:0] expected[0:3];integer counts[0:1];integer cycle=0;reg injected=0;
 wire negative=$test$plusargs("CALLER_DUE");
 for(genvar g=0;g<2;g=g+1)begin:caller
  ot_hbm_w2_existing_caller_result_cut #(.ENABLE(1),.PROTECTED_PARENT_BOUNDARY(g)) u_cut(
   .clk(clk),.rst_n(por_n),.producer_cv(cv),.producer_fault(1'b0),.producer_crow(row),.producer_cy(cy),
   .producer_busy(cv),.producer_arrive(1'b0),.producer_released(1'b0),
   .caller_start(start),.caller_sm_ready(1'b1),.caller_pair(1'b1),.caller_bound(1'b1),
   .caller_rows(9'd4),.caller_op_a(32'd0),.caller_op_b(32'd1),
   .ctx_ready(ready[g]),.rv(rv[g]),.rrow(rr[g]),.rop(op[g]),.rdata(data[g]),
   .busy(),.arrive(),.released(),.fault(fault[g]));
 end
 always @(posedge clk)if(por_n)begin
  cycle<=cycle+1;
  for(integer g=0;g<2;g=g+1)begin
   if(fault[g]&&!(g==1&&negative&&injected))$fatal(1,"caller protection/identity fault g=%0d",g);
   if(rv[g])begin
    if(counts[g]>=4||rr[g]!==8'(counts[g]%2)||op[g]!==32'(counts[g]/2)||data[g]!==expected[counts[g]])
     $fatal(1,"canonical caller row/data mismatch g=%0d count=%0d",g,counts[g]);
    counts[g]<=counts[g]+1;
   end
  end
 end
 reg [2047:0] gold;
 initial begin
  if(!$value$plusargs("GOLD=%s",gold))$fatal(1,"canonical gold required");
  $readmemh(gold,expected);counts[0]=0;counts[1]=0;
  repeat(3)@(negedge clk);por_n=1;
  wait(&ready);@(negedge clk);start=1;@(negedge clk);start=0;
  for(integer i=0;i<4;i=i+1)begin cv=1;row=8'(i);cy=expected[i];@(negedge clk);end
  cv=0;
  if($test$plusargs("CALLER_CE")||negative)begin
   caller[1].u_cut.protected_caller.u_protected.u_identity.code[0]=
    caller[1].u_cut.protected_caller.u_protected.u_identity.code[0]^(negative?72'h3:72'h1);
   injected=1;
   @(negedge clk);
   if(negative)begin
    repeat(12)begin @(negedge clk);
     if(!fault[1]||rv[1]||ready[1]||caller[1].u_cut.protected_caller.u_protected.cnt==0)
      $fatal(1,"caller DUE erased accepted identity or permission escaped");
    end
    $display("PASS_CALLER_DUE_ACCEPTED_IDENTITY_RETAINED");$finish;
   end else begin
    while(!caller[1].u_cut.protected_caller.u_protected.normal)begin
     if(fault[1]||rv[1]||ready[1])$fatal(1,"caller CE unchecked permission");
     @(negedge clk);
    end
    $display("PASS_CALLER_CE_REPAIR cycle=%0d",cycle);
   end
  end
  wait(counts[0]==4&&counts[1]==4);@(negedge clk);
  if(|fault)$fatal(1,"caller final fault");
  $display("PASS_PROTECTED_CALLER_CANONICAL rows=4 words=32 cycle=%0d",cycle);$finish;
 end
endmodule
