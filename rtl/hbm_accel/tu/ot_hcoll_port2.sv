`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hcoll_port2 (stream coll-fallback, 2026-10-08): TWO ot_hcoll_port slices hardened as one block, for the 4-slice
// split of hfd_coll (ot_hbm_accel_tu_endpoint_ps2: 4 x ot_hcoll_port2 + core).  Port a = even port 2q, port b = odd
// port 2q+1 of the endpoint.  Nothing is shared between the two halves (each keeps its own queues, arbiter, credit,
// TX/RX wire lines, pacing and receive buffer): the pair only changes how the slices are hardened (36 SRAM macros in
// rows with wide horizontal channels, ~50% utilisation) -- 0 cycles against the 8-slice split.
// Every input lands in a flop and every output leaves a flop (inside ot_hcoll_port).
// ---------------------------------------------------------------------------
module ot_hcoll_port2 #(
    parameter integer PWT = 545,
    parameter integer RXPIN = `ifdef OT_HCOLL_RXPIN 1 `else 0 `endif   // struct-close: see ot_hcoll_port RXPIN
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire [1:0]       qp_push,
    input  wire [2*PWT-1:0] qp_din,
    input  wire [1:0]       qr_push,
    input  wire [2*PWT-1:0] qr_din,
    input  wire [1:0]       sw_cr_ret,
    output wire [1:0]       ph_tx_v,
    output wire [2*PWT-1:0] ph_tx_flit,
    input  wire [1:0]       ph_rx_v,
    input  wire [2*PWT-1:0] ph_rx_flit,
    output wire [1:0]       rb_v,
    output wire [2*PWT-1:0] rb_d,
    input  wire [1:0]       rb_cr,
    output wire [1:0]       stall,
    output wire [1:0]       fault
);
    for (genvar h = 0; h < 2; h = h + 1) begin : g_h
        ot_hcoll_port #(.PWT(PWT), .RXPIN(RXPIN)) u_port (.clk(clk), .rst_n(rst_n),
            .qp_push(qp_push[h]), .qp_din(qp_din[h*PWT +: PWT]), .qr_push(qr_push[h]), .qr_din(qr_din[h*PWT +: PWT]),
            .sw_cr_ret(sw_cr_ret[h]), .ph_tx_v(ph_tx_v[h]), .ph_tx_flit(ph_tx_flit[h*PWT +: PWT]),
            .ph_rx_v(ph_rx_v[h]), .ph_rx_flit(ph_rx_flit[h*PWT +: PWT]),
            .rb_v(rb_v[h]), .rb_d(rb_d[h*PWT +: PWT]), .rb_cr(rb_cr[h]), .stall(stall[h]), .fault(fault[h]));
    end
endmodule
