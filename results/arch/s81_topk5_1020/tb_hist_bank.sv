`timescale 1ns/1ps
module tb_hist_bank;
parameter integer MUT=0;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,clr=0,iv=0;
reg[15:0] en=0; reg[127:0] dg=0; reg[3:0] gs=0,gd=0;
wire[239:0] goldsum,bsum; wire[175:0] goldbin; wire goldbusy;
wire[8*176-1:0] bin_values;wire[7:0] busy;reg oldbusy;
always@(posedge clk)begin gd<=gs;oldbusy<=goldbusy;end
ot_s81ph_hist256_gold_topk5 #(.W(16),.CB(11),.HPIPE(1)) gold(
.clk(clk),.rst_n(rst_n),.clr(clr),.i_v(iv),.i_en(en),.i_dg(dg),.gsel(gd),.gsel_c({16{gd}}),.gsum(goldsum),.gbin(goldbin),.busy(goldbusy));
genvar b;
generate for(b=0;b<8;b=b+1)begin:leaf
 wire c=(MUT==2 && b==3)?1'b0:clr;
 wire[3:0] s=(MUT==1 && b==3)?(gs^4'b0001):gs;
 ot_s81ph_native_sel_hist_bank #(.W(16),.CB(11),.BANK(b)) u(
 .clk(clk),.rst_n(rst_n),.clr(c),.i_v(iv),.i_en(en),.i_dg(dg),.gsel(s),
 .gsum(bsum[30*b+:30]),.gbin(bin_values[176*b+:176]),.busy(busy[b]));
end endgenerate
reg[175:0] joined;integer k;
always@*begin joined=0;for(integer q=0;q<8;q=q+1)joined=joined|bin_values[176*q+:176];end
integer cyc=0,checks=0; reg failed=0;reg[31:0] random=32'h12345678;
function automatic[31:0] rnd(input[31:0]x);reg[31:0]r;begin r=x^(x<<13);r=r^(r>>17);rnd=r^(r<<5);end endfunction
initial begin: scenario
 repeat(5)@(negedge clk);rst_n=1;
 for(cyc=0;cyc<1200 && !failed;cyc=cyc+1)begin
  @(negedge clk);
  if(cyc>40)begin
   checks=checks+1;
   if(bsum!==goldsum || joined!==goldbin || busy!=={8{oldbusy}})begin
    $display("HIST_BANK FAIL MUT=%0d cycle=%0d sums=%0b bin_values=%0b busy=%0b",MUT,cyc,bsum!==goldsum,joined!==goldbin,busy!=={8{oldbusy}});failed=1;
   end
  end
  random=rnd(random);gs=random[3:0];
  clr=(cyc==0 || cyc==600 || cyc==601 || cyc==930);iv=(cyc<20)?1'b0:((cyc<500)?1'b1:random[4]);en=(cyc<500)?16'hffff:random[31:16];
  for(k=0;k<16;k=k+1)begin random=rnd(random);dg[8*k+:8]=(cyc<500)?8'h6d:random[7:0];end
 end
 if(failed) $fatal(1,"HIST_BANK_REJECT MUT=%0d",MUT);
 else $display("HIST_BANK PASS MUT=%0d checks=%0d",MUT,checks);$finish;
end
endmodule
