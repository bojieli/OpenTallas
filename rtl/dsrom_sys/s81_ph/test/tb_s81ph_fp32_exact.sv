`timescale 1ns/1ps
module tb_s81ph_fp32_exact;
 reg clk=0,rst_n=0,v=0;reg[31:0] a=0,b=0;
 always #0.5 clk=~clk;
 wire[31:0] y;wire[1:0] err;wire vo;
 `ifdef S81PH_FP32_PREEXP
 ot_s81ph_fp32_add_rne_preexp #(
`else
 ot_fp32_add_rne_deep #(
`endif
.SPLIT(7),.KS(1)) dut(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(y),.err(err),.valid_out(vo));
 reg[7:0] vh=0;reg[33:0] expected[0:7];reg[31:0] ey=0;integer ee=0;
 integer i,checked=0,fd,rc,iv,phase,nvalid;
 reg[31:0] ia,ib,iy;integer ie;reg[4095:0] vectors;
 always @(posedge clk) begin
  if(!rst_n) vh<=0;
  else begin
   vh<={vh[6:0],v};expected[0]<={ee[1:0],ey};
   for(i=1;i<8;i=i+1) expected[i]<=expected[i-1];
  end
  #0.01;
  if(rst_n) begin
   if(vo!==vh[7]) $fatal(1,"FP32 exact8-edge valid mismatch checked=%0d",checked);
   if(vo) begin
    if({err,y}!==expected[7]) $fatal(1,"FP32 independent reference mismatch checked=%0d got=%08x err=%0d expected=%08x err=%0d",checked,y,err,expected[7][31:0],expected[7][33:32]);
    checked=checked+1;
   end
  end
 end
 initial begin
  if(!$value$plusargs("VECTORS=%s",vectors)||!$value$plusargs("NVALID=%d",nvalid)) $fatal(1,"Missing exactreference inputs");
  fd=$fopen(vectors,"r");if(!fd)$fatal(1,"Cannot open vectors");
  repeat(3)@(negedge clk);rst_n=1;
  while(!$feof(fd)) begin
   rc=$fscanf(fd,"%d %h %h %h %d\n",iv,ia,ib,iy,ie);
   if(rc==5) begin @(negedge clk);v=iv;a=ia;b=ib;ey=iy;ee=ie;end
  end
  $fclose(fd);@(negedge clk);v=0;repeat(10)@(negedge clk);
  for(phase=0;phase<6;phase=phase+1) begin
   #(0.07+0.02*phase);rst_n=0;#0.05;
   if(vo!==0||y!==0||err!==0)$fatal(1,"FP32 short reset phase%0d failed",phase);
   rst_n=1;@(negedge clk);a=32'h3f800000;b=32'h33800000;ey=32'h3f800000;ee=0;v=1;
   @(negedge clk);v=0;repeat(10)@(negedge clk);
  end
  if(checked!=nvalid+6)$fatal(1,"FP32 vector count %0d expected%0d",checked,nvalid+6);
  $display("FP32_EXACT_GATE PASS checked=%0d latency_edges=8 short_reset_phases=6 KS=1 SPLIT=7",checked);
  $finish;
 end
endmodule
