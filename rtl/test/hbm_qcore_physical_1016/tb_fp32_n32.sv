`timescale 1ns/1ps
module tb_fp32_n32;
 parameter integer DUT_LAT=6;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,v=0;reg[31:0]a=0,b=0;wire[31:0]dy,ry;wire[1:0]de,re;wire dv,rv;
 ot_hdc_fp32_add_lat #(.LAT(6),.DRST(0)) gold(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(ry),.err(re),.valid_out(rv));
 ot_hdc_fp32_add_n32 #(.LAT(DUT_LAT),.DRST(0)) dut(.clk(clk),.rst_n(rst_n),.valid_in(v),.a(a),.b(b),.y(dy),.err(de),.valid_out(dv));
 integer checks=0,errors=0,valids=0,cyc,seed=1,dummy;
 always @(posedge clk)begin #1;checks=checks+1;valids=valids+rv;
  if({dy,de,dv}!=={ry,re,rv})begin errors=errors+1;if(errors<5)$display("FP32_N32 mismatch cyc=%0d y=%h/%h e=%h/%h v=%b/%b",cyc,dy,ry,de,re,dv,rv);end
 end
 initial begin
  dummy=$value$plusargs("seed=%d",seed);dummy=$urandom(seed);
  for(cyc=0;cyc<20030;cyc=cyc+1)begin
   @(negedge clk);rst_n=(cyc>3 && (cyc%509)>2);v=rst_n&&(($urandom%4)!=0);a=$urandom;b=$urandom;
   case(cyc%32)
    0:begin a=0;b=32'h80000000;end
    1:begin a=32'h7f800000;b=32'hff800000;end
    2:begin a=32'h7fc12345;b=32'h3f800000;end
    3:begin a=32'h7f7fffff;b=32'h7f7fffff;end
    4:begin a=1;b=32'h80000001;end
    5:begin a=32'h00800000;b=32'h807fffff;end
    6:begin a=32'h3f800000;b=32'hbf800000;end
    7:begin a=32'h3f800000;b=32'h33800000;end
   endcase
  end
  if(errors==0&&checks>=20000&&valids>1000)$display("FP32_N32 PASS checks=%0d valid=%0d seed=%0d",checks,valids,seed);
  else $display("FP32_N32 FAIL errors=%0d checks=%0d valid=%0d",errors,checks,valids);
  $finish;
 end
endmodule
