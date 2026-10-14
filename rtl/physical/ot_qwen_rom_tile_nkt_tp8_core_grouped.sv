// Native TP8 configuration ports are explicit; every tile_id must be bound by the die generator.
module ot_qwen_rom_tile_nkt_tp8_core_grouped #(
    parameter integer CMUT = 0
) (
    input  wire              clk_ctl,
    input wire [4:0] clk_rp,
    input wire [7:0] clk_sl,
    input wire clk_node,
    input wire clk_tx_group,
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
    ot_qwen_tile_kids_grouped #(.CODE_BANKS(5), .RPS(0), .CMUT(CMUT), .MCLK(1), .SPLIT(1)) u_kids (.clk(clk_ctl), .clk_rp(clk_rp), .clk_sl(clk_sl), .clk_node(clk_node), .clk_tx_group(clk_tx_group), .clk_rqr(clk_rqr), .rst_n(rst_n),
        .cx_rreq(cx_rreq), .cx_rq(cx_rq), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lq(cx_lq), .cx_td(512'd0), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault),
        .n_a(n_a), .n_b(n_b), .n_va(n_va), .n_y(n_y), .n_vy(n_vy), .t_out(t_out), .t_vout(t_vout),
        .rom_req_m(), .rom_rd({2*5*266{1'b0}}));
endmodule
