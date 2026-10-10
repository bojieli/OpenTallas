`timescale 1ns/1ps
// A symbolic leaf vehicle verifies only the composition. The actual SRAM/ECC
// half has separate real transaction gates; this vehicle cannot qualify it.
module ot_hcoll_port #(parameter integer PWT=545,PAYLOAD_ECC=0,FACE_CK=0)(
 input wire clk,ckf,rst_n,qp_push,qr_push,sw_cr_ret,ph_rx_v,rb_cr,
 input wire [PWT-1:0] qp_din,qr_din,ph_rx_flit,
 output wire ph_tx_v,rb_v,stall,fault,ecc_ce,
 output wire [1:0] rx_ecc_drop,
 output wire [PWT-1:0] ph_tx_flit,rb_d
);
 assign ph_tx_v=qp_push^qr_push^sw_cr_ret^clk;
 assign ph_tx_flit=qp_din^{qr_din[PWT-2:0],qr_din[PWT-1]};
 assign rb_v=ph_rx_v^rb_cr^ckf;
 assign rb_d=ph_rx_flit;
 assign stall=qp_push^sw_cr_ret^rst_n;
 assign fault=qr_push^rb_cr^rst_n;
 assign ecc_ce=PAYLOAD_ECC?ph_rx_v:1'b0;
 assign rx_ecc_drop={FACE_CK?ckf:clk,rb_cr};
endmodule
module tb_pair_wiring;
 parameter integer MUT=0;
 localparam integer PWT=545;
 reg clk=0,rst_n=0;reg [1:0] ckf=0,qp_push,qr_push,sw_cr_ret,ph_rx_v,rb_cr;
 reg [1089:0] qp_din,qr_din,ph_rx_flit;
 wire [1:0] ph_tx_v,rb_v,stall,fault,ecc_ce;
 wire [3:0] rx_ecc_drop;
 wire [1089:0] ph_tx_flit,rb_d;
 wire [1:0] ref_tx_v,ref_rb_v,ref_stall,ref_fault,ref_ce;
 wire [3:0] ref_drop;
 wire [1089:0] ref_tx,ref_rb;
 ot_hcoll_port2_tiles #(.PAYLOAD_ECC(1),.FACE_CK(1),.MUT_MAP(MUT)) dut(.*);
 for(genvar h=0;h<2;h=h+1) begin : g_ref
  ot_hcoll_port #(.PAYLOAD_ECC(1),.FACE_CK(1)) refhalf(
   .clk(clk),.ckf(ckf[h]),.rst_n(rst_n),.qp_push(qp_push[h]),.qr_push(qr_push[h]),
   .sw_cr_ret(sw_cr_ret[h]),.ph_rx_v(ph_rx_v[h]),.rb_cr(rb_cr[h]),
   .qp_din(qp_din[h*545+:545]),.qr_din(qr_din[h*545+:545]),.ph_rx_flit(ph_rx_flit[h*545+:545]),
   .ph_tx_v(ref_tx_v[h]),.ph_tx_flit(ref_tx[h*545+:545]),.rb_v(ref_rb_v[h]),.rb_d(ref_rb[h*545+:545]),
   .stall(ref_stall[h]),.fault(ref_fault[h]),.ecc_ce(ref_ce[h]),.rx_ecc_drop(ref_drop[h*2+:2]));
 end
 initial begin
  for(integer n=0;n<512;n=n+1)begin
   clk=$urandom;ckf=$urandom;rst_n=$urandom;qp_push=$urandom;qr_push=$urandom;
   sw_cr_ret=$urandom;ph_rx_v=$urandom;rb_cr=$urandom;
   for(integer b=0;b<1090;b=b+1)begin qp_din[b]=$urandom;qr_din[b]=$urandom;ph_rx_flit[b]=$urandom;end
   #1;
   if({ph_tx_v,rb_v,stall,fault,ecc_ce,rx_ecc_drop,ph_tx_flit,rb_d} !==
      {ref_tx_v,ref_rb_v,ref_stall,ref_fault,ref_ce,ref_drop,ref_tx,ref_rb})
     $fatal(1,"PORT2_TILES_WIRING_MISMATCH iteration=%0d",n);
  end
  $display("PORT2_TILES_WIRING PASS vectors=512 full_width=545 halves=2");$finish;
 end
endmodule
