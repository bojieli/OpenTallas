`timescale 1ns/1ps
// q18 (2026-10-13): the THIN Qwen ROM die tile master: the pins of ot_qwen_rom_tile_nk (r5: RPH 2 + NDH 1 + RQR 1, XTX 2)
// over hardened children ONLY -- ot_qwen_tile_ctl (every tile register outside the other leaves) and ot_qwen_tile_kids
// (5 bank rows, 8 lane slices, the tree node, wired).  No register, no gate at this level: the parent is wires and the
// clock / reset distribution to 15 child pins.  Cycle-exact to ot_qwen_rom_tile_nk at the same parameters.
module ot_qwen_rom_tile_nkt #(
    parameter integer CMUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    input  wire              ib_go,
    input  wire [378:0]      ib,
    input  wire [127:0]      xl,
    output wire [511:0]      t_out,
    output wire              t_vout,
    input  wire [511:0]      n_a,
    input  wire [511:0]      n_b,
    input  wire              n_va,
    output wire [511:0]      n_y,
    output wire              n_vy,
    output wire              fault
);
    wire [69:0]   cx_rreq;
    wire [5119:0] cx_rq;
    wire [3127:0] cx_ld;
    wire [583:0]  cx_lq;
    wire [2047:0] cx_rqr;
    wire [71:0] cx_lerr;
    genvar li;
    generate for(li=0;li<8;li=li+1) begin:g_lerr
        assign cx_lerr[9*li+:9] = cx_lq[73*li+64+:9];
    end endgenerate
    wire          cx_tvd, cx_nfault;
    ot_qwen_tile_ctl u_ctl (.clk(clk), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl), .fault(fault),
        .cx_rreq(cx_rreq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lerr(cx_lerr), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault));
    ot_qwen_tile_kids #(.CODE_BANKS(5), .RPS(0), .CMUT(CMUT), .MCLK(1), .SPLIT(1)) u_kids (.clk(clk), .clk_rp({5{clk}}), .clk_sl({8{clk}}), .clk_node(clk), .clk_tx({8{clk}}), .clk_rqr({2{clk}}), .rst_n(rst_n),
        .cx_rreq(cx_rreq), .cx_rq(cx_rq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lq(cx_lq), .cx_td(512'd0), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault),
        .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .t_out(t_out), .t_vout(t_vout),
        .rom_req_m(), .rom_rd({2*5*266{1'b0}}));
endmodule

// Independent die-delivered child clocks: 15 entries, each at phi minus the child insertion.
`timescale 1ns/1ps
// q18 (2026-10-13): the THIN Qwen ROM die tile master: the pins of ot_qwen_rom_tile_nk (r5: RPH 2 + NDH 1 + RQR 1, XTX 2)
// over hardened children ONLY -- ot_qwen_tile_ctl (every tile register outside the other leaves) and ot_qwen_tile_kids
// (5 bank rows, 8 lane slices, the tree node, wired).  No register, no gate at this level: the parent is wires and the
// clock / reset distribution to 15 child pins.  Cycle-exact to ot_qwen_rom_tile_nk at the same parameters.
module ot_qwen_rom_tile_nkt_mc #(
    parameter integer CMUT = 0
) (
    input  wire              clk_ctl,
    input wire [4:0] clk_rp,
    input wire [7:0] clk_sl,
    input wire clk_node,
    input wire [7:0] clk_tx,
    input wire [1:0] clk_rqr,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    input  wire              ib_go,
    input  wire [378:0]      ib,
    input  wire [127:0]      xl,
    output wire [511:0]      t_out,
    output wire              t_vout,
    input  wire [511:0]      n_a,
    input  wire [511:0]      n_b,
    input  wire              n_va,
    output wire [511:0]      n_y,
    output wire              n_vy,
    output wire              fault
);
    wire [69:0]   cx_rreq;
    wire [5119:0] cx_rq;
    wire [3127:0] cx_ld;
    wire [583:0]  cx_lq;
    wire [2047:0] cx_rqr;
    wire [71:0] cx_lerr;
    genvar li;
    generate for(li=0;li<8;li=li+1) begin:g_lerr
        assign cx_lerr[9*li+:9] = cx_lq[73*li+64+:9];
    end endgenerate
    wire          cx_tvd, cx_nfault;
    ot_qwen_tile_ctl u_ctl (.clk(clk_ctl), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl), .fault(fault),
        .cx_rreq(cx_rreq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lerr(cx_lerr), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault));
    ot_qwen_tile_kids #(.CODE_BANKS(5), .RPS(0), .CMUT(CMUT), .MCLK(1), .SPLIT(1)) u_kids (.clk(clk_ctl), .clk_rp(clk_rp), .clk_sl(clk_sl), .clk_node(clk_node), .clk_tx(clk_tx), .clk_rqr(clk_rqr), .rst_n(rst_n),
        .cx_rreq(cx_rreq), .cx_rq(cx_rq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lq(cx_lq), .cx_td(512'd0), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault),
        .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .t_out(t_out), .t_vout(t_vout),
        .rom_req_m(), .rom_rd({2*5*266{1'b0}}));
endmodule

// Native TP8 configuration ports are explicit; every tile_id must be bound by the die generator.
module ot_qwen_rom_tile_nkt_tp8_core #(
    parameter integer CMUT = 0
) (
    input  wire              clk_ctl,
    input wire [4:0] clk_rp,
    input wire [7:0] clk_sl,
    input wire clk_node,
    input wire [7:0] clk_tx,
    input wire [1:0] clk_rqr,
    input  wire              rst_n,
    input  wire [15:0]       tile_id,
    input  wire              ib_go,
    input  wire [378:0]      ib,
    input  wire [127:0]      x_response,
    output wire [511:0]      t_out,
    output wire              t_vout,
    input  wire [511:0]      n_a,
    input  wire [511:0]      n_b,
    input  wire              n_va,
    output wire [511:0]      n_y,
    output wire              n_vy,
    output wire              fault,
    output wire [3:0] cx_xre,
    output wire [95:0] cx_xaddr,
    output wire [20:0] cx_xepoch
);
    wire [69:0]   cx_rreq;
    wire [5119:0] cx_rq;
    wire [3127:0] cx_ld;
    wire [583:0]  cx_lq;
    wire [2047:0] cx_rqr;
    wire [71:0] cx_lerr;
    genvar li;
    generate for(li=0;li<8;li=li+1) begin:g_lerr
        assign cx_lerr[9*li+:9] = cx_lq[73*li+64+:9];
    end endgenerate
    wire          cx_tvd, cx_nfault;
    ot_qwen_tile_ctl_tp8 u_ctl (.clk(clk_ctl), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(x_response), .fault(fault), .cx_xre(cx_xre), .cx_xaddr(cx_xaddr), .cx_xepoch(cx_xepoch),
        .cx_rreq(cx_rreq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lerr(cx_lerr), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault));
    ot_qwen_tile_kids #(.CODE_BANKS(5), .RPS(0), .CMUT(CMUT), .MCLK(1), .SPLIT(1)) u_kids (.clk(clk_ctl), .clk_rp(clk_rp), .clk_sl(clk_sl), .clk_node(clk_node), .clk_tx(clk_tx), .clk_rqr(clk_rqr), .rst_n(rst_n),
        .cx_rreq(cx_rreq), .cx_rq(cx_rq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lq(cx_lq), .cx_td(512'd0), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault),
        .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .t_out(t_out), .t_vout(t_vout),
        .rom_req_m(), .rom_rd({2*5*266{1'b0}}));
endmodule
