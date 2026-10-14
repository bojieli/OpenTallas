`timescale 1ns/1ps
`default_nettype none
// Physical lane-pair ports: byte-identical normative response mapping, each pair has a local W pin bank.
module ot_hgi_qdq_q_pin4 #(
    parameter integer LQ  = 10,     // lane credits a lane (= the slice bank's wide-lane queue depth, 4 + 2 x 3 relay stages,
                                    // B2 SPEC v0.8 D-B2-12; 4 credits at 3 relays measured 1.29x)
    parameter integer LD  = 16,     // per-lane response FIFO (read round trip at 0.5 sector / lane / cycle; >= LQ)
    parameter integer NB  = 32,     // issued-beat FIFO (>= read round trip in beats; 16 caps S=3 at 18 cyc a 16-beat record)
    parameter integer OD  = 64,     // result FIFO beats (>= decode latency 26 + write round trip at S=3)
    parameter integer RQ  = 16,     // record queue
    parameter integer DEC3 = 1,     // decoder: 1 = ot_hgi_qw_dec3 (track B: dxl / dbq / daq tiles), 0 = ot_hgi_qw_dec (one tile)
    parameter integer SPANPIPE = 0, // opt-in: seven local span stages (+6 edges), exact 52-bit product
    parameter integer MUT = 0,
    parameter integer WRSPLIT = 0, // opt-in private payload/completion source
    parameter integer FINFLAGS = 0,
    parameter integer FRONTFAST = 0, // opt-in new mixed frontend physical composition
    parameter integer FASTFIN = 0 // explicit native candidate; new views required
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [682:0]      rec,          // {n_O, n_A, desc_O, desc_A, header, valid} (hgi_die_dispatch 'quant')
    output wire [2:0]        ret,          // {fault, done, ready}
    output wire [8*16-1:0]   wrq,
    input  wire [7:0]        wrq_cr,
    input wire [513:0] wrr_p0, wrr_p1, wrr_p2, wrr_p3,
    output wire [8*280-1:0]  wwq,
    input  wire [7:0]        wwq_cr,
    input  wire [7:0]        wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    ot_hgi_qdq_q #(.LQ(LQ), .LD(LD), .NB(NB), .OD(OD), .RQ(RQ), .DEC3(DEC3), .SPANPIPE(SPANPIPE), .MUT(MUT), .FASTFIN(FASTFIN),.FRONTFAST(FRONTFAST),.FINFLAGS(FINFLAGS),.WRSPLIT(WRSPLIT)) u_qdq (
        .clk(clk), .rst_n(rst_n), .rec(rec), .ret(ret), .wrq(wrq), .wrq_cr(wrq_cr),
        .wrr({wrr_p3,wrr_p2,wrr_p1,wrr_p0}), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done),
        .rg_req(rg_req), .rg_gnt(rg_gnt), .wg_req(wg_req), .wg_gnt(wg_gnt));
endmodule
`default_nettype wire
