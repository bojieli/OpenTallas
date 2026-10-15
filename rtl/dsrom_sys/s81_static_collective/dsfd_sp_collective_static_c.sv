`timescale 1ns/1ps
// Native static collective slab source. This is a composition of independently
// hardened leaves, not a single-root replacement for the historical slab view.
// refclk/por feed the existing real PLL hard-IP boundary/reset controller.
// ck_* are the clocks returned by the die delivery tree at each leaf's pin;
// phi-R insertion compensation, reach and reset epoch must be physically bound.
// No grants or ready pins exist. tv* is the scheduled PHY beat-valid signal,
// essential for the 512-bit/every-four-stream-cycles physical bandwidth budget.
module dsfd_sp_collective_static_c #(
 parameter ROM_FILE="",parameter integer CYCLES=1
)(
 input wire[0:0]refclk,por,
 input wire[4:0]ck_control,input wire[7:0]ck_lane,input wire[15:0]ck_hc_lane,
 input wire[1:0]f_rank,
 input wire[512:0]f_crs,output wire[14:0]t_crq,output wire[2203:0]t_vm,
 input wire[514:0]rW0,rW1,rW2,rW3,rE0,rE1,rE2,rE3,
 output wire[511:0]tdW0,tdW1,tdW2,tdW3,tdE0,tdE1,tdE2,tdE3,
 output wire[0:0]tvW0,tvW1,tvW2,tvW3,tvE0,tvE1,tvE2,tvE3,
 output wire[0:0]tfW0,tfW1,tfW2,tfW3,tfE0,tfE1,tfE2,tfE3,
 output wire[0:0]pll_stream,pll_serial,pll_hbm,rst_stream,rst_serial,rst_hbm,
 input wire[84:0]c_cmd,output wire[8:0]c_done,output wire[1:0]c_st,
 input wire[513:0]f_wfc,output wire[513:0]t_wfc,
 input wire[76:0]f_host,output wire[514:0]t_host,
 output wire[8191:0]t_hc_y,output wire[0:0]t_hc_yv,output wire[31:0]t_hc_tag
);
 dsfd_coll_ck clocks(.refclk(refclk),.por(por),.pll_stream(pll_stream),
 .pll_serial(pll_serial),.pll_hbm(pll_hbm),.rst_stream(rst_stream),
 .rst_serial(rst_serial),.rst_hbm(rst_hbm));
 reg[1:0]reset_q;
 always @(posedge ck_control[0] or negedge rst_stream[0])
  if(!rst_stream[0])reset_q<=0;else reset_q<={reset_q[0],1'b1};
 wire[4119:0]rx={rE3,rE2,rE1,rE0,rW3,rW2,rW1,rW0};
 wire[7:0]rx_valid,rx_live,rx_fault,tx_valid;wire[4095:0]rx_data,tx_data;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:L
  assign rx_valid[g]=rx[g*515];assign rx_data[g*512+:512]=rx[g*515+1+:512];
  assign rx_live[g]=rx[g*515+513];assign rx_fault[g]=rx[g*515+514];
 end endgenerate
 s81_static_collective_slab #(.ROM_FILE(ROM_FILE),.CYCLES(CYCLES)) slab(
 .ck_control(ck_control),.ck_lane(ck_lane),.ck_hc_lane(ck_hc_lane),.rst_n(reset_q[1]),
 .f_rank(f_rank),.c_cmd(c_cmd),.c_done(c_done),.c_st(c_st),
 .t_crq(t_crq),.f_crs(f_crs),.t_vm(t_vm),
 .phy_rx_valid(rx_valid),.phy_rx_data(rx_data),.phy_rx_fault(rx_fault),.phy_rx_live(rx_live),
 .phy_tx_valid(tx_valid),.phy_tx_data(tx_data),.f_wfc(f_wfc),.t_wfc(t_wfc),
 .f_host(f_host),.t_host(t_host),.t_hc_y(t_hc_y),.t_hc_yv(t_hc_yv[0]),.t_hc_tag(t_hc_tag));
 assign {tdE3,tdE2,tdE1,tdE0,tdW3,tdW2,tdW1,tdW0}=tx_data;
 assign {tvE3,tvE2,tvE1,tvE0,tvW3,tvW2,tvW1,tvW0}=tx_valid;
 ot_s81ph_ckbuf cW0(.a(ck_lane[0]),.y(tfW0[0]));
 ot_s81ph_ckbuf cW1(.a(ck_lane[1]),.y(tfW1[0]));
 ot_s81ph_ckbuf cW2(.a(ck_lane[2]),.y(tfW2[0]));
 ot_s81ph_ckbuf cW3(.a(ck_lane[3]),.y(tfW3[0]));
 ot_s81ph_ckbuf cE0(.a(ck_lane[4]),.y(tfE0[0]));
 ot_s81ph_ckbuf cE1(.a(ck_lane[5]),.y(tfE1[0]));
 ot_s81ph_ckbuf cE2(.a(ck_lane[6]),.y(tfE2[0]));
 ot_s81ph_ckbuf cE3(.a(ck_lane[7]),.y(tfE3[0]));
endmodule
