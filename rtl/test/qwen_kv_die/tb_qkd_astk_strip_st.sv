`timescale 1ns/1ps
// KVE-2-ASTK 2026-10-17: exact lockstep of the credit-free, lane-free static ASTK strip (qkd_astk_strip_st + its leaves
// qkd_astk_ep_s / _ex_s / _ctl_s) against the selected static composition qkd_astk_native_stack_cal (old leaves
// qkd_astk_ep_cal / qkd_astk_ex / qkd_astk_ctl_tp8_cal with every lane and credit input tied to 0).  The same e-read
// service splices both so / si buses.  Every edge compares: the engine si bus (8 x 633 b; the old si[633] must stay 0),
// the hub sideband ap (the old ap's P.V fields must stay 0), lt, the e-read responses and the strip fault.
// Phase 1 is tb_qkd_astk_native_stack's functional stimulus (T 8192, 8,192 score words, M, 2,048 e reads) with its checks
// on the new strip; phase 2 restarts with T 600 under random so / am / reads (lockstep only).
// Mutants: +define+KVD_STMUT=1 (ep_s), 2 (ex_s), 3 (ctl_s) must FAIL.
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
module tb_qkd_astk_strip_st;
 // Z_AGE 1000 (was 900, copied from tb_qkd_astk_native_stack): on the cal composition (RL relays) the Z block sums of k 0..5 land
 // after their 900-age slots (Z words 0 + slot fault); 1000 is the first legal calendar with margin (k 6.. were exact at 900).
 localparam integer EXP_AGE=500, LMAX_AGE=350, Z_AGE=1000, Z_STRIDE=16;
 function automatic [31:0] score_word(input integer eng,addr,head);
  score_word=32'h30000000 | (eng<<12) | (addr<<2) | head;
 endfunction
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg [539:0] aq=0;reg [35:0] am=0;reg [47:0] cal={16'(EXP_AGE),16'(Z_AGE),16'(LMAX_AGE)};
 reg [3399:0] so=0;
 reg er_v=0;reg [10:0] er_addr=0;
 // ---- A: the selected composition (old leaves) ------------------------------------------------------------------------
 wire [5071:0] si_a;wire [562:0] ap_a;wire af_a;wire [20:0] lt_a;wire erv_a;wire [10:0] era_a;wire [63:0] erd_a;
 wire [15:0] com_a;wire scom_a;
 qkd_astk_native_stack_cal #(.STATIC_SCHEDULE(1),.Z_STRIDE(Z_STRIDE)) ua(.cal(cal),
  .ck_c(ck),.ck_z({4{ck}}),.ck_x({32{ck}}),.ck_e({8{ck}}),.ck_r(ck),.rst_n(rst_n),.st(2'd0),
  .aq(aq),.am(am),.ap(ap_a),.af(af_a),.lt(lt_a),.er_v(er_v),.er_addr(er_addr),.er_rsp_v(erv_a),.er_rsp_addr(era_a),.er_data(erd_a),
  .exp_committed(com_a),.score_committed(scom_a),
  .so0(so[0+:425]),.so1(so[425+:425]),.so2(so[850+:425]),.so3(so[1275+:425]),
  .so4(so[1700+:425]),.so5(so[2125+:425]),.so6(so[2550+:425]),.so7(so[2975+:425]),
  .si0(si_a[0+:634]),.si1(si_a[634+:634]),.si2(si_a[1268+:634]),.si3(si_a[1902+:634]),
  .si4(si_a[2536+:634]),.si5(si_a[3170+:634]),.si6(si_a[3804+:634]),.si7(si_a[4438+:634]));
 // ---- B: the e-read service on the bus of the new strip -------------------------------------------------------------
 wire [3399:0] aso_b;wire [5071:0] asi_b,si_b;wire [633*8-1:0] ssi_b;wire [413*8-1:0] sso_b;
 wire [42:0] ap_b;wire af_b,erf_b;wire [20:0] lt_b;wire erv_b;wire [10:0] era_b;wire [63:0] erd_b;
 qkd_astk_native_er_service ub_er(.ck(ck),.rst_n(rst_n),.read_v(er_v),.read_addr(er_addr),.engine_so(so),.astk_so(aso_b),
  .astk_si(asi_b),.engine_si(si_b),.response_v(erv_b),.response_addr(era_b),.response_data(erd_b),.fault(erf_b));
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_bus
  assign sso_b[413*g+:413]={aso_b[425*g+424],aso_b[425*g+:412]};
  assign asi_b[634*g+:634]={1'b0,ssi_b[633*g+:633]};   // bench adapter only: the old service's 634-b lane
 end endgenerate
 qkd_astk_strip_st #(.RL(1),.Z_STRIDE(Z_STRIDE)) ub(.ck_c(ck),.ck_z({4{ck}}),.ck_x({32{ck}}),.ck_e({8{ck}}),.ck_r(ck),
  .rst_n(rst_n),.st(2'd0),.aq(aq),.am(am),.cal(cal),.ap(ap_b),.af(af_b),.lt(lt_b),.so(sso_b),.si(ssi_b));
 // ---- lockstep --------------------------------------------------------------------------------------------------------
 integer cycle=0,errors=0,mism=0;
 integer n;
 reg [15:0] com_b;
 always @* begin com_b=0;for(n=0;n<8;n=n+1)com_b=com_b|ssi_b[633*n+537+:16];end
 always @(negedge ck)if(rst_n)begin
  cycle=cycle+1;
  if(si_b!==si_a || ap_b!==ap_a[42:0] || ap_a[562:43]!==0 || lt_b!==lt_a || erv_b!==erv_a || era_b!==era_a || erd_b!==erd_a ||
     af_b!==ua.ctl_fault || com_b!==com_a)begin
   mism=mism+1;
   if(mism<6)$display("MISMATCH cycle=%0d si=%b ap=%b apPV0=%b lt=%b er=%b%b%b af=%b/%b com=%b",cycle,si_b===si_a,ap_b===ap_a[42:0],
     ap_a[562:43]===0,lt_b===lt_a,erv_b===erv_a,era_b===era_a,erd_b===erd_a,af_b,ua.ctl_fault,com_b===com_a);
  end
 end
 // ---- phase-1 functional checks on B (tb_qkd_astk_native_stack's) -------------------------------------------------------
 reg chk=1;
 integer lmax_words=0,z_words=0,z_done=0,reads=0,score_checks=0,afs=0;
 always @(negedge ck)if(rst_n&&chk)begin
  afs=afs|af_b|erf_b;
  if(ap_b[0] && cycle>120)begin
   if(ap_b[3] || !ap_b[10])begin errors=errors+1;$display("FAIL sideband group/any");end
   case(ap_b[2:1])
   0:begin if(ap_b[42:11]!==0 || ap_b[5:4]!==2'(lmax_words))begin errors=errors+1;$display("FAIL lmax");end lmax_words=lmax_words+1;end
   1:begin
    if(ap_b[42:11]!==32'h43000000 || ap_b[9:6]!==4'(z_words/4) || ap_b[5:4]!==2'(z_words%4))begin errors=errors+1;if(errors<6)$display("FAIL Z word=%0d got=%h",z_words,ap_b[42:11]);end
    z_words=z_words+1;
   end
   2:z_done=z_done+1;
   default:begin errors=errors+1;$display("FAIL sidebandtype");end
   endcase
  end
  if(erv_b)begin
   if(era_b!==11'(reads) || erd_b!==64'h3f803f803f803f80)begin errors=errors+1;if(errors<6)$display("FAIL e read=%0d got=%h",reads,erd_b);end
   reads=reads+1;
  end
 end
 genvar e;
 generate for(e=0;e<8;e=e+1)begin:g_trace
  integer seen=0,hh,addr;
  always @(negedge ck)if(rst_n&&chk&&ub.g_ep[e].u_ep.xa[0])begin
   addr=((seen%16)<<4)|(seen/16);
   for(hh=0;hh<4;hh=hh+1)begin
    if(ub.g_ep[e].u_ep.xa[66*hh+2+:32]!==score_word(e,addr,hh))begin errors=errors+1;if(errors<6)$display("FAIL score e=%0d n=%0d",e,seen);end
    score_checks=score_checks+1;
   end
   seen=seen+1;
  end
 end endgenerate
 integer t,i,h,seed=17;
 initial begin
  repeat(6)@(negedge ck);rst_n=1;repeat(10)@(negedge ck);
  aq[14:1]=8192;aq[0]=1;@(negedge ck);aq[0]=0;
  for(t=0;t<3500;t=t+1)begin
   for(i=0;i<8;i=i+1)begin
    so[425*i+:425]=0;so[425*i+410]=1;
    if(t>=40 && t<296)begin so[425*i+13]=1;so[425*i+14+:12]={1'b0,8'(t-40),3'(i)};
     for(h=0;h<4;h=h+1)so[425*i+26+32*h+:32]=score_word(i,t-40,h);end
   end
   am=0;
   if(t>=360&&t<364)am={32'd0,2'(t-360),1'b0,1'b1};
   er_v=(t>=1300&&t<3348);er_addr=11'(t-1300);
   @(negedge ck);
  end
  er_v=0;
  if(afs!==0||score_checks!=8192||lmax_words!=4||z_words!=64||z_done!=1||reads!=2048||com_b!==16'hffff)begin
   errors=errors+1;$display("FAIL counts af=%b scores=%0d lm=%0d z=%0d done=%0d reads=%0d commits=%h",afs,score_checks,lmax_words,z_words,z_done,reads,com_b);end
  // phase 2: restart with T 600, random engine words, M words and reads (lockstep only)
  chk=0;
  aq[14:1]=600;aq[0]=1;@(negedge ck);aq[0]=0;
  for(t=0;t<2500;t=t+1)begin
   for(i=0;i<8;i=i+1)begin
    so[425*i+:425]={14{$random(seed)}};so[425*i]=0;so[425*i+424]=(t==2400&&i==3);
    so[425*i+13]=(t<300)&&($random(seed)%3==0);
   end
   am=(t>=300&&t<304)?{$random(seed),2'(t-300),1'b0,1'b1}:36'd0;
   er_v=($random(seed)%4==0)&&t>200;er_addr=$random(seed);
   @(negedge ck);
  end
  if(mism!=0)begin errors=errors+1;$display("FAIL lockstep mismatches=%0d",mism);end
  if(errors==0)$display("PASS qkd_astk_strip_st lockstep vs qkd_astk_native_stack_cal: %0d edges, scores %0d, lmax %0d, Z %0d, e reads %0d, mut %0d",cycle,score_checks,lmax_words,z_words,reads,`KVD_STMUT);
  else $display("FAIL qkd_astk_strip_st errors=%0d mismatches=%0d mut %0d",errors,mism,`KVD_STMUT);
  $finish;
 end
endmodule
