`timescale 1ns/1ps
// CB16c-COLL 10-22 (STEWARD-QKc / SQC-CB16c ALT, structural, closure-first): REGIONAL SPLIT of a Qwen collective IO face
// (qfd_coll_face_{s0,p,..}_pl) into hardened sub-tiles with their own local clock roots.
//
// Why: the flat 907.2-um face leaf is pin-bound; every wide pin bus hangs on ONE root across an edge (cal_ck tx_data
// pin flops y 457-905 + cdc_fault/peer_slot at y 3-7: 554 boundary sinks over ~0.9 mm -> 128-259 ps TT spread; rx_rck
// rx_data y 9-454; codec0p phy_tx/phy_rx y 10-905).  Gate FIX hint (clock_span): "split into hardened sub-tiles with
// local roots (kind cluster)".
//
// Structure (one face = wires-only parent of 13 hard children):
//   u_core            the face body qfd_coll_face_<p>_cxb (12 roots, 6 SRAMs, calendar/CDC/codec; its boundary flops are
//                     banded beside their roots, NOT spread at its pins)
//   u_txs0..2         qfd_coll_eslice182 (x3) = the tx_data pin register (was td_q, TOK_REG) on entries cal_ck_t0..2
//   u_rxs0..2         qfd_coll_eslice182 (x3) = the rx_data pin register (was the RX CDC o_data rank) on rx_rck_r0..2
//   u_pts0..2         qfd_coll_eslice199 (x3) = phy_tx pin register on codec0p_t0..2           (+1 TX edge, XT)
//   u_prs0..2         qfd_coll_eslice199 (x3) = phy_rx pin register on codec0p_r0..2           (+1 RX edge, XR)
// Each slice is <= ~146 um of its bus, beside its own face pins; one master per width, hardened ONCE, replicated (6x).
// The new clock ports are further ENTRIES of the existing die clocks (as codec0p is of codec0): cal_ck_t* = cal_ck,
// rx_rck_r* = rx_rck, codec0p_t*/r* = codec0p.  Every slice <-> body crossing is a registered one-cycle hop between
// two entries of the same die clock (related same-frequency, static schedule, no flow control).
// Cycles: tx_data 0, rx_data 0 (ranks moved, not added); PHY TX +1 and PHY RX +1, consumed by the static calendar
// (qfd_coll_static_face_x XT/XR: phy_tx_slot +1, peer expectation +1, RX CDC write +1).  Face latency L -> L + 2.
// External equivalence (tb_cb16c_coll_face_cx lockstep vs the original face RTL, same stimulus): phy_tx / phy_tx_valid
// / phy_tx_slot / phy_rx_slot exactly 1 edge later, rx_valid / rx_data exactly 2 edges later, all faults equal (0).
// Die-side interface: every original port keeps its name, width and bit order; 12 clock-entry ports are added.
// Mutants: OT_CB16C_MUT_SWAP (two tx bits crossed in slice 1), OT_CB16C_MUT_RXSKIP (rx slice 0 bypassed),
//          OT_CB16C_MUT_NOXR / OT_CB16C_MUT_NOXT (calendar compensation removed, body file).
module qfd_coll_eslice182(input wire ck, input wire [181:0] d, output reg [181:0] q);
 always @(posedge ck) q <= d;
endmodule

module qfd_coll_eslice199(input wire ck, input wire [198:0] d, output reg [198:0] q);
 always @(posedge ck) q <= d;
endmodule

// Face bodies (hard children).  Same port list and internal names (u_body...) as qfd_coll_face_<p>_pl.
module qfd_coll_face_s0_cxb(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 localparam integer PLD=2, PLK=1;   // hard master: no parameters (no yosys paramod renaming of the bound child)
 // S0 profile (qfd_coll_face_s0_pl): PHY 350, R 0, PEER_R 5, L 378+1+2*PLK; + XT + XR = +2
 qfd_coll_static_face_x #(.FW(546),.PHY(350),.L(378+1+2*PLK+2),.R(0),.PEER_R(5),.TOK_REG(1),.SAFE(1),.PLAND(1),.PLD(PLD),.PLK(PLK),.XT(1),.XR(1))u_body(
 .codec_ck({codec4,codec3,codec2,codec1,codec0}),.codec_phy_ck(codec0p),.cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),.rst_n(rst_n),.tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),.phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),.phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

module qfd_coll_face_p_cxb(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 localparam integer PLD=2, PLK=1;   // hard master: no parameters
 // P profile (qfd_coll_face_p_pl): PHY 20, R 5, PEER_R 5, L 53+1+2*PLK; + XT + XR = +2
 qfd_coll_static_face_x #(.FW(546),.PHY(20),.L(53+1+2*PLK+2),.R(5),.PEER_R(5),.TOK_REG(1),.SAFE(1),.PLAND(1),.PLD(PLD),.PLK(PLK),.XT(1),.XR(1))u_body(
 .codec_ck({codec4,codec3,codec2,codec1,codec0}),.codec_phy_ck(codec0p),.cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),.rst_n(rst_n),.tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),.phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),.phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

// Face parent (wires only).  HARD 1 = S0 body, 2 = P body, 3 = S1 body, 4 = S2 body, 0 = generic body (bench partner faces with any profile).
module qfd_coll_face_cx #(parameter integer PHY=350, L=383, R=0, PEER_R=5, PLD=2, PLK=1, HARD=1)(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire cal_ck_t0,cal_ck_t1,cal_ck_t2,rx_rck_r0,rx_rck_r1,rx_rck_r2,
 input wire codec0p_t0,codec0p_t1,codec0p_t2,codec0p_r0,codec0p_r1,codec0p_r2,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 wire [545:0] b_txd, b_rxd;
 wire [596:0] b_ptx, b_prx;
`define CB16C_BODY_PORTS .cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),\
 .codec0(codec0),.codec1(codec1),.codec2(codec2),.codec3(codec3),.codec4(codec4),.codec0p(codec0p),.rst_n(rst_n),\
 .tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(b_txd),.rx_valid(rx_valid),.rx_data(b_rxd),\
 .phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(b_prx),.phy_tx_valid(phy_tx_valid),.phy_tx(b_ptx),\
 .phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause)
 initial if (HARD != 0 && (PLD != 2 || PLK != 1)) $error("qfd_coll_face_cx: hard bodies are PLD 2 / PLK 1");
 if (HARD == 1) begin : g_s0
  qfd_coll_face_s0_cxb u_core(`CB16C_BODY_PORTS);   // hard master: PLD 2 / PLK 1 fixed
 end else if (HARD == 2) begin : g_p
  qfd_coll_face_p_cxb u_core(`CB16C_BODY_PORTS);   // hard master: PLD 2 / PLK 1 fixed
 end else if (HARD == 3) begin : g_s1
  qfd_coll_face_s1_cxb u_core(`CB16C_BODY_PORTS);  // CB16c-COLL2-SR: S1 hard master
 end else if (HARD == 4) begin : g_s2
  qfd_coll_face_s2_cxb u_core(`CB16C_BODY_PORTS);  // CB16c-COLL2-SR: S2 hard master
 end else begin : g_gen
  qfd_coll_face_gen_cxb #(.PHY(PHY),.L(L),.R(R),.PEER_R(PEER_R),.PLD(PLD),.PLK(PLK)) u_core(`CB16C_BODY_PORTS);
 end
