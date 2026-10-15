`timescale 1ns/1ps
module tb_hbm_su_static_data_store;
 parameter integer QUARTERS=4,BANKS_PER_QUARTER=128,MUT_COHERENCE=0;
 localparam B=QUARTERS*BANKS_PER_QUARTER,R=6;
 reg clk=0;always #5 clk=~clk;
 reg[B*R-1:0]rv=0;reg[B*R*9-1:0]ra=0;wire[B*R*32-1:0]rd;
 reg[B-1:0]wv=0;reg[B*9-1:0]wa=0;reg[B*32-1:0]wd=0;
 ot_hbm_su_static_data_store #(.QUARTERS(QUARTERS),.BANKS_PER_QUARTER(BANKS_PER_QUARTER),.MUT_COHERENCE(MUT_COHERENCE))d(
 .clk_macro({B*R{clk}}),.read_v(rv),.read_addr(ra),.read_data(rd),.write_v(wv),.write_addr(wa),.write_data(wd));
 integer b,r,c,a,checks=0,errors=0;
 function automatic[31:0]word(input integer row,input integer bank);
 word=32'((row<<10)+bank+1);endfunction
 task compare(input integer cycle,input integer updated);
  integer b,r,row;reg[31:0]expected;
  begin
   for(b=0;b<B;b=b+1)for(r=0;r<R;r=r+1)begin
    row=(cycle+17*r)%512;
    expected=updated!=0?32'hdead0000+32'(b):word(row,b);
    checks=checks+1;
    if(rd[(b*R+r)*32+:32]!==expected)begin
     if(errors<4)$display("ERR bank=%0d readclass=%0d row=%0d got=%h expected=%h",b,r,row,rd[(b*R+r)*32+:32],expected);
     errors=errors+1;
    end
   end
  end
 endtask
 initial begin
  @(negedge clk);wv='1;
  for(c=0;c<512;c=c+1)begin
   for(b=0;b<B;b=b+1)begin wa[b*9+:9]=9'(c);wd[b*32+:32]=word(c,b);end
   @(negedge clk);
  end
  wv=0;rv='1;
  for(c=0;c<512;c=c+1)begin
   for(b=0;b<B;b=b+1)for(r=0;r<R;r=r+1)ra[(b*R+r)*9+:9]=9'((c+17*r)%512);
   @(posedge clk);#1;compare(c,0);@(negedge clk);
  end
  // All six physical replicas must observe old data on a simultaneous read/write.
  for(b=0;b<B;b=b+1)begin
   wa[b*9+:9]=9'd511;wd[b*32+:32]=32'hdead0000+32'(b);
   for(r=0;r<R;r=r+1)ra[(b*R+r)*9+:9]=9'd511;
  end
  wv='1;@(posedge clk);#1;
  for(b=0;b<B;b=b+1)for(r=0;r<R;r=r+1)begin
   checks=checks+1;if(rd[(b*R+r)*32+:32]!==word(511,b))errors=errors+1;
  end
  @(negedge clk);wv=0;@(posedge clk);#1;compare(511,1);
  if(errors)$fatal(1,"SU_STATIC_STORE FAIL banks=%0d replicas=%0d checks=%0d errors=%0d",B,B*R,checks,errors);
  $display("SU_STATIC_STORE PASS quarters=%0d banks=%0d actual_SRAMs=%0d words_per_replica=%0d checks=%0d six_independent_read_rows_per_bank coherence prewrite_semantics",QUARTERS,B,B*R,B*512,checks);$finish;
 end
endmodule
