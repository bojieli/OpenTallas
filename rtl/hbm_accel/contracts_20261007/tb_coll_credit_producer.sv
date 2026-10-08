`timescale 1ps/1fs
// Native credit producer bench.  RX: partner (own core clock, random phase) -> forward link (FWD cycles)
// -> RX protected CDC (II1 refill, PHY write / core read) -> receive buffer (C entries) -> random drain
// -> producer K/READY -> PHY synchronisers -> return link (RET cycles) -> partner consumer.
// TX: flight gate -> WSTG pipeline -> TX protected CDC -> PHY pacer with long stalls.
// Checks: READY exactly SYNC+1 core edges after the later release; order and no loss (sequence numbers);
// no overflow (RB <= C, CDC write always ready, no arrival in a domain held in reset); full rate under a
// continuous drain (C >= loop); credit conservation after quiesce; coordinated mid-stream reset in both
// release orders; TX: no CDC overflow at DTX = CDC depth under stalls, full rate at DTX_MIN.
// -DNEG_PRELOAD: partner preloads C at its own reset (the legacy stub) -> CREDIT_LOSS / OVERFLOW.
module tb_coll_credit_producer;
 parameter integer C=256, CW=9, SYNC=2, FWD=77, RET=137, NFLITS=30000, DTX_MIN=25, WSTG=14, H=2;
 // PHY slightly faster than core (same nominal rate, slow phase sweep) so every synchroniser sees edges
 // inside its metastability window; the partner runs at the core rate (locked).  Arrival <= drain.
 parameter real TCORE_PS=833.333, TPH_PS=832.9, TPART_PS=833.333;
 localparam integer RBMAX=C;
 // ---------------------------------------------------------------- clocks (independent phases)
 reg clk=0,pclk=0,bclk=0;
 initial begin #(137); forever #(TCORE_PS/2.0) clk=~clk; end
 initial begin #(411); forever #(TPH_PS/2.0) pclk=~pclk; end
 initial begin #(59);  forever #(TPART_PS/2.0) bclk=~bclk; end
 // ---------------------------------------------------------------- resets
 reg por_stream=1,por_link=1,por_part=1;wire rst_n,prst_n;
 ot_hbm_collective_reset_entry #(.ENABLE(1)) u_rst(.clk_stream(clk),.clk_link(pclk),.por_stream(por_stream),
  .por_link(por_link),.rst_n(rst_n),.prst_n(prst_n));
 reg [1:0] brs;always @(posedge bclk or posedge por_part)if(por_part)brs<=2'b11;else brs<={brs[0],1'b0};
 wire brst_n=~brs[1];
 // ---------------------------------------------------------------- RX endpoint
 wire [CW-1:0] k_gray,k_gray_ph;wire ready,ready_ph;reg rb_pop=0;
 ot_hbm_coll_credit_producer #(.C(C),.CW(CW),.SYNC(SYNC)) u_prod(.clk(clk),.rst_n(rst_n),.phy_rst_n(prst_n),
  .rb_pop(rb_pop),.k_gray(k_gray),.ready(ready));
 ot_hbm_coll_credit_phy_tx #(.CW(CW),.SYNC(SYNC)) u_ptx(.pclk(pclk),.prst_n(prst_n),.k_gray_core(k_gray),
  .ready_core(ready),.k_gray_ph(k_gray_ph),.ready_ph(ready_ph));
 // RX CDC (committed II1 refill), 64 b payload carries the sequence number.
 reg cdc_in_v=0;reg [63:0] cdc_in_d=0;wire cdc_in_r,cdc_out_v;wire [63:0] cdc_out_d;wire cdc_we,cdc_re,cdc_f;
 wire cdc_out_r;
 ot_hbm_collective_protected_cdc_refill #(.ENABLE(1),.W(64),.AW(6)) u_rxcdc(.wclk(pclk),.wrst_n(prst_n),
  .in_v(cdc_in_v),.in_r(cdc_in_r),.in_d(cdc_in_d),.rclk(clk),.rrst_n(rst_n),.out_v(cdc_out_v),.out_r(cdc_out_r),
  .out_d(cdc_out_d),.wempty(cdc_we),.rempty(cdc_re),.fault(cdc_f));
 // ---------------------------------------------------------------- partner
 reg [CW-1:0] k_link=0;reg rdy_link=0;wire can_send;wire [CW-1:0] avail,k_seen;wire rdy_seen;reg send=0;
`ifdef NEG_PRELOAD
 wire rdy_in=1'b1;   // legacy stub: credits preloaded at the partner's own reset
