`timescale 1ns/1ps
// HKV-ASTK 2026-10-18 (from HKV-CALENDAR's tb, Codex 10-19 draft): production-profile calendar bench of the actual static ASTK
// strip WITH its e-read (qkd_astk_strip_er_st: ctl_s + 8 ep_s + 32 ex_s + 4 zn + mapped score/e SRAM macros) at the die's
// hop latency RL (KVD_RL), the closed ctl's Z stride (KVD_CAL_STRIDE) and the e-read organisation (KVD_DER 0 = closed star
// qkd_astk_er_tap_st ERL3, 1 = distributed owner chain qkd_astk_er_chain_st).  Ages come from plusargs +T +LMAX +EXP +Z +READ
// so one binary sweeps the minimal calendar; every run checks exact LMAX/Z sideband words, all 8192 score operands (T 8192),
// every e-read response (address order, value) and the strip/e-read fault.  It reports the measured e-read response latency.
// Mutant: +define+KVD_STMUT=1 (ep_s), 2 (ex_s), 3 (ctl_s) must FAIL.
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
module tb_qkd_astk_calendar;
 `ifndef KVD_CAL_STRIDE
 `define KVD_CAL_STRIDE 4
 `endif
 `ifndef KVD_RL
 `define KVD_RL 3
 `endif
 `ifndef KVD_DER
 `define KVD_DER 1
 `endif
 localparam integer Z_STRIDE=`KVD_CAL_STRIDE;
 integer EXP_AGE=500, LMAX_AGE=350, Z_AGE=1016, CTX=8192, READ_AGE=1800;
 function automatic [31:0] fpcount(input integer n);
  integer e; begin e=0; while((1<<e)<=n && e<15)e=e+1;
  fpcount=n==0?0:((127+e-1)<<23)|((n-(1<<(e-1)))<<(24-e));end
 endfunction
 function automatic [31:0] score_word(input integer eng,addr,head);
  score_word=32'h30000000 | (eng<<12) | (addr<<2) | head;
 endfunction
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg [539:0] aq=0;reg [35:0] am=0;reg [47:0] cal=0;
 reg [3399:0] so=0;
 reg er_v=0;reg [10:0] er_addr=0;
 // ---- B: the actual strip with its inline e-read (port 0 used; ports 1..3 idle) ------------------------------------------
 wire [633*8-1:0] ssi_b;wire [413*8-1:0] sso_b;
 wire [42:0] ap_b;wire af_b,erf_b;wire [20:0] lt_b;
 wire [3:0] erv4;wire [43:0] era4;wire [255:0] erd4;
 wire erv_b=erv4[0];wire [10:0] era_b=era4[10:0];wire [63:0] erd_b=erd4[63:0];
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_bus
  assign sso_b[413*g+:413]={so[425*g+424],so[425*g+13+:399],13'd0};   // strip_er_st splices its own aso into so[12:0]
 end endgenerate
 qkd_astk_strip_er_st #(.RL(`KVD_RL),.DISTRIBUTED_ER(`KVD_DER),.Z_STRIDE(Z_STRIDE),.N(4)) ub(.ck_c(ck),.ck_z({4{ck}}),
  .ck_x({32{ck}}),.ck_e({8{ck}}),.ck_r(ck),.ck_er(ck),.rst_n(rst_n),.st(2'd0),.aq(aq),.am(am),.cal(cal),.ap(ap_b),.af(af_b),
  .lt(lt_b),.so(sso_b),.si(ssi_b),.read_v({3'd0,er_v}),.read_addr({33'd0,er_addr}),.response_v(erv4),.response_addr(era4),
  .response_data(erd4),.er_fault(erf_b));
 integer cycle=0, errors=0;
 integer first_issue=-1, first_rsp=-1;
 always @(negedge ck)if(rst_n)begin if(er_v&&first_issue<0)first_issue=cycle; if(erv_b&&first_rsp<0)first_rsp=cycle; end
 integer n;
 reg [15:0] com_b;
 always @* begin com_b=0;for(n=0;n<8;n=n+1)com_b=com_b|ssi_b[633*n+537+:16];end
 always @(negedge ck)if(rst_n)cycle=cycle+1;
 // ---- phase-1 functional checks on B (tb_qkd_astk_native_stack's) -------------------------------------------------------
 reg chk=1;
 integer lmax_words=0,z_words=0,z_done=0,reads=0,score_checks=0,afs=0;
 always @(negedge ck)if(rst_n&&chk)begin
  afs=afs|af_b|erf_b;
  if(ap_b[0])begin
   if(ap_b[3] || !ap_b[10])begin errors=errors+1;$display("FAIL sideband group/any");end
   case(ap_b[2:1])
   0:begin if(ap_b[42:11]!==0 || ap_b[5:4]!==2'(lmax_words))begin errors=errors+1;$display("FAIL lmax");end lmax_words=lmax_words+1;end
   1:begin
    if(ap_b[42:11]!==fpcount(((CTX-(z_words/4)*512)>128)?128:(CTX-(z_words/4)*512)) || ap_b[9:6]!==4'(z_words/4) || ap_b[5:4]!==2'(z_words%4))begin errors=errors+1;if(errors<6)$display("FAIL Z word=%0d got=%h",z_words,ap_b[42:11]);end
    z_words=z_words+1;
   end
   2:z_done=z_done+1;
   default:begin errors=errors+1;$display("FAIL sidebandtype");end
   endcase
  end
  if(erv_b)begin
   if(era_b!==11'((reads/128)*128+((reads%128)/64)*64+(reads%8)*8+((reads%64)/8)) || erd_b!==64'h3f803f803f803f80)begin errors=errors+1;if(errors<6)$display("FAIL e read=%0d got=%h",reads,erd_b);end
   reads=reads+1;
  end
 end
 genvar e;
 generate for(e=0;e<8;e=e+1)begin:g_trace
  integer seen=0,hh,addr;
  always @(negedge ck)if(rst_n&&chk&&CTX==8192&&ub.u_strip.g_ep[e].u_ep.xa[0])begin
   addr=((seen%16)<<4)|(seen/16);
   for(hh=0;hh<4;hh=hh+1)begin
    if(ub.u_strip.g_ep[e].u_ep.xa[66*hh+2+:32]!==score_word(e,addr,hh))begin errors=errors+1;if(errors<6)$display("FAIL score e=%0d n=%0d",e,seen);end
    score_checks=score_checks+1;
   end
   seen=seen+1;
  end
 end endgenerate
 integer t,i,h,read_index,expected_reads,nb,unused;
 initial begin
  unused=$value$plusargs("T=%d",CTX); unused=$value$plusargs("LMAX=%d",LMAX_AGE);
  unused=$value$plusargs("EXP=%d",EXP_AGE); unused=$value$plusargs("Z=%d",Z_AGE);
  unused=$value$plusargs("READ=%d",READ_AGE);
  nb=(CTX+511)/512;
  expected_reads=(CTX/512)*128+((CTX%512)>128?128:(CTX%512));
  cal={16'(EXP_AGE),16'(Z_AGE),16'(LMAX_AGE)};
  $display("CAL T=%0d RL=%0d DER=%0d stride=%0d LMAX=%0d EXP=%0d Z=%0d READ=%0d ",CTX,`KVD_RL,`KVD_DER,Z_STRIDE,LMAX_AGE,EXP_AGE,Z_AGE,READ_AGE);
  repeat(6)@(negedge ck);rst_n=1;repeat(10)@(negedge ck);
  aq[14:1]=14'(CTX);aq[0]=1;@(negedge ck);aq[0]=0;
  read_index=0;
  for(t=0;t<READ_AGE+expected_reads+100;t=t+1)begin
   for(i=0;i<8;i=i+1)begin
    so[425*i+:425]=0;so[425*i+410]=1;
    if(t>=40 && t<40+nb*16)begin so[425*i+13]=1;so[425*i+14+:12]={1'b0,8'(t-40),3'(i)};
     for(h=0;h<4;h=h+1)so[425*i+26+32*h+:32]=score_word(i,t-40,h);end
   end
   am=0;
   if(t>=LMAX_AGE+10&&t<LMAX_AGE+14)am={32'd0,2'(t-LMAX_AGE-10),1'b0,1'b1};
   er_v=(t>=READ_AGE&&read_index<expected_reads);
   er_addr=11'((read_index/128)*128+((read_index%128)/64)*64+(read_index%8)*8+((read_index%64)/8));
   if(er_v)read_index=read_index+1;
   @(negedge ck);
  end
  er_v=0;
  if(afs!==0||(CTX==8192&&score_checks!=8192)||lmax_words!=4||z_words!=4*nb||z_done!=1||reads!=expected_reads)begin
   errors=errors+1;$display("FAIL counts af=%b scores=%0d lm=%0d z=%0d done=%0d reads=%0d commits=%h",afs,score_checks,lmax_words,z_words,z_done,reads,com_b);end
  if(errors==0)$display("PASS qkd_astk_calendar RL=%0d DER=%0d stride=%0d LMAX=%0d EXP=%0d Z=%0d READ=%0d erlat=%0d T=%0d edges=%0d scores=%0d lmax=%0d Z=%0d reads=%0d mut=%0d",`KVD_RL,`KVD_DER,Z_STRIDE,LMAX_AGE,EXP_AGE,Z_AGE,READ_AGE,first_rsp-first_issue,CTX,cycle,score_checks,lmax_words,z_words,reads,`KVD_STMUT);
  else $display("FAIL qkd_astk_calendar errors=%0d mut=%0d",errors,`KVD_STMUT);
  $finish;
 end
endmodule
