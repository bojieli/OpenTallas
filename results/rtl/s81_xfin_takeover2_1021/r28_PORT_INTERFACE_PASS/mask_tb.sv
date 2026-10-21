`timescale 1ns/1ps
(* keep_hierarchy=1 *) module mask_old #(parameter integer LO=0)(input wire signed[11:0] power,output wire[7:0] mr,ms);
 wire signed[11:0] sub=-(power+12'sd149);
 wire[5:0] sh=(sub>12'sd63)?6'd63:sub[5:0];
 for(genvar g=0;g<8;g=g+1)begin:g_b
  assign mr[g]=({6'd0,6'(LO+g)}=={6'd0,sh}-12'd1);
  assign ms[g]=({6'd0,6'(LO+g)}<{6'd0,sh}-12'd1);
 end
endmodule
(* keep_hierarchy=1 *) module mask_new #(parameter integer LO=0)(input wire[11:0] power,output wire[7:0] mr,ms);
 wire[11:0] sub=-($signed(power)+12'sd149);
 wire[5:0] sh=($signed(sub)>12'sd63)?6'd63:sub[5:0];
 for(genvar g=0;g<8;g=g+1)begin:g_b
  assign mr[g]=({6'd0,6'(LO+g)}=={6'd0,sh}-12'd1);
  assign ms[g]=({6'd0,6'(LO+g)}<{6'd0,sh}-12'd1);
 end
endmodule
module mask_tb;
reg [11:0] power;wire [47:0] oround,osticky,nround,nsticky;
for(genvar g=0;g<6;g=g+1)begin:g_mask
 mask_old #(.LO(8*g)) u_old(power,oround[g*8+:8],osticky[g*8+:8]);
 mask_new #(.LO(8*g)) u_new(power,nround[g*8+:8],nsticky[g*8+:8]);
end
integer bad=0;
initial begin
 for(integer p=0;p<4096;p=p+1)begin
  power=12'(p); #1;
  if({oround,osticky} !== {nround,nsticky})begin bad=bad+1; $display("BAD p=%d",p);end
 end
 $display("MASK_EXHAUSTIVE powers=4096 groups=6 comparisons=24576 bad=%0d",bad);
 if(bad) $fatal(1,"MASK_MISMATCH");$finish;
end
endmodule
