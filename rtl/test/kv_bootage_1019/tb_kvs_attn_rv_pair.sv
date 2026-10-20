`timescale 1ns/1ps
// KV-ATTN2 2026-10-19: WHOLE-TILE PAIR LOCKSTEP of the structurally safe attention tile against the ba5 tile.
//   A = qkd_kvs_attn_fl_ba5 (the boot-age tile, behavioural ancestor of the safe_control / pr32 / pr32b27 native lineage)
//   B = qkd_kvs_attn_fl (rtl/lib/face_land/qkd_kvs_attn_fl_rv.sv -> qkd_kvs_attn_rv; MUT = bench mutant)
// Shared pin stimulus: i_ctl (cfg ages, go / ctx_t, authority, issue, run), the d2d RX record stream (CMD + 32 Q beats on the
// compiled RX ages of the controller, which both tiles share: run edges are identical).  Per-tile stimulus (each from its own
// state, the die's static schedule): the d2d TX slots on its controller's tx_first (A 1750, B 1751), the final-join beat
// stream fin on its face window (root age + RESULT_AGE), unit faults (B one edge after A).
// CHECK every edge: B's ports now == A's ports one edge earlier (B = A + 1 edge, the priced K.rx_record +1):
//   attn__tx_valid (+ payload when valid), pvst, pvfst, ahs, acal_*, prg valids (+ position / Q when valid), arh valid (+ beat).
// MODE 0 legal (NCMD commands, A fault-free with 1 request / 32 Q / 33 TX each); fault modes (one command, both must fault):
//   1 CMD data bit 300, 2 Q beat 6 wrong epoch, 3 Q beat 9 missing, 4 extra RX record after the Q run, 5 TX slot 3 wrong kind,
//   6 unit fault ufs_ES in the RESULT run, 7 fin beat 13 missing, 8 Q beat 4 kind STATUS, 9 ufk_WN pulse in the RESULT run,
//   10 authority token out of range.
// Verdict: KVS_RVPAIR PASS|FAIL mode=M mut=U checks=N ...
module tb_kvs_attn_rv_pair;
 parameter integer MUT=0,PL=0,FD=1,DQK=0,DRL=0,NCMD=3,SEED=1,RS=0,SD=0;   // RS/SD: B RETIRE_STATIC / STATUS_DELAY (B's STATUS = A's + 1 + SD edges)
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0;
 reg [108:0] ictl=0;
 reg rx_ev=0;reg [547:0] rx_pl=0;
 reg sl_a=0,sl_b=0;reg [3:0] sk_a=0,sk_b=0;reg [4:0] sb_a=0,sb_b=0;
 reg [533:0] fin_a=0,fin_b=0;
 reg [7:0] ufd_a=0,ufd_b=0;reg [3:0] ufc_a=0,ufc_b=0;
 integer mode=0;
 wire txv_a,txv_b;wire [547:0] txp_a,txp_b;wire [30:0] pvst_a,pvst_b;wire [64:0] pvfst_a,pvfst_b;
 wire [164:0] ahs_a,ahs_b;wire [536:0] prg_a,prg_b;wire [47:0] c0a,c1a,c2a,c3a,c0b,c1b,c2b,c3b;wire [7:0] arh_a,arh_b;
 qkd_kvs_attn_fl_ba5 #(.MUT(0)) uA(.ck(ck),.rst_n(rst_n),.ufs_WS(ufd_a[0]),.ufs_WN(ufd_a[1]),.ufs_ES(ufd_a[2]),.ufs_EN(ufd_a[3]),
  .ufh(ufd_a[4]),.ufp0(ufd_a[5]),.ufp1(ufd_a[6]),.uff(ufd_a[7]),.ufk_WS(ufc_a[0]),.ufk_WN(ufc_a[1]),.ufk_ES(ufc_a[2]),.ufk_EN(ufc_a[3]),
  .d2d__srx({521'd0,rx_ev}),.d2d__rx_payload(rx_pl),.d2d__att_tx_slot(sl_a),.d2d__att_tx_kind(sk_a),.d2d__att_tx_beat(sb_a),
  .fin(fin_a),.attn__tx_valid(txv_a),.attn__tx_payload(txp_a),.pvst(pvst_a),.pvfst(pvfst_a),.ahs(ahs_a),.prg(prg_a),
  .acal_WS(c0a),.acal_WN(c1a),.acal_ES(c2a),.acal_EN(c3a),.arh(arh_a),.i_ctl(ictl));
`ifdef RV_RS
 qkd_kvs_attn_fl #(.MUT(MUT),.RETIRE_STATIC(RS),.STATUS_DELAY(SD)) uB(
