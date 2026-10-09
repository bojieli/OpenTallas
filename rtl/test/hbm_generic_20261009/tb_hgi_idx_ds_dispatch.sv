`timescale 1ns/1ps
module tb_hgi_idx_ds_dispatch;
 parameter MUTANT=0;
 reg clk=0;always #.4166665 clk=~clk;
 reg rst_n=0,cv=0,iv=0,last=0;reg[3:0]unit_id=9;reg[5:0]op=3;reg[511:0]vals;
 wire cr,error,ready,ov,done,bv;wire[53:0]ids,bids;
 ot_hgi_idx_ds_dispatch #(.MUTANT_DROP_LAST(MUTANT)) dut(.clk(clk),.rst_n(rst_n),
 .cmd_valid(cv),.cmd_unit(unit_id),.cmd_op(op),.cmd_ready(cr),.error(error),
 .ds_in_valid(iv),.ds_in_vals(vals),.ds_in_last(last),.ds_in_ready(ready),
 .ds_out_valid(ov),.ds_out_ids(ids),.done(done));
 ot_gpu_router_topk refds(.clk(clk),.rst_n(rst_n),.in_valid(iv),.in_vals(vals),.in_last(last),.out_valid(bv),.out_ids(bids));
 integer b,j,t,cycle=0,outputs=0;
 always @(negedge clk)if(rst_n)begin
  cycle=cycle+1;
  if(ov!==bv||(ov&&ids!==bids))$fatal(1,"DS_LOCKSTEP mismatch cycle%0d refv%0d dutv%0d",cycle,bv,ov);
  if(ov)outputs=outputs+1;
 end
 initial begin
  repeat(3)@(negedge clk);rst_n=1;
  for(t=0;t<12;t=t+1)begin
   @(negedge clk);cv=1;@(negedge clk);cv=0;
   for(b=0;b<24;b=b+1)begin
    @(negedge clk);iv=1;last=b==23;
    for(j=0;j<16;j=j+1)vals[j*32+:32]=32'h3f800000+((b*16+j+t*71)%19);
    @(negedge clk);iv=0;last=0;
   end
   wait(bv);repeat(3)@(negedge clk);
  end
  if(outputs!=12)$fatal(1,"DS_LOCKSTEP outputs%0d",outputs);
  $display("PASS DS_LOCKSTEP 12 vectors N384 P16 K6 same-cycle sortedIDs unchanged native mechanism");$finish;
 end
 initial begin repeat(3000)@(posedge clk);$fatal(1,"DS_LOCKSTEP timeout");end
endmodule
