`timescale 1ns/1ps
// Native credit producer for the HBM collective endpoint CDC (contract: tools/hbm_collective_cdc_design.py,
// claude/hbm-collective-cdc-design-v2-20261007 2ae0d7d33, results/rtl/hbm_collective_cdc_design_20261007).
// Replaces the testbench preload (eg_cred = 1<<RXAW) and the core-clock rx_credit pulse with a real crossing.
//
//   ot_hbm_coll_credit_producer  RX endpoint, CORE domain.  K: CW-bit free-running RETIREMENT counter,
//                                +1 per receive-buffer pop, registered as Gray; READY: one level, raised
//                                SYNC+1 core edges after BOTH domains left reset (3 edges at SYNC=2).
//   ot_hbm_coll_credit_phy_tx    RX endpoint, PHY domain: SYNC-flop synchronisers of K and READY; the PHY
//                                TX carries them to the partner in its control field.
//   ot_hbm_coll_credit_consumer  PARTNER, its core domain: synchronises K/READY as received, keeps `sent`,
//                                avail = (READY ? C : 0) + K - sent (mod 2^CW); may send while avail != 0.
//                                The configured C is added on READY (one synchronised level, never counted).
//   ot_hbm_coll_tx_flight_gate   TX endpoint, CORE domain: issue only while issued - sync(TX CDC pops) < DTX,
//                                counting the WSTG flight and the Gray/sync lag; full rate needs
//                                DTX >= WSTG + 2*SYNC + H + 7 (= 27 at WSTG 14, SYNC 2, H 2; the design model's 25
//                                plus the registered popped count and the registered allow).
// Contract assertions (simulation; `ifndef SYNTHESIS): CREDIT_WIDTH (2^CW > C), CREDIT_LOSS (a pop before
// READY: data reached the buffer before any grant), CREDIT_READY_EARLY, CREDIT_OVERGRANT (avail > C),
// CREDIT_OVERSEND (send with avail 0), CREDIT_STALE (partner keeps credits after the far end left READY
// without a coordinated reset), DTX bound (elaboration), TX_FLIGHT (inflight > DTX).
// Synthesis: plain flops; every synchroniser is ot_hbm_coll_sync (ASYNC_REG, no logic between stages).

// SYNC-stage synchroniser.  Simulation models metastability: a bit that changed less than META_PS before
// the sampling edge resolves to old or new at random (the reason K must be Gray).
module ot_hbm_coll_sync #(parameter integer W=1, SYNC=2, parameter [W-1:0] RV={W{1'b0}})(
 input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] q);
 (* ASYNC_REG="TRUE", keep=1, dont_touch=1 *) reg [W-1:0] s[0:SYNC-1];
 // The first stage samples d; simulation resolves a bit that changed less than META_PS before the edge to
 // old or new at random (evaluated AT the edge, procedurally).
`ifndef SYNTHESIS
 localparam real META_PS=20.0;
 reg [W-1:0] d_prev=0,d_cur=0; realtime t_change=-1.0e9;
 integer meta_events=0;
 always @(d) begin d_prev=d_cur;d_cur=d;t_change=$realtime; end
 function automatic [W-1:0] sample(input [W-1:0] nw,input [W-1:0] old,input realtime age_ps);
  reg [W-1:0] m;
  begin
   if(age_ps<META_PS)begin meta_events=meta_events+1;for(integer b=0;b<W;b=b+1)m[b]=$urandom%2;sample=(nw&m)|(old&~m);end
   else sample=nw;
  end
 endfunction
`endif
 integer i;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)for(i=0;i<SYNC;i=i+1)s[i]<=RV;
  else begin
`ifndef SYNTHESIS
   s[0]<=sample(d,d_prev,($realtime-t_change)*1000.0);
`else
   s[0]<=d;
