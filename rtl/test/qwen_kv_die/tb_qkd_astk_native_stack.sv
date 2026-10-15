`timescale 1ns/1ps
module tb_qkd_astk_native_stack;
 parameter integer STATIC=0,EXP_AGE=500,LMAX_AGE=350,Z_AGE=900,Z_STRIDE=16,READ_MUT=0,FAULT_MUT=0;
 integer score_mut=0,am_delay=0,inject_fault=0;
 initial begin
  if($value$plusargs("SCORE_MUT=%d",score_mut))begin end
  if($value$plusargs("AM_DELAY=%d",am_delay))begin end
  if($value$plusargs("FAULT_MUT=%d",inject_fault))begin end
 end
 function automatic [31:0] score_word(input integer eng,addr,head);
  // Distinct positive finite FP32 live-in scores below2^-30; exp rounds1.
  score_word=32'h30000000 | (eng<<12) | (addr<<2) | head;
 endfunction
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg [539:0] aq=0;reg [35:0] am=0;
 reg [3399:0] so=0;wire [5071:0] si;
 wire [562:0] ap;wire af;wire [20:0] lt;
 reg er_v=0;reg [10:0] er_addr=0;wire erv;wire [10:0] era;wire [63:0] erd;
 wire [15:0] commits;wire score_commit;
 qkd_astk_native_stack_s #(.STATIC_SCHEDULE(STATIC),.EXP_START_AGE(EXP_AGE),.LMAX_START_AGE(LMAX_AGE),.Z_START_AGE(Z_AGE),.Z_STRIDE(Z_STRIDE)) u(
 .ck_c(ck),.ck_z({4{ck}}),.ck_x({32{ck}}),.ck_e({8{ck}}),.ck_r(ck),.rst_n(rst_n),.st(2'd0),
 .aq(aq),.am(am),.ap(ap),.af(af),.lt(lt),.er_v(er_v),.er_addr(er_addr),.er_rsp_v(erv),.er_rsp_addr(era),.er_data(erd),
 .exp_committed(commits),.score_committed(score_commit),
 .so0(so[0+:425]),.si0(si[0+:634]),
 .so1(so[425+:425]),.si1(si[634+:634]),
 .so2(so[850+:425]),.si2(si[1268+:634]),
 .so3(so[1275+:425]),.si3(si[1902+:634]),
 .so4(so[1700+:425]),.si4(si[2536+:634]),
 .so5(so[2125+:425]),.si5(si[3170+:634]),
 .so6(so[2550+:425]),.si6(si[3804+:634]),
 .so7(so[2975+:425]),.si7(si[4438+:634]));
 reg observed_af=0;
 integer cycle=0,errors=0,lmax_words=0,z_words=0,z_done=0,reads=0;
 always @(negedge ck)if(rst_n)begin
  cycle=cycle+1;
  observed_af=observed_af|af;
  if(ap[0] && cycle>120)begin
   if(ap[3] || !ap[10])begin errors=errors+1;$display("FAIL sideband group/any");end
   case(ap[2:1])
   0:begin
    if(ap[42:11]!==0 || ap[5:4]!==2'(lmax_words))begin errors=errors+1;$display("FAIL lmax");end
    if(lmax_words==0)$display("TRACE LMAX cycle=%0d ctl_age=%0d",cycle,u.u_ctl.u.schedule_age);
    lmax_words=lmax_words+1;
   end
   1:begin
    if(ap[42:11]!==32'h43000000 || ap[9:6]!==4'(z_words/4) || ap[5:4]!==2'(z_words%4))begin errors=errors+1;if(errors<6)$display("FAIL Z word=%0d got=%h k=%0d h=%0d",z_words,ap[42:11],ap[9:6],ap[5:4]);end
    if(z_words==0)$display("TRACE Z cycle=%0d ctl_age=%0d",cycle,u.u_ctl.u.schedule_age);
    z_words=z_words+1;
   end
   2:z_done=z_done+1;
   default:begin errors=errors+1;$display("FAIL sidebandtype");end
   endcase
  end
  if(ap[43])begin errors=errors+1;$display("FAIL legacy PV emitted");end
  if(erv)begin
   if(era!==11'(reads) || erd!==64'h3f803f803f803f80)begin errors=errors+1;if(errors<6)$display("FAIL actualEXP e=%0d addr=%0d got=%h",reads,era,erd);end
   reads=reads+1;
  end
 end
 genvar e;
 integer score_checks=0;
 generate for(e=0;e<8;e=e+1)begin:g_trace
  integer seen=0,h,addr;
  always @(negedge ck)if(rst_n&&u.g_ep[e].u_ep.xa[0])begin
   addr=((seen%16)<<4)|(seen/16);
   for(h=0;h<4;h=h+1)begin
    if(u.g_ep[e].u_ep.xa[66*h+2+:32]!==score_word(e,addr,h))begin
     errors=errors+1;if(errors<6)$display("FAIL actualscore e=%0d n=%0d h=%0d got=%h",e,seen,h,u.g_ep[e].u_ep.xa[66*h+2+:32]);
    end
    score_checks=score_checks+1;
   end
   seen=seen+1;
  end
  always @(posedge ck)if(rst_n&&u.g_ep[e].u_ep.trig)$display("TRACE EP%0d trigger_cycle=%0d local_age=%0d",e,cycle,u.g_ep[e].u_ep.schedule_age+1);
 end endgenerate
 integer t,i,h;
 initial begin
  repeat(6)@(negedge ck);rst_n=1;repeat(10)@(negedge ck);
  aq[14:1]=8192;aq[0]=1;@(negedge ck);aq[0]=0;
  // Diagnostic live-in uses actual8score SRAM ports, one write/engine/edge.
  // Tiny distinct scores and zero hub maxima give actualEXP1 and each Z block128.
  for(t=0;t<3500;t=t+1)begin
   for(i=0;i<8;i=i+1)begin
    so[425*i+:425]=0;so[425*i+410]=1;
    if((FAULT_MUT||inject_fault) && t==1200 && i==0)so[425*i+424]=1;
    if(t>=40 && t<296)begin so[425*i+13]=1;so[425*i+14+:12]={1'b0,8'((t-40)^score_mut),3'(i)};
     for(h=0;h<4;h=h+1)so[425*i+26+32*h+:32]=score_word(i,t-40,h);end
   end
   am=0;
   if(t>=360+am_delay&&t<364+am_delay)am={32'd0,2'(t-360-am_delay),1'b0,1'b1};
   er_v=(t>=1300&&t<3348);er_addr=11'(t-1300)^11'(READ_MUT);
   @(negedge ck);
  end
  er_v=0;
  if(observed_af!==1'(FAULT_MUT||inject_fault)||score_checks!=8192||lmax_words!=4||z_words!=64||z_done!=1||reads!=2048||commits!==16'hffff)begin errors=errors+1;$display("FAIL counts af=%b lm=%0d z=%0d done=%0d reads=%0d commits=%h",af,lmax_words,z_words,z_done,reads,commits);end
  if(errors==0)$display("PASS mapped_astk static=%0d actual_EP8_EX32_ZN4 roots46 native_er2048 scorewords8192 lmax4 Z64 nolegacyPV",STATIC);
  else $display("FAIL mapped_astk errors=%0d",errors);
  $finish;
 end
endmodule