`undef CB16C_BODY_PORTS
 // W edge: tx_data in (cal_ck entries) and rx_data out (rx_rck entries), 182 bits per slice, bit order kept
 wire [545:0] txs_d;
`ifdef OT_CB16C_MUT_SWAP
 assign txs_d = {tx_data[545:184], tx_data[182], tx_data[183], tx_data[181:0]};
`else
 assign txs_d = tx_data;
`endif
 qfd_coll_eslice182 u_txs0(.ck(cal_ck_t0),.d(txs_d[  0+:182]),.q(b_txd[  0+:182]));
 qfd_coll_eslice182 u_txs1(.ck(cal_ck_t1),.d(txs_d[182+:182]),.q(b_txd[182+:182]));
 qfd_coll_eslice182 u_txs2(.ck(cal_ck_t2),.d(txs_d[364+:182]),.q(b_txd[364+:182]));
 wire [181:0] rxs0_q;
 qfd_coll_eslice182 u_rxs0(.ck(rx_rck_r0),.d(b_rxd[  0+:182]),.q(rxs0_q));
`ifdef OT_CB16C_MUT_RXSKIP
 assign rx_data[0+:182] = b_rxd[0+:182];
`else
 assign rx_data[0+:182] = rxs0_q;
`endif
 qfd_coll_eslice182 u_rxs1(.ck(rx_rck_r1),.d(b_rxd[182+:182]),.q(rx_data[182+:182]));
 qfd_coll_eslice182 u_rxs2(.ck(rx_rck_r2),.d(b_rxd[364+:182]),.q(rx_data[364+:182]));
 // E edge: phy_tx out and phy_rx in (codec0p entries), 199 bits per slice, bit order kept
 qfd_coll_eslice199 u_pts0(.ck(codec0p_t0),.d(b_ptx[  0+:199]),.q(phy_tx[  0+:199]));
 qfd_coll_eslice199 u_pts1(.ck(codec0p_t1),.d(b_ptx[199+:199]),.q(phy_tx[199+:199]));
 qfd_coll_eslice199 u_pts2(.ck(codec0p_t2),.d(b_ptx[398+:199]),.q(phy_tx[398+:199]));
 qfd_coll_eslice199 u_prs0(.ck(codec0p_r0),.d(phy_rx[  0+:199]),.q(b_prx[  0+:199]));
 qfd_coll_eslice199 u_prs1(.ck(codec0p_r1),.d(phy_rx[199+:199]),.q(b_prx[199+:199]));
 qfd_coll_eslice199 u_prs2(.ck(codec0p_r2),.d(phy_rx[398+:199]),.q(b_prx[398+:199]));
endmodule

// Generic body (bench partner faces with any profile; not a hardened master) (any profile), same as the hard bodies with parameters.
module qfd_coll_face_gen_cxb #(parameter integer PHY=350, L=383, R=0, PEER_R=5, PLD=2, PLK=1)(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 qfd_coll_static_face_x #(.FW(546),.PHY(PHY),.L(L),.R(R),.PEER_R(PEER_R),.TOK_REG(1),.SAFE(1),.PLAND(1),.PLD(PLD),.PLK(PLK),.XT(1),.XR(1))u_body(
 .codec_ck({codec4,codec3,codec2,codec1,codec0}),.codec_phy_ck(codec0p),.cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),.rst_n(rst_n),.tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),.phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),.phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

// ---------------------------------------------------------------------------------------------------------------
// CB16c-COLL2-SR 10-22: faces S1, S2 (546/597 b: same es182/es199 slices, parent qfd_coll_face_cx HARD 3/4) and R
// (514/565 b: parent qfd_coll_face_r_cx on two new masters, es257 = 514/2 for the W tx_data/rx_data ranks and
// es113 = 565/5 for the E phy_tx/phy_rx ranks; every slice <= 146 um of its bus on its own clock entry).
// ---------------------------------------------------------------------------------------------------------------
module qfd_coll_face_s1_cxb(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 localparam integer PLD=2, PLK=1;   // hard master: no parameters
 // S1 profile (qfd_coll_face_s1_pl): FW 546, PHY 339, R 0, PEER_R 0, L 378+1+2*PLK; + XT + XR = +2
 qfd_coll_static_face_x #(.FW(546),.PHY(339),.L(378+1+2*PLK+2),.R(0),.PEER_R(0),.TOK_REG(1),.SAFE(1),.PLAND(1),.PLD(PLD),.PLK(PLK),.XT(1),.XR(1))u_body(
 .codec_ck({codec4,codec3,codec2,codec1,codec0}),.codec_phy_ck(codec0p),.cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),.rst_n(rst_n),.tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),.phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),.phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

module qfd_coll_face_s2_cxb(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 localparam integer PLD=2, PLK=1;   // hard master: no parameters
 // S2 profile (qfd_coll_face_s2_pl): FW 546, PHY 349, R 5, PEER_R 0, L 378+1+2*PLK; + XT + XR = +2
 qfd_coll_static_face_x #(.FW(546),.PHY(349),.L(378+1+2*PLK+2),.R(5),.PEER_R(0),.TOK_REG(1),.SAFE(1),.PLAND(1),.PLD(PLD),.PLK(PLK),.XT(1),.XR(1))u_body(
 .codec_ck({codec4,codec3,codec2,codec1,codec0}),.codec_phy_ck(codec0p),.cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),.rst_n(rst_n),.tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),.phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),.phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

module qfd_coll_eslice257(input wire ck, input wire [256:0] d, output reg [256:0] q);
 always @(posedge ck) q <= d;
endmodule

module qfd_coll_eslice113(input wire ck, input wire [112:0] d, output reg [112:0] q);
 always @(posedge ck) q <= d;
endmodule

module qfd_coll_face_r_cxb(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[513:0]tx_data,
 output wire rx_valid,output wire[513:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[564:0]phy_rx,
 output wire phy_tx_valid,output wire[564:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 localparam integer PLD=2, PLK=1;   // hard master: no parameters
 // R profile (qfd_coll_face_r_pl): FW 514, PHY 20, R 5, PEER_R 5, L 53+1+2*PLK; + XT + XR = +2
 qfd_coll_static_face_x #(.FW(514),.PHY(20),.L(53+1+2*PLK+2),.R(5),.PEER_R(5),.TOK_REG(1),.SAFE(1),.PLAND(1),.PLD(PLD),.PLK(PLK),.XT(1),.XR(1))u_body(
 .codec_ck({codec4,codec3,codec2,codec1,codec0}),.codec_phy_ck(codec0p),.cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),.rst_n(rst_n),.tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),.phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),.phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

// Generic 514-b body (bench partner faces of R with any profile; not a hardened master).
module qfd_coll_face_gen514_cxb #(parameter integer PHY=20, L=58, R=5, PEER_R=5, PLD=2, PLK=1)(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[513:0]tx_data,
 output wire rx_valid,output wire[513:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[564:0]phy_rx,
 output wire phy_tx_valid,output wire[564:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 qfd_coll_static_face_x #(.FW(514),.PHY(PHY),.L(L),.R(R),.PEER_R(PEER_R),.TOK_REG(1),.SAFE(1),.PLAND(1),.PLD(PLD),.PLK(PLK),.XT(1),.XR(1))u_body(
 .codec_ck({codec4,codec3,codec2,codec1,codec0}),.codec_phy_ck(codec0p),.cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),.rst_n(rst_n),.tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),.phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),.phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

// R face parent (wires only): HARD 1 = R body, 0 = generic 514-b body.  Clock entries: cal_ck_t0..1 / rx_rck_r0..1
// (es257 x2 each, W) and codec0p_t0..4 / codec0p_r0..4 (es113 x5 each, E).  Same cycles as qfd_coll_face_cx (L + 2).
module qfd_coll_face_r_cx #(parameter integer PHY=20, L=58, R=5, PEER_R=5, PLD=2, PLK=1, HARD=1)(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire cal_ck_t0,cal_ck_t1,rx_rck_r0,rx_rck_r1,
 input wire codec0p_t0,codec0p_t1,codec0p_t2,codec0p_t3,codec0p_t4,
 input wire codec0p_r0,codec0p_r1,codec0p_r2,codec0p_r3,codec0p_r4,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[513:0]tx_data,
 output wire rx_valid,output wire[513:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[564:0]phy_rx,
 output wire phy_tx_valid,output wire[564:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 wire [513:0] b_txd, b_rxd;
 wire [564:0] b_ptx, b_prx;
`define CB16C_BODY_PORTS .cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),\
 .codec0(codec0),.codec1(codec1),.codec2(codec2),.codec3(codec3),.codec4(codec4),.codec0p(codec0p),.rst_n(rst_n),\
 .tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(b_txd),.rx_valid(rx_valid),.rx_data(b_rxd),\
 .phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(b_prx),.phy_tx_valid(phy_tx_valid),.phy_tx(b_ptx),\
 .phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause)
 initial if (HARD != 0 && (PLD != 2 || PLK != 1)) $error("qfd_coll_face_r_cx: hard bodies are PLD 2 / PLK 1");
 if (HARD == 1) begin : g_r
  qfd_coll_face_r_cxb u_core(`CB16C_BODY_PORTS);   // hard master: PLD 2 / PLK 1 fixed
 end else begin : g_gen
  qfd_coll_face_gen514_cxb #(.PHY(PHY),.L(L),.R(R),.PEER_R(PEER_R),.PLD(PLD),.PLK(PLK)) u_core(`CB16C_BODY_PORTS);
 end
