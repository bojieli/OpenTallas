`timescale 1ns/1ps
module tb_s81_hcx_projection_leaf;
 reg clk=0;always #5 clk=~clk;
 reg rn=0,sb=0,sv=0,cv=0,ffn=0;reg[6:0]a=0;reg[4095:0]d=0;wire ov,f;wire[31:0]od;
 reg[4095:0]x0[0:79],x1[0:79];reg[31:0]expectm[0:1],eps[0:0];
 reg[5:0]layer=0;integer layer_arg;string dir;integer cyc=0,t0,lat=-1,got=0,errors=0;
`ifdef MUT_BANK
 localparam integer MUT=1;
`else
 localparam integer MUT=0;
`endif
`ifdef MUT_PAGE
 localparam integer MPAGE=1;
`else
 localparam integer MPAGE=0;
`endif
 ot_s81_hcx_projection_leaf #(.MUT_BANK(MUT),.MUT_PAGE(MPAGE))u(.clk(clk),.rst_n(rn),.stage_begin(sb),.stage_v(sv),.stage_word(a),.stage_d(d),.cmd_v(cv),.cmd_ffn(ffn),.cmd_layer(layer),.norm_eps(eps[0]),.o_v(ov),.o_d(od),.fault(f));
 always @(posedge clk)cyc<=cyc+1;
 initial begin
  if($value$plusargs("LAYER=%d",layer_arg))layer=6'(layer_arg);
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
  $readmemh({dir,"/x0.mem"},x0);$readmemh({dir,"/x1.mem"},x1);$readmemh({dir,"/expected.mem"},expectm);$readmemh({dir,"/eps.mem"},eps);
  repeat(3)@(negedge clk);rn=1;
  for(integer b=0;b<2;b=b+1)begin
   sb=1;@(negedge clk);sb=0;
   for(integer i=0;i<80;i=i+1)begin sv=1;a=7'(i);d=b?x1[i]:x0[i];@(negedge clk);end
   sv=0;repeat(3)@(negedge clk);
   ffn=b;cv=1;t0=cyc;@(negedge clk);cv=0;
   while(!ov && cyc-t0<3000)@(negedge clk);
   if(!ov||f||od!==expectm[b])begin errors++;$display("HCX PROJ ERR block%0d expected%h got%h fault%0d",b,expectm[b],od,f);end
   if(lat<0)lat=cyc-t0;else if(cyc-t0!=lat)$fatal(1,"data dependent projection latency");
   $display("HCX PROJ block%0d result%h exact%0d native_cycles%0d",b,od,od===expectm[b],cyc-t0);
   repeat(4)@(negedge clk);
  end
  if(errors)$fatal(1,"HCX_PROJECTION FAIL errors%0d",errors);
  $display("HCX_PROJECTION PASS real20480BF16+2released20480FP32rows nativeROM/SRAM cycle%0d",lat);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
