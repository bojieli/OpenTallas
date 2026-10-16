`timescale 1ns/1ps
module tb;
 reg ck=0,rs=1; reg [3:0] data=0;
 wire [3:0] result; wire reference;
 ot_s81_rly4 dut(ck,rs,data[0],data[1],data[2],data[3],result[0],result[1],result[2],result[3]);
 reg selected=0;
 dsfd_rly_1_EW ref_u(.ck(ck),.rs(rs),.i(selected),.o(reference));
 integer fi,fo,n,k,checks=0; reg [31:0] rng=32'h9234517b;
 task check;begin
  for(k=0;k<4;k=k+1) begin
   if(result[k] !== reference) begin $display("RLY4_MISMATCH facein=%0d faceout=%0d port=%0d n=%0d expected=%b got=%b",fi,fo,k,n,reference,result[k]);$fatal(1);end
   checks=checks+1;
  end
 end endtask
 initial begin
 for(fi=0;fi<4;fi=fi+1) for(fo=0;fo<4;fo=fo+1) begin
  ck=0;rs=1;data=0;selected=0;#1;rs=0;#1;check();rs=1;
  for(n=0;n<2000;n=n+1) begin
   rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
   data=0;selected=rng[0];data[fi]=selected;#1;check();
   ck=1;#1;check();
   if(n%127==49)begin rs=0;#1;check();rs=1;#1;check();end
   ck=0;#1;check();
  end
 end
 $display("RLY4_EXACT PASS 16 face pairs, checked_bits=%0d",checks);$finish;
 end
endmodule
