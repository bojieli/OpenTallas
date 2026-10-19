`timescale 1ns/1ps
// RTL-BUILD-KV/ASTK 2026-10-18: exact lockstep of the static KV die's ASTK strip with its e-read inline
// (qkd_astk_strip_er_st = qkd_astk_strip_st + qkd_astk_er_tap_st) against the CURRENT composition
// qkd_astk_native_stack_w4_cal (qkd_astk_native_stack_cal's leaves + qkd_astk_native_er_service_w N 4 + the e-read
// visibility glue).  A is driven on the 425-b engine ABI with so[423:413] random and so[412] (legacy node-beat valid) 0;
// B gets the 413-b ABI {so[424], so[411:0]}.  Every edge compares: the engine si bus (A si[633] must stay 0), the hub
// sideband ap (A's P.V fields must stay 0), lt, the 4 e-read responses (valid, addr, data), the ctl fault, the e-read
// fault (A er_service fault | visibility fault) against the tap fault.  KV-ERTAP 2026-10-18: the tap registers every pin, so
// A takes the reads 2 edges late and B's responses / er_fault are compared 2 / 1 edges late (A's af not compared).
// Phase 1: T 8192 functional stimulus (8,192 score words, 4 LMAX, 64 Z, 2,048 e reads on 4 ports to distinct owners,
// commits ffff, no fault) with the functional checks on B.  Phase 2: restart T 600 with random so / am / 4-port reads
// (collisions and reads of uncommitted groups occur: both fault laws compared).
// Mutants: +define+KVD_STMUT=1 ep_s, 2 ex_s, 3 ctl_s, 4 tap visibility check removed, 5 tap response owner one stage early,
// 6 tap e quad bypassing its esi pin registers (KV-ERTAP).
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
// AD-KV-ASTK 2026-10-18: +define+KVD_RL=<k> runs BOTH strips with k-edge chain hops (landed / die-relayed hop latency).
`ifndef KVD_RL
`define KVD_RL 1
`endif
// +define+KVD_ZAGE=<age>: the compiler's Z start age (cal[31:16]); default 1000 (the RL 1 calendar).
`ifndef KVD_ZAGE
`define KVD_ZAGE 1000
`endif
module tb_qkd_astk_strip_er_st;
 localparam integer EXP_AGE=500, LMAX_AGE=350, Z_AGE=`KVD_ZAGE, Z_STRIDE=16, N=4;
 function automatic [31:0] score_word(input integer eng,addr,head);
  score_word=32'h30000000 | (eng<<12) | (addr<<2) | head;
 endfunction
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg [539:0] aq=0;reg [35:0] am=0;reg [47:0] cal={16'(EXP_AGE),16'(Z_AGE),16'(LMAX_AGE)};
 reg [3399:0] so=0;
 reg [N-1:0] er_v=0;reg [11*N-1:0] er_addr=0;
 // KV-ERTAP 2026-10-18: B's e-read tap registers every pin (request reaches the EP 2 edges after the read pin, response
 // 4 edges later than the service, er_fault 1 edge later relative to the EP read).  A gets the reads 2 edges late (its EPs
 // then read in the same cycle as B's, so si stays exact); B's responses are compared with A's 2 edges late, er_fault 1.
 reg [N-1:0] er_v1=0,er_v2=0;reg [11*N-1:0] er_a1=0,er_a2=0;
 always @(posedge ck)begin er_v1<=er_v;er_v2<=er_v1;er_a1<=er_addr;er_a2<=er_a1;end
 // ---- A: the current composition ------------------------------------------------------------------------------------
 wire [5071:0] si_a;wire [562:0] ap_a;wire af_a;wire [20:0] lt_a;wire [N-1:0] erv_a;wire [11*N-1:0] era_a;wire [64*N-1:0] erd_a;
 wire [15:0] com_a;wire scom_a;
 qkd_astk_native_stack_w4_cal #(.RL(`KVD_RL),.STATIC_SCHEDULE(1),.Z_STRIDE(Z_STRIDE)) ua(.cal(cal),
  .ck_c(ck),.ck_z({4{ck}}),.ck_x({32{ck}}),.ck_e({8{ck}}),.ck_r(ck),.rst_n(rst_n),.st(2'd0),
  .aq(aq),.am(am),.ap(ap_a),.af(af_a),.lt(lt_a),.er_v(er_v2),.er_addr(er_a2),.er_rsp_v(erv_a),.er_rsp_addr(era_a),.er_data(erd_a),
  .exp_committed(com_a),.score_committed(scom_a),
  .so0(so[0+:425]),.so1(so[425+:425]),.so2(so[850+:425]),.so3(so[1275+:425]),
  .so4(so[1700+:425]),.so5(so[2125+:425]),.so6(so[2550+:425]),.so7(so[2975+:425]),
  .si0(si_a[0+:634]),.si1(si_a[634+:634]),.si2(si_a[1268+:634]),.si3(si_a[1902+:634]),
  .si4(si_a[2536+:634]),.si5(si_a[3170+:634]),.si6(si_a[3804+:634]),.si7(si_a[4438+:634]));
 // ---- B: the successor on the 413 / 633-b engine ABI -----------------------------------------------------------------
 wire [413*8-1:0] so_b;wire [633*8-1:0] si_b;
 wire [42:0] ap_b;wire af_b,erf_b;wire [20:0] lt_b;wire [N-1:0] erv_b;wire [11*N-1:0] era_b;wire [64*N-1:0] erd_b;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_bus
  assign so_b[413*g+:413]={so[425*g+424],so[425*g+:412]};
 end endgenerate
 qkd_astk_strip_er_st #(.RL(`KVD_RL),.Z_STRIDE(Z_STRIDE),.N(N)) ub(.ck_c(ck),.ck_z({4{ck}}),.ck_x({32{ck}}),.ck_e({8{ck}}),.ck_r(ck),
  .ck_er(ck),.rst_n(rst_n),.st(2'd0),.aq(aq),.am(am),.cal(cal),.ap(ap_b),.af(af_b),.lt(lt_b),.so(so_b),.si(si_b),
  .read_v(er_v),.read_addr(er_addr),.response_v(erv_b),.response_addr(era_b),.response_data(erd_b),.er_fault(erf_b));
 // ---- lockstep --------------------------------------------------------------------------------------------------------
 integer cycle=0,errors=0,mism=0,n;
 reg [5071:0] si_bw;
 always @* for(n=0;n<8;n=n+1)si_bw[634*n+:634]={1'b0,si_b[633*n+:633]};
 reg ret_b=0;
 wire obs_b=af_b|erf_b;
 always @(posedge ck or negedge rst_n)if(!rst_n)ret_b<=0;else if(obs_b)ret_b<=1;
 wire erf_a0=ua.er_fault|ua.visibility_fault;
 reg erf_a=0;reg [N-1:0] erv_a1=0,erv_ad=0;reg [11*N-1:0] era_a1=0,era_ad=0;reg [64*N-1:0] erd_a1=0,erd_ad=0;
 always @(posedge ck)begin erf_a<=erf_a0;erv_a1<=erv_a;erv_ad<=erv_a1;era_a1<=era_a;era_ad<=era_a1;erd_a1<=erd_a;erd_ad<=erd_a1;end
 always @(negedge ck)if(rst_n)begin
  cycle=cycle+1;
  if(si_bw!==si_a || ap_b!==ap_a[42:0] || ap_a[562:43]!==0 || lt_b!==lt_a || erv_b!==erv_ad || era_b!==era_ad || erd_b!==erd_ad ||
     af_b!==ua.ctl_fault || erf_b!==erf_a || ua.legacy_fault!==0)begin
   mism=mism+1;
   if(mism<6)$display("MISMATCH cycle=%0d si=%b ap=%b apPV0=%b lt=%b er=%b%b%b ctlf=%b/%b erf=%b/%b af=%b/%b",cycle,si_bw===si_a,
     ap_b===ap_a[42:0],ap_a[562:43]===0,lt_b===lt_a,erv_b===erv_ad,era_b===era_ad,erd_b===erd_ad,af_b,ua.ctl_fault,erf_b,erf_a,obs_b|ret_b,af_a);
  end
 end
 // ---- phase-1 functional checks on B ---------------------------------------------------------------------------------
 reg chk=1;
 integer lmax_words=0,z_words=0,z_done=0,reads=0,score_checks=0,afs=0,j;
 integer rcount[0:N-1];
 initial for(j=0;j<N;j=j+1)rcount[j]=0;
 // phase-1 read schedule: edge r (0..511), port j -> addr {r[8:4], j[1:0], r[0], r[3:1]}: 4 distinct owners an edge
 function automatic [10:0] p1_addr(input integer r,input integer jj);
  p1_addr={5'(r>>4),2'(jj),1'(r),3'(r>>1)};
 endfunction
 reg [15:0] com_b;
 always @* begin com_b=0;for(n=0;n<8;n=n+1)com_b=com_b|si_b[633*n+537+:16];end
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
  for(j=0;j<N;j=j+1)if(erv_b[j])begin
   if(era_b[11*j+:11]!==p1_addr(rcount[j],j) || erd_b[64*j+:64]!==64'h3f803f803f803f80)begin
    errors=errors+1;if(errors<6)$display("FAIL e read port=%0d n=%0d addr=%h got=%h",j,rcount[j],era_b[11*j+:11],erd_b[64*j+:64]);end
   rcount[j]=rcount[j]+1;reads=reads+1;
  end
 end
 genvar e;
 generate for(e=0;e<8;e=e+1)begin:g_trace
  integer seen=0,hh,addr;
  always @(negedge ck)if(rst_n&&chk&&ub.u_strip.g_ep[e].u_ep.xa[0])begin
   addr=((seen%16)<<4)|(seen/16);
   for(hh=0;hh<4;hh=hh+1)begin
    if(ub.u_strip.g_ep[e].u_ep.xa[66*hh+2+:32]!==score_word(e,addr,hh))begin errors=errors+1;if(errors<6)$display("FAIL score e=%0d n=%0d",e,seen);end
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
    so[425*i+413+:11]=$random(seed);           // k / v done, node-beat fields: not read by either strip
    if(t>=40 && t<296)begin so[425*i+13]=1;so[425*i+14+:12]={1'b0,8'(t-40),3'(i)};
     for(h=0;h<4;h=h+1)so[425*i+26+32*h+:32]=score_word(i,t-40,h);end
   end
   am=0;
   if(t>=360&&t<364)am={32'd0,2'(t-360),1'b0,1'b1};
   for(j=0;j<N;j=j+1)begin er_v[j]=(t>=1300&&t<1812);er_addr[11*j+:11]=p1_addr(t-1300,j);end
   @(negedge ck);
  end
  er_v=0;
  repeat(4)@(negedge ck);
  if(afs!==0||score_checks!=8192||lmax_words!=4||z_words!=64||z_done!=1||reads!=2048||com_b!==16'hffff)begin
   errors=errors+1;$display("FAIL counts af=%b scores=%0d lm=%0d z=%0d done=%0d reads=%0d commits=%h",afs,score_checks,lmax_words,z_words,z_done,reads,com_b);end
  // phase 2: restart with T 600, random engine words, M words and 4-port reads (lockstep only)
  chk=0;
  aq[14:1]=600;aq[0]=1;@(negedge ck);aq[0]=0;
  for(t=0;t<2500;t=t+1)begin
   for(i=0;i<8;i=i+1)begin
    so[425*i+:425]={14{$random(seed)}};so[425*i]=0;so[425*i+412]=0;so[425*i+424]=(t==2400&&i==3);
    so[425*i+13]=(t<300)&&($random(seed)%3==0);
   end
   am=(t>=300&&t<304)?{$random(seed),2'(t-300),1'b0,1'b1}:36'd0;
   for(j=0;j<N;j=j+1)begin er_v[j]=($random(seed)%6==0)&&t>200;er_addr[11*j+:11]=$random(seed);end
   @(negedge ck);
  end
  if(mism!=0)begin errors=errors+1;$display("FAIL lockstep mismatches=%0d",mism);end
  if(errors==0)$display("PASS qkd_astk_strip_er_st lockstep vs qkd_astk_native_stack_w4_cal: %0d edges, scores %0d, lmax %0d, Z %0d, e reads %0d, erf %b, mut %0d, RL %0d, Z age %0d",
   cycle,score_checks,lmax_words,z_words,reads,erf_b,`KVD_STMUT,`KVD_RL,`KVD_ZAGE);
  else $display("FAIL qkd_astk_strip_er_st errors=%0d mismatches=%0d mut %0d RL %0d",errors,mism,`KVD_STMUT,`KVD_RL);
  $finish;
 end
endmodule
