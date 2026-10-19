`timescale 1ns/1ps
module tb_station_math;
 reg ck=0,rst=0,v=0;always #5 ck=~ck;
 reg[31:0] a=0,b=0;wire[31:0] ay,ag,my,mg;wire[1:0] ae,age,me,mge,arep;wire av,agv,mv,mgv;
 ot_hdc_fp32_add_lat #(.LAT(7),.DRST(0)) u_a(.clk(ck),.rst_n(rst),.valid_in(v),.a(a),.b(b),.y(ay),.err(ae),.valid_out(av));
 qfd_dv_station_add_g u_ag(.clk(ck),.rst_n(rst),.valid_in(v),.a(a),.b(b),.y(ag),.err(age),.valid_out(agv),.valid_rep(arep));
 ot_hdc_fp32_mul_lat #(.LAT(6),.DRST(0)) u_m(.clk(ck),.rst_n(rst),.valid_in(v),.a(a),.b(b),.y(my),.err(me),.valid_out(mv));
 qfd_dv_station_mul_g u_mg(.clk(ck),.rst_n(rst),.valid_in(v),.a(a),.b(b),.y(mg),.err(mge),.valid_out(mgv));
 reg[31:0] seed=32'h5e671899;integer cycle=0,age_since_reset=0,ap=0,mp=0;
 function automatic[31:0] step(input[31:0] x);reg[31:0] y;begin y=x^(x<<13);y=y^(y>>17);step=y^(y<<5);end endfunction
 function automatic[31:0] directed(input integer n);
  case(n%16)
   0:directed=0;1:directed=32'h80000000;2:directed=32'h00000001;3:directed=32'h007fffff;
   4:directed=32'h00800000;5:directed=32'h3f800000;6:directed=32'hbf800000;7:directed=32'h3f800001;
   8:directed=32'h7f7fffff;9:directed=32'hff7fffff;10:directed=32'h7f800000;11:directed=32'hff800000;
   12:directed=32'h7fc00001;13:directed=32'hffc00001;14:directed=32'h33800000;15:directed=32'hb3800000;
  endcase
 endfunction
 always @(negedge ck) begin
  rst=!(cycle<8||(cycle>=5000&&cycle<5008));v=rst&&age_since_reset>16&&cycle%7!=0;
  seed=step(seed);a=seed;seed=step(seed);b=seed;
  if(cycle%3==0) begin a=directed(cycle/3);b=directed(cycle/48);end
  if(cycle%11==0) b=a^32'h80000000;
  if(cycle%13==0) b=a;
 end
 always @(posedge ck) begin
  cycle=cycle+1;if(!rst)age_since_reset=0;else age_since_reset=age_since_reset+1;
  #1;
  if(age_since_reset>16) begin
   if({av,mv,arep}!={agv,mgv,{2{agv}}}) $fatal(1,"MATH_VALID_AGE_MISMATCH");
   if(av) begin if({ay,ae}!={ag,age}) $fatal(1,"ADD_BITS_MISMATCH cycle%0d",cycle);ap=ap+1;end
   if(mv) begin if({my,me}!={mg,mge}) $fatal(1,"MUL_BITS_MISMATCH cycle%0d",cycle);mp=mp+1;end
  end
  if(cycle==10000) begin $display("STATION_MATH_EQ PASS cycles10000 resets2 add%0d mul%0d fullwidth/directed/RNE/ties/zero/subnormal/Inf/NaN",ap,mp);$finish;end
 end
endmodule
