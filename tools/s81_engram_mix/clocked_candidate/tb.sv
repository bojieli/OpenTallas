`timescale 1ns/1ps
module tb #(parameter MUT=0);
 reg clk=0;always #1 clk=~clk;
 reg rn=0;reg [5:0] v=0;reg [130:0] data=0;
 integer cy=0,checked=0,errors=0;
 genvar d;
 generate for(d=0;d<=5;d=d+1)begin:g
  localparam N=(d>0)?d:1;
  wire [N-1:0] ck={N{clk}} & ((MUT && d==5)?{{(N-1){1'b1}},1'b0}:{N{1'b1}});
  wire [5:0] va,vb;wire [130:0] da,db;
  ot_s81_engram_vrly #(.D(d),.WV(6),.WD(131)) ref_u(clk,rn,v,data,va,da);
  ot_s81_engram_vrly_clocked #(.D(d),.WV(6),.WD(131)) dut(ck,rn,v,data,vb,db);
  always @(negedge clk)if(cy>10)begin checked=checked+1;if(va!==vb||da!==db)errors=errors+1;end
 end endgenerate
 initial begin
  for(cy=0;cy<8192;cy=cy+1)begin
   @(negedge clk);rn=(cy%487)>4;v=(cy*23)^cy;data={32'(cy*7),32'(~cy),32'(cy^32'hdeaf),32'(cy*123),3'(cy)};
  end
  @(posedge clk);#0.1;
  if(errors)$fatal(1,"CLOCKED_RELAY_FAIL checked=%0d errors=%0d mutant=%0d",checked,errors,MUT);
  $display("CLOCKED_RELAY_PASS checked=%0d depths=6 cycles=8192 resets=17",checked);$finish;
 end
endmodule
