`timescale 1ns/1ps
// Opt-in structural successor of qfd_link_adp512. Eight independent roots;
// every slice holds the complete RXD512 controller, with identical header inputs.
// Parent is wires only: no shared clock, combinational control seam or SRAM bus.
// No cycle added and no payload/credit width reduced. Physical slot fit is pending.
module qfd_link_adp128 #(parameter integer MUT=0) (
 input wire ck,rst_n,c_v, input wire [127:0] c_d,
 output wire c_cr,r_v, output wire [127:0] r_d, input wire r_cr,tx_up,
 output wire tx_v, output wire [146:0] tx_flit,
 input wire rx_v, input wire [146:0] rx_flit, output wire fault);
 ot_qfd_link_adapter #(.W(128),.RXD(512),.SRAM(1),.PINREG(1),.NG(1),.MUT(MUT)) u_body
 (.clk(ck),.rst_n(rst_n),.c_v(c_v),.c_d(c_d),.c_cr(c_cr),.r_v(r_v),.r_d(r_d),.r_cr(r_cr),
 .tx_up(tx_up),.tx_v(tx_v),.tx_flit(tx_flit),.rx_v(rx_v),.rx_flit(rx_flit),.fault(fault));
endmodule
module qfd_link_adp512_split #(parameter integer MUT=0) (
 input wire [7:0] ck, input wire rst_n,c_v, input wire [1023:0] c_d,
 output wire c_cr,r_v, output wire [1023:0] r_d, input wire r_cr,tx_up,
 output wire tx_v, output wire [1042:0] tx_flit,
 input wire rx_v, input wire [1042:0] rx_flit, output wire fault);
 wire [7:0] cc,rv,tv,ff;
 wire [18:0] headers[0:7];
 genvar g;
 generate for(g=0;g<8;g=g+1) begin:g_slice
  wire [146:0] tf;
  wire [146:0] rf={rx_flit[1042],rx_flit[18+128*g+:128],rx_flit[17:0]};
  qfd_link_adp128 #(.MUT((MUT==2 && g!=7)?0:MUT)) u_slice
  (.ck(ck[g]),.rst_n(rst_n),.c_v(c_v),.c_d(c_d[128*g+:128]),.c_cr(cc[g]),
   .r_v(rv[g]),.r_d(r_d[128*g+:128]),.r_cr(r_cr),.tx_up(tx_up),
   .tx_v(tv[g]),.tx_flit(tf),.rx_v(rx_v),.rx_flit(rf),.fault(ff[g]));
  assign tx_flit[18+128*g+:128]=tf[18+:128];
  assign headers[g]={tf[146],tf[17:0]};
 end endgenerate
 assign {tx_flit[1042],tx_flit[17:0]}=headers[0];
 assign c_cr=cc[0]; assign r_v=rv[0]; assign tx_v=tv[0]; assign fault=ff[0];
 // Control state is payload-independent. Equal registered inputs and clocks
 // make cc/rv/tv/ff/header equal in every slice; the bench checks this invariant.
endmodule