`else
 qkd_kvs_attn_fl #(.MUT(MUT)) uB(
`endif.ck(ck),.rst_n(rst_n),.ufs_WS(ufd_b[0]),.ufs_WN(ufd_b[1]),.ufs_ES(ufd_b[2]),.ufs_EN(ufd_b[3]),
  .ufh(ufd_b[4]),.ufp0(ufd_b[5]),.ufp1(ufd_b[6]),.uff(ufd_b[7]),.ufk_WS(ufc_b[0]),.ufk_WN(ufc_b[1]),.ufk_ES(ufc_b[2]),.ufk_EN(ufc_b[3]),
  .d2d__srx({521'd0,rx_ev}),.d2d__rx_payload(rx_pl),.d2d__att_tx_slot(sl_b),.d2d__att_tx_kind(sk_b),.d2d__att_tx_beat(sb_b),
  .fin(fin_b),.attn__tx_valid(txv_b),.attn__tx_payload(txp_b),.pvst(pvst_b),.pvfst(pvfst_b),.ahs(ahs_b),.prg(prg_b),
  .acal_WS(c0b),.acal_WN(c1b),.acal_ES(c2b),.acal_EN(c3b),.arh(arh_b),.i_ctl(ictl));
 // ---- state taps (stimulus only; checks use ports) ----
 wire a_busy=uA.u_core.u_attn.ctl.busy, b_busy=uB.u_core.u_attn.ctl.busy;
 wire [15:0] a_age=uA.u_core.u_attn.ctl.age, b_age=uB.u_core.u_attn.ctl.age;
 wire [15:0] a_rxc=uA.u_core.u_attn.ctl.rx_cmd, a_txf=uA.u_core.u_attn.ctl.tx_first, b_txf=uB.u_core.u_attn.ctl.tx_first;
 wire [15:0] b_last=uB.u_core.u_attn.ctl.last; wire [15:0] b_st=(RS!=0)?b_last-16'd1:b_txf+16'd33;
 wire [15:0] a_ep=uA.u_core.u_attn.ctl.ep; wire [5:0] a_ly=uA.u_core.u_attn.ctl.layer; wire [17:0] a_pos=uA.u_core.u_attn.ctl.pos;
 wire a_fault=uA.u_core.u_attn.ctl.fault, b_fault=uB.u_core.u_attn.ctl.fault;
 wire a_run=uA.u_core.u_attn_root.running, b_run=uB.u_core.u_attn_root.running;
 wire a_sq=uA.u_core.u_attn_root.start_qk, b_sq=uB.u_core.u_attn_root.start_qk;
 wire [15:0] a_rage=uA.u_core.u_attn_root.age, b_rage=uB.u_core.u_attn_root.age;
 wire [15:0] a_rep=uA.u_core.u_attn_root.ep, b_rep=uB.u_core.u_attn_root.ep;
 wire [15:0] a_res=uA.u_core.u_attn_face.res_t, b_res=uB.u_core.u_attn_face.res_t;
 wire a_lf=uA.u_core.u_attn_root.local_fault|uA.u_core.u_attn_root.io_fault;
 integer seed,k,errs=0,checks=0,nreq=0,nq=0,ntx=0,cmds=0,afault=0,bfault=0,cyc=0;
 function [511:0] beatv(input integer b,input integer c);
  integer w;begin for(w=0;w<16;w=w+1)beatv[32*w+:32]=32'h9e3779b9*(b+1)^(w<<9)^(32'h6c078965*(c+SEED));end
 endfunction
 // ---- per-edge stimulus (negedge) ----
 integer ra,rb2;
 always @(negedge ck)begin
  rx_ev=0;rx_pl=0;sl_a=0;sl_b=0;sk_a=0;sk_b=0;sb_a=0;sb_b=0;fin_a=0;fin_b=0;
  // RX records (shared): CMD at rx_cmd, Q beats rx_cmd+1..+32 of the controller age (identical in A and B)
  if(a_busy&&a_age>=a_rxc&&a_age<=a_rxc+32&&!(mode==3&&a_age==a_rxc+10))begin
   rx_ev=1;
   if(a_age==a_rxc)rx_pl={5'd0,4'd1,a_ly,a_ep,5'd0,{493'd0,5'd0,a_pos[12:0],1'b1}};
   else rx_pl={5'd0,4'd2,a_ly,a_ep,5'(a_age-a_rxc-1),beatv(a_age-a_rxc-1,cmds+7)};
   if(mode==1&&a_age==a_rxc)rx_pl[300]=1'b1;
   if(mode==2&&a_age==a_rxc+7)rx_pl[532:517]=a_ep+16'd1;
   if(mode==8&&a_age==a_rxc+5)rx_pl[542:539]=4'd4;
  end
  if(mode==4&&a_busy&&a_age==a_rxc+40)begin rx_ev=1;rx_pl={5'd0,4'd2,a_ly,a_ep,5'd0,512'd0};end
  // TX slots (per tile, its own tx_first)
  if(a_busy&&((a_age>=a_txf&&a_age<a_txf+32)||a_age==a_txf+33))begin
   sl_a=1;sk_a=(a_age==a_txf+33)?4'd4:4'd3;sb_a=(a_age==a_txf+33)?5'd0:5'(a_age-a_txf);
   if(mode==5&&a_age==a_txf+3)sk_a=4'd4;
  end
  if(b_busy&&((b_age>=b_txf&&b_age<b_txf+32)||b_age==b_st))begin
   sl_b=1;sk_b=(b_age==b_st)?4'd4:4'd3;sb_b=(b_age==b_st)?5'd0:5'(b_age-b_txf);
   if(mode==5&&b_age==b_txf+3)sk_b=4'd4;
  end
  // final-join beat stream (per tile): landed one edge later, so beat b leaves the pins at root age RESULT_AGE + b - 1
  if(a_run&&!a_sq&&(a_rage+16'd1)>=a_res&&(a_rage+16'd1-a_res)<16'd32)begin
   ra=a_rage+1-a_res;
   if(!(mode==7&&ra==13))fin_a={beatv(ra,cmds),a_rep,5'(ra),1'b1};
  end
  if(b_run&&!b_sq&&(b_rage+16'd1)>=b_res&&(b_rage+16'd1-b_res)<16'd32)begin
   rb2=b_rage+1-b_res;
   if(!(mode==7&&rb2==13))fin_b={beatv(rb2,cmds),b_rep,5'(rb2),1'b1};
  end
  // unit faults: B one edge after A
  ufd_b=ufd_a;ufc_b=ufc_a;
  if(a_run&&a_rage==a_res+16'd8&&mode==6)ufd_a[2]=1'b1;
  if(a_run&&a_rage==a_res+16'd8&&mode==9)ufc_a[1]=1'b1;
 end
 // ---- lockstep check (posedge sample of the settled values): B now vs A one edge ago ----
 reg p_txv=0;reg [547:0] p_txp=0;reg [30:0] p_pvst=0;reg [64:0] p_pvfst=0;reg [164:0] p_ahs=0;reg [536:0] p_prg=0;
 reg [191:0] p_cal=0;reg [7:0] p_arh=0;reg armed=0;
 reg st_pend=0;integer st_due=0;reg [547:0] st_pl=0;
 task automatic chk(input ok,input [8*20-1:0] what);
  begin checks=checks+1;if(!ok)begin errs=errs+1;if(errs<=10)$display("MISMATCH cyc=%0d %0s",cyc,what);end end
 endtask
 always @(posedge ck)begin
  cyc=cyc+1;
  if(armed)begin
   // STATUS (kind 4) moves by SD more edges under RS: checked against the queued A STATUS instead
   if(!(SD!=0&&((p_txv&&p_txp[542:539]==4'd4)||(txv_b&&txp_b[542:539]==4'd4))))begin
    chk(txv_b===p_txv,"tx_valid");
    if(p_txv)chk(txp_b===p_txp,"tx_payload");
   end
   if(SD!=0&&txv_b&&txp_b[542:539]==4'd4)begin chk(st_pend&&cyc==st_due,"status timing");chk(txp_b===st_pl,"status payload");st_pend=0;end
   chk(pvst_b===p_pvst,"pvst");
   chk(pvfst_b===p_pvfst,"pvfst");
   chk(ahs_b===p_ahs,"ahs");
   chk({c0b,c1b,c2b,c3b}===p_cal,"acal");
   chk(prg_b[0]===p_prg[0]&&prg_b[19]===p_prg[19],"prg valids");
   if(p_prg[0])chk(prg_b[18:1]===p_prg[18:1],"prg position");
   if(p_prg[19])chk(prg_b[536:20]===p_prg[536:20],"prg q");
   chk(arh_b[7:5]===p_arh[7:5],"arh valid");
   if(p_arh[7])chk(arh_b[4:0]===p_arh[4:0],"arh beat");
  end
  if(rst_n)begin
   if(prg_a[0])nreq=nreq+1;
   if(prg_a[19])nq=nq+1;
   if(txv_a)ntx=ntx+1;
  end
  if(SD!=0&&txv_a&&txp_a[542:539]==4'd4)begin st_pend=1;st_due=cyc+1+SD;st_pl=txp_a;end
  p_txv=txv_a;p_txp=txp_a;p_pvst=pvst_a;p_pvfst=pvfst_a;p_ahs=ahs_a;p_cal={c0a,c1a,c2a,c3a};p_prg=prg_a;p_arh=arh_a;
 end
 task automatic pulse(input integer bit_i);
  begin ictl[bit_i]=1'b1;@(negedge ck);ictl[bit_i]=1'b0;end
 endtask
 integer t,ctx,w;reg [17:0] tok;
 initial begin
  if($value$plusargs("MODE=%d",mode))begin end
  seed=SEED;
  ictl[7:0]=8'(PL);ictl[15:8]=8'(FD);ictl[23:16]=8'(DQK);ictl[31:24]=8'(DRL);ictl[32]=1'b1;ictl[33]=1'b1;
  repeat(4)@(negedge ck);rst_n=1;
  repeat(100)@(negedge ck);armed=1;
  for(k=0;k<((mode==0)?NCMD:1);k=k+1)begin
   ctx=(k%3==0)?300:((k%3==1)?2000:77);
   tok=(mode==10)?18'd200000:18'(19+k*101);
   ictl[49:36]=14'(ctx);ictl[65:50]=16'h0b00+16'(k);ictl[83:66]=18'(100+k*37);ictl[89:84]=6'(1+k%36);ictl[108:91]=tok;
   pulse(90);                          // go: the calendar for this context
   repeat(16)@(negedge ck);
   pulse(34);                          // issue
   repeat(6)@(negedge ck);
   pulse(35);                          // run
   w=0;
   while(w<4000&&(a_busy||b_busy||w<8))begin @(negedge ck);w=w+1;end
   repeat(20)@(negedge ck);
   cmds=cmds+1;
  end
  afault=a_fault||a_lf;bfault=b_fault;
  if(mode==0&&(afault||nreq!=NCMD||nq!=32*NCMD||ntx!=33*NCMD))begin
   errs=errs+1;$display("MISMATCH reference A not legal: fault=%0d req=%0d Q=%0d TX=%0d",afault,nreq,nq,ntx);
  end
  if(mode==0&&bfault)begin errs=errs+1;$display("MISMATCH B faulted on the legal stream");end
  if(st_pend)begin errs=errs+1;$display("MISMATCH B STATUS never sent");end
  if(mode!=0&&!afault)begin errs=errs+1;$display("MISMATCH reference A missed fault mode %0d",mode);end
  if(mode!=0&&!bfault)begin errs=errs+1;$display("MISMATCH B missed fault mode %0d",mode);end
  $display("KVS_RVPAIR %s mode=%0d mut=%0d checks=%0d errors=%0d cmds=%0d req=%0d Q=%0d TX=%0d faultA=%0d faultB=%0d",
   errs==0?"PASS":"FAIL",mode,MUT,checks,errs,cmds,nreq,nq,ntx,afault,bfault);
  $finish;
 end
endmodule
