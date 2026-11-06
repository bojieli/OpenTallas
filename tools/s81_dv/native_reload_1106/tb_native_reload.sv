`timescale 1ns/1fs
module tb;
 parameter integer BAD=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,rk=0,rn=0;integer cyc=0,txi=0,rxi=0,ks_count=0,next_send=0;
 wire[53:0]remote_kit;wire remote_kit_valid;wire[76:0]test_thost;reg hsend=0,ksend=0;reg[514:0]hw=0;wire hready,haccept,kaccept;
 wire[543:0]p0d,p1d,p0p,p1p;wire t0,t1;wire[76:0]remote;wire rv;wire[6:0]pf;
 wire[511:0]tx0,tx1,rx0,rx1;wire[1:0]s0,s1;wire[2:0]f0,f1;
 wire[552:0]nlod0,nlod1,nlid0,nlid1,klod0,klod1,klid0,klid1;
 wire nlov0,nlov1,nlor0,nlor1,nliv0,nliv1,nlir0,nlir1,nrx0,nrx1;
 wire klov0,klov1,klor0,klor1,kliv0,kliv1,klir0,klir1;wire[1:0]krx,ks0,ks1;wire[2:0]kf0,kf1;
 wire[514:0]fh;wire[52:0]fk;wire lf;wire[3:0]host_lf;
 ot_tb_s81_native_host_peer #(.WIRE_PROFILE_BAD(BAD)) peer(.clk(clk),.rst_n(rst_n),.host_send(hsend),.host_word(hw),.host_ready(hready),.host_accepted(haccept),
 .ks_send(ksend),.ks_word(KS),.ks_accepted(kaccept),.pma_from_die0(p0d),.pma_from_die1(p1d),.pma_die_tck0(t0),.pma_die_tck1(t1),
 .pma_to_die0(p0p),.pma_to_die1(p1p),.remote_host_status(remote),.remote_host_valid(rv),.fault(pf),.remote_kit(remote_kit),.remote_kit_valid(remote_kit_valid));
 ot_pdie_serdes_col #(.PMA_LAT(4),.TXL(2)) phy0(.clk(clk),.rst(rst_n),.tx(tx0),.rx(rx0),.st(s0),.pma_tx(p0d),.pma_tck(t0),.pma_rx(p0p),.pma_rck(clk));
 ot_pdie_serdes_col #(.PMA_LAT(4),.TXL(2)) phy1(.clk(clk),.rst(rst_n),.tx(tx1),.rx(rx1),.st(s1),.pma_tx(p1d),.pma_tck(t1),.pma_rx(p1p),.pma_rck(clk));
 dsfd_coll_lane_e_safe8_ntf #(.CORE_CRED(12)) lane0(.ck(clk),.rs(rn),.chb(1'b1),.rx({s0[0],s0[1],rx0,nrx0}),.tx(tx0),.lo_v(nlov0),.lo_r(nlor0),.lo_d(nlod0),.li_v(nliv0),.li_r(nlir0),.li_d(nlid0),.flt(f0));
 dsfd_coll_lane_e_safe8_ntf #(.CORE_CRED(12)) lane1(.ck(clk),.rs(rn),.chb(1'b1),.rx({s1[0],s1[1],rx1,nrx1}),.tx(tx1),.lo_v(nlov1),.lo_r(nlor1),.lo_d(nlod1),.li_v(nliv1),.li_r(nlir1),.li_d(nlid1),.flt(f1));
 ot_s81_mu72_lnland #(.KN_EPOCH_BIAS(5),.NK_EPOCH_BIAS(3)) land0(.ck_k(clk),.ck_n(clk),.rs_k(rk),.rs_n(rn),
 .k_lo_v(klov0),.k_lo_d(klod0),.k_lo_r(klor0),.k_li_v(kliv0),.k_li_d(klid0),.k_li_r(klir0),.k_rxv(krx[0]),.k_flt(kf0),.k_st(ks0),
 .n_lo_v(nlov0),.n_lo_d(nlod0),.n_lo_r(nlor0),.n_li_v(nliv0),.n_li_d(nlid0),.n_li_r(nlir0),.n_rxv(nrx0),.n_flt(f0),.n_st(s0));
 ot_s81_mu72_lnland #(.KN_EPOCH_BIAS(5),.NK_EPOCH_BIAS(3)) land1(.ck_k(clk),.ck_n(clk),.rs_k(rk),.rs_n(rn),
 .k_lo_v(klov1),.k_lo_d(klod1),.k_lo_r(klor1),.k_li_v(kliv1),.k_li_d(klid1),.k_li_r(klir1),.k_rxv(krx[1]),.k_flt(kf1),.k_st(ks1),
 .n_lo_v(nlov1),.n_lo_d(nlod1),.n_lo_r(nlor1),.n_li_v(nliv1),.n_li_d(nlid1),.n_li_r(nlir1),.n_rxv(nrx1),.n_flt(f1),.n_st(s1));
 // Same HOST/MU/A-B/RX-SRAM/native32/face-stage options as the selected S7N LEP.
 ot_s81sl_lep_core #(.DT(512),.DR(12),.CRED(12),.SRAM(1),.HOST_EN(1),.MU_EN(1),.AB_EN(1),.NB(80),.RX_SRAM(1),.IN_PIPE(1),.NATIVE32(1),.IDX_EN(1),.IDX_TP(1)) lep(
 .clk(clk),.rst_n(rk),.ro(1104'd0),.ri(),.lo0_v(klov0),.lo0_r(klor0),.lo0_d(klod0),.lo1_v(klov1),.lo1_r(klor1),.lo1_d(klod1),
 .li0_v(kliv0),.li0_r(klir0),.li0_d(klid0),.li1_v(kliv1),.li1_r(klir1),.li1_d(klid1),.rxv(krx),.sl_f(1'b0),.l0_f(kf0),.l1_f(kf1),.l0_st(ks0),.l1_st(ks1),
 .t_host(test_thost),.t_kd(t_kd ^ (bad_kit ? 54'h400000 : 54'd0)),.f_host(fh),.f_lf(host_lf),.f_ks(fk),.mu_c(34'd0),.mu_rt(),.ml_wv(),.ml_wd(),.ml_rv(1'b0),.ml_rd(1104'd0),.ml_f(1'b0),
 .lo2_v(),.lo2_r(1'b0),.lo2_d(),.lo3_v(),.lo3_r(1'b0),.lo3_d(),.li2_v(1'b0),.li2_r(),.li2_d(553'd0),.li3_v(1'b0),.li3_r(),.li3_d(553'd0),.rxvb(),.l2_f(3'd0),.l3_f(3'd0),.fault(lf),.tl(276'd0),.ca(),.cb(),.tm(276'd0),.qc(258'd0),.ql());
 `include "fixture_defs.svh"
 wire[275:0]vo_n,vo_s;wire[53:0]t_kd;wire[32:0]s_j;
 wire cw_v;wire[9:0]cw_a;wire[255:0]cw_d;
 dsdv_hostb_seqhost_mux #(.HOSTB_ENABLE(0),.STATIC_KS6(0)) seqdut(
 .ck(clk),.rst_n(rk),.tap_k(8'd0),.sink_k(8'd0),.vi_s(276'd0),.vi_n(276'd0),.vo_s(vo_s),.vo_n(vo_n),
 .select_hbe(1'b0),.hbe_f_host(515'd0),.starter_f_ks(53'd0),.hbe_ks_slot(3'd0),
 .f_host(fh),.t_host(test_thost),.f_lf(host_lf),.f_ks(fk),.t_kd(t_kd),
 .sid_ri(1'b0),.vid_ri(1'b0),.s_j(s_j),.s_jd_w(2'd0),.s_jd_e(2'd0),.s_hc_w(9'd0),.s_hc_e(9'd0),
 .st_rg_w(2'b01),.st_rg_e(2'b01),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),.mu_rt_7n(32'd0),.mu_rt_0n(32'd0));
 `define ISS seqdut.u_seqhost.u.u_u.u_l1.u_iss
 wire iss_busy=`ISS.busy,iss_sealed=`ISS.sealed,iss_fault=`ISS.fault;
 wire[1:0]iss_phase=`ISS.phase_q;
 reg[514:0]host0[0:HOST0_N-1],host1[0:HOST1_N-1];
 reg[299:0]exp_n0[0:EXP_N0-1],exp_s0[0:EXP_S0-1],exp_n1[0:EXP_N1-1],exp_s1[0:EXP_S1-1];
 integer job=0,state=0,launch_at=-1,ks_at=-1,end_at=-1,n_count=0,s_count=0,kits=0;
 integer first_book=7272; integer total_host=0,total_v=0,first_ks_at=-1;integer returns=0,local_kit_at=-1;bit bad_kit=0;bit alive=0,seen_busy=0,bad_payload=0;
 wire[52:0]KS={1'b1,10'(37+job),21'(1000+job),21'(5000+job)};
 function automatic integer host_n(input integer j);host_n=j?HOST1_N:HOST0_N;endfunction
 function automatic integer n_n(input integer j);n_n=j?EXP_N1:EXP_N0;endfunction
 function automatic integer s_n(input integer j);s_n=j?EXP_S1:EXP_S0;endfunction
 function automatic integer kit_issue(input integer j);kit_issue=j?KIT1_ISSUE:KIT0_ISSUE;endfunction
 function automatic reg[514:0]wire_word(input integer j,input integer index);
  reg[514:0]w;begin w=j?host1[index]:host0[index];
   // Corrupt one actual template through the real peer. The transport shadow
   // expects this changed word; the command golden remains the original image.
   if(bad_payload&&j==0&&w[8:1]==8'h13&&w[15:9]==MUT_TEMPLATE0)w[42]=~w[42];
   wire_word=w;end
 endfunction
 task automatic command(input bit south,input[275:0]actual);
  reg[299:0]e;integer index,wanted_edge;begin
   index=south?s_count:n_count;
   if(index>=(south?s_n(job):n_n(job)))$fatal(1,"NATIVE_RELOAD_EXTRA_COMMAND job=%0d south=%b edge=%0d",job,south,cyc);
   if(south)e=job?exp_s1[index]:exp_s0[index];else e=job?exp_n1[index]:exp_n0[index];
   if(actual!==e[275:0])$fatal(1,"NATIVE_RELOAD_COMMAND_PAYLOAD job=%0d south=%b index=%0d edge=%0d got=%h expected=%h",job,south,index,cyc,actual,e[275:0]);
   wanted_edge=ks_at+int'(e[299:276])+11+(south?1:0);
   if(cyc!=wanted_edge)$fatal(1,"NATIVE_RELOAD_COMMAND_DATE job=%0d south=%b index=%0d edge=%0d expected=%0d KS=%0d",job,south,index,cyc,wanted_edge,ks_at);
   if(south)s_count=s_count+1;else n_count=n_count+1;total_v=total_v+1;
   $display("NATIVE_RELOAD_V job=%0d south=%b index=%0d edge=%0d",job,south,index,cyc);
  end
 endtask
 realtime prev_edge;
 always @(posedge clk)begin
  if(cyc==10)prev_edge=$realtime;
  if(cyc==11)begin
   if(($realtime-prev_edge<0.832999999)||($realtime-prev_edge>0.833000001))$fatal(1,"CLOCK_PERIOD");
   $display("NATIVE_RELOAD_PERIOD_FS 833000");
  end
  cyc<=cyc+1;
 end
 initial begin
  bad_kit=$test$plusargs("bad_kit");bad_payload=$test$plusargs("bad_payload"); if($value$plusargs("first_book=%d",first_book))begin end
  if(first_book%4!=0)$fatal(1,"FIRST_BOOK_PHASE");
  $readmemh("page0.host.memh",host0);$readmemh("page1.host.memh",host1);
  $readmemh("expect_n0.memh",exp_n0);$readmemh("expect_s0.memh",exp_s0);$readmemh("expect_n1.memh",exp_n1);$readmemh("expect_s1.memh",exp_s1);
  repeat(16)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);rk=1;repeat(5)@(negedge clk);rn=1;
  // Functional deadlock budget from actual two host streams, their END ages,
  // and measured physical warmup/drain; there is no wall/CPU timeout.
  repeat(1000+(HOST0_N+HOST1_N)*12+END0_ISSUE+END1_ISSUE+1024)@(negedge clk);
  $fatal(1,"NATIVE_RELOAD_TIMEOUT job=%0d state=%0d tx=%0d rx=%0d N=%0d S=%0d kits=%0d phase=%0d sealed=%b busy=%b remote=%h",job,state,txi,rxi,n_count,s_count,kits,iss_phase,iss_sealed,iss_busy,remote);
 end
 always @(negedge clk)if(rst_n)begin
  hsend<=0;ksend<=0;
  if(cyc>32&&(pf!=0||f0!=0||f1!=0||lf||test_thost[75]||seqdut.t_mf!=0||iss_fault))
   $fatal(1,"NATIVE_RELOAD_FAULT edge=%0d job=%0d peer=%h lane=%h/%h LEP=%b host=%h mf=%h issuer=%b code=%0d",cyc,job,pf,f0,f1,lf,test_thost,seqdut.t_mf,iss_fault,`ISS.fault_code);
  if(rv&&remote[76])begin alive=1;$display("NATIVE_RELOAD_ALIVE edge=%0d",cyc);end
  if(state==0&&alive)begin state=1;next_send=cyc+16;end
  if(haccept)begin txi=txi+1;next_send=cyc+5;end
  if(state==1&&txi<host_n(job)&&hready&&cyc+1>=next_send)begin hw<=wire_word(job,txi);hsend<=1;end
  if(fh[0])begin
   if(state!=1||rxi>=host_n(job)||fh!==wire_word(job,rxi))$fatal(1,"NATIVE_RELOAD_HOST_DATA job=%0d index=%0d edge=%0d",job,rxi,cyc);
   rxi=rxi+1;total_host=total_host+1;
  end
  if(state==1&&rxi==host_n(job)&&txi==host_n(job)&&iss_sealed&&!iss_busy&&iss_phase==0)begin
   if(job==0)begin
    if(seqdut.u_seqhost.u.g_mu.u_hs.gn!=2||seqdut.u_seqhost.u.g_mu.u_hs.lw!=1||seqdut.u_seqhost.u.g_mu.u_hs.cs!=4096||seqdut.u_seqhost.u.g_mu.u_hs.crl!=804||seqdut.u_seqhost.u.g_mu.u_hs.gt[47:0]!={24'd4095,24'd4095}||seqdut.u_seqhost.u.g_mu.u_hs.armed||seqdut.u_seqhost.u.g_mu.u_hs.vld!=0)$fatal(1,"FINAL_HS_CONFIG_IMAGE");
    if(seqdut.u_seqhost.u_win.gn!=2||seqdut.u_seqhost.u_win.lw!=1||seqdut.u_seqhost.u_win.cs!=4096||seqdut.u_seqhost.u_win.crl!=804||seqdut.u_seqhost.u_win.gt[0]!=4096||seqdut.u_seqhost.u_win.gt[1]!=4096||seqdut.u_seqhost.u_win.armed||seqdut.u_seqhost.u_win.vld!=0||seqdut.u_seqhost.u_win.esel!=7||seqdut.u_seqhost.u_win.ek!=8'hff)$fatal(1,"FINAL_WIN_CONFIG_IMAGE");
    for(integer e=0;e<8;e=e+1)if(seqdut.u_seqhost.u_win.eep[e]!=0||seqdut.u_seqhost.u_win.eD[e]!=4+e||seqdut.u_seqhost.u_win.eat[e][0]!=0||seqdut.u_seqhost.u_win.eat[e][1]!=0)$fatal(1,"FINAL_EVENT_CONFIG_IMAGE event%0d",e);
    $display("NATIVE_RELOAD_CONFIG_IMAGE_OK slots2 RL804 gaps4096 events8 prefix35 original_native_boot_encoder");
   end
   launch_at=job==0?cyc+3949:first_ks_at+4096-120;if(launch_at<=cyc+1)$fatal(1,"MU_BOOK_TOO_SHORT");state=2;$display("NATIVE_RELOAD_SEALED job=%0d edge=%0d queue=%0d",job,cyc,launch_at);
  end
  if(state==2&&cyc+1==launch_at)begin ksend<=1;state=3;$display("NATIVE_RELOAD_KS_QUEUE job=%0d edge=%0d",job,cyc+1);end
  if(fk[52])begin
   if(state!=3||fk!==KS)$fatal(1,"NATIVE_RELOAD_KS_DATA job=%0d edge=%0d word=%h",job,cyc,fk);
   ks_at=cyc+1;if(job==0)begin first_ks_at=ks_at;if(ks_at!=first_book)$fatal(1,"MU_FIRST_BOOK expected%0d got%0d",first_book,ks_at);end else if(ks_at!=first_ks_at+4096)$fatal(1,"MU_NEXT_BOOK");state=4;$display("NATIVE_RELOAD_KS_RX job=%0d edge=%0d phase=%0d word=%h",job,ks_at,iss_phase,fk);
  end
  if(vo_n[0])command(0,vo_n);if(vo_s[0])command(1,vo_s);
  if(cw_v||s_j[32])$fatal(1,"NATIVE_RELOAD_UNEXPECTED_ENGINE job=%0d edge=%0d",job,cyc);
  if(t_kd[53])begin
   if(state!=4||kits!=0||t_kd!=={1'b1,21'(1000+job),10'(37+job),21'(5000+job),1'b0}||cyc!=ks_at+kit_issue(job)+7)
    $fatal(1,"NATIVE_RELOAD_KIT job=%0d edge=%0d KS=%0d got=%h",job,cyc,ks_at,t_kd);
   local_kit_at=cyc;kits=kits+1;$display("NATIVE_RELOAD_KIT job=%0d edge=%0d",job,cyc);
  end
  if(remote_kit_valid)begin
   if(returns!=0||local_kit_at<0||remote_kit!=={1'b1,21'(1000+job),10'(37+job),21'(5000+job),1'b0})$fatal(1,"NATIVE_RELOAD_RETURN_KIT job=%0d edge=%0d got=%h",job,cyc,remote_kit);
   returns=returns+1;$display("NATIVE_RELOAD_RETURN_KIT job=%0d local=%0d remote=%0d age=%0d word=%h",job,local_kit_at,cyc,cyc-local_kit_at,remote_kit);
  end
  if(state==4&&iss_busy)seen_busy=1;
  if(state==4&&seen_busy&&!iss_busy)begin end_at=cyc;state=5;$display("NATIVE_RELOAD_SEQ_END job=%0d edge=%0d",job,cyc);end
  if(state==5&&cyc>=end_at+12&&returns==1)begin
   if(n_count!=n_n(job)||s_count!=s_n(job)||kits!=1)$fatal(1,"NATIVE_RELOAD_INCOMPLETE job=%0d N=%0d S=%0d kits=%0d",job,n_count,s_count,kits);
   if(job==1)begin
    $display("NATIVE_RELOAD_PASS jobs=2 host=%0d V=%0d resets=1 faults=0 external_KIT2 no_layer_retirement_claim=1",total_host,total_v);$finish;
   end else begin
    $display("NATIVE_RELOAD_NEXT_PAGE after_SEQ_END=%0d first_source_edge=%0d",end_at,cyc+4);
    job=1;state=1;txi=0;rxi=0;n_count=0;s_count=0;kits=0;returns=0;local_kit_at=-1;seen_busy=0;ks_at=-1;launch_at=-1;end_at=-1;next_send=cyc+4;
   end
  end
 end
 `undef ISS
endmodule
