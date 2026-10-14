`timescale 1ns/1ps
module tb_hgi_sfu_lane_map #(parameter integer MUT=0);
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0; reg [3:0] j,ls,lvw;
 reg [479:0] terms; reg [23:0] ov,iv,row;
 reg emit; reg [460:0] pass;
 wire [1199:0] ldc;wire [23:0] mo,mi,mr;wire [3:0] mls,mlvw;wire me;wire [460:0] mp;
 ot_hgi_sfu_lane_map #(.MUT_LANE(MUT)) dut(.clk(clk),.rst_n(rst_n),.lane_j(j),.ld_terms(terms),
  .i_o_v(ov),.i_i_v(iv),.i_krow(row),.i_ls(ls),.i_lvw(lvw),.i_emit(emit),.i_pass(pass),
  .o_ld_c(ldc),.o_o_v(mo),.o_i_v(mi),.o_krow(mr),.o_ls(mls),.o_lvw(mlvw),.o_emit(me),.o_pass(mp));
 reg [23:0] eo[0:3],ei[0:3],er[0:3];reg ee[0:3];reg [460:0] ep[0:3];reg [599:0] offsets[0:3];
 integer checks=0,errors=0;
 initial begin
  j=0;ls=0;lvw=0;terms=0;ov=0;iv=0;row=0;emit=0;pass=0;
  repeat(8) @(negedge clk);rst_n=1;
  for(integer n=0;n<4096;n=n+1) begin
   @(negedge clk);
   j=4'(n);ls=4'(n>>4);lvw=4'(n>>8);ov=$urandom;iv=$urandom;row=$urandom;emit=$urandom;
   for(integer k=0;k<20;k=k+1)terms[k*24+:24]=$urandom;
   for(integer k=0;k<15;k=k+1)pass[k*30+:30]=30'($urandom);pass[460:450]=11'($urandom);
   for(integer q=3;q>0;q=q-1) begin eo[q]=eo[q-1];ei[q]=ei[q-1];er[q]=er[q-1];ee[q]=ee[q-1];ep[q]=ep[q-1];offsets[q]=offsets[q-1];end
   // Reference observable fields of the frozen source instantiated at desired j.
   eo[0]=ov+(24'(j)>>ls);ei[0]=iv+(24'(j)&((24'd1<<ls)-1));er[0]=row+(24'(j)>>ls);
   ee[0]=emit && (24'(j)<(24'd1<<lvw));ep[0]=pass;
   for(integer s=0;s<5;s=s+1) begin
    offsets[0][s*120+:120]=0;
    for(integer k=0;k<4;k=k+1)if(j[k])offsets[0][s*120+:24]+=terms[(s*4+k)*24+:24];
   end
   @(posedge clk);#1;
   if(n>=4) begin
    checks++;
    if(24'(mo+(24'd5>>mls))!==eo[3] || 24'(mi+(24'd5&((24'd1<<mls)-1)))!==ei[3] ||
       24'(mr+(24'd5>>mls))!==er[3] || (me && (24'd5<(24'd1<<mlvw)))!==ee[3] || mp!==ep[3])errors++;
    for(integer s=0;s<5;s=s+1)if(24'(ldc[s*240+:24]+ldc[s*240+48+:24])!==offsets[3][s*120+:24])errors++;
   end
  end
  // Prime every retained ring slot, then warm-reset. Payload may survive,
  // but the load strobe (pass[460]) must never replay a pre-reset operation.
  @(negedge clk);pass='0;pass[460]=1;emit=1;
  repeat(12) @(negedge clk);
  rst_n=0;pass='0;emit=0;
  repeat(8) @(negedge clk);
  rst_n=1;
  repeat(4) begin
   @(posedge clk);#1;checks++;
   if(mp[460]!==0 || me!==0) begin
    errors++;$display("SFU_WARM_RESET stale load=%b emit=%b",mp[460],me);
   end
   @(negedge clk);
  end
  if(errors)begin $display("SFU_LANE_MAP FAIL checks=%0d errors=%0d",checks,errors);$fatal(1,"fixed-lane mapping mismatch");end
  $display("SFU_LANE_MAP PASS checks=%0d errors=0",checks);$finish;
 end
endmodule