`endif
   for(i=1;i<SYNC;i=i+1)s[i]<=s[i-1];
  end
 assign q=s[SYNC-1];
endmodule

module ot_hbm_coll_credit_producer #(parameter integer C=256, CW=9, SYNC=2)(
 input wire clk,rst_n,          // core domain (released by ot_hbm_collective_reset_entry)
 input wire phy_rst_n,          // PHY-domain reset level (its own released prst_n), sampled here
 input wire rb_pop,             // receive-buffer pop (one flit retired), core domain
 output wire [CW-1:0] k_gray,   // registered Gray retirement count
 output wire ready              // registered READY level
);
`ifndef SYNTHESIS
 initial if((1<<CW)<=C)$fatal(1,"CREDIT_WIDTH 2^CW=%0d must exceed C=%0d (avail = C would read 0)",1<<CW,C);
`endif
 wire [0:0] phy_rel_q;
 ot_hbm_coll_sync #(.W(1),.SYNC(SYNC)) u_phy_rel(.clk(clk),.rst_n(rst_n),.d(phy_rst_n),.q(phy_rel_q));
 reg core_live,ready_q;reg [CW-1:0] k_bin,k_gray_q;
 wire both_released=phy_rel_q[0]&&core_live;
 wire [CW-1:0] k_bin_n=k_bin+{{(CW-1){1'b0}},rb_pop};
 wire [CW-1:0] k_gray_d;
 assign k_gray_d=k_bin_n^(k_bin_n>>1);
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin core_live<=0;ready_q<=0;k_bin<=0;k_gray_q<=0;end
  else begin
   core_live<=1'b1;
   ready_q<=both_released;
   k_bin<=k_bin_n;k_gray_q<=k_gray_d;
  end
 assign k_gray=k_gray_q;assign ready=ready_q;
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n&&rb_pop&&!ready_q)$fatal(1,"CREDIT_LOSS retirement before READY: a flit reached the buffer before any grant");
 always @(posedge clk)if(rst_n&&ready_q&&!phy_rst_n)$fatal(1,"CREDIT_READY_EARLY READY high while the PHY (CDC write) domain is in reset");
`endif
endmodule

module ot_hbm_coll_credit_phy_tx #(parameter integer CW=9, SYNC=2)(
 input wire pclk,prst_n,input wire [CW-1:0] k_gray_core,input wire ready_core,
 output wire [CW-1:0] k_gray_ph,output wire ready_ph);
 ot_hbm_coll_sync #(.W(CW+1),.SYNC(SYNC)) u_s(.clk(pclk),.rst_n(prst_n),.d({ready_core,k_gray_core}),.q({ready_ph,k_gray_ph}));
endmodule

module ot_hbm_coll_credit_consumer #(parameter integer C=256, CW=9, SYNC=2)(
 input wire clk,rst_n,                         // partner core domain
 input wire [CW-1:0] k_gray_link,input wire ready_link, // as received from the link (asynchronous here)
 input wire send,                              // one flit launched (must hold a credit)
 output wire can_send,output wire [CW-1:0] avail_o,output wire [CW-1:0] k_seen_o,output wire ready_seen_o);
