`timescale 1ns/1fs
module tb;
 parameter integer BAD=0;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,rk=0,rn=0;integer cyc=0,txi=0,rxi=0,ks_count=0,next_send=0;
 reg[76:0]test_thost=0;reg hsend=0,ksend=0;reg[514:0]hw=0;wire hready,haccept,kaccept;
 wire[543:0]p0d,p1d,p0p,p1p;wire t0,t1;wire[76:0]remote;wire rv;wire[6:0]pf;
 wire[511:0]tx0,tx1,rx0,rx1;wire[1:0]s0,s1;wire[2:0]f0,f1;
 wire[552:0]nlod0,nlod1,nlid0,nlid1,klod0,klod1,klid0,klid1;
 wire nlov0,nlov1,nlor0,nlor1,nliv0,nliv1,nlir0,nlir1,nrx0,nrx1;
 wire klov0,klov1,klor0,klor1,kliv0,kliv1,klir0,klir1;wire[1:0]krx,ks0,ks1;wire[2:0]kf0,kf1;
 wire[514:0]fh;wire[52:0]fk;wire lf;reg[514:0]words[0:11];
 localparam[52:0]KS={1'b1,10'd37,21'd1000,21'd5000};
 ot_tb_s81_native_host_peer #(.WIRE_PROFILE_BAD(BAD)) peer(.clk(clk),.rst_n(rst_n),.host_send(hsend),.host_word(hw),.host_ready(hready),.host_accepted(haccept),
 .ks_send(ksend),.ks_word(KS),.ks_accepted(kaccept),.pma_from_die0(p0d),.pma_from_die1(p1d),.pma_die_tck0(t0),.pma_die_tck1(t1),
 .pma_to_die0(p0p),.pma_to_die1(p1p),.remote_host_status(remote),.remote_host_valid(rv),.fault(pf));
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
 .t_host(test_thost),.t_kd(54'd0),.f_host(fh),.f_lf(),.f_ks(fk),.mu_c(34'd0),.mu_rt(),.ml_wv(),.ml_wd(),.ml_rv(1'b0),.ml_rd(1104'd0),.ml_f(1'b0),
 .lo2_v(),.lo2_r(1'b0),.lo2_d(),.lo3_v(),.lo3_r(1'b0),.lo3_d(),.li2_v(1'b0),.li2_r(),.li2_d(553'd0),.li3_v(1'b0),.li3_r(),.li3_d(553'd0),.rxvb(),.l2_f(3'd0),.l3_f(3'd0),.fault(lf),.tl(276'd0),.ca(),.cb(),.tm(276'd0),.qc(258'd0),.ql());
 initial begin:setup
  reg[31:0]p;p=32'h15374829;
  for(integer n=0;n<12;n=n+1)begin
   words[n][0]=1;
   for(integer j=1;j<515;j=j+1)begin words[n][j]=p[0];p={p[30:0],p[31]^p[21]^p[1]^p[0]};end
  end
  repeat(16)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);rk=1;repeat(5)@(negedge clk);rn=1;
  repeat(150)@(negedge clk);test_thost={1'b1,76'd0};$display("PMA_STATUS_RISE edge=%0d",cyc);
  repeat(2400)@(negedge clk);$fatal(1,"PMA_HOST_TIMEOUT BAD=%0d tx=%0d rx=%0d ks=%0d remote=%h peer_fault=%h lanes=%h/%h lep=%b",BAD,txi,rxi,ks_count,remote,pf,f0,f1,lf);
 end
 reg alive=0,ks_once=0;
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)if(rst_n)begin
  hsend<=0;ksend<=0;
  if(cyc%500==0)$display("PMA_STATE edge=%0d phy=%h/%h peer_gb=%b up=%b die_gb=%b up=%b ph_v=%b hpgo=%b hist=%h",cyc,s0,s1,peer.l0.u.gb_l,peer.l0.u.up,lane0.u.gb_l,lane0.u.up,lep.g_htx.ph_v,lep.hp_go,lep.h_status_old);
  if(rv&&remote[76])begin alive=1;$display("PMA_HOST_ALIVE edge=%0d",cyc);end
  if(haccept)begin txi=txi+1;next_send=cyc+5;end
  if(alive&&txi<12&&hready&&cyc+1>=next_send)begin hw<=words[txi];hsend<=1;end
  if(fh[0])begin
   if(rxi>=12||fh!==words[rxi])$fatal(1,"PMA_HOST_DATA index=%0d got=%h expected=%h",rxi,fh,words[rxi]);
   $display("PMA_HOST_RX index=%0d edge=%0d",rxi,cyc);rxi=rxi+1;
  end
  if(rxi==12&&!ks_once&&hready)begin ksend<=1;ks_once=1;$display("PMA_KS_QUEUE edge=%0d",cyc);end
  if(fk[52])begin
   if(fk!==KS)$fatal(1,"PMA_KS_DATA got=%h expected=%h",fk,KS);ks_count=ks_count+1;
   if(rxi!=12||ks_count!=1||pf!=0||f0!=0||f1!=0||lf)$fatal(1,"PMA_HOST_FAULT");
   $display("PMA_HOST_PASS words514=%0d valid_andKS53_exact=1 edge=%0d",rxi,cyc);$finish;
  end
 end
endmodule