`else
 wire rdy_in=rdy_link;
`endif
 ot_hbm_coll_credit_consumer #(.C(C),.CW(CW),.SYNC(SYNC)) u_cons(.clk(bclk),.rst_n(brst_n),.k_gray_link(k_link),
  .ready_link(rdy_in),.send(send),.can_send(can_send),.avail_o(avail),.k_seen_o(k_seen),.ready_seen_o(rdy_seen));
 // ---------------------------------------------------------------- links (transport delay queues)
 realtime fq_t[0:65535];reg [63:0] fq_d[0:65535];integer fw=0,fr=0;
 realtime rq_t[0:1048575];reg [CW:0] rq_v[0:1048575];integer rw=0,rr=0;
 reg flush=0;
 always @(posedge pclk)if(!flush)begin rq_t[rw%1048576]=$realtime+RET*TCORE_PS;rq_v[rw%1048576]={ready_ph,k_gray_ph};rw=rw+1;end
 initial forever begin
  wait(rr<rw);
  if(rq_t[rr%1048576]>$realtime)#(rq_t[rr%1048576]-$realtime);
  {rdy_link,k_link}=rq_v[rr%1048576];rr=rr+1;
 end
 // ---------------------------------------------------------------- traffic control
 integer seq_tx=0,seq_rx=0,pops=0,sends=0;integer send_pct=100,drain_pct=100;reg send_en=0;
 reg [63:0] rb[0:RBMAX-1];integer rb_w=0,rb_r=0,rb_n=0,rb_max=0;
 // Decisions at negedges (stable before the sampling posedge): no race with the DUT flops.
 always @(negedge bclk)send=brst_n&&send_en&&can_send&&($urandom%100<send_pct);
 always @(posedge bclk)if(brst_n&&send)begin
  fq_t[fw%65536]=$realtime+FWD*TCORE_PS;fq_d[fw%65536]=seq_tx;fw=fw+1;seq_tx=seq_tx+1;sends=sends+1;
 end
 // PHY write side: an arrived flit is written at the next PHY edge; arrival during PHY reset = loss.
 always @(negedge pclk)begin
  cdc_in_v=0;
  if(fr<fw&&fq_t[fr%65536]<=$realtime&&!flush)begin
   if(!prst_n)$fatal(1,"CREDIT_LOSS flit %0d arrived while the CDC write domain is in reset",fq_d[fr%65536]);
   if(fw-fr>2&&fq_t[(fr+2)%65536]<=$realtime)$fatal(1,"CREDIT_PHY_BACKLOG arrivals faster than the PHY clock");
   if(!cdc_in_r)$fatal(1,"CREDIT_OVERFLOW RX CDC full on arrival");
   cdc_in_v=1;cdc_in_d=fq_d[fr%65536];fr=fr+1;
  end
 end
 reg out_r_q=0;assign cdc_out_r=out_r_q;
 always @(negedge clk)begin
  rb_pop=0;out_r_q=0;
  if(rst_n)begin
   if(cdc_f)$fatal(1,"CREDIT_CDC_FAULT");
   if(rb_n>0&&($urandom%100<drain_pct))begin
    if(rb[rb_r]!==seq_rx)$fatal(1,"CREDIT_ORDER got %0d expected %0d",rb[rb_r],seq_rx);
    rb_r=(rb_r+1)%RBMAX;rb_n=rb_n-1;seq_rx=seq_rx+1;pops=pops+1;rb_pop=1;
   end
   // the CDC word visible now is popped at the next posedge iff out_r is high then
   if(rb_n<RBMAX)begin
    out_r_q=1;
    if(cdc_out_v)begin rb[rb_w]=cdc_out_d;rb_w=(rb_w+1)%RBMAX;rb_n=rb_n+1;if(rb_n>rb_max)rb_max=rb_n;end
   end
   if(rb_n>RBMAX)$fatal(1,"CREDIT_OVERFLOW receive buffer");
  end
 end
 // ---------------------------------------------------------------- READY timing rule
 integer core_edges=0,t_prel=-1,t_crel=-1,t_ready=-1,ready_checks=0;reg prst_q=0,rst_q=0,ready_q=0;
 always @(posedge clk)begin
  core_edges=core_edges+1;
  if(ready&&!ready_q)begin
   t_ready=core_edges-1;  // READY was set by the previous edge
   // t_prel / t_crel: core edges completed before each release; READY rises on the (SYNC+1)-th edge after the later
   if(t_ready-((t_prel>t_crel)?t_prel:t_crel)!=SYNC+1)
    $fatal(1,"CREDIT_READY_RULE READY %0d core edges after the later release (expected %0d; prel %0d crel %0d)",
     t_ready-((t_prel>t_crel)?t_prel:t_crel),SYNC+1,t_prel,t_crel);
   ready_checks=ready_checks+1;
  end
  ready_q=ready;
  // rst_n is released BY a core edge: first seen high at the following edge
  if(rst_n&&!rst_q)t_crel=core_edges-1;
  rst_q=rst_n;
 end
 always @(posedge prst_n)t_prel=core_edges;
 task check_ready_rule;begin
  wait(t_ready>=0);@(posedge clk);
 end endtask
 // ---------------------------------------------------------------- TX flight gates
 // lane 0: DTX = CDC depth (64) with long pacer stalls -> never overflows; lane 1: DTX_MIN, no stalls -> full rate.
 wire [1:0] allow;reg [1:0] want=0;wire [1:0] issue=want&allow;
 reg [WSTG-1:0] wv0=0,wv1=0;wire [1:0] cdc_wr={wv1[WSTG-1],wv0[WSTG-1]};
 wire [1:0] tin_r,tout_v;reg [1:0] tout_r=0;wire [1:0] phy_pop=tout_v&tout_r;wire [63:0] td0,td1;
 wire [7:0] infl0,infl1;
 ot_hbm_coll_tx_flight_gate #(.DTX(64),.DW(8),.WSTG(WSTG),.SYNC(SYNC),.H(H)) u_g0(.clk(clk),.rst_n(rst_n),.pclk(pclk),
  .prst_n(prst_n),.issue(issue[0]),.cdc_wr(cdc_wr[0]),.phy_pop(phy_pop[0]),.allow(allow[0]),.inflight_o(infl0));
 ot_hbm_coll_tx_flight_gate #(.DTX(DTX_MIN),.DW(8),.WSTG(WSTG),.SYNC(SYNC),.H(H)) u_g1(.clk(clk),.rst_n(rst_n),.pclk(pclk),
  .prst_n(prst_n),.issue(issue[1]),.cdc_wr(cdc_wr[1]),.phy_pop(phy_pop[1]),.allow(allow[1]),.inflight_o(infl1));
 ot_hbm_collective_protected_cdc_refill #(.ENABLE(1),.W(64),.AW(6)) u_tx0(.wclk(clk),.wrst_n(rst_n),.in_v(cdc_wr[0]),
  .in_r(tin_r[0]),.in_d(64'd0),.rclk(pclk),.rrst_n(prst_n),.out_v(tout_v[0]),.out_r(tout_r[0]),.out_d(td0),.wempty(),.rempty(),.fault());
 ot_hbm_collective_protected_cdc_refill #(.ENABLE(1),.W(64),.AW(6)) u_tx1(.wclk(clk),.wrst_n(rst_n),.in_v(cdc_wr[1]),
  .in_r(tin_r[1]),.in_d(64'd0),.rclk(pclk),.rrst_n(prst_n),.out_v(tout_v[1]),.out_r(tout_r[1]),.out_d(td1),.wempty(),.rempty(),.fault());
 integer tx_issued1=0,tx_win_start=-1,tx_win_issued=0,tx_max0=0;reg tx_measure=0;
 always @(posedge clk)if(rst_n)begin
  wv0<={wv0[WSTG-2:0],issue[0]};wv1<={wv1[WSTG-2:0],issue[1]};
  if(cdc_wr[0]&&!tin_r[0])$fatal(1,"TX_FLIGHT_OVERFLOW lane0: CDC full at the WSTG exit (inflight %0d)",infl0);
  if(cdc_wr[1]&&!tin_r[1])$fatal(1,"TX_FLIGHT_OVERFLOW lane1");
  if(issue[1])tx_issued1=tx_issued1+1;
  if(tx_measure&&issue[1])tx_win_issued=tx_win_issued+1;
 end else begin wv0<=0;wv1<=0;end
 integer stall_ctr=0;
 always @(posedge pclk)begin
  stall_ctr=stall_ctr+1;
  tout_r[0]<=((stall_ctr/97)%3==0)?1'b0:($urandom%8!=0);   // long stalls on lane 0
  tout_r[1]<=1'b1;
 end
 // ---------------------------------------------------------------- scenario
 task cold(input integer core_first,input integer gap);begin
  flush=1;send_en=0;want=0;
  por_stream=1;por_link=1;por_part=1;
  repeat(4)@(posedge clk);
  // coordinated: link in-flight state discarded, queues emptied, partner reset with the endpoint
  fr=fw;rr=rw;k_link=0;rdy_link=0;rb_w=0;rb_r=0;rb_n=0;seq_tx=0;seq_rx=0;pops=0;sends=0;
  flush=0;t_ready=-1;t_prel=-1;t_crel=-1;
  // the partner has traffic waiting from the start: only the credit protocol holds it back
  send_en=1;
  if(core_first)begin por_stream=0;por_part=0;repeat(gap)@(posedge clk);por_link=0;end
  else begin por_link=0;por_part=0;repeat(gap)@(posedge clk);por_stream=0;end
  check_ready_rule();
  @(negedge clk);
 end endtask
 integer i,t0,n0;
 initial begin
  // Scenario 1: PHY (write domain) released 400 cycles after the core.
  cold(1,400);
  want=2'b11;
  // continuous drain: full rate over a window after the loop fills
  drain_pct=100;send_pct=100;
  repeat(2000)@(posedge clk);
  t0=core_edges;n0=pops;repeat(4000)@(posedge clk);
  if(pops-n0<4000*98/100)$fatal(1,"CREDIT_RATE %0d pops in 4000 cycles: C=%0d does not cover the loop",pops-n0,C);
  // TX full-rate window on lane 1 (no stalls)
  tx_win_issued=0;tx_measure=1;repeat(2000)@(posedge clk);tx_measure=0;
  if(tx_win_issued<2000*99/100)$fatal(1,"TX_RATE lane1 issued %0d of 2000 at DTX=%0d",tx_win_issued,DTX_MIN);
  // random drain with stalls
  for(i=0;i<NFLITS;i=i+1)begin
   drain_pct=((i/1500)%4==1)?0:(((i/1500)%4==2)?30:100);send_pct=((i/700)%5==3)?20:100;@(posedge clk);
  end
  // quiesce and check conservation
  @(negedge clk);send_en=0;drain_pct=100;want=0;
  repeat(RET+FWD+600)@(posedge clk);
  if(rb_n!=0||seq_rx!=seq_tx)$fatal(1,"CREDIT_LOSS after quiesce rx=%0d tx=%0d rb=%0d",seq_rx,seq_tx,rb_n);
  if(avail!=C||k_seen!=(pops%(1<<CW)))$fatal(1,"CREDIT_CONSERVATION avail=%0d k_seen=%0d pops=%0d",avail,k_seen,pops);
  $display("PASS_PHASE1 flits=%0d rb_max=%0d",seq_rx,rb_max);
  // Scenario 2: coordinated mid-stream reset while traffic is in flight, core released 400 cycles late.
  @(negedge clk);send_en=1;want=2'b11;drain_pct=50;repeat(3000)@(posedge clk);
  cold(0,400);
  want=2'b11;drain_pct=100;
  for(i=0;i<NFLITS/2;i=i+1)begin drain_pct=((i/900)%3==1)?10:100;@(posedge clk);end
  @(negedge clk);send_en=0;drain_pct=100;want=0;repeat(RET+FWD+600)@(posedge clk);
  if(rb_n!=0||seq_rx!=seq_tx)$fatal(1,"CREDIT_LOSS after reset quiesce rx=%0d tx=%0d",seq_rx,seq_tx);
  if(avail!=C||k_seen!=(pops%(1<<CW)))$fatal(1,"CREDIT_CONSERVATION after reset avail=%0d",avail);
  // Scenario 3: simultaneous release.
  cold(1,0);want=2'b11;repeat(5000)@(posedge clk);
  @(negedge clk);send_en=0;want=0;repeat(RET+FWD+600)@(posedge clk);
  if(seq_rx!=seq_tx||avail!=C)$fatal(1,"CREDIT_CONSERVATION scenario 3");
  if(u_ptx.u_s.meta_events==0||u_cons.u_s.meta_events==0)$fatal(1,"CREDIT_META no synchroniser sampled inside its window: Gray property unexercised");
  $display("META_EVENTS phy_sync=%0d partner_sync=%0d",u_ptx.u_s.meta_events,u_cons.u_s.meta_events);
  if(ready_checks!=3)$fatal(1,"CREDIT_READY_RULE checked %0d releases (expected 3)",ready_checks);
  $display("PASS_CREDIT rx_flits_last=%0d rb_max=%0d C=%0d CW=%0d fwd=%0d ret=%0d tx_issued_lane1=%0d dtx_min=%0d ready_after_release=%0d",
   seq_rx,rb_max,C,CW,FWD,RET,tx_issued1,DTX_MIN,SYNC+1);
  $finish;
 end
 initial begin #(64'd2000000000); $fatal(1,"CREDIT_TIMEOUT"); end
endmodule
