`timescale 1ns/1ps
// COLLIO-SR2 10-23 (COORD tile review: the 864 x 907 split bodies are BAD -- 6 small macros, ~2% fill, ~1.8k unregistered
// body pins): ONE compact flat tile per face.  Wires-only wrapper of the regional split face (qfd_coll_face_cx /
// qfd_coll_face_r_cx, unchanged RTL, so cycles = the split's L+2 and the lockstep bench/mutants stand): the edge slices
// become the FACE PIN REGISTERS of this tile, clocked by the root that owns their face band (tx_data by cal_ck, rx_data by
// rx_rck, phy_tx / phy_rx by codec0p): in the compact tile each bus spans ~150 um, so the separate slice entries are not
// needed.  12 clock entries = the body's 12 roots (same die interface as the body).

module qfd_coll_face_s0_fx(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 qfd_coll_face_cx #(.PHY(350),.L(383),.R(0),.PEER_R(5),.HARD(1)) u_face(
 .cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),
 .codec0(codec0),.codec1(codec1),.codec2(codec2),.codec3(codec3),.codec4(codec4),.codec0p(codec0p),.rst_n(rst_n),
 .cal_ck_t0(cal_ck),.cal_ck_t1(cal_ck),.cal_ck_t2(cal_ck),.rx_rck_r0(rx_rck),.rx_rck_r1(rx_rck),.rx_rck_r2(rx_rck),
 .codec0p_t0(codec0p),.codec0p_t1(codec0p),.codec0p_t2(codec0p),.codec0p_r0(codec0p),.codec0p_r1(codec0p),.codec0p_r2(codec0p),
 .tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),
 .phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),
 .phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

module qfd_coll_face_p_fx(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 qfd_coll_face_cx #(.PHY(20),.L(58),.R(5),.PEER_R(5),.HARD(2)) u_face(
 .cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),
 .codec0(codec0),.codec1(codec1),.codec2(codec2),.codec3(codec3),.codec4(codec4),.codec0p(codec0p),.rst_n(rst_n),
 .cal_ck_t0(cal_ck),.cal_ck_t1(cal_ck),.cal_ck_t2(cal_ck),.rx_rck_r0(rx_rck),.rx_rck_r1(rx_rck),.rx_rck_r2(rx_rck),
 .codec0p_t0(codec0p),.codec0p_t1(codec0p),.codec0p_t2(codec0p),.codec0p_r0(codec0p),.codec0p_r1(codec0p),.codec0p_r2(codec0p),
 .tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),
 .phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),
 .phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

module qfd_coll_face_s1_fx(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 qfd_coll_face_cx #(.PHY(339),.L(383),.R(0),.PEER_R(0),.HARD(3)) u_face(
 .cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),
 .codec0(codec0),.codec1(codec1),.codec2(codec2),.codec3(codec3),.codec4(codec4),.codec0p(codec0p),.rst_n(rst_n),
 .cal_ck_t0(cal_ck),.cal_ck_t1(cal_ck),.cal_ck_t2(cal_ck),.rx_rck_r0(rx_rck),.rx_rck_r1(rx_rck),.rx_rck_r2(rx_rck),
 .codec0p_t0(codec0p),.codec0p_t1(codec0p),.codec0p_t2(codec0p),.codec0p_r0(codec0p),.codec0p_r1(codec0p),.codec0p_r2(codec0p),
 .tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),
 .phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),
 .phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

module qfd_coll_face_s2_fx(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[545:0]tx_data,
 output wire rx_valid,output wire[545:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[596:0]phy_rx,
 output wire phy_tx_valid,output wire[596:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 qfd_coll_face_cx #(.PHY(349),.L(383),.R(5),.PEER_R(0),.HARD(4)) u_face(
 .cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),
 .codec0(codec0),.codec1(codec1),.codec2(codec2),.codec3(codec3),.codec4(codec4),.codec0p(codec0p),.rst_n(rst_n),
 .cal_ck_t0(cal_ck),.cal_ck_t1(cal_ck),.cal_ck_t2(cal_ck),.rx_rck_r0(rx_rck),.rx_rck_r1(rx_rck),.rx_rck_r2(rx_rck),
 .codec0p_t0(codec0p),.codec0p_t1(codec0p),.codec0p_t2(codec0p),.codec0p_r0(codec0p),.codec0p_r1(codec0p),.codec0p_r2(codec0p),
 .tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),
 .phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),
 .phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule

module qfd_coll_face_r_fx(
 input wire cal_ck,cal_lck,tx_wck,tx_rck,rx_wck,rx_rck,
 input wire codec0,codec1,codec2,codec3,codec4,codec0p,input wire rst_n,
 input wire tx_slot,peer_slot,input wire tx_valid,input wire[513:0]tx_data,
 output wire rx_valid,output wire[513:0]rx_data,
 input wire phy_up,phy_rx_valid,input wire[564:0]phy_rx,
 output wire phy_tx_valid,output wire[564:0]phy_tx,
 output wire phy_tx_slot,phy_rx_slot,
 output wire[3:0]cdc_fault,output wire epoch_abort,output wire[7:0]fault_cause
);
 qfd_coll_face_r_cx #(.PHY(20),.L(58),.R(5),.PEER_R(5),.HARD(1)) u_face(
 .cal_ck(cal_ck),.cal_lck(cal_lck),.tx_wck(tx_wck),.tx_rck(tx_rck),.rx_wck(rx_wck),.rx_rck(rx_rck),
 .codec0(codec0),.codec1(codec1),.codec2(codec2),.codec3(codec3),.codec4(codec4),.codec0p(codec0p),.rst_n(rst_n),
 .cal_ck_t0(cal_ck),.cal_ck_t1(cal_ck),.rx_rck_r0(rx_rck),.rx_rck_r1(rx_rck),
 .codec0p_t0(codec0p),.codec0p_t1(codec0p),.codec0p_t2(codec0p),.codec0p_t3(codec0p),.codec0p_t4(codec0p),.codec0p_r0(codec0p),.codec0p_r1(codec0p),.codec0p_r2(codec0p),.codec0p_r3(codec0p),.codec0p_r4(codec0p),
 .tx_slot(tx_slot),.peer_slot(peer_slot),.tx_valid(tx_valid),.tx_data(tx_data),.rx_valid(rx_valid),.rx_data(rx_data),
 .phy_up(phy_up),.phy_rx_valid(phy_rx_valid),.phy_rx(phy_rx),.phy_tx_valid(phy_tx_valid),.phy_tx(phy_tx),
 .phy_tx_slot(phy_tx_slot),.phy_rx_slot(phy_rx_slot),.cdc_fault(cdc_fault),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
endmodule
