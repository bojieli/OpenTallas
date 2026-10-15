`timescale 1ns/1ps
// qwen-tp8/coll4 2026-10-12: column-ordered physical top of the TP4 io_collective cluster (qfd_io_collective_ct).
// Pure wiring around ot_rom_oneshot_die_m (CT 1): the 546-bit records are re-bundled per 128-bit column so each
// hardened ot_coll_col_tile row has its own contiguous pin band (in_cK / rx_cK on the W face, tx_cK / out_cK on the
// E face, K = 0..3 data columns, K = 4 the {tag, mode, last} column).  Bit k of column K is record bit 128K + k; the
// rx column bundles the four sources: rx_cK[128r + k] = rx_rec[546r + 128K + k] (rx_c4: 34 bits per source).
module ot_coll_io_rt #(
    parameter integer N = 4, parameter integer RANK = 0, parameter integer LANES = 16, parameter integer TAGW = 32,
    parameter integer DEPTH = 32, parameter integer ADD_LAT = 7, parameter integer IB = 4, parameter integer PR = 2,
    parameter integer TXK = 1, parameter integer FPIPE = 2, parameter integer HDLO = 0, parameter integer MEMM = 1,
    parameter integer FSL = 1, parameter integer IBH = 1, parameter integer CT = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          in_valid,
    output wire          in_cr,
    input  wire [127:0]  in_c0, in_c1, in_c2, in_c3,
    input  wire [33:0]   in_c4,
    output wire          tx_valid,
    output wire [127:0]  tx_c0, tx_c1, tx_c2, tx_c3,
    output wire [33:0]   tx_c4,
    input  wire [3:0]    tx_ready,
    input  wire [3:0]    cr_in,
    input  wire [3:0]    rx_valid,
    input  wire [511:0]  rx_c0, rx_c1, rx_c2, rx_c3,
    input  wire [135:0]  rx_c4,
    output wire [3:0]    cr_out,
    output wire          out_valid,
    output wire [127:0]  out_c0, out_c1, out_c2, out_c3,
    output wire          out_last,
    output wire [1:0]    out_rank,
    output wire          out_err,
    output wire          fault,
    output wire [2:0]    fault_code
);
    localparam integer PW = 546;
    wire [PW-1:0]   txr;
    wire [4*PW-1:0] rxr;
    wire [511:0]    od;
    genvar r;
    generate for (r = 0; r < 4; r = r + 1) begin : g_rx
        assign rxr[r*PW +: PW] = {rx_c4[r*34 +: 34], rx_c3[r*128 +: 128], rx_c2[r*128 +: 128], rx_c1[r*128 +: 128],
                                  rx_c0[r*128 +: 128]};
    end endgenerate
    assign {tx_c4, tx_c3, tx_c2, tx_c1, tx_c0} = txr;
    assign {out_c3, out_c2, out_c1, out_c0} = od;
    ot_rom_oneshot_die_m #(.N(N), .RANK(RANK), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH), .ADD_LAT(ADD_LAT), .IB(IB),
        .PR(PR), .OPQ(0), .TXK(TXK), .FPIPE(FPIPE), .HDLO(HDLO), .MEMM(MEMM), .FSL(FSL), .IBH(IBH), .CT(CT)) u_eng (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_cr(in_cr),
        .in_data({in_c3, in_c2, in_c1, in_c0}), .in_last(in_c4[0]), .in_mode(in_c4[1]), .in_tag(in_c4[33:2]),
        .tx_valid(tx_valid), .tx_rec(txr), .tx_ready(tx_ready), .cr_in(cr_in), .rx_valid(rx_valid), .rx_rec(rxr),
        .cr_out(cr_out), .out_valid(out_valid), .out_data(od), .out_last(out_last), .out_rank(out_rank),
        .out_err(out_err), .fault(fault), .fault_code(fault_code));
endmodule
