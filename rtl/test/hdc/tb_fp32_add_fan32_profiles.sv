`timescale 1ns/1ps
module tb_fp32_add_fan32_profiles;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,valid_in=0;reg[31:0]a=0,b=0;
 integer cyc=0,errors=0,checked=0;reg[31:0]rng=32'h51f0a32;
 function automatic[31:0]step(input[31:0]x);reg[31:0]z;begin z=x^(x<<13);z=z^(z>>17);step=z^(z<<5);end endfunction
 genvar k;generate for(k=0;k<33;k=k+1)begin:g_cfg
  localparam integer MASK=k/2;
  localparam integer L=k==32?7:3+((MASK>>0)&1)+((MASK>>1)&1)+((MASK>>2)&1)+((MASK>>3)&1);
  localparam integer R=k==32?0:k%2;
  localparam integer CUT=k==32?-1:MASK;
  wire[31:0]yg,yd;wire[1:0]eg,ed;wire vg,vd;
  ot_hdc_fp32_add_lat #(.LAT(L),.DRST(R),.CUTS(CUT)) gold(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yg),.err(eg),.valid_out(vg));
  if(k==32)begin:g_native
   ot_hdc_fp32_add_lat_fan32 #(.LAT(L),.DRST(R),.CUTS(CUT),.SAFE_DIST(1)) dut(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yd),.err(ed),.valid_out(vd));
  end else begin:g_default
   ot_hdc_fp32_add_lat_fan32 #(.LAT(L),.DRST(R),.CUTS(CUT)) dut(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),.a(a),.b(b),.y(yd),.err(ed),.valid_out(vd));
  end
  always @(negedge clk)if(cyc>1)begin
   if(vg!==vd || ((vg||vd)&&({yg,eg}!=={yd,ed})))begin $display("PROFILE_MISMATCH cycle=%0d cfg=%0d LAT=%0d DRST=%0d CUTS=%0d",cyc,k,L,R,CUT);errors=errors+1;end
   checked=checked+1;
  end
 end endgenerate
 initial begin
  repeat(3000)begin
   @(posedge clk);#1;cyc=cyc+1;rst_n=(cyc>3&&(cyc%311)!=0&&(cyc%311)!=1);
   rng=step(rng);a=rng;rng=step(rng);b=rng;valid_in=(rng[3:0]!=0);
   case(cyc%13)
    0:a=32'h00000000;1:a=32'h80000000;2:a=32'h7f800000;3:a=32'h7fc00001;4:a=32'h00000001;
    5:begin a=32'h7f7fffff;b=a;end 6:b=a^32'h80000000;7:begin a=32'h00800000;b=32'h807fffff;end
   endcase
  end
  @(negedge clk);#1;if(errors)$fatal(1,"FAN32_PROFILES_FAIL errors=%0d",errors);
  $display("FAN32_PROFILES_PASS checks=%0d released32+native1 no-warm firstvalid/inflightreset",checked);$finish;
 end
endmodule
