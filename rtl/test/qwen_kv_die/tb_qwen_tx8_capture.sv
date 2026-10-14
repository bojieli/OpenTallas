`timescale 1ns/1ps
module tb_qwen_tx8_capture;
 reg clk=0;reg [7:0] rst_n=0;reg [3119:0] d=0;
 wire [3119:0] grouped,original;
 ot_qwen_tile_tx8_capture u_group(clk,rst_n,d,grouped);
 genvar i;generate for(i=0;i<8;i=i+1)begin:g_ref
  ot_qwen_tile_tx u_orig(clk,rst_n[i],d[390*i+:390],original[390*i+:390]);
 end endgenerate
 integer n,l,b,edges=0,pauses=0,resets=0;
 task check;
 begin if(grouped!==original)$fatal(1,"TX8 differential mismatch cycle%0d",n);end endtask
 initial begin
  #1;rst_n=255;#1;rst_n=0;#1;check();rst_n=255;
  for(n=0;n<4096;n=n+1)begin
   for(l=0;l<8;l=l+1)begin
    for(b=0;b<390;b=b+1)d[390*l+b]=((n*73+l*17+b*3)>>(b%11))&1;
    // Distinct per-lane context/word patterns and independent valid resets.
    if((n+7*l)%29==0)begin rst_n[l]=0;resets=resets+1;end else rst_n[l]=1;
   end
   #1;check();
   if(n%13>=4)begin clk=1;edges=edges+1;end else pauses=pauses+1;
   #1;check();clk=0;#1;check();
  end
  $display("PASS TX8 grouped capture4096cycles edges%0d pauses%0d independentresets%0d full3120bitwordorder",edges,pauses,resets);$finish;
 end
endmodule
