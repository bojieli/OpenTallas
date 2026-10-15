`timescale 1ns/1ps
module tb_hbm_attn_transpose_regs;
 reg clk=0;always #2 clk=~clk;reg rst_n=0,we=0,wh=0,rh=0;reg[7:0]wc=0,rc=0;reg[1:0]pad=0;reg[529:0]g=0;
 wire[575:0]a,b,unused;wire fault;integer mut=0,h,c,k,round_,checks=0;reg active=0;
 ot_hbm_attn_transpose_regs dut(.clk(clk),.rst_n(rst_n),.w_en_i(we),.w_half_i(wh),.w_cnt_i(wc),.w_pad_i(pad),.w_g(g),
 .r_half_i(rh),.r_c_i(rc),.sel_i(1'b0),.qk_ib(576'd0),.col(a),.eib(),.fault(fault));
 ot_hdc_v41x_attn_tr #(.TD(32),.DPT(16),.NL(2),.XOFF(0),.REPL(0))ref_(.clk(clk),.rst_n(rst_n),
 .w_en_i(we),.w_half_i(wh),.w_cnt_i(wc),.w_pad_i(pad),.w_g(g),.r_half_i(rh),.r_c_i(rc),.sel_i(1'b0),.qk_ib(576'd0),.col(b),.eib(unused));
 task automatic fillword(input integer n);
  for(integer l=0;l<2;l=l+1)begin
   for(integer j=0;j<33;j=j+1)g[l*265+j*8+:8]=8'(n*73+l*19+j*11);
   g[l*265+264]=1'((n+l)%2);
  end
 endtask
 always @(posedge clk)begin
  #1;
  if(active)begin
   if(fault)$fatal(1,"TRANSPOSE_REGS phase fault");
   if(a!==b)$fatal(1,"TRANSPOSE_REGS exactsource mismatch");
   checks++;
  end
 end
 initial begin
  void'($value$plusargs("MUT=%d",mut));repeat(5)@(negedge clk);rst_n=1;
  for(h=0;h<2;h=h+1)for(c=0;c<16;c=c+1)begin
   @(negedge clk);we=1;wh=1'(h);wc=8'(c);pad=2'(c%4);fillword(h*16+c);
  end
  @(negedge clk);we=0;active=1;
  for(round_=0;round_<4;round_=round_+1)begin
   for(h=0;h<2;h=h+1)for(c=0;c<16;c=c+1)begin
    @(negedge clk);rh=1'(h);rc=8'(c);
    if(round_>0)begin we=1;wh=1'(1-h);wc=8'(c);pad=2'(c%4);fillword(round_*100+h*16+c);end
    if(mut==1&&round_==0&&h==0&&c==0)force dut.g_row[0].g_half[0].g_dim[0].value=18'h3ffff;
    if(mut==2&&round_==0&&h==0&&c==0)begin we=1;wc=16;end
   end
  end
  @(negedge clk);we=0;
  $display("PASS TRANSPOSE_REGS exactTD32_DPT16_NL2 cells1024 bits18432 mixedFP8_FP4 padding doublehalfoverlap checks%0d",checks);$finish;
 end
endmodule
