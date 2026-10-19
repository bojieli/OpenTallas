module tb;
reg clk=0,re=0,we=0;reg[5:0]wa=0,ra=0;reg[287:0]wd=0;wire[511:0]rd;wire[319:0]sd;
integer t,j,mut=0,checks=0;reg[287:0]expectq=0;reg[287:0]mem[0:31];
wire[4:0]swa=(mut==1)?{1'b0,wa[3:0]}:wa[4:0];
wire[319:0]data={32'b0,((mut==2)?(wd & ~(288'b1<<287)):wd)};
ot_sram_1r1w_64x512_m1_r2c2 orig(.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(rd),.w_ce_in(we),.w_addr_in(wa),.wd_in({224'b0,wd}),.w_mask_in({512{1'b1}}),.rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(18'b0));
for(genvar b=0;b<5;b++)begin:s
hidx_storage_equation_32x64 u(.clk(clk),.r_ce_in(re||(mut==4)),.r_addr_in(ra[4:0]),.rd_out(sd[b*64+:64]),.w_ce_in(we),.w_addr_in(swa),.wd_in(data[b*64+:64]),.w_mask_in({64{1'b1}}));
end
wire[287:0]result=(mut==3&&re&&we&&ra==wa)?wd:sd[287:0];
task step;
begin
 if(re)expectq=mem[ra];
 if(we)mem[wa]=wd;
 #5;clk=1;#5;
 if(checks>0||re)begin
  if(rd[287:0]!==expectq)$fatal(1,"ORIGINAL_EXPECTATION_FAIL");
  if(result!==rd[287:0])$fatal(1,"PROJECTION_FAIL mutant=%0d cycle=%0d",mut,t);
  checks++;
 end
 clk=0;
end endtask
initial begin
 if($value$plusargs("mut=%d",mut))begin end
 for(j=0;j<32;j++)mem[j]=0;
 for(t=0;t<32;t++)begin we=1;wa=t;wd={288{1'b1}}^(288'(t)<<7);step();end
 we=0;re=1;ra=0;t=32;step();
 we=1;wa=0;wd=288'h123456;re=1;ra=0;t=33;step();
 we=0;re=0;ra=1;t=34;step();
 re=1;ra=0;t=35;step();
 for(t=36;t<2036;t++)begin
  re=$urandom_range(0,1);we=$urandom_range(0,1);wa=$urandom_range(0,31);ra=$urandom_range(0,7);
  for(j=0;j<9;j++)wd[j*32+:32]=$urandom;
  step();
 end
 $display("PASS actual original vs generated singleclock OLD low288 checks=%0d",checks);$finish;
end
endmodule
