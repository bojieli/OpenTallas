`timescale 1ns/1ps
module tb_hist_banked;
parameter integer MUT=0;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clr=0,iv=0;reg[15:0]en=0;reg[127:0]dg=0;reg[3:0]gs=0;
reg clr1=0,iv1=0;reg[15:0]en1=0;reg[127:0]dg1=0;reg[3:0]gs1=0,gs2=0;
wire[239:0]goldsum,bsum;wire[175:0]goldbin,obin;wire goldbusy,busy;
reg[239:0]goldsum_q;reg[175:0]goldbin_q;reg oldbusy1=0,oldbusy2=0;
always@(posedge clk)begin clr1<=clr;iv1<=iv;en1<=en;dg1<=dg;gs1<=gs;gs2<=gs1;goldsum_q<=goldsum;goldbin_q<=goldbin;oldbusy1<=goldbusy;oldbusy2<=oldbusy1;end
ot_s81ph_hist256_gold_topk5 #(.W(16),.CB(11),.HPIPE(1))gold(.clk(clk),.rst_n(rst_n),.clr(clr1),.i_v(iv1),.i_en(en1),.i_dg(dg1),.gsel(gs2),.gsel_c({16{gs2}}),.gsum(goldsum),.gbin(goldbin),.busy(goldbusy));
ot_s81ph_native_sel_hist_banked #(.MUT(MUT))dut(.clk(clk),.rst_n(rst_n),.clr(clr),.i_v(iv),.i_en(en),.i_dg(dg),.gsel(gs),.gsum(bsum),.gbin(obin),.busy(busy));
integer cyc=0,checks=0,k; reg failed=0;reg[31:0] random=32'h12345678;
function automatic[31:0] rnd(input[31:0]x);reg[31:0]r;begin r=x^(x<<13);r=r^(r>>17);rnd=r^(r<<5);end endfunction
initial begin: scenario
 repeat(5)@(negedge clk);rst_n=1;
 for(cyc=0;cyc<1200 && !failed;cyc=cyc+1)begin
  @(negedge clk);
  if(cyc>40)begin
   checks=checks+1;
   if(bsum!==goldsum_q || obin!==goldbin_q || busy!==oldbusy2)begin
    $display("HIST_BANKED FAIL MUT=%0d cycle=%0d sums=%0b bin_values=%0b busy=%0b",MUT,cyc,bsum!==goldsum_q,obin!==goldbin_q,busy!==oldbusy2);failed=1;
   end
  end
  random=rnd(random);gs=random[3:0];
  clr=(cyc==0 || cyc==600 || cyc==601 || cyc==930);iv=(cyc<20)?1'b0:((cyc<500)?1'b1:random[4]);en=(cyc<500)?16'hffff:random[31:16];
  for(k=0;k<16;k=k+1)begin random=rnd(random);dg[8*k+:8]=(cyc<500)?8'h6d:random[7:0];end
 end
 if(failed) $fatal(1,"HIST_BANKED_REJECT MUT=%0d",MUT);
 else $display("HIST_BANKED PASS MUT=%0d checks=%0d",MUT,checks);$finish;
end
endmodule
