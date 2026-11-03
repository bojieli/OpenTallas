`timescale 1ns/1ps
`default_nettype none
// DH55-HSPLIT: hd_host_e = lane1 only; see ot_s81hd_host_w_core.sv for the seam contract (l1_rx E->W, l1_tx W->E).
// DH56-HSPLIT (DIE-HEAD-56 FACE-HOME ruling, 3_place r2r census 11-03): the lane1 macro cluster sits ~365 um from
// the W-face seam windows and ~245 um from the S-face coll_o1 window, so three registered mid stages (MID=1):
//   l1rx_m  lane1 RX {flt, rx_v, rx_d} -> l1_rx_o            (602 um rx_d -> u_bout_l1_rx_o: +1 E->W)
//   l1tx_m  l1_tx_i -> lane1 tx_v/tx_d                        (531 um u_bin_l1_tx_i -> lane kf/txd_p: +1 W->E)
//   co_m    lane1 tx flits -> coll_o1                          (539 um gearbox beat_tx -> u_bout_coll_o1: +1 on the
//           physical HOST1 egress link; the safe8 credit/ACK protocol absorbs it, plan lane fixed_cycles +1)
// Valid / fault bits are reset, data unreset.  MID=0 restores the DH55 form (bench reference only).
module ot_s81hd_host_e_core #(
 parameter[1:0]CH_B=2'b11,
 parameter integer MID=1
)(
 input wire ck,rst_n,
 input wire[513:0]coll_i1,
 output wire[511:0]coll_o1,
 output wire[557:0]l1_rx_o,
 input wire[553:0]l1_tx_i
);
 wire rx_v;wire[552:0]rx_d;wire[3:0]flt;wire[511:0]co;
 wire tv;wire[552:0]td;
 ot_s81hd_mesh_lane u_lane1(.ck(ck),.rst_n(rst_n),.chb(CH_B[1]),
  .rx(coll_i1),.tx(co),.tx_v(tv),.tx_d(td),
  .rx_v(rx_v),.rx_d(rx_d),.flt(flt));
 generate if(MID!=0)begin:g_mid
  (* keep="true" *)reg l1rx_mv;(* keep="true" *)reg[3:0]l1rx_mf;(* keep="true" *)reg[552:0]l1rx_md;
  (* keep="true" *)reg l1tx_mv;(* keep="true" *)reg[552:0]l1tx_md;
  (* keep="true" *)reg[511:0]co_m;
  always@(posedge ck or negedge rst_n)if(!rst_n)begin l1rx_mv<=0;l1rx_mf<=0;l1tx_mv<=0;end
   else begin l1rx_mv<=rx_v;l1rx_mf<=flt;l1tx_mv<=l1_tx_i[553];end
  always@(posedge ck)begin l1rx_md<=rx_d;l1tx_md<=l1_tx_i[552:0];co_m<=co;end
  assign l1_rx_o={l1rx_mf,l1rx_mv,l1rx_md};
  assign tv=l1tx_mv;assign td=l1tx_md;assign coll_o1=co_m;
 end else begin:g_direct
  assign l1_rx_o={flt,rx_v,rx_d};
  assign tv=l1_tx_i[553];assign td=l1_tx_i[552:0];assign coll_o1=co;
 end endgenerate
endmodule
`default_nettype wire
