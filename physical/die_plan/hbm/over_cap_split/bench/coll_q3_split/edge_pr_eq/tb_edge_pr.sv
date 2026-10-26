`timescale 1ns/1ps
// PATH-HBM/Q3 2026-10-25: equivalence bench of the coll_q3 edge _pr twins vs the pinned members.
//   ot_hgi_coll_link_e_pr       == ot_hgi_coll_link_e                    every output, every edge (0 edges added)
//   ot_hgi_coll_argmax_m_tp192_pr: out_v/out_flit == ot_hgi_coll_argmax_m_tp192 delayed 1 edge; fault == same edge
// Random stimulus (strobes at density 1/dens, data uniform), inputs idle in reset and 3 edges after each release.
// +mut=1: compare the argmax outputs WITHOUT the +1 delay (must FAIL); +mut=2: corrupt link held_epoch into the _pr
// twin only (must FAIL).
module tb;
 reg clk=0; always #1 clk=~clk;
 integer cyc=0, errs=0, seed=1, ncyc=20000, dens=4, mut=0, quiet=0, nov=0;
 reg rst_n=0;
 // link
 reg ep_b=0; reg [7:0] ep_n=0, ep_h=0; reg wr_v=0, wr_ov=0; reg [15:0] wr_seq=0; reg [544:0] wr_flit=0;
 reg rd_v=0; reg [15:0] rd_seq=0; reg rxe_v=0; reg [15:0] rxe_seq=0; reg phy_up=0; reg rxp_v=0; reg [611:0] rxp_f=0;
 wire a_tv, b_tv, a_rv, b_rv, a_ab, b_ab, a_rr, b_rr; wire [611:0] a_tf, b_tf; wire [544:0] a_rf, b_rf; wire [10:0] a_fc, b_fc;
 ot_hgi_coll_link_e u_la(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(ep_b),.epoch_new(ep_n),.held_epoch(ep_h),
  .wr_v(wr_v),.wr_observed_v(wr_ov),.wr_seq(wr_seq),.wr_flit(wr_flit),.rd_v(rd_v),.rd_seq(rd_seq),
  .rx_expect_v(rxe_v),.rx_expect_seq(rxe_seq),.phy_up(phy_up),.tx_pin_v(a_tv),.tx_pin_flit(a_tf),
  .rx_pin_v(rxp_v),.rx_pin_flit(rxp_f),.rx_v(a_rv),.rx_flit(a_rf),.epoch_abort(a_ab),.retry_requested(a_rr),.fault_cause(a_fc));
 ot_hgi_coll_link_e_pr u_lb(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(ep_b),.epoch_new(ep_n),
  .held_epoch(ep_h ^ {7'd0, mut==2 && !ep_b}),
  .wr_v(wr_v),.wr_observed_v(wr_ov),.wr_seq(wr_seq),.wr_flit(wr_flit),.rd_v(rd_v),.rd_seq(rd_seq),
  .rx_expect_v(rxe_v),.rx_expect_seq(rxe_seq),.phy_up(phy_up),.tx_pin_v(b_tv),.tx_pin_flit(b_tf),
  .rx_pin_v(rxp_v),.rx_pin_flit(rxp_f),.rx_v(b_rv),.rx_flit(b_rf),.epoch_abort(b_ab),.retry_requested(b_rr),.fault_cause(b_fc));
 // argmax
 reg st=0, mode=0, fl=0, pb=0; reg [7:0] g=0, gb=0, rk=0; reg [3:0] sl=0, iv=0; reg [255:0] key=0; reg [131:0] meta=0;
 wire a_ov, b_ov, a_af, b_af; wire [544:0] a_of, b_of;
 ot_hgi_coll_argmax_m_tp192 u_aa(.clk(clk),.rst_n(rst_n),.start(st),.mode(mode),.cfg_g(g),.cfg_gbase(gb),.cfg_rank(rk),
  .in_slot(sl),.in_v(iv),.in_key(key),.in_meta(meta),.flush_slot(fl),.publish_slot(pb),.out_v(a_ov),.out_flit(a_of),.fault(a_af));
 ot_hgi_coll_argmax_m_tp192_pr u_ab(.clk(clk),.rst_n(rst_n),.start(st),.mode(mode),.cfg_g(g),.cfg_gbase(gb),.cfg_rank(rk),
  .in_slot(sl),.in_v(iv),.in_key(key),.in_meta(meta),.flush_slot(fl),.publish_slot(pb),.out_v(b_ov),.out_flit(b_of),.fault(b_af));
 reg a_ov_d=0; reg [544:0] a_of_d=0;
 always @(posedge clk) begin a_ov_d<=a_ov; a_of_d<=a_of; end
 integer hold=0, lastrst=-100, nflitdc=0, nq=0;
 function automatic bit st8(input integer d); st8 = ($urandom % d) == 0; endfunction
 task automatic drive; begin
  if (!rst_n || hold>0) begin
   ep_b=0; wr_v=0; wr_ov=0; rd_v=0; rxe_v=0; rxp_v=0; st=0; fl=0; pb=0; iv=0; sl=0; mode=0;
  end else begin
   ep_b=st8(dens); wr_v=st8(dens); wr_ov=st8(dens); rd_v=st8(dens); rxe_v=st8(dens); rxp_v=st8(dens);
   st=st8(4*dens); fl=st8(dens); pb=st8(dens); iv=$urandom; sl=$urandom; mode=$urandom;
  end
  ep_n=$urandom; ep_h=$urandom; wr_seq=$urandom; rd_seq=$urandom; rxe_seq=$urandom; phy_up=($urandom%16)!=0;
  for (integer i=0;i<17;i=i+1) wr_flit[i*32+:32]=$urandom;
  for (integer i=0;i<19;i=i+1) rxp_f[i*32+:32]=$urandom;
  wr_flit[544]=$urandom; rxp_f[611:608]=$urandom;
  g=$urandom; gb=$urandom; rk=$urandom; for (integer i=0;i<8;i=i+1) key[i*32+:32]=$urandom;
  for (integer i=0;i<4;i=i+1) meta[i*33+:32]=$urandom; meta[32]=$urandom; meta[65]=$urandom; meta[98]=$urandom; meta[131]=$urandom;
 end endtask
 always @(negedge clk) begin
  // compare (outputs settled after posedge)
  if (cyc > 2 && rst_n && hold==0) begin
   if ({a_tv,a_tf,a_rv,a_rf,a_ab,a_rr,a_fc} !== {b_tv,b_tf,b_rv,b_rf,b_ab,b_rr,b_fc}) begin
    errs=errs+1; if (errs<6) $display("MISMATCH link cyc=%0d tv %b/%b rv %b/%b ab %b/%b fc %h/%h", cyc,a_tv,b_tv,a_rv,b_rv,a_ab,b_ab,a_fc,b_fc); end
   // ARG ABI: out_v and fault every edge; out_flit whenever out_v=1, except a FAULTED publish within 64 edges of an
   // async reset.  Those and out_flit while out_v=0 (not a result) are counted as unqualified_flit: the reset hits
   // both copies on the same edge, i.e. 1 edge early in the _pr copy's delayed timeline, so non-reset fold data
   // (amerge s1a.., acca) captured around a reset can differ until overwritten; a publish then is faulted (sticky).
   if ((mut==1 ? a_ov : a_ov_d) === b_ov && a_af === b_af && (b_ov == 1'b0 || (b_af && cyc - lastrst <= 64)) &&
       (mut==1 ? a_of : a_of_d) !== b_of)
    nflitdc=nflitdc+1;
   else if ((mut==1 ? {a_ov,a_of} : {a_ov_d,a_of_d}) !== {b_ov,b_of} || a_af !== b_af) begin
    errs=errs+1; if (errs<6) $display("MISMATCH arg cyc=%0d lastrst=%0d ov %b(d %b)/%b f %b/%b", cyc,lastrst,a_ov,a_ov_d,b_ov,a_af,b_af); end
   if (b_ov) nov=nov+1;
   if (b_ov && !b_af) nq=nq+1;
  end
  cyc=cyc+1;
  if (cyc==8) rst_n=1;
  else if (rst_n && ($urandom % 3000)==0) begin rst_n=0; hold=0; lastrst=cyc; end
  else if (!rst_n && cyc>8 && ($urandom%6)==0) begin rst_n=1; hold=4; end
  else if (hold>0) hold=hold-1;
  drive;
  if (cyc>=ncyc) begin
   $display("EDGE_PR_EQ %s mut=%0d seed=%0d dens=%0d cycles=%0d errors=%0d arg_out_v=%0d unfaulted=%0d unqualified_flit=%0d", errs?"FAIL":"PASS", mut, seed, dens, cyc, errs, nov, nq, nflitdc);
   $finish;
  end
 end
 initial begin
  if ($value$plusargs("seed=%d", seed)) ; if ($value$plusargs("mut=%d", mut)) ; if ($value$plusargs("dens=%d", dens)) ;
  if ($value$plusargs("cycles=%d", ncyc)) ;
  void'($urandom(seed));
 end
endmodule
