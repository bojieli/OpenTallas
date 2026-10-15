`timescale 1ns/1ps
// Controller protocol/two-clock calendar only. Real HCP arithmetic is gated
// separately in tb_s81_hcx_projection_leaf; these timed producers are not a
// whole-HC or token correctness claim.
module tb_s81_hcx_controller #(parameter integer FAST=0);
 reg ck=1,sk=1;always #3 ck=~ck;always #4 sk=~sk;
 reg rn=0;reg[84:0]cmd=0;wire[8:0]done;wire[1:0]st;
 wire[7:0]rv;wire[111:0]ra;wire sb,sv,cv,ffn;wire[6:0]sw;wire rawv;wire[191:0]rawd;
 reg[3:0]rdue=0;reg[263:0]due=0;
`ifdef MUT_LEAF
 wire[5:0]lv={6{due[263]}}&6'b111110;
`else
 wire[5:0]lv={6{due[263]}};
`endif
 reg[191:0]ld;integer fc=0,sc=0,t0,rawcount=0;
 ot_s81_hcx_controller #(.RL(4),.FAST_CYC(FAST))u(.cck(ck),.crst_n(rn),.sk(sk),.srst_n(rn),.c_cmd(cmd),.c_done(done),.c_st(st),.rq_v(rv),.rq_row(ra),.rs_v({8{rdue[3]}}),.stage_begin(sb),.stage_v(sv),.stage_word(sw),.leaf_cmd_v(cv),.leaf_ffn(ffn),.leaf_v(lv),.leaf_fault(6'd0),.leaf_d(ld),.t_raw_v(rawv),.t_raw_d(rawd));
 always @(posedge ck)fc<=fc+1;
 always @(posedge sk)begin
  sc<=sc+1;rdue<={rdue[2:0],rv[0]};due<={due[262:0],cv};
  if(cv)for(integer l=0;l<6;l=l+1)ld[32*l+:32]<=32'h10000000+32'(l)+32'(ffn*16);
  if(rawv)begin
   rawcount<=rawcount+1;
   for(integer l=0;l<6;l=l+1)if(rawd[32*l+:32]!==32'h10000000+32'(l)+32'(ffn*16))$fatal(1,"join corruption");
  end
 end
 initial begin:run
  #25;rn=1;
  for(integer job=0;job<(FAST==0?1:3);job=job+1)begin
   @(negedge ck);while(u.phase!=2)@(negedge ck);
   cmd=0;cmd[84]=1;cmd[6:0]=7'(job);cmd[7]=job[0];t0=fc;
   @(negedge ck);cmd=0;
   if(FAST==0)begin
    while(u.esync2==u.eseen && fc-t0<1000)@(negedge ck);
    $display("HCX_CONTROLLER_CALIBRATE FAST_CYC=%0d",u.ctick+2);$finish;disable run;
   end
   while(!done[8] && fc-t0<1000)@(negedge ck);
   if(!done[8]||done[7:0]!==8'(job)||fc-t0!=FAST+1)$fatal(1,"fixed fast completion mismatch fast%0d elapsed%0d tag%0d",FAST,fc-t0,done[7:0]);
   repeat(4)@(negedge ck);if(st!==2'b10)$fatal(1,"calendar fault status%0b cfault%0d sfault%0d",st,u.cfault,u.sfault);
   $display("HCX_CONTROLLER job%0d fixed_fast_cycles%0d",job,fc-t0-4);
  end
  if(rawcount!=3)$fatal(1,"wrong native join count");
  $display("HCX_CONTROLLER PASS twoactualrelatedclocks,threephase2commands,compiledjoins/completions,nocredits");$finish;
 end
 initial begin #50000;$fatal(1,"timeout");end
endmodule
