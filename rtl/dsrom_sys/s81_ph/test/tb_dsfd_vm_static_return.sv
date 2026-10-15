`timescale 1ns/1ps
module tb_dsfd_vm_static_return;
 reg ck=0;always #2 ck=~ck;reg rn=0;
 reg [31:0] iv=0;reg [255:0] it=0;reg [4095:0] id=0;
 reg rv=0;reg [3:0] rg=0;reg [15:0] rm=0;
 wire [15:0] ov;wire [2047:0] od;wire [3:0] og;wire fault;
 dsfd_vm_static_return u(.ck(ck),.rst_n(rn),.i_v(iv),.i_tag(it),.i_data(id),
 .release_v(rv),.release_group(rg),.release_mask(rm),.o_v(ov),.o_data(od),.o_group(og),.fault(fault));
 integer bad=0,checks=0;
 function automatic[127:0] value(input integer g,input integer s);
 value={32'(g),32'(s),32'hfedcba98,32'(g*127+s*773)};
 endfunction
 initial begin
  #9;rn=1;repeat(4)@(negedge ck);
  for(integer g=0;g<64;g=g+2)begin
   // Two groups' first halves on one bank-return edge, second halves next.
   @(negedge ck);iv=32'h00ff00ff;
   for(integer s=0;s<8;s=s+1)begin
    it[8*s+:8]={4'(g),4'(s)};id[128*s+:128]=value(g,s);
    it[8*(16+s)+:8]={4'(g+1),4'(s)};id[128*(16+s)+:128]=value(g+1,s);
   end
   @(negedge ck);iv=32'hff00ff00;
   for(integer s=0;s<8;s=s+1)begin
    it[8*(8+s)+:8]={4'(g),4'(s+8)};id[128*(8+s)+:128]=value(g,s+8);
    it[8*(24+s)+:8]={4'(g+1),4'(s+8)};id[128*(24+s)+:128]=value(g+1,s+8);
   end
   @(negedge ck);iv=0;rv=1;rg=g;rm=16'hffff;
   @(posedge ck);#0.1;
   if(ov!=16'hffff || og!=4'(g) || fault)bad=bad+1;
   for(integer s=0;s<16;s=s+1)if(od[128*s+:128]!=value(g,s))bad=bad+1;
   checks=checks+1;
   @(negedge ck);rg=g+1;
   @(posedge ck);#0.1;
   if(ov!=16'hffff || og!=4'(g+1) || fault)bad=bad+1;
   for(integer s=0;s<16;s=s+1)if(od[128*s+:128]!=value(g+1,s))bad=bad+1;
   checks=checks+1;@(negedge ck);rv=0;
  end
  // Missing data is a checked failure at the exact scheduled edge, never a wait.
  @(negedge ck);rv=1;rg=4'h7;rm=16'hffff;
  @(posedge ck);#0.1;if(!fault || ov!=0)bad=bad+1;
  $display("RESULT groups%0d bad%0d checked_missing_fault%0d",checks,bad,fault);
  if(bad==0)$display("PASS");else $display("FAIL");$finish;
 end
endmodule