`ifndef SYNTHESIS
 initial if((1<<CW)<=C)$fatal(1,"CREDIT_WIDTH 2^CW=%0d must exceed C=%0d (avail = C would read 0)",1<<CW,C);
`endif
 wire [CW-1:0] kg;wire rdy;
 ot_hbm_coll_sync #(.W(CW+1),.SYNC(SYNC)) u_s(.clk(clk),.rst_n(rst_n),.d({ready_link,k_gray_link}),.q({rdy,kg}));
 reg [CW-1:0] kb;integer j;
 always @*begin kb[CW-1]=kg[CW-1];for(j=CW-2;j>=0;j=j-1)kb[j]=kb[j+1]^kg[j];end
 reg [CW-1:0] sent_q,kb_q;reg rdy_q;
 // registered view of the synchronised count (one more edge, no combinational sync -> use path)
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin kb_q<=0;rdy_q<=0;end else begin kb_q<=kb;rdy_q<=rdy;end
 localparam [CW-1:0] CC=C[CW-1:0];
 // Registered credit view (no combinational path to the partner's launch decision): the next edge's
 // availability is computed from the already-registered K (one edge older, so never more than the truth)
 // and the send count INCLUDING this edge's send.  avail_q <= truth always; the bound is exact.
 wire [CW-1:0] sent_n=sent_q+{{(CW-1){1'b0}},send};
 wire [CW-1:0] avail_n=(rdy_q?CC:{CW{1'b0}})+kb_q-sent_n;
 reg [CW-1:0] avail_q;reg can_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin sent_q<=0;avail_q<=0;can_q<=0;end
  else begin sent_q<=sent_n;avail_q<=avail_n;can_q<=avail_n!=0;end
 assign can_send=can_q;
 assign avail_o=avail_q;assign k_seen_o=kb_q;assign ready_seen_o=rdy_q;
`ifndef SYNTHESIS
 wire [CW-1:0] avail=(rdy_q?CC:{CW{1'b0}})+kb_q-sent_q;   // the true availability at this edge
 always @(posedge clk)if(rst_n)begin
  if(avail>CC)$fatal(1,"CREDIT_OVERGRANT avail=%0d > C=%0d (k_seen=%0d sent=%0d ready=%0d)",avail,C,kb_q,sent_q,rdy_q);
  if(send&&(avail==0||!can_q))$fatal(1,"CREDIT_OVERSEND send with no credit");
  if(rdy&&rdy_q&&((kb-kb_q)&{CW{1'b1}})>CC)$fatal(1,"CREDIT_K_BACKWARDS synchronised K moved from %0d to %0d",kb_q,kb);
  if(!rdy&&rdy_q&&(sent_q!=0||kb_q!=0))$fatal(1,"CREDIT_STALE far end left READY; partner must be reset with it (coordinated cold reset)");
 end
`endif
endmodule

module ot_hbm_coll_tx_flight_gate #(parameter integer DTX=64, DW=8, WSTG=14, SYNC=2, H=2)(
 input wire clk,rst_n,           // core domain
 input wire pclk,prst_n,         // PHY domain (TX CDC read side)
 input wire issue,               // a flit enters the WSTG pipeline (core)
 input wire cdc_wr,              // the flit enters the TX CDC write port after WSTG (core)
 input wire phy_pop,             // TX CDC read (PHY)
 output wire allow,              // core may issue this cycle
 output wire [DW-1:0] inflight_o);
 localparam integer BOUND=WSTG+2*SYNC+H+7;   // +2: registered popped count and registered allow
`ifndef SYNTHESIS
 initial if(DTX<BOUND)$fatal(1,"DTX=%0d below the full-rate bound D_tx >= WSTG+2*SYNC+H+7 = %0d",DTX,BOUND);
 initial if((1<<DW)<=DTX+WSTG)$fatal(1,"DW too narrow for DTX");
`endif
 // PHY-domain pop count as Gray, synchronised into core.
 reg [DW-1:0] pb,pg;
 always @(posedge pclk or negedge prst_n)
  if(!prst_n)begin pb<=0;pg<=0;end
  else if(phy_pop)begin pb<=pb+1'b1;pg<=(pb+1'b1)^((pb+1'b1)>>1);end
 wire [DW-1:0] pgs;
 ot_hbm_coll_sync #(.W(DW),.SYNC(SYNC)) u_s(.clk(clk),.rst_n(rst_n),.d(pg),.q(pgs));
 reg [DW-1:0] popped_s;integer j;
 always @*begin popped_s[DW-1]=pgs[DW-1];for(j=DW-2;j>=0;j=j-1)popped_s[j]=popped_s[j+1]^pgs[j];end
 reg [DW-1:0] issued,written,ps_q;reg allow_q;
 wire [DW-1:0] issued_n=issued+{{(DW-1){1'b0}},issue};
 wire [DW-1:0] written_n=written+{{(DW-1){1'b0}},cdc_wr};
 // allow for the NEXT edge from registered counts: the popped count is one edge older (never ahead of the
 // truth) and the issue count includes this edge's issue, so inflight <= DTX holds exactly.
 wire [DW-1:0] inflight_n=issued_n-ps_q;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin issued<=0;written<=0;ps_q<=0;allow_q<=0;end
  else begin issued<=issued_n;written<=written_n;ps_q<=popped_s;allow_q<=inflight_n<DTX;end
 assign allow=allow_q;
 assign inflight_o=issued-ps_q;
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n&&issue&&!allow_q)$fatal(1,"TX_FLIGHT issue beyond D_tx");
 wire unused_w=^written_n;
`endif
endmodule
