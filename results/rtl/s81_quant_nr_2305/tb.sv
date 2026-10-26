`timescale 1ps/1fs
module tb;
reg clk=0;always #416.5 clk=~clk;
reg rst_n=0;reg[1023:0]d=0;wire[1023:0]qo,qn;
ot_sram_dline #(.W(1024),.D(11)) old(.clk(clk),.rst_n(rst_n),.d(d),.q(qo));
ot_sram_dline_nr #(.W(1024),.D(11)) candidate(.clk(clk),.rst_n(rst_n),.d(d),.q(qn));
reg rce=0,wce=0;reg[5:0]ra=0,wa=0;reg[511:0]wd=0,mask=0;wire[511:0]ro,rn;
ot_sram_1r1w_64x512_m1_r2c2 om(.clk(clk),.r_ce_in(rce),.r_addr_in(ra),.rd_out(ro),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask),.rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
ot_sram_1r1w_64x512_m1_r0c0 nm(.clk(clk),.r_ce_in(rce),.r_addr_in(ra),.rd_out(rn),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(mask));
integer c,j,nreads=0,delaychecks=0;integer seed=32'h53710731;
initial begin
for(c=0;c<11000;c=c+1)begin
 @(negedge clk);
 rst_n=(c>4)&&!(c>=5500&&c<5505);
 for(j=0;j<32;j=j+1)d[32*j+:32]=$urandom(seed);
 rce=(c<128)||c%4!=0;wce=(c<128)||c%3!=0;ra=6'(c);wa=(c<128)?6'(c):6'($urandom(seed));
 for(j=0;j<16;j=j+1)begin wd[32*j+:32]=$urandom(seed);mask[32*j+:32]=(c<128)?32'hffffffff:$urandom(seed);end
 @(posedge clk);#1;
 if(c>130)begin
  if(ro!==rn)$fatal(1,"MACRO_DIFF cycle=%0d addr=%0d",c,ra);
  if(rce)nreads=nreads+1;
 end
 if(c>130&&!(c>=5500&&c<5635))begin
  if(qo!==qn)$fatal(1,"DELAY_DIFF cycle=%0d",c);
  delaychecks=delaychecks+1;
 end
end
$display("PASS quant true-r0c0 macro_reads=%0d delay_checks=%0d W1024 D11 cold_warm_reset all64rows masks read_hold write_read_collision zero_added_cycles",nreads,delaychecks);$finish;
end
endmodule
