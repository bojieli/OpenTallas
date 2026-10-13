`timescale 1ns/1ps
module tb_vm_ck4;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,capture_i=0,check_i=0,write_i=1;
 reg [287:0] sample_i,expected_i;
 reg [255:0] owner_mask_i=0,padding_mask_i=0;
 wire [7:0] capture_regions_i=0,check_regions_i=0;
 wire error_o,valid_o;wire [287:0] repaired_o;
 vm_ck4 dut(.*);
 function [71:0] encode64(input [63:0] data);
  begin encode64={^{data[0],data[1],data[2],data[4],data[5],data[7],data[10],data[11],data[12],data[14],data[17],data[18],data[21],data[23],data[24],data[26],data[27],data[29],data[32],data[33],data[36],data[38],data[39],data[41],data[44],data[46],data[47],data[50],data[51],data[53],data[56],data[57],data[58],data[60],data[63]},data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}}; end
 endfunction
 function [65:0] decode64(input [71:0] code);
  reg [71:0] c; reg [6:0] s; reg ov,ue,cor;
  begin
   s={^{code[63],code[64],code[65],code[66],code[67],code[68],code[69],code[70]},^{code[31],code[32],code[33],code[34],code[35],code[36],code[37],code[38],code[39],code[40],code[41],code[42],code[43],code[44],code[45],code[46],code[47],code[48],code[49],code[50],code[51],code[52],code[53],code[54],code[55],code[56],code[57],code[58],code[59],code[60],code[61],code[62]},^{code[15],code[16],code[17],code[18],code[19],code[20],code[21],code[22],code[23],code[24],code[25],code[26],code[27],code[28],code[29],code[30],code[47],code[48],code[49],code[50],code[51],code[52],code[53],code[54],code[55],code[56],code[57],code[58],code[59],code[60],code[61],code[62]},^{code[7],code[8],code[9],code[10],code[11],code[12],code[13],code[14],code[23],code[24],code[25],code[26],code[27],code[28],code[29],code[30],code[39],code[40],code[41],code[42],code[43],code[44],code[45],code[46],code[55],code[56],code[57],code[58],code[59],code[60],code[61],code[62]},^{code[3],code[4],code[5],code[6],code[11],code[12],code[13],code[14],code[19],code[20],code[21],code[22],code[27],code[28],code[29],code[30],code[35],code[36],code[37],code[38],code[43],code[44],code[45],code[46],code[51],code[52],code[53],code[54],code[59],code[60],code[61],code[62],code[67],code[68],code[69],code[70]},^{code[1],code[2],code[5],code[6],code[9],code[10],code[13],code[14],code[17],code[18],code[21],code[22],code[25],code[26],code[29],code[30],code[33],code[34],code[37],code[38],code[41],code[42],code[45],code[46],code[49],code[50],code[53],code[54],code[57],code[58],code[61],code[62],code[65],code[66],code[69],code[70]},^{code[0],code[2],code[4],code[6],code[8],code[10],code[12],code[14],code[16],code[18],code[20],code[22],code[24],code[26],code[28],code[30],code[32],code[34],code[36],code[38],code[40],code[42],code[44],code[46],code[48],code[50],code[52],code[54],code[56],code[58],code[60],code[62],code[64],code[66],code[68],code[70]}}; ov=^code; ue=1'b0; cor=1'b0; c=code;
   if(s!=7'd0)begin
    if(ov&&s<=7'd71)begin c=code^(72'd1<<(s-7'd1)); cor=1'b1; end else ue=1'b1;
   end else if(ov)begin c[71]=~c[71]; cor=1'b1; end
   decode64={ue,cor,{c[70],c[69],c[68],c[67],c[66],c[65],c[64],c[62],c[61],c[60],c[59],c[58],c[57],c[56],c[55],c[54],c[53],c[52],c[51],c[50],c[49],c[48],c[47],c[46],c[45],c[44],c[43],c[42],c[41],c[40],c[39],c[38],c[37],c[36],c[35],c[34],c[33],c[32],c[30],c[29],c[28],c[27],c[26],c[25],c[24],c[23],c[22],c[21],c[20],c[19],c[18],c[17],c[16],c[14],c[13],c[12],c[11],c[10],c[9],c[8],c[6],c[5],c[4],c[2]}};
  end
 endfunction

 integer cases=0;reg [287:0] clean;reg [255:0] raw;
 reg [287:0] stream_expected[0:1];
 task run(input [287:0] sample,input bit want_error,input bit want_repair);
  begin
   @(negedge ck);sample_i=sample;capture_i=1;check_i=0;
   @(negedge ck);capture_i=0;check_i=1;
   @(negedge ck);check_i=0;cases=cases+1;
   if(!valid_o||error_o!==want_error)$fatal(1,"CK4 verdict case=%0d got=%b want=%b",cases,error_o,want_error);
   if(want_repair&&repaired_o!==clean)$fatal(1,"CK4 repair case=%0d",cases);
  end
 endtask
 initial begin
  sample_i=0;expected_i=0;
  repeat(3)@(negedge ck);rst_n=1;
  for(integer k=0;k<8;k=k+1)raw[k*32+:32]=$urandom;
  for(integer k=0;k<4;k=k+1)clean[k*72+:72]=encode64(raw[k*64+:64]);
  expected_i=clean;run(clean,0,1);
  for(integer w=0;w<4;w=w+1)begin
   for(integer b=0;b<72;b=b+1)run(clean^(288'd1<<(w*72+b)),0,1);
   for(integer a=0;a<72;a=a+1)for(integer b=a+1;b<72;b=b+1)
    run(clean^(288'd1<<(w*72+a))^(288'd1<<(w*72+b)),1,0);
  end
  // Exact identity masks across all 256 positions, including unaligned owner boundaries.
  write_i=0;
  for(integer b=0;b<256;b=b+1)begin
   owner_mask_i=256'd1<<b;
   expected_i=clean;expected_i[(b/64)*72+:72]=encode64(raw[(b/64)*64+:64]^(64'd1<<(b%64)));
   run(clean,1,1);
   owner_mask_i=0;run(clean,0,1);
  end
  expected_i=clean;write_i=1;
  for(integer b=0;b<256;b=b+1)begin
   padding_mask_i=256'd1<<b;run(clean,raw[b],1);
  end
  padding_mask_i=0;
  // Single-bit correction of expected seat must match the legacy decoder too.
  for(integer b=0;b<288;b=b+1)begin expected_i=clean^(288'd1<<b);run(clean,0,1);end
  for(integer w=0;w<4;w=w+1)
   for(integer a=0;a<72;a=a+1)for(integer b=a+1;b<72;b=b+1)begin
    expected_i=clean^(288'd1<<(w*72+a))^(288'd1<<(w*72+b));run(clean,1,1);
   end
  expected_i=clean;
  @(negedge ck);rst_n=0;@(negedge ck);rst_n=1;check_i=1;
  @(negedge ck);if(valid_o||!error_o)$fatal(1,"CK4 stale capture consumed after reset");
  // Native required checker throughput: one independently encoded/corrected row per cycle.
  write_i=1;owner_mask_i=0;padding_mask_i=0;check_i=0;
  for(integer n=0;n<2050;n=n+1)begin
   @(negedge ck);
   if(n>=2)begin
    if(!valid_o||error_o||repaired_o!==stream_expected[(n-2)%2])$fatal(1,"CK4 stream lost/mixed row=%0d",n-2);
   end
   capture_i=n<2048;check_i=n>0&&n<2049;
   if(n<2048)begin
    for(integer w=0;w<4;w=w+1)clean[w*72+:72]=encode64(64'(n+1)^(64'h12345678abcdef01<<(w+1)));
    expected_i=clean;sample_i=clean^(288'd1<<(n%288));stream_expected[n%2]=clean;
   end
  end
  $display("VM_CK4_STREAM PASS beats=2048 cycles=2050 initiation_interval=1");
  $display("VM_CK4 PASS cases=%0d single=576 sample_double=10224 expected_double=10224 identity=512 padding=256",cases);$finish;
 end
endmodule
