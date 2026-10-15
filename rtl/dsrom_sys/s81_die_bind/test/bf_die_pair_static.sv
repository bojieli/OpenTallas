`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// bf_die_pair_static (S-BIND 2026-10-15; from bf_die_pair, s81-die-rtl-bind 2026-10-14): bench composition of ONE S81 BF pair exactly as the die netlist wires it:
// dsfd_bf_col (W, MB 0) | dsfd_bf_front | dsfd_bf_col (E, MB 1), every die port a bit vector, the seams c0 -> W.ci,
// c1 -> E.ci, W.qy -> qy0, E.qy -> qy1.  The pair's die-level inputs / outputs are packed here in the die lane
// convention the q elements share (tools/dsrom_s81_fulldie.py real_ports_r8: x0 = {xs_q0, xs_e0, xs_b, xs_p, xs_pos,
// xs_sv, xs_v} lsb first, x1 = {xs_q1, xs_e1}, cfg = {cfg_a, cfg_d, cfg_v}, st = {busy, fault}, leaf r = {pv, pval,
// prow, pseg, pnseg, perr, ppos}) plus the BF stream port xb = {go_bf, xb_pos, xb_v, xb_b, xb_sv, xb_u, xb_d}.
// Same pins as ot_s81_bf_native (the transaction shadow of tools/s81/bf_txn_bench.py --die-pair).
// ---------------------------------------------------------------------------------------------------------------------
module bf_die_pair_static #(parameter INSTANCE = "", parameter integer DELTA = 0, parameter DESC = "bf_desc.hex") (
    input  wire          clk, rst_n,
    input  wire          cfg_v, input wire [4:0] cfg_a, input wire [47:0] cfg_d,
    input  wire          go, go_bf,
    input  wire          xs_v, input wire [7:0] xs_p, input wire [2:0] xs_b, input wire [1:0] xs_sv,
    input  wire [255:0]  xs_q0, input wire [9:0] xs_e0, input wire [255:0] xs_q1, input wire [9:0] xs_e1,
    input  wire [2:0]    xs_pos, xb_pos,
    input  wire          xb_v, input wire [2:0] xb_b, input wire [3:0] xb_sv, input wire [31:0] xb_u,
    input  wire [1023:0] xb_d,
    output wire [1:0]    pv, output wire [63:0] pval, output wire [31:0] prow, output wire [9:0] pseg, pnseg,
    output wire [1:0]    perr, output wire [5:0] ppos,
    output wire          busy, fault, hph
);
    wire [53:0]   cfg = {cfg_v, cfg_d, cfg_a};
    wire [282:0]  x0  = {xs_v, xs_sv, xs_pos, xs_p, xs_b, xs_e0, xs_q0};
    wire [265:0]  x1  = {xs_e1, xs_q1};
    wire [1067:0] xb  = {xb_d, xb_u, xb_sv, xb_b, xb_v, xb_pos, go_bf};
    wire [1:0]    st;
    wire [775:0]  c0, c1;
    wire [0:0]    qy0, qy1;
    wire [62:0]   rw, re;
    // S-BIND 2026-10-15: the static front fed by its per-pair programme producer; descriptor = the compiled phase
    // table (die: the cfg ROM spare columns; bench: DESC, one line per go in order)
    reg [81:0] dtab [0:1023];
    integer nph = 0;
    initial $readmemh(DESC, dtab);
    reg go_d = 1'b0;
    always @(posedge clk) begin go_d <= go; if (rst_n && go && !go_d) nph <= nph + 1; end
`ifdef OT_BF_ISSUE_TRACE
    always @(posedge clk) if (go != go_d) $display("BFPROG_GO t=%0t go=%0d rst_n=%0d nph=%0d", $time, go, rst_n, nph);
`endif
    wire [37:0] f_prog;
    wire pfault;
    ot_s81_bf_prog_seq #(.DELTA(DELTA)) u_prog (.ck(clk), .rst_n(rst_n), .go(go), .desc(dtab[nph]), .f_prog(f_prog),
        .fault(pfault));
    dsfd_bf_front_static #(.INSTANCE(INSTANCE)) e0 (.cfg(cfg), .go(go), .st(st), .x0(x0), .x1(x1), .ck(clk), .rs(rst_n),
        .c0(c0), .qy0(qy0), .c1(c1), .qy1(qy1), .xb(xb), .f_prog(f_prog), .io_clk(clk));
    dsfd_bf_col #(.INSTANCE(INSTANCE), .MB(0)) e0w (.ck(clk), .rs(rst_n), .ci(c0), .qy(qy0), .r(rw));
    dsfd_bf_col #(.INSTANCE(INSTANCE), .MB(1)) e0e (.ck(clk), .rs(rst_n), .ci(c1), .qy(qy1), .r(re));
    assign {busy, fault} = {st[0], st[1]};
    assign hph = 1'b1;                               // HALF 0 (the front's hph has no die reader)
    assign {ppos[2:0], perr[0], pnseg[4:0], pseg[4:0], prow[15:0], pval[31:0], pv[0]} = rw;
    assign {ppos[5:3], perr[1], pnseg[9:5], pseg[9:5], prow[31:16], pval[63:32], pv[1]} = re;
`ifndef SYNTHESIS
    // BF16 x-beat adjacency at the pair's pins (the serial-BF-lane question): beats, back-to-back pairs, min gap
    integer n_xb = 0, n_b2b = 0, n_xs = 0, n_xs_b2b = 0, gap_min = 1 << 30, cyc = 0, last_xb = -1000000, last_xs = -1000000;
    always @(posedge clk) if (rst_n) begin
        cyc <= cyc + 1;
        if (xb_v) begin
            n_xb <= n_xb + 1; if (cyc - last_xb == 1) n_b2b <= n_b2b + 1;
            if (last_xb > -1000000 && cyc - last_xb < gap_min) gap_min <= cyc - last_xb;
            last_xb <= cyc;
        end
        if (xs_v) begin n_xs <= n_xs + 1; if (cyc - last_xs == 1) n_xs_b2b <= n_xs_b2b + 1; last_xs <= cyc; end
    end
    final $display("BF_PROG phases=%0d producer_fault=%0d front_fault=%0d", nph, pfault, st[1]);
    final $display("BF_PIN_BEAT_ADJACENCY xb_beats=%0d xb_back_to_back=%0d xb_min_gap=%0d xs_beats=%0d xs_back_to_back=%0d",
                   n_xb, n_b2b, gap_min, n_xs, n_xs_b2b);
`endif
endmodule
