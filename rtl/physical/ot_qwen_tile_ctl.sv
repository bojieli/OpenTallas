`timescale 1ns/1ps
// q18 (2026-10-13): the CONTROL LEAF of the thin Qwen ROM die tile (hardened once, 1 a tile): every register of the tile
// that is not inside a hardened child -- the instruction / x pin registers (ib, ib_go, xl, tile_id), the engine control
// (ot_qwen_w12_matvec_part: issue loop, tags, mq / s2 captures), the x delay line, the transmit rungs and reset relays
// of the 8 lane-slice leaves, the bank rows' request relay and the two group registers of their relay words, and the
// tile's fault pin register.  = ot_qwen_rom_tile_logic_w12 at the tile-die parameters with CEXT 1 (the children's seams
// on the cx_* ports) + the fault register of ot_qwen_rom_tile_nk.  Parameter-free top (the parent instantiates the
// hardened leaf by this fixed name, as ot_qwen_tile_lsl / _rpair / _node).  Own clock root; seams are flop -> flop
// except the group OR of the bank rows' relay words in front of the group registers.
module ot_qwen_tile_ctl (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [15:0]   tile_id,
    input  wire          ib_go,
    input  wire [378:0]  ib,
    input  wire [127:0]  xl,
    output wire          fault,
    output wire [3:0] cx_xre,
    output wire [95:0] cx_xaddr,
    output wire [20:0] cx_xepoch,
    output wire [69:0]   cx_rreq,
    input  wire [2047:0] cx_rqr,
    output wire [3127:0] cx_ld,
    input  wire [71:0] cx_lerr,
    output wire          cx_tvd,
    input  wire          cx_nfault
);
    wire tile_fault;
    wire [583:0] cx_lq;
    genvar li;
    generate for(li=0;li<8;li=li+1) begin:g_lerr
        assign cx_lq[73*li+:73] = {cx_lerr[9*li+:9],64'd0};
    end endgenerate
    ot_qwen_rom_tile_logic_w12 #(.NW(18), .GT(6144), .SMIN(7), .CODE_BANKS(5), .KV_LOCAL(0), .KV_VB(131072), .KV_NH(2),
        .MEM_EXTRA(1), .ACC_LAT(7), .TREE_LAT(7), .FAST_ISSUE(1), .KV_PREP(4), .MUL_LAT(8), .ROM_PIPE(1), .ROM_ARELAY(2),
        .ROM_CAP2(1), .ROM_CAPX(2), .LRST(3), .ARPB(1), .MPR(1), .HIER(2), .HIER_HARD(1), .TOREG(1), .TIDR(1), .LRR(1),
        .RPH(2), .RQR(1), .XTX(2), .ANR(1), .BAW(12), .NDH(1), .BMUT(0), .CEXT(2)) u_logic (
        .clk(clk), .rst_n(rst_n), .tile_id(tile_id), .ib_go(ib_go), .ib(ib), .xl(xl),
        .t_out(), .t_vout(), .n_a(512'd0), .n_b(512'd0), .n_va(1'b0), .n_y(), .n_vy(), .fault(tile_fault),
        .rom_ce(), .rom_addr(), .rom_addr_n(), .rom_addr_b(), .rom_req_m(), .rom_rd({2*5*266{1'b0}}),
        .kvs_r_ce(), .kvs_r_addr(), .kvs_rd(512'd0), .kv_re(), .kv_addr(), .kv_q({4*16*32{1'b0}}),
        .cx_xre(cx_xre), .cx_xaddr(cx_xaddr), .cx_xepoch(cx_xepoch),
        .cx_rreq(cx_rreq), .cx_rq(5120'd0), .cx_rqr(cx_rqr), .cx_ld(cx_ld), .cx_lq(cx_lq), .cx_td(), .cx_tvd(cx_tvd), .cx_nfault(cx_nfault));
    (* keep *) reg fault_q;    // the tile's flop-launched fault pin (ot_qwen_rom_tile_nk fault_q)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_q <= 1'b0; else fault_q <= tile_fault;
    assign fault = fault_q;
endmodule
