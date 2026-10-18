`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// tb_hbm_host_cp_rxs (H-D4G5/HOSTEP 2026-10-18): the d4g host control plane on the static endpoint, end to end, against
// the closed predecessor.
//   DIE  (clock ca): ot_hbm_host_cp_rxs (DUT) <-> hfd_ep_static (die host_ep) <-> ot_pdie_ucie (die host_N) -> REAL
//        ot_hbm_host_static_ingress (TARGET 112).
//   HOST (clock cb, 300 ppm slow): ot_pdie_ucie <-> hfd_ep_static <-> ot_hbm_host_link_capture <-> ot_hbm_host_link_seq
//        (OPENER 1) <- the host driver (one request per TXGAP, <= 192 outstanding = landing 256 bound, counted from the
//        responses it has received; no die-side credit).
//   REF  (clock ca): the CLOSED fold ot_hbm_host_cp_rx (hdie_host_cprx_r1) fed the SAME request list on its old endpoint
//        face (landing credit 256 on pop, t_cr credit model) -> its own REAL ot_hbm_host_static_ingress.
// Traffic: NREQ legal configuration requests (F20 target 112 / 8 x F24 -> cfg_v / F28 / F2c, F30 status and
// random-address reads), > 65,536 by default so both link directions wrap their 16-bit sequence; irq / fault toggled
// every ~6,000 edges (one status packet each).
// PASS: the DUT ingress's ordered cfg / desc / launch events == the reference's; the ordered op81 / op82 responses the
// host receives == the reference's f_flit responses (545 b exact); status values in order equal; no fault anywhere
// (DUT land / protocol / link / seq, both endpoints incl. cal_fault / early, host link abort, host seq, PHY st[0]).
// MUT: 1 TX calendar one step late, 2 RX expect one edge early, 3 no TX spacing, 4 rx word bit 40 flipped, 5 saturating
// link sequence counters (COLL) -> each must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hbm_host_cp_rxs;
 parameter integer MUT=0;
 parameter integer NREQ=70000;
 localparam [7:0] SES=8'h5a;
 reg ca=0,cb=0,rst=0;
 always #0.41667 ca=~ca;
 always #0.41679 cb=~cb;
 reg irq=0,fault=0;
 // ---------------- request list (shared by host driver and reference)
 reg [511:0] req[0:NREQ-1];
 function automatic [511:0] pk(input [7:0] op,input [15:0] id,input [11:0] a,input [31:0] d,input [3:0] st);
  pk={340'd0,1'b0,1'b0,2'd0,4'd0,st,32'd0,d,52'd0,a,id,8'd1,op}; endfunction
 integer seed=29,ng=0,rows=0,jj,kk;
 task add(input [7:0] op,input [11:0] a,input [31:0] d);
  begin if(ng<NREQ)begin req[ng]=pk(op,ng[15:0],a,d,4'hf);ng=ng+1;end end endtask
 initial begin
  while(ng<NREQ)begin
   add(8'h01,12'hf20,{12'd0,2'd0,rows[9:0],8'd112});
   for(kk=0;kk<8;kk=kk+1)begin add(8'h01,12'hf24,$random(seed)); if(kk==3)add(8'h02,12'hf30,0); end
   add(8'h01,12'hf28,{7'd0,13'd200+{3'd0,rows[9:0]},12'd10});
   add(8'h01,12'hf2c,{16'd0,16'd1+{6'd0,rows[9:0]}});
   if(rows%3==0)add(8'h02,$random(seed),0);
   rows=rows+1;
  end
 end
 // =============================================================== DIE
 wire tx_v; wire [611:0] tx_f; wire arm_v,arm_b,rel_v,rel_b,slot_v,slot_b; wire [6:0] words; wire [5:0] slot_i;
 wire rx_pv; wire [611:0] rx_pf; wire [1:0] bready; wire up,epf; wire [10:0] epc;
 wire [511:0] sdt,sdr; wire [1:0] sds; wire [512:0] pma_d,pma_h; wire tck_d,tck_h;
 wire awv,wv,br,arv,rr; wire [11:0] awa,ara; wire [31:0] wd,rd; wire [3:0] ws; wire awr,wr,bv,arr,rv; wire [1:0] bresp;
 wire lf,pf,kf,sf;
 ot_hbm_host_cp_rxs #(.MUT(MUT)) dut(.clk(ca),.rst_n(rst),.session(SES),
  .ep_tx_v(tx_v),.ep_tx_frame(tx_f),.ep_rx_arm_v(arm_v),.ep_rx_arm_bank(arm_b),.ep_rx_block_words(words),
  .ep_rx_release_v(rel_v),.ep_rx_release_bank(rel_b),.ep_rx_slot_v(slot_v),.ep_rx_slot_bank(slot_b),.ep_rx_slot_index(slot_i),
  .ep_rx_pin_v(rx_pv),.ep_rx_pin_flit(rx_pf),.ep_rx_block_ready(bready),.ep_phy_up(up),
  .s_awvalid(awv),.s_awready(awr),.s_awaddr(awa),.s_wvalid(wv),.s_wready(wr),.s_wdata(wd),.s_wstrb(ws),
  .s_bvalid(bv),.s_bresp(bresp),.s_bready(br),.s_arvalid(arv),.s_arready(arr),.s_araddr(ara),
  .s_rvalid(rv),.s_rready(rr),.s_rdata(rd),.irq(irq),.fault(fault),
  .land_fault(lf),.protocol_fault(pf),.link_fault(kf),.seq_fault(sf));
 hfd_ep_static dep(.clk(ca),.rst_n(rst),.tx_v(tx_v),.tx_frame(tx_f),.rx_arm_v(arm_v),.rx_arm_bank(arm_b),
  .rx_block_words(words),.rx_release_v(rel_v),.rx_release_bank(rel_b),.rx_slot_v(slot_v),.rx_slot_bank(slot_b),
  .rx_slot_index(slot_i),.rx_pin_v(rx_pv),.rx_pin_flit(rx_pf),.rx_block_ready(bready),.phy_up(up),.fault(epf),
  .fault_cause(epc),.sd_tx(sdt),.sd_rx(sdr),.sd_st(sds));
 ot_pdie_ucie du(.clk(ca),.rst(rst),.tx(sdt),.rx(sdr),.st(sds),.pma_tx(pma_d),.pma_tck(tck_d),.pma_rx(pma_h),.pma_rck(tck_h));
 wire cfgv,descv,lv,ingf; wire [7:0] ct; wire [11:0] ca_,db; wire [255:0] cd; wire [12:0] dl; wire [15:0] dlp;
 ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1<<112)) ing(.clk(ca),.rst_n(rst),
  .s_awvalid(awv),.s_awready(awr),.s_awaddr(awa),.s_wvalid(wv),.s_wready(wr),.s_wdata(wd),.s_wstrb(ws),
  .s_bvalid(bv),.s_bready(br),.s_bresp(bresp),.s_arvalid(arv),.s_arready(arr),.s_araddr(ara),
  .s_rvalid(rv),.s_rready(rr),.s_rdata(rd),.block_ready(1'b0),.program_active(1'b0),.program_fault(1'b0),
  .cfg_v(cfgv),.cfg_target(ct),.cfg_addr(ca_),.cfg_data(cd),.desc_v(descv),.desc_base(db),.desc_limit(dl),
  .desc_loops(dlp),.launch_v(lv),.fault(ingf));
 // =============================================================== HOST
 wire [0:0] hr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) hrr(.clk(cb),.rst_n_in(rst),.rst_n(hr));
 reg h_v=0; reg [544:0] h_f=0;
 wire h_crst,h_eb,h_wv,h_rdv,h_xv,h_up,h_rxv,h_ab,h_sf; wire [15:0] h_ws,h_rs,h_xs; wire [544:0] h_wf,h_rxf; wire [10:0] h_cz;
 wire h_txv; wire [611:0] h_txf; wire h_arm,h_armb,h_rel,h_relb,h_sl,h_slb; wire [6:0] h_words; wire [5:0] h_sli;
 wire h_pv; wire [611:0] h_pf; wire [1:0] h_br; wire h_epup,h_epf; wire [10:0] h_epc; wire [511:0] hst,hsr; wire [1:0] hss;
 ot_hbm_host_link_seq #(.OPENER(1),.OPEN_WAIT(256)) hseq(.clk(cb),.rst_n(hr[0]),.c_tx_v(h_v),.c_tx_flit(h_f),.client_rst_n(h_crst),
  .lc_epoch_begin(h_eb),.lc_wr_v(h_wv),.lc_wr_seq(h_ws),.lc_wr_flit(h_wf),.lc_rd_v(h_rdv),.lc_rd_seq(h_rs),
  .lc_rx_expect_v(h_xv),.lc_rx_expect_seq(h_xs),.lc_phy_up(h_up),.lc_rx_v(h_rxv),
  .ep_arm_v(h_arm),.ep_arm_bank(h_armb),.ep_block_words(h_words),.ep_release_v(h_rel),.ep_release_bank(h_relb),
  .ep_slot_v(h_sl),.ep_slot_bank(h_slb),.ep_slot_index(h_sli),.ep_block_ready(h_br),.ep_phy_up(h_epup),.seq_fault(h_sf));
 ot_hbm_host_link_capture hlink(.clk(cb),.rst_n(hr[0]),.epoch_begin(h_eb),.epoch(SES),
  .wr_v(h_wv),.wr_observed_v(h_wv),.wr_seq(h_ws),.wr_flit(h_wf),.rd_v(h_rdv),.rd_seq(h_rs),
  .rx_expect_v(h_xv),.rx_expect_seq(h_xs),.phy_up(h_up),.tx_pin_v(h_txv),.tx_pin_flit(h_txf),
  .rx_pin_v(h_pv),.rx_pin_flit(h_pf),.rx_v(h_rxv),.rx_flit(h_rxf),.epoch_abort(h_ab),.fault_cause(h_cz));
 hfd_ep_static hep(.clk(cb),.rst_n(rst),.tx_v(h_txv),.tx_frame(h_txf),.rx_arm_v(h_arm),.rx_arm_bank(h_armb),
  .rx_block_words(h_words),.rx_release_v(h_rel),.rx_release_bank(h_relb),.rx_slot_v(h_sl),.rx_slot_bank(h_slb),
  .rx_slot_index(h_sli),.rx_pin_v(h_pv),.rx_pin_flit(h_pf),.rx_block_ready(h_br),.phy_up(h_epup),.fault(h_epf),
  .fault_cause(h_epc),.sd_tx(hst),.sd_rx(hsr),.sd_st(hss));
 ot_pdie_ucie hu(.clk(cb),.rst(rst),.tx(hst),.rx(hsr),.st(hss),.pma_tx(pma_h),.pma_tck(tck_h),.pma_rx(pma_d),.pma_rck(tck_d));
 // =============================================================== REFERENCE (closed fold, old endpoint face)
 reg r_in_v=0; reg [544:0] r_in=0; reg r_tcr=0;
 wire r_pop,r_send,r_lf,r_pf; wire [544:0] r_flit;
 wire r_awv,r_wv,r_br,r_arv,r_rr; wire [11:0] r_awa,r_ara; wire [31:0] r_wd,r_rd; wire [3:0] r_ws;
 wire r_awr,r_wr,r_bv,r_arr,r_rv; wire [1:0] r_bresp;
 ot_hbm_host_cp_rx ref_rx(.clk(ca),.rst_n(rst),.in_v(r_in_v),.in_data(r_in),.pop(r_pop),.f_send(r_send),.f_flit(r_flit),.t_cr(r_tcr),
  .s_awvalid(r_awv),.s_awready(r_awr),.s_awaddr(r_awa),.s_wvalid(r_wv),.s_wready(r_wr),.s_wdata(r_wd),.s_wstrb(r_ws),
  .s_bvalid(r_bv),.s_bresp(r_bresp),.s_bready(r_br),.s_arvalid(r_arv),.s_arready(r_arr),.s_araddr(r_ara),
  .s_rvalid(r_rv),.s_rready(r_rr),.s_rdata(r_rd),.irq(irq),.fault(fault),.land_fault(r_lf),.protocol_fault(r_pf));
 wire r_cfgv,r_descv,r_lv,r_ingf; wire [7:0] r_ct; wire [11:0] r_ca,r_db; wire [255:0] r_cd; wire [12:0] r_dl; wire [15:0] r_dlp;
 ot_hbm_host_static_ingress #(.TARGET_MASK(256'd1<<112)) r_ing(.clk(ca),.rst_n(rst),
  .s_awvalid(r_awv),.s_awready(r_awr),.s_awaddr(r_awa),.s_wvalid(r_wv),.s_wready(r_wr),.s_wdata(r_wd),.s_wstrb(r_ws),
  .s_bvalid(r_bv),.s_bready(r_br),.s_bresp(r_bresp),.s_arvalid(r_arv),.s_arready(r_arr),.s_araddr(r_ara),
  .s_rvalid(r_rv),.s_rready(r_rr),.s_rdata(r_rd),.block_ready(1'b0),.program_active(1'b0),.program_fault(1'b0),
  .cfg_v(r_cfgv),.cfg_target(r_ct),.cfg_addr(r_ca),.cfg_data(r_cd),.desc_v(r_descv),.desc_base(r_db),.desc_limit(r_dl),
  .desc_loops(r_dlp),.launch_v(r_lv),.fault(r_ingf));
 // =============================================================== event streams (hashed in order) + counts
 // ingress events: cfg {target, addr, data}, desc {base, limit, loops}, launch
 reg [63:0] h_ev_d=64'h1, h_ev_r=64'h1, h_rsp_d=64'h1, h_rsp_r=64'h1, h_st_d=64'h1, h_st_r=64'h1;
 integer n_ev_d=0,n_ev_r=0,n_rsp_d=0,n_rsp_r=0,n_st_d=0,n_st_r=0,n_cfg=0,n_rd=0,first_bad=-1;
 function automatic [63:0] mix(input [63:0] h,input [575:0] x);
  integer q; reg [63:0] t; begin t=h; for(q=0;q<9;q=q+1)begin t=(t^x[q*64+:64])*64'h9E3779B97F4A7C15; t=t^(t>>29); end mix=t; end
 endfunction
 always @(posedge ca)begin
  if(cfgv)begin h_ev_d<=mix(h_ev_d,{2'd1,ct,ca_,cd});n_ev_d<=n_ev_d+1;n_cfg<=n_cfg+1;end
  else if(descv)begin h_ev_d<=mix(h_ev_d,{2'd2,db,dl,dlp});n_ev_d<=n_ev_d+1;end
  else if(lv)begin h_ev_d<=mix(h_ev_d,{2'd3});n_ev_d<=n_ev_d+1;end
  if(r_cfgv)begin h_ev_r<=mix(h_ev_r,{2'd1,r_ct,r_ca,r_cd});n_ev_r<=n_ev_r+1;end
  else if(r_descv)begin h_ev_r<=mix(h_ev_r,{2'd2,r_db,r_dl,r_dlp});n_ev_r<=n_ev_r+1;end
  else if(r_lv)begin h_ev_r<=mix(h_ev_r,{2'd3});n_ev_r<=n_ev_r+1;end
  if(r_send)begin
   if(r_flit[7:0]==8'hff)begin h_st_r<=mix(h_st_r,r_flit);n_st_r<=n_st_r+1;end
   else begin h_rsp_r<=mix(h_rsp_r,r_flit);n_rsp_r<=n_rsp_r+1;end
  end
 end
 // per-response exact compare: reference responses are kept in order, host responses checked against them
 reg [544:0] rq[0:NREQ-1]; integer rq_w=0;
 always @(posedge ca) if(r_send && r_flit[7:0]!=8'hff)begin rq[rq_w]<=r_flit; rq_w<=rq_w+1; end
 integer mism=0,q;
 reg [544:0] hq[0:NREQ-1];
 always @(posedge cb) if(h_rxv)begin
  if(h_rxf[7:0]==8'hff)begin h_st_d<=mix(h_st_d,h_rxf);n_st_d<=n_st_d+1;end
  else begin
   h_rsp_d<=mix(h_rsp_d,h_rxf);
   if(n_rsp_d<NREQ)hq[n_rsp_d]<=h_rxf;
   if(h_rxf[7:0]==8'h82)n_rd<=n_rd+1;
   n_rsp_d<=n_rsp_d+1;
  end
 end
 task compare_rsp; begin
  for(q=0;q<NREQ;q=q+1) if(q<n_rsp_d && q<rq_w && hq[q]!==rq[q])begin mism=mism+1; if(first_bad<0)first_bad=q; end
 end endtask
 // =============================================================== drivers
 // host: one request per published slot, <= 192 outstanding (responses received), host store <= 40 unread
 integer hs=0;
 initial begin
  wait(rst); wait(hseq.opened);
  while(hs<NREQ)begin
   @(negedge cb); h_v<=0;
   if((hs-n_rsp_d)<192 && (hseq.lc_wr_seq-hseq.rc)<16'd40)begin h_v<=1; h_f<={33'd0,req[hs]}; hs=hs+1; end
  end
  @(negedge cb); h_v<=0;
 end
 // reference: endpoint face model of the old fold (landing credit 256 on pop; t_cr returned 3..13 edges after f_send)
 integer rs=0,lcred=256,cyc=0,crq[0:262143],crh=0,crt=0,seed2=5;
 always @(posedge ca)begin
  cyc<=cyc+1; r_tcr<=0;
  if(r_send)begin crq[crt]=cyc+3+($unsigned($random(seed2))%11); crt=crt+1; end
  if(crh!=crt && crq[crh]<=cyc)begin r_tcr<=1; crh=crh+1; end
 end
 always @(negedge ca) if(rst && r_pop) lcred=lcred+1;
 initial begin
  wait(rst); repeat(40)@(negedge ca);
  while(rs<NREQ)begin
   @(negedge ca); r_in_v<=0;
   if(lcred>0 && ($unsigned($random(seed2))%4)!=0)begin r_in_v<=1; r_in<={33'd0,req[rs]}; rs=rs+1; lcred=lcred-1; end
  end
  @(negedge ca); r_in_v<=0;
 end
 // irq / fault: one change every ~6000 die edges (each gives exactly one status packet in both systems)
 integer tg=0;
 always @(posedge ca) if(rst)begin tg<=tg+1; if(tg%6000==5999)begin if((tg/6000)%3==2)fault<=~fault; else irq<=~irq; end end
 // =============================================================== faults + finish
 wire any_fault=lf|pf|kf|sf|epf|h_epf|h_ab|h_sf|sds[0]|hss[0];
 integer fault_edge=-1;
 always @(posedge ca) if(rst && any_fault && fault_edge<0)begin fault_edge=cyc;
  $display("FAULT at die edge %0d: land %b prot %b link %b seq %b ep %b/%h host_ep %b/%h host_link %b/%h host_seq %b st %b/%b",
   cyc,lf,pf,kf,sf,epf,epc,h_epf,h_epc,h_ab,h_cz,h_sf,sds,hss); end
 reg ok;
 initial begin
  repeat(8)@(posedge ca); rst=1;
  fork
   begin wait(n_rsp_d==NREQ && n_rsp_r==NREQ); repeat(3000)@(posedge ca); end
   begin repeat(NREQ*40+20000)@(posedge ca); $display("HOST_CP_RXS timeout: host responses %0d ref %0d sent %0d", n_rsp_d,n_rsp_r,hs); end
   begin wait(fault_edge>=0); repeat(200)@(posedge ca); end
  join_any
  compare_rsp;
  ok=(fault_edge<0) && mism==0 && n_rsp_d==NREQ && n_rsp_r==NREQ && h_rsp_d==h_rsp_r && n_ev_d==n_ev_r && h_ev_d==h_ev_r &&
     n_st_d==n_st_r && h_st_d==h_st_r && n_st_d>=4 && n_cfg>1000 && n_rd>1000 && ingf==0 && r_ingf==0 &&
     hseq.lc_wr_seq==16'(NREQ) && dut.u_seq.lc_wr_seq==16'(NREQ+n_st_d);   // both directions published exactly NREQ (+status) mod 2^16
  if(ok)$display("HOST_CP_RXS_PASS requests=%0d responses=%0d cfg=%0d reads=%0d events=%0d status=%0d mism=0 seq_wrapped=%0d die_edges=%0d",
   NREQ,n_rsp_d,n_cfg,n_rd,n_ev_d,n_st_d,NREQ>=65536,cyc);
  else $display("HOST_CP_RXS_FAIL MUT=%0d fault_edge=%0d mism=%0d first_bad=%0d rsp %0d/%0d ev %0d/%0d (eq %b) st %0d/%0d (eq %b) rsp_eq %b cfg=%0d rd=%0d ingf %b/%b",
   MUT,fault_edge,mism,first_bad,n_rsp_d,n_rsp_r,n_ev_d,n_ev_r,h_ev_d==h_ev_r,n_st_d,n_st_r,h_st_d==h_st_r,h_rsp_d==h_rsp_r,n_cfg,n_rd,ingf,r_ingf);
  $finish;
 end
endmodule
