`timescale 1ns/1ps
// Own-flop native command root: complete151bit configuration and captured
// four-bit DEL reservation bitmap. Control62 leases/ACK share the native40
// wire but are ignored by the configuration decoder. Producer pacing remains
// an explicit parent contract; this leaf invents no flight delay or sideband.
module ot_hfd_tkm_native_config_leaf(
 input wire clk,rst_n,input wire[39:0]packet,
 output wire start,fault,output wire[11:0]n,output wire[12:0]k,nout,
 output wire[7:0]g,gbase,output wire[15:0]pf,output wire[39:0]obase,rbase,output wire has_r,
 output wire[3:0]reservations
);
 wire[0:0]rr;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 ot_hfd_tkm_cfg_rx u_cfg(.clk(clk),.rst_n(rr[0]),.packet(packet),.start(start),.fault(fault),
  .n(n),.k(k),.nout(nout),.g(g),.gbase(gbase),.pf(pf),.obase(obase),.rbase(rbase),.has_r(has_r));
 ot_hfd_tkm_reservation_rx u_reserve(.clk(clk),.rst_n(rr[0]),.control(packet),.del_reserve(reservations));
endmodule