`undef CB16C_BODY_PORTS
 // W edge: tx_data in (cal_ck entries) and rx_data out (rx_rck entries), 257 bits per slice, bit order kept
 wire [513:0] txs_d;
`ifdef OT_CB16C_MUT_SWAP
 assign txs_d = {tx_data[513:259], tx_data[257], tx_data[258], tx_data[256:0]};
`else
 assign txs_d = tx_data;
`endif
 qfd_coll_eslice257 u_txs0(.ck(cal_ck_t0),.d(txs_d[  0+:257]),.q(b_txd[  0+:257]));
 qfd_coll_eslice257 u_txs1(.ck(cal_ck_t1),.d(txs_d[257+:257]),.q(b_txd[257+:257]));
 wire [256:0] rxs0_q;
 qfd_coll_eslice257 u_rxs0(.ck(rx_rck_r0),.d(b_rxd[  0+:257]),.q(rxs0_q));
`ifdef OT_CB16C_MUT_RXSKIP
 assign rx_data[0+:257] = b_rxd[0+:257];
`else
 assign rx_data[0+:257] = rxs0_q;
`endif
 qfd_coll_eslice257 u_rxs1(.ck(rx_rck_r1),.d(b_rxd[257+:257]),.q(rx_data[257+:257]));
 // E edge: phy_tx out and phy_rx in (codec0p entries), 113 bits per slice, bit order kept
 qfd_coll_eslice113 u_pts0(.ck(codec0p_t0),.d(b_ptx[  0+:113]),.q(phy_tx[  0+:113]));
 qfd_coll_eslice113 u_pts1(.ck(codec0p_t1),.d(b_ptx[113+:113]),.q(phy_tx[113+:113]));
 qfd_coll_eslice113 u_pts2(.ck(codec0p_t2),.d(b_ptx[226+:113]),.q(phy_tx[226+:113]));
 qfd_coll_eslice113 u_pts3(.ck(codec0p_t3),.d(b_ptx[339+:113]),.q(phy_tx[339+:113]));
 qfd_coll_eslice113 u_pts4(.ck(codec0p_t4),.d(b_ptx[452+:113]),.q(phy_tx[452+:113]));
 qfd_coll_eslice113 u_prs0(.ck(codec0p_r0),.d(phy_rx[  0+:113]),.q(b_prx[  0+:113]));
 qfd_coll_eslice113 u_prs1(.ck(codec0p_r1),.d(phy_rx[113+:113]),.q(b_prx[113+:113]));
 qfd_coll_eslice113 u_prs2(.ck(codec0p_r2),.d(phy_rx[226+:113]),.q(b_prx[226+:113]));
 qfd_coll_eslice113 u_prs3(.ck(codec0p_r3),.d(phy_rx[339+:113]),.q(b_prx[339+:113]));
 qfd_coll_eslice113 u_prs4(.ck(codec0p_r4),.d(phy_rx[452+:113]),.q(b_prx[452+:113]));
endmodule
