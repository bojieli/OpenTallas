`timescale 1ns/1ps
// Static 6-core-edge : 5-FDI-edge transport through a 200 MHz BLOCK stage.
// Six {valid,597b CRCframe} slots = 3588 bits occupy FOUR 1043-bit FDI beats;
// beat 4 of every 5 is reserved idle.
//
// r10 structural redesign (2026-10-15): the r9 gearbox crossed core (1.2 GHz)
// and FDI (1 GHz) directly; ordinary STA sees a 166.7 ps nearest edge pair on
// every such path and cannot see the enabled-bank windows. Here NO path joins
// core and FDI. Both meet only a block register clocked by blk_ck (200 MHz,
// the common /30 of the PLL; blk_tx_ck and blk_rx_ck are two same-phase roots): core->blk and blk->core are integer 6:1, FDI->blk
// and blk->FDI integer 5:1, so every crossing has an ordinary single-cycle
// relation of >= 833 ps (setup) and coincident-edge hold, with no exceptions.
// Requirement: core_ck, fdi_ck, fdi_rx_ck, blk_tx_ck, blk_rx_ck phase-aligned at the
// 5 ns frame (common PLL, synchronous dividers); skew is an ordinary STA check.
//
// Calendar (B(m)=F(5m)=C(6m) are the block edges; frame m0 = first block edge
// after rst_n release, reset released synchronously through blk_tx_ck):
//  core writes word j of frame m into the stage at C(6m+j);
//  TX block register captures the stage at B(m+1);
//  FDI emits beat k at F(5m+6+k), k=0..3; F(5m+10) idle;
//  4-FDI-edge PHY + capture: RX beat k at F(5m+11+k);
//  RX block register captures at B(m+3);
//  core outputs word j at C(6m+19+j): constant 19 core edges (r9: 24).
// Counters advance unconditionally; checks (frame alignment, PHY valid
// calendar, padding, early word) only set sticky faults, never reschedule.
// Every boundary input is captured by a register before any check logic.
// No FIFO, ready, credit, arbiter or retry.
// MUT: 1 padding bit set, 2 wrong output word, 4 core frame misaligned (bench
// mutants; 3 = PHY 5 edges lives in the bench).
module qfd_ucie_six_five #(parameter integer MUT=0)(
 input wire core_ck,fdi_ck,fdi_rx_ck,blk_tx_ck,blk_rx_ck,rst_n,
 input wire tx_valid,input wire[596:0]tx_frame,
 output reg phy_tx_valid,output reg[1042:0]phy_tx_frame,
 input wire phy_rx_valid,input wire[1042:0]phy_rx_frame,
 output reg rx_valid,output reg[596:0]rx_frame,
 output reg core_fault,output reg fdi_fault
);
 // ---- block domain (blk_tx_ck = TX block root): reset release + frame mark
 reg[1:0]rbs;wire rb_n=rbs[1];
 always @(posedge blk_tx_ck or negedge rst_n)if(!rst_n)rbs<=0;else rbs<={rbs[0],1'b1};
 reg bt;
 always @(posedge blk_tx_ck or negedge rb_n)if(!rb_n)bt<=0;else bt<=~bt;
 // ---- local synchronous reset releases (integer-related, ordinary paths)
 reg rc_n,rf_n;
 always @(posedge core_ck or negedge rst_n)if(!rst_n)rc_n<=0;else rc_n<=rb_n;
 always @(posedge fdi_ck or negedge rst_n)if(!rst_n)rf_n<=0;else rf_n<=rb_n;
 // ---- core domain: one-hot position we[j]=1 at C(6m+j) (registered enables,
 // no binary decode on the 3588-flop stage); rs = read select, one position behind
 reg[5:0]we,rs;reg cs;
 localparam[5:0]WE0=(MUT==4)?6'b001000:6'b000100;
 localparam[5:0]RS0=(MUT==4)?6'b000100:6'b000010;
 always @(posedge core_ck or negedge rc_n)
  if(!rc_n)begin we<=WE0;rs<=RS0;cs<=0;end
  else begin we<={we[4:0],we[5]};rs<={rs[4:0],rs[5]};cs<=bt;end
 reg[5:0]stg_v;(* keep *)reg[6*597-1:0]stg_d;
 for(genvar j=0;j<6;j=j+1)begin:g_stage
  always @(posedge core_ck or negedge rc_n)if(!rc_n)stg_v[j]<=0;else if(we[j])stg_v[j]<=tx_valid;
  always @(posedge core_ck)if(we[j])stg_d[j*597+:597]<=tx_frame;
 end
 wire[3587:0]stg_bits;
 for(genvar j=0;j<6;j=j+1)begin:g_pack
  assign stg_bits[j*598+:598]={stg_v[j],stg_d[j*597+:597]};
 end
 // ---- TX block register: captures the whole stage every 5 ns, no enable
 (* keep *)reg[3587:0]txblk;
 always @(posedge blk_tx_ck)txblk<=stg_bits;
 // ---- FDI domain: position tp equals k at F(5m+1+k); 4 = idle. txsel/rxen are
 // the registered one-hot beat enables for the NEXT edge (no decode fan-out).
 reg[2:0]tp;reg[1:0]fw;reg fs;reg[3:0]txsel,rxen;reg rxchk,rx3;
 wire[2:0]tp_n=tp==4?3'd0:tp+1'b1;
 wire[1:0]fw_n=(tp==4 && fw!=3)?fw+1'b1:fw;
 wire[3:0]oh_n={tp_n==3,tp_n==2,tp_n==1,tp_n==0};
 always @(posedge fdi_ck or negedge rf_n)
  if(!rf_n)begin tp<=1;fw<=0;fs<=0;phy_tx_valid<=0;txsel<=0;rxen<=0;rxchk<=0;rx3<=0;end
  else begin
   tp<=tp_n;fw<=fw_n;fs<=bt;
   phy_tx_valid<=|txsel;
   txsel<=(fw_n!=0)?oh_n:4'b0;
   rxen<=(fw_n>=2)?oh_n:4'b0;
   rxchk<=fw_n>=2 && tp_n<4;      // expected PHY valid at the next edge
   rx3<=rxen[3];
  end
 always @(posedge fdi_ck)
  phy_tx_frame<=({1043{txsel[0]}}&txblk[0+:1043])|({1043{txsel[1]}}&txblk[1043+:1043])|
                ({1043{txsel[2]}}&txblk[2086+:1043])|({1043{txsel[3]}}&{(MUT==1),583'b0,txblk[3129+:459]});
 // ---- FDI RX beat registers (fdi_rx_ck root). Beat 3 is captured full width
 // so the padding check works on registered bits; valid bits kept separately reset.
 (* keep *)reg[3587:0]rxb;(* keep *)reg[583:0]rxpad;reg[5:0]rxv;
 always @(posedge fdi_rx_ck)begin
  if(rxen[0])rxb[0+:1043]<=phy_rx_frame;
  if(rxen[1])rxb[1043+:1043]<=phy_rx_frame;
  if(rxen[2])rxb[2086+:1043]<=phy_rx_frame;
  if(rxen[3])begin rxb[3129+:459]<=phy_rx_frame[458:0];rxpad<=phy_rx_frame[1042:459];end
 end
 // word j valid bit 598j+597 lands in beat (598j+597)/1043 at that offset
 always @(posedge fdi_rx_ck or negedge rf_n)
  if(!rf_n)rxv<=0;
  else begin
   if(rxen[0])rxv[0]<=phy_rx_frame[597];
   if(rxen[1])begin rxv[1]<=phy_rx_frame[152];rxv[2]<=phy_rx_frame[750];end
   if(rxen[2])begin rxv[3]<=phy_rx_frame[305];rxv[4]<=phy_rx_frame[903];end
   if(rxen[3])rxv[5]<=phy_rx_frame[458];
  end
 // padding check on the registered beat-3 pad bits, one FDI edge after capture
 reg padbad;
 always @(posedge fdi_rx_ck or negedge rf_n)if(!rf_n)padbad<=0;else padbad<=rx3 && (|rxpad);
 // PHY valid registered at the pin and compared one edge later
 reg pv_q,pv_exp;
 always @(posedge fdi_ck or negedge rf_n)if(!rf_n)begin pv_q<=0;pv_exp<=0;end else begin pv_q<=phy_rx_valid;pv_exp<=rxchk;end
 // ---- RX block register (blk_rx_ck root)
 (* keep *)reg[3587:0]rxblk;reg[5:0]rxblk_v;
 always @(posedge blk_rx_ck)rxblk<=rxb;
 always @(posedge blk_rx_ck or negedge rb_n)if(!rb_n)rxblk_v<=0;else rxblk_v<=rxv;
 // ---- core output: word j of the block captured at B(m) leaves at C(6m+1+j);
 // one-hot AND-OR select (MUT 2 reads one word late)
 wire[5:0]sel=(MUT==2)?we:rs;
 reg[596:0]rword;reg rvalid;integer w;
 always @*begin
  rword=0;rvalid=0;
  for(w=0;w<6;w=w+1)begin
   rword=rword|({597{sel[w]}}&rxblk[w*598+:597]);
   rvalid=rvalid|(sel[w]&rxblk_v[w]);
  end
 end
 always @(posedge core_ck or negedge rc_n)if(!rc_n)rx_valid<=0;else rx_valid<=rvalid;
 always @(posedge core_ck)rx_frame<=rword;
 // ---- checks: sticky faults only
 wire we_bad=(we==0)||((we&(we-1'b1))!=0)||({we[0],we[5:1]}!=rs);
 always @(posedge core_ck or negedge rst_n)
  if(!rst_n)core_fault<=0;
  else begin
   if(!rc_n && tx_valid)core_fault<=1;            // word offered before the frame exists
   if(rc_n && ((bt^cs)!=we[1]))core_fault<=1;     // core frame not aligned to the block clock
   if(rc_n && we_bad)core_fault<=1;
  end
 always @(posedge fdi_ck or negedge rst_n)
  if(!rst_n)fdi_fault<=0;
  else if(rf_n)begin
   if((bt^fs)!=(tp==0))fdi_fault<=1;              // FDI frame not aligned to the block clock
   if(pv_q!=pv_exp)fdi_fault<=1;                  // PHY valid off its compiled calendar
   if(padbad)fdi_fault<=1;
   if(tp>4)fdi_fault<=1;
  end
endmodule
