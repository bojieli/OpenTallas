`timescale 1ns/1ps
`ifndef MUT
`define MUT 0
`endif
module tb_credit_sram(input wire clk);
 localparam integer W=553,NS=(W+15)/16;
 reg rst_n=0, lv=0,ready=0; reg [W-1:0] data=0; reg [31:0] seed=32'h81c01155;
 wire [1:0] av,bv,ac,bc,af,bf; wire [W-1:0] ad[0:1],bd[0:1];
 genvar k;generate for(k=0;k<2;k=k+1) begin:g
  ot_link_credit_rx #(.W(W),.DEPTH(8),.WFREE(k+1)) a(.clk(clk),.rst_n(rst_n),
   .l_valid(lv),.l_data(data),.l_credit(ac[k]),.o_valid(av[k]),.o_ready(ready),.o_data(ad[k]),.fault(af[k]));
  ot_link_credit_rx_sram #(.W(W),.DEPTH(8),.WFREE(k+1),.MUT(`MUT)) b(.clk(clk),.rst_n(rst_n),.head_rst_n({NS{rst_n}}),
   .l_valid(lv),.l_data(data),.l_credit(bc[k]),.o_valid(bv[k]),.o_ready(ready),.o_data(bd[k]),.fault(bf[k]));
 end endgenerate
 integer c=0,err=0,ncheck=0,takes=0,fulls=0,b,j;
 always @(negedge clk) begin
  if(c>2) begin
   for(j=0;j<2;j=j+1) begin
    ncheck=ncheck+1;
    if(av[j]!==bv[j] || ac[j]!==bc[j] || af[j]!==bf[j] || (av[j] && ad[j]!==bd[j])) begin
     err=err+1;if(err<8)$display("CREDIT_EQ_ERR cycle%0d WFREE%0d valid%0b/%0b credit%0b/%0b fault%0b/%0b",c,j+1,av[j],bv[j],ac[j],bc[j],af[j],bf[j]);
    end
   end
   if(av[0]&&ready)takes=takes+1;
   if(af[0])fulls=fulls+1;
  end
  c=c+1;
  seed=seed^(seed<<13);seed=seed^(seed>>17);seed=seed^(seed<<5);
  rst_n=!(c<6 || (c>=3000 && c<3008));
  if(c<70) begin lv=1;ready=0;end
  else if(c<140) begin lv=1;ready=1;end
  else if(c<210) begin lv=0;ready=1;end
  else begin lv=seed[0]|seed[2];ready=seed[4]|seed[5];end
  for(b=0;b<W;b=b+1)data[b]=seed[(b+c)%32]^((b/32+c)&1);
  if(c==10000) begin
   if(err==0 && takes>1000 && fulls>0)$display("CREDIT_SRAM_EQ PASS checks=%0d takes=%0d fault_cycles=%0d MUT=%0d",ncheck,takes,fulls,`MUT);
   else $display("CREDIT_SRAM_EQ FAIL errors=%0d takes=%0d MUT=%0d",err,takes,`MUT);
   $finish;
  end
 end
endmodule
