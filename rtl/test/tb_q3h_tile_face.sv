`timescale 1ns/1ps
// Bench-only tile face for the q3h C_B16 fabric bench (Q-DIEPLAN3-CB 2026-10-16).  It reproduces, register for register,
// the A0 parent's (qfd_tile_nk_rp2_45, RPH 3 under qfd_tile_nk_rp2_romleaf) pin faces: tap / reset pin registers
// (ck_fa4), the t_out pin register (ck_fa2) behind the node leaf's TOREG feed-through, the n_a / n_b pin registers
// (ck_fa0 / ck_fa1), the alignment / fault registers and n_y_q (ck_fa3); the node is the REAL hardened node leaf RTL
// ot_qwen_tile_node (FP32 pair adders, TREE_LAT 7, ANR 1).  The matrix engine is replaced by a beat generator: TLD edges
// after the captured go the face emits this slot's K-slice partial vector (vec.hex[op * 16 + K]); the tile's own go ->
// t_out latency is a constant of the tile and does not enter the fabric's exactness.  Checks (counted into tb.errors):
//   go reaches this tile at tb.t_go[op] + LAT, with the op's ib; the tile's x line (hold) = the line tagged with its sidx.
module tb_q3h_tile_face #(
    parameter integer C = 0,
    parameter integer R = 0,
    parameter integer K = 0,          // logical K-slice = morton(C, R)
    parameter integer HOST = 1,
    parameter integer TLD = 5,
    parameter integer LAT = 3,        // compiled bc -> tap latency of this row
    parameter integer NOPS = 4
) (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [507:0] tap,
    output wire [513:0] t_out,
    input  wire [513:0] n_a,
    input  wire [513:0] n_b,
    output wire [513:0] n_y
);
    `include "q3h_cb16_tbdefs.svh"
    reg [507:0] tap_q;
    reg         reset_q;
    always @(posedge ck) begin tap_q <= tap; reset_q <= rst_n; end
    reg [511:0] vmem [0:NOPS*16-1];
    initial $readmemh("vec.hex", vmem);
    reg [TLD-2:0] gd;
    integer bop;
    reg [511:0] td;
    reg         tvd;
    initial begin gd = 0; bop = 0; td = 0; tvd = 0; end
    always @(posedge ck) begin
        gd <= {gd, reset_q & tap_q[0]};
        tvd <= gd[TLD-2];
        if (gd[TLD-2]) begin td <= vmem[bop * 16 + K]; bop <= bop + 1; end
        else td <= 512'd0;
    end
    wire [511:0] to, ny;
    wire         tv, nvy, nf;
    reg  [513:0] n_a_q, n_b_q;
    always @(posedge ck) begin n_a_q <= n_a; n_b_q <= n_b; end
    generate if (HOST != 0) begin : g_node
        ot_qwen_tile_node u_node (.clk(ck), .rst_n(reset_q), .a(n_a_q[511:0]), .b(n_b_q[511:0]), .va(n_a_q[512]),
                                  .y(ny), .vy(nvy), .fault(nf), .t_d(td), .t_vd(tvd), .t_out(to), .t_vout(tv));
    end else begin : g_nonode
        reg [511:0] to_q;
        reg         tv_q;
        always @(posedge ck) begin to_q <= td; tv_q <= reset_q & tvd; end
        assign to = to_q; assign tv = tv_q; assign ny = 512'd0; assign nvy = 1'b0; assign nf = 1'b0;
    end endgenerate
    reg [513:0] t_out_q;
    always @(posedge ck) begin
        t_out_q[511:0] <= to;
        t_out_q[513:512] <= reset_q ? {1'b0, tv} : 2'd0;
    end
    assign t_out = t_out_q;
    reg fy_q, mis_q;
    always @(posedge ck)
        if (!reset_q) begin fy_q <= 1'b0; mis_q <= 1'b0; end
        else begin
            mis_q <= mis_q | (n_a_q[512] ^ n_b_q[512]);
            fy_q  <= n_a_q[513] | n_b_q[513] | mis_q;
        end
    reg [513:0] n_y_q;
    always @(posedge ck) begin
        n_y_q[511:0] <= ny;
        n_y_q[513:512] <= reset_q ? {fy_q, nvy} : 2'd0;
    end
    assign n_y = (HOST != 0) ? n_y_q : 514'd0;
    // ---- checks ----
    integer gseen, o, i;
    reg [63:0] hl;
    initial gseen = 0;
    always @(negedge ck) begin
        if (tap[0] === 1'b1) begin
            if (gseen >= NOPS || tb.cyc != tb.t_go[gseen] + LAT) begin
                $display("FAIL go tile (%0d,%0d): op %0d at cycle %0d, expected %0d", C, R, gseen, tb.cyc,
                         (gseen < NOPS) ? tb.t_go[gseen] + LAT : -1);
                tb.errors = tb.errors + 1;
            end else if (tap[379:1] !== `Q3H_IB(gseen)) begin
                $display("FAIL ib tile (%0d,%0d) op %0d", C, R, gseen);
                tb.errors = tb.errors + 1;
            end
            gseen = gseen + 1;
        end
        for (o = 0; o < NOPS; o = o + 1)
            if (tb.cyc == tb.t_go[o] + LAT + 6) begin
                hl = `Q3H_LINE(o, C, (tb.far ? 7 - R : R));
                for (i = 0; i < 4; i = i + 1)
                    if (tap[380 + 32*i +: 32] !== {hl[16*i +: 16], 16'h0000}) begin
                        $display("FAIL x line tile (%0d,%0d) op %0d quad %0d: %h expected %h", C, R, o, i,
                                 tap[380 + 32*i +: 32], {hl[16*i +: 16], 16'h0000});
                        tb.errors = tb.errors + 1;
                    end
            end
        if (HOST != 0 && reset_q && (nf === 1'b1 || mis_q === 1'b1) && !tb.fault_seen) begin
            $display("NOTE node fault / leg misalignment at tile (%0d,%0d) cycle %0d (nf %b mis %b)", C, R, tb.cyc, nf, mis_q);
            tb.fault_seen = 1;
        end
    end
    final if (gseen != NOPS) begin
        $display("FAIL tile (%0d,%0d) saw %0d gos, expected %0d", C, R, gseen, NOPS);
    end
endmodule
