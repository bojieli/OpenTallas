`timescale 1ns/1ps
module tb_svg_meta_delay7;
 parameter MUT=0,D=7;
 reg clk=0;always #5 clk=~clk;
 reg rst=0;reg[34:0]d=0;wire[34:0]q,q7;
 reg[34:0]gold[0:D-1];reg[34:0]lfsr=35'h51d031a5b;
 integer i,n,phase,errors=0,checks=0,async_checks=0;reg[7:0]reset_phases=0;
 ot_hbm_svg_meta_delay7 #(.MUT(MUT),.DELAY(D)) dut(.clk(clk),.rst_n(rst),.data_in(d),.data_out(q));
 meta_delay7_reference ref7(.clk(clk),.rst_n(rst),.data_in(d),.data_out(q7));
 always @(posedge clk or negedge rst)begin
  if(!rst)for(i=0;i<D;i=i+1)gold[i]=0;
  else begin for(i=D-1;i>0;i=i-1)gold[i]=gold[i-1];gold[0]=d;end
  #1;
  if(q!==gold[D-1])begin errors=errors+1;if(errors<4)$display("META_FAIL D=%0d q=%h gold=%h",D,q,gold[D-1]);end
  if(D==7&&q!==q7)begin errors=errors+1;if(errors<4)$display("META_DEFAULT_MITER_FAIL q=%h ref=%h",q,q7);end
  checks=checks+1;
 end
 initial begin
  if(D!=7&&D!=8)$fatal(1,"invalid test delay");
  repeat(3)@(negedge clk);
  for(phase=0;phase<8;phase=phase+1)begin
   rst=1;
   for(n=0;n<257+phase;n=n+1)begin
    lfsr={lfsr[33:0],lfsr[34]^lfsr[32]^lfsr[1]^lfsr[0]};d=lfsr;
    @(negedge clk);
   end
   reset_phases[dut.g_slice[0].u_slice.wp]=1;
   #2;rst=0;#1;
   if(q!==0)begin errors=errors+1;$display("META_ASYNC_FAIL D=%0d q=%h",D,q);end
   async_checks=async_checks+1;
   repeat(2)@(negedge clk);
  end
  if(reset_phases!==8'hff)$fatal(1,"missing reset phases mask=%h",reset_phases);
  if(errors)begin $display("META_FAIL D=%0d mut=%0d errors=%0d",D,MUT,errors);$fatal(1);end
  $display("META_PASS D=%0d checks=%0d async_checks=%0d occupied_reset_phases=%h",D,checks,async_checks,reset_phases);$finish;
 end
endmodule
