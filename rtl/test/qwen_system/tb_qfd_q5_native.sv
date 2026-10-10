`timescale 1ns/1ps
module tb_qfd_q5_native;
 parameter integer MUT=0,INTERLEAVED=1;
 import ot_gpu_w6_secded_pkg::*;
 reg clk=0,hclk=0,rst=0;
 always #0.416666 clk=~clk;
 always #0.512 hclk=~hclk;
 reg iv=0,pop=0;reg [287:0] code=0;reg [16:0] sec=0;reg [7:0] row=0;
 wire lv,cf,hf,ef;wire [255:0] data;wire [16:0] os;wire [7:0] orow;wire [2:0] cr;wire [31:0] ces;
 reg [255:0] golden;
 ot_qfd_stream4_cdc_ecc_pc #(.ENABLE(1),.INTERLEAVED(INTERLEAVED)) dut(
  .clk(clk),.c_arst_n(rst),.l_v(lv),.l_sec(os),.l_row(orow),.l_data(data),.l_pop(pop),
  .w_v(1'b0),.w_sec(24'b0),.w_data(256'b0),.w_tag(9'b0),.w_room(),.wd_v(),.wd_tag(),.c_fault(cf),
  .hclk(hclk),.h_arst_n(rst),.h_lv(iv),.h_lsec(sec),.h_lrow(row),.h_lcode(code),.h_cred(cr),
  .h_wv(),.h_wsec(),.h_hand(1'b0),.h_wcon(1'b0),.h_cv(),.h_csec(),.h_cdata(),.h_ctag(),
  .h_av(1'b0),.h_atag(9'b0),.h_fault(hf),.h_ecc_fault(ef),.h_ce_count(ces));
 // MUT replacement is exercised on the real producer correction gate itself.
 wire mv;wire [255:0] md;
 ot_qfd_kv_landing_ecc #(.ENABLE(1),.MUT(MUT),.INTERLEAVED(INTERLEAVED)) mutant(
  .hclk(hclk),.h_rst_n(rst),.i_v(iv),.i_code(code),.i_sec(sec),.i_row(row),
  .o_v(mv),.o_data(md),.o_sec(),.o_row(),.ce(),.ue(),.fault(),.ce_count());
 function automatic [287:0] enc(input [255:0] x);
  integer w,p,j,k;reg [71:0] c;begin enc=0;
   for(w=0;w<4;w=w+1)begin
    c=encode64(x[w*64+:64]);
    if(INTERLEAVED)enc[w*72+:72]=c;
    else begin j=0;k=0;for(p=1;p<=71;p=p+1)
     if((p&(p-1))!=0)begin enc[w*64+j]=c[p-1];j=j+1;end
     else begin enc[256+w*8+k]=c[p-1];k=k+1;end
     enc[256+w*8+7]=c[71];
    end
   end
  end
 endfunction
 integer credits=0,t,seen=0,accepted=0;
 always @(posedge hclk)if(rst)credits<=credits+cr;else credits<=0;
 task automatic send(input [287:0] x,input integer id);
  begin
   @(negedge hclk);iv=1;code=x;sec=17'(id+31);row=8'(id);
   @(negedge hclk);iv=0;
   if(!mv||md!==golden)$fatal(1,"correction mutant/data failure id=%0d",id);
   t=0;while(!lv&&t<80)begin @(negedge clk);t=t+1;end
   if(!lv||data!==golden||os!==17'(id+31)||orow!==8'(id)||cf||hf)$fatal(1,"native metadata/data/valid failure %0d",id);
   repeat(5)begin @(negedge clk);if(data!==golden||os!==17'(id+31)||!lv)$fatal(1,"hold unstable");end
   pop=1;@(negedge clk);pop=0;accepted=accepted+1;
   repeat(12)@(negedge hclk);
   if(credits!=accepted)$fatal(1,"credit retired=%0d accepted=%0d",credits,accepted);
  end
 endtask
 integer i,w;reg [287:0] good,bad;
 initial begin
  repeat(4)@(negedge hclk);rst=1;repeat(20)@(negedge hclk);
  for(w=0;w<8;w=w+1)golden[w*32+:32]=32'habc87654^(w*32'h1337);
  good=enc(golden);send(good,0);
  for(i=0;i<288;i=i+1)send(good^(288'b1<<i),i+1);
  if(ces!=288)$fatal(1,"CE counter %0d",ces);
  bad=good^(288'b1<<0)^(288'b1<<1);
  @(negedge hclk);iv=1;code=bad;sec=91;row=73;
  @(negedge hclk);iv=0;repeat(30)@(negedge hclk);
  if(!ef||!hf||!cf||lv||credits!=accepted)$fatal(1,"UE released/credit leak");
  @(negedge hclk);iv=1;code=good;
  @(negedge hclk);iv=0;repeat(30)@(negedge hclk);
  if(lv||credits!=accepted)$fatal(1,"post-UE silent continuation");
  $display("Q5_NATIVE_PASS layout=%0d exact=%0d corrected=%0d UE_quarantined=1 stall_hold=1 credits=%0d",INTERLEAVED,accepted,ces,credits);
  $finish;
 end
endmodule
