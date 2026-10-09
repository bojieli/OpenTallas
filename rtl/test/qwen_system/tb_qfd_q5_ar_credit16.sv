`timescale 1ns/1ps
module tb_qfd_q5_ar_credit16;
 parameter integer MUT_CREDIT=0;
 reg clk=0,hclk=0,rst=0,iv=0,pop=0;
 always #0.416666 clk=~clk;always #0.512 hclk=~hclk;
 reg [287:0] code;reg [16:0] sec;reg [7:0] row;
 wire lv,cf,hf,ef;wire [255:0] data;wire [16:0] os;wire [7:0] orow;wire [2:0] cr;
 ot_qfd_stream4_cdc_ecc_pc #(.ENABLE(1),.MARGIN(1),.RSEL(1),.RNG(10),.LCRED(MUT_CREDIT?6:16)) dut(
  .clk(clk),.c_arst_n(rst),.l_v(lv),.l_sec(os),.l_row(orow),.l_data(data),.l_pop(pop),
  .w_v(1'b0),.w_sec(24'b0),.w_data(256'b0),.w_tag(9'b0),.w_room(),.wd_v(),.wd_tag(),.c_fault(cf),
  .hclk(hclk),.h_arst_n(rst),.h_lv(iv),.h_lsec(sec),.h_lrow(row),.h_lcode(code),.h_cred(cr),
  .h_wv(),.h_wsec(),.h_hand(1'b0),.h_wcon(1'b0),.h_cv(),.h_csec(),.h_cdata(),.h_ctag(),
  .h_av(1'b0),.h_atag(9'b0),.h_fault(hf),.h_ecc_fault(ef),.h_ce_count());
 function automatic [71:0] enc64(input [63:0] d);
  reg [71:0] c;integer p,j,k;
  begin c=0;j=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin c[p-1]=d[j];j=j+1;end
   for(k=0;k<7;k=k+1)for(p=1;p<=71;p=p+1)if((p&(1<<k))!=0&&p!=(1<<k))c[(1<<k)-1]=c[(1<<k)-1]^c[p-1];
   c[71]=^c[70:0];enc64=c;
  end
 endfunction
 function automatic [255:0] payload(input integer n);
  for(integer w=0;w<8;w=w+1)payload[w*32+:32]=32'h9abcdef0^(n*7919+w*277);
 endfunction
 function automatic [287:0] encode(input [255:0] d);
  for(integer w=0;w<4;w=w+1)encode[w*72+:72]=enc64(d[w*64+:64]);
 endfunction
 integer seen=0,credits=0;
 always @(negedge clk)if(rst&&lv)begin
  if(data!==payload(seen)||os!==17'(seen+32)||orow!==8'(seen)||cf||hf||ef)$fatal(1,"AR creditburst payload/metadata/order failure index=%0d",seen);
  seen=seen+1;
 end
 always @(negedge hclk)if(rst)credits=credits+cr;
 integer n,t;
 initial begin
  repeat(4)@(negedge hclk);rst=1;repeat(20)@(negedge hclk);
  for(n=0;n<17;n=n+1)begin @(negedge hclk);iv=1;code=encode(payload(n));sec=17'(n+32);row=8'(n);end
  @(negedge hclk);iv=0;
  // All16reserved destination slots must accept before ANY retirement.
  repeat(80)@(negedge clk);
  if(seen!=16)$fatal(1,"AR landing requested16credits but delivered%0d before retirement (legacy6-credit mutant)",seen);
  repeat(20)@(negedge clk);if(seen!=16)$fatal(1,"AR landing exceeded16reserved slots");
  @(negedge clk);pop=1;@(negedge clk);pop=0;
  repeat(20)@(negedge clk);if(seen!=17)$fatal(1,"actual one retired credit did not admit queued17th word");
  if(cf||hf||ef)$fatal(1,"AR native credit contract fault");
  $display("Q5_AR_CREDIT16_PASS MARGIN1_RSEL1_RNG10=1 no_retirement_before16=1 seventeenth_waits_actual_pop=1 payload_metadata_order=1");$finish;
 end
endmodule
