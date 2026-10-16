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
// r11 structural fix (2026-10-15, Q-DVM+LINK): every wide crossing between two
// CTS roots now passes a HALF-CYCLE register on the negedge of the fast root
// (core / FDI / FDI-RX), so ordinary STA sees setup T/2 and hold T/2 instead of
// a coincident-edge hold race between independently balanced trees (r10 route
// a534fb815: FF hold -104 ps on 16,901 endpoints, 43k hold buffers). Same
// calendar, 0 added cycles: txmid (core neg) before txblk; txfm (fdi neg) after
// the beat mux; rxen_n (fdi_rx neg) before the RX beat enables; rxmid (fdi_rx
// neg) before rxblk; rxcm/rvm (core neg) after the word select. Negedge
// registers carry no reset (data only).
// r12 (2026-10-15, Q-DVM+LINK): ONE pin register per data input (txp core /
// rxp fdi_rx), so every input has a single capture flop at its pin (r11 route
// 95790e7a6: 7,590 FF hold violators were the 6-way stg_d / 4-way rxq input
// fanout captures, unpaddable by recipe 2). Same calendar, 0 added cycles: stage
// words 0..4 are written one edge later from txp and word 5 rides txp into txmid
// at C(6m+5.5); rxq beats 0..2 are written one edge later from rxp and beat 3
// (with its pad and valid bits) rides rxp into rxmid at F(5m+14.5).
// MUT: 1 padding bit set, 2 wrong output word, 4 core frame misaligned, 5 TX stage
// crossing on the full-cycle edge, 6 RX beat crossing on the full-cycle edge (bench
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
 // we/rs are replicated: three copies, each owning 199 bits of every word (<=256 loads)
 reg[5:0]we,rs;reg cs;(* keep *)reg[5:0]we_c[0:2];(* keep *)reg[5:0]rs_c[0:2];
 localparam[5:0]WE0=(MUT==4)?6'b001000:6'b000100;
 localparam[5:0]RS0=(MUT==4)?6'b000100:6'b000010;
 always @(posedge core_ck or negedge rc_n)
  if(!rc_n)begin we<=WE0;rs<=RS0;cs<=0;
   we_c[0]<=WE0;we_c[1]<=WE0;we_c[2]<=WE0;rs_c[0]<=RS0;rs_c[1]<=RS0;rs_c[2]<=RS0;end
  else begin we<={we[4:0],we[5]};rs<={rs[4:0],rs[5]};cs<=bt;
   for(int c=0;c<3;c++)begin we_c[c]<={we_c[c][4:0],we_c[c][5]};rs_c[c]<={rs_c[c][4:0],rs_c[c][5]};end
  end
 // input pin registers: word j offered at C(6m+j) sits in txp from C(6m+j) to C(6m+j+1)
 reg txp_v;(* keep *)reg[596:0]txp;
 always @(posedge core_ck)txp_v<=tx_valid;   // no reset: the core_fault early-word check reads it during !rc_n
 always @(posedge core_ck)txp<=tx_frame;
 // stage words 0..4, written at C(6m+j+1) (one-hot we at j+1); word 5 is never stored
 reg[4:0]stg_v;(* keep *)reg[5*597-1:0]stg_d;
 for(genvar j=0;j<5;j=j+1)begin:g_stage
  always @(posedge core_ck or negedge rc_n)if(!rc_n)stg_v[j]<=0;else if(we[j+1])stg_v[j]<=txp_v;
  for(genvar c=0;c<3;c=c+1)begin:g_cp
   always @(posedge core_ck)if(we_c[c][j+1])stg_d[j*597+c*199+:199]<=txp[c*199+:199];
  end
 end
 wire[3587:0]stg_bits;
 for(genvar j=0;j<5;j=j+1)begin:g_pack
  assign stg_bits[j*598+:598]={stg_v[j],stg_d[j*597+:597]};
 end
 assign stg_bits[5*598+:598]={txp_v,txp};
 // ---- TX block register: captures the whole stage every 5 ns, no enable
 (* keep *)reg[3587:0]txmid;
 if(MUT==5)begin:g_m5 always @(posedge core_ck)txmid<=stg_bits;end          // mutant: full-cycle stage (misses word 5)
 else begin:g_txm always @(negedge core_ck)txmid<=stg_bits;end                  // C(6m+5.5) holds words 0..5 of frame m
 (* keep *)reg[3587:0]txblk;
 always @(posedge blk_tx_ck)txblk<=txmid;
 // ---- FDI domain: position tp equals k at F(5m+1+k); 4 = idle. txsel/rxen are
 // the registered one-hot beat enables for the NEXT edge (no decode fan-out).
 reg[2:0]tp;reg[1:0]fw;reg fs;reg[3:0]txsel,rxen;reg rxchk,rx3;
 // beat enables replicated: five copies, each owning <=209 bits of the 1043-bit beat
 (* keep *)reg[3:0]txsel_c[0:4];(* keep *)reg[3:0]rxen_c[0:4];
 wire[2:0]tp_n=tp==4?3'd0:tp+1'b1;
 wire[1:0]fw_n=(tp==4 && fw!=3)?fw+1'b1:fw;
 wire[3:0]oh_n={tp_n==3,tp_n==2,tp_n==1,tp_n==0};
 always @(posedge fdi_ck or negedge rf_n)
  if(!rf_n)begin tp<=1;fw<=0;fs<=0;phy_tx_valid<=0;txsel<=0;rxen<=0;rxchk<=0;rx3<=0;
   for(int c=0;c<5;c++)begin txsel_c[c]<=0;rxen_c[c]<=0;end end
  else begin
   tp<=tp_n;fw<=fw_n;fs<=bt;
   phy_tx_valid<=|txsel;
   txsel<=(fw_n!=0)?oh_n:4'b0;
   rxen<=(fw_n>=2)?oh_n:4'b0;
   for(int c=0;c<5;c++)begin txsel_c[c]<=(fw_n!=0)?oh_n:4'b0;rxen_c[c]<=(fw_n>=2)?oh_n:4'b0;end
   rxchk<=fw_n>=2 && tp_n<4;      // expected PHY valid at the next edge
   rx3<=rxen[3];
  end
 (* keep *)reg[1042:0]txfm;
 wire[1042:0]tb3={(MUT==1),583'b0,txblk[3129+:459]};
 for(genvar c=0;c<5;c=c+1)begin:g_txs
  localparam integer LO=c*209,W=(c==4)?1043-4*209:209;
  // txsel_c at F(x-0.5) already holds the enables for edge F(x)
  always @(negedge fdi_ck)
   txfm[LO+:W]<=({W{txsel_c[c][0]}}&txblk[LO+:W])|({W{txsel_c[c][1]}}&txblk[1043+LO+:W])|
                ({W{txsel_c[c][2]}}&txblk[2086+LO+:W])|({W{txsel_c[c][3]}}&tb3[LO+:W]);
  always @(posedge fdi_ck)phy_tx_frame[LO+:W]<=txfm[LO+:W];
 end
 // ---- FDI RX beat registers (fdi_rx_ck root). Beat 3 is captured full width
 // so the padding check works on registered bits; valid bits kept separately reset.
 // input pin register: beat k at the pins at F(5m+11+k) sits in rxp until F(5m+12+k)
 (* keep *)reg[1042:0]rxp;
 always @(posedge fdi_rx_ck)rxp<=phy_rx_frame;
 (* keep *)reg[3128:0]rxq;reg[5:0]rxv;   // beats 0..2 (written one edge after the pins); beat 3 stays in rxp
 (* keep *)reg[3:0]rxen_n[0:4];reg[3:0]rxen_vn;   // fdi_rx negedge copies of the FDI-domain beat enables
 always @(negedge fdi_rx_ck)begin for(int c=0;c<5;c++)rxen_n[c]<=rxen_c[c];rxen_vn<=rxen;end
 (* keep *)reg[3:0]rxen_p[0:4];reg[3:0]rxen_vp;   // same root, one edge later: write beat k from rxp
 always @(posedge fdi_rx_ck)begin for(int c=0;c<5;c++)rxen_p[c]<=rxen_n[c];rxen_vp<=rxen_vn;end
 for(genvar c=0;c<5;c=c+1)begin:g_rxs
  localparam integer LO=c*209,W=(c==4)?1043-4*209:209;
  for(genvar k=0;k<3;k=k+1)begin:g_k
   always @(posedge fdi_rx_ck)if(rxen_p[c][k])rxq[k*1043+LO+:W]<=rxp[LO+:W];
  end
 end
 wire[3587:0]rxb={rxp[458:0],rxq};wire[583:0]rxpad=rxp[1042:459];
 // word j valid bit 598j+597 lands in beat (598j+597)/1043 at that offset; beat 3's (word 5) rides rxp
 always @(posedge fdi_rx_ck or negedge rf_n)
  if(!rf_n)rxv<=0;
  else begin
   if(rxen_vp[0])rxv[0]<=rxp[597];
   if(rxen_vp[1])begin rxv[1]<=rxp[152];rxv[2]<=rxp[750];end
   if(rxen_vp[2])begin rxv[3]<=rxp[305];rxv[4]<=rxp[903];end
   rxv[5]<=0;
  end
 wire[5:0]rxv_now={rxp[458],rxv[4:0]};
 // padding check on the registered beat-3 pad bits, one FDI edge after capture
 reg padbad;
 always @(posedge fdi_rx_ck or negedge rf_n)if(!rf_n)padbad<=0;else padbad<=rx3 && (|rxpad);
 // PHY valid registered at the pin and compared one edge later
 reg pv_q,pv_exp;
 always @(posedge fdi_ck or negedge rf_n)if(!rf_n)begin pv_q<=0;pv_exp<=0;end else begin pv_q<=phy_rx_valid;pv_exp<=rxchk;end
 // ---- RX block register (blk_rx_ck root)
 (* keep *)reg[3587:0]rxmid;reg[5:0]rxmid_v;
 if(MUT==6)begin:g_m6 always @(posedge fdi_rx_ck)begin rxmid<=rxb;rxmid_v<=rxv_now;end end   // mutant: misses beat 3
 else begin:g_rxm always @(negedge fdi_rx_ck)begin rxmid<=rxb;rxmid_v<=rxv_now;end end           // F(5m+14.5) holds beats 0..3
 (* keep *)reg[3587:0]rxblk;reg[5:0]rxblk_v;
 always @(posedge blk_rx_ck)rxblk<=rxmid;
 always @(posedge blk_rx_ck or negedge rb_n)if(!rb_n)rxblk_v<=0;else rxblk_v<=rxmid_v;
 // ---- core output: word j of the block captured at B(m) leaves at C(6m+1+j);
 // one-hot AND-OR select (MUT 2 reads one word late)
 wire[5:0]sel=(MUT==2)?we:rs;
 reg rvalid;integer w;
 always @*begin
  rvalid=0;
  for(w=0;w<6;w=w+1)rvalid=rvalid|(sel[w]&rxblk_v[w]);
 end
 reg rvm;always @(negedge core_ck)rvm<=rvalid;     // rs at C(x-0.5) = the select for edge C(x)
 always @(posedge core_ck or negedge rc_n)if(!rc_n)rx_valid<=0;else rx_valid<=rvm;
 // data select per replicated copy: copy c owns bits c*199 +: 199 of the word
 for(genvar c=0;c<3;c=c+1)begin:g_rd
  wire[5:0]sc=(MUT==2)?we_c[c]:rs_c[c];
  reg[198:0]rw;integer v;
  always @*begin
   rw=0;
   for(v=0;v<6;v=v+1)rw=rw|({199{sc[v]}}&rxblk[v*598+c*199+:199]);
  end
  (* keep *)reg[198:0]rxcm;
  always @(negedge core_ck)rxcm<=rw;
  always @(posedge core_ck)rx_frame[c*199+:199]<=rxcm;
 end
 // ---- checks: sticky faults only
 wire we_bad=(we==0)||((we&(we-1'b1))!=0)||({we[0],we[5:1]}!=rs)||
             (we_c[0]!=we)||(we_c[1]!=we)||(we_c[2]!=we)||(rs_c[0]!=rs)||(rs_c[1]!=rs)||(rs_c[2]!=rs);
 always @(posedge core_ck or negedge rst_n)
  if(!rst_n)core_fault<=0;
  else begin
   if(!rc_n && txp_v)core_fault<=1;            // word offered before the frame exists
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
