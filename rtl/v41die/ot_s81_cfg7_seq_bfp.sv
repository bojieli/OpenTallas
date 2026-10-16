`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_cfg7_seq_bfp (S-BIND 2026-10-15): the BF pair's configuration sequencer die master WITH its static programme.
// = ot_s81_cfg7_seq_bf (the pinned PQ 0 loader, unchanged cfg / go_e / st, cycle-identical) + the per-pair programme
// producer ot_s81_bf_prog_seq driving dsfd_bf_front_static.f_prog.  Owner rule 2026-10-14T18:59: the BF issue edges are
// compiled; no readiness or data availability decides an issue.
// Descriptor storage: the phase's 82-bit programme descriptor sits in the SPARE columns rd_out[71:48] of the first four
// rows of the phase's 25-row block in the pair's own seven cfg ROMs (rows k = 0..3 -> desc[24k +: 24]; desc[95:82] = 0).
// The loader already reads those rows at every cfg broadcast, so the descriptor arrives with the configuration: no extra
// macro, address or cycle.  The producer captures it at the phase's go (a go before the load finished is already the
// loader's fault).  q[0..6] are the macros' full 72-bit rd_out (the cfg path keeps bits [47:0]).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_cfg7_seq_bfp #(
    parameter integer NSEG = 8,
    parameter integer PHW = 10,
    parameter integer NROM = 7,
    parameter integer DELTA = -1
) (
    input  wire [0:0]          clk,
    input  wire [0:0]          rst_n,
    input  wire [PHW+4:0]      lc,
    output wire [11:0]         a,
    output wire [0:0]          ce0, ce1, ce2, ce3, ce4, ce5, ce6,
    input  wire [71:0]         q0, q1, q2, q3, q4, q5, q6,
    output wire [53:0]         cfg,
    output wire [0:0]          go_e,
    output wire [1:0]          st,
    output wire [37:0]         f_prog
);
    wire [1:0] st_ld;
    wire pfault;
    ot_s81_cfg7_seq_bf #(.NSEG(NSEG), .PHW(PHW), .NROM(NROM)) u_ld (.clk(clk), .rst_n(rst_n), .lc(lc), .a(a),
        .ce0(ce0), .ce1(ce1), .ce2(ce2), .ce3(ce3), .ce4(ce4), .ce5(ce5), .ce6(ce6),
        .q0(q0[47:0]), .q1(q1[47:0]), .q2(q2[47:0]), .q3(q3[47:0]), .q4(q4[47:0]), .q5(q5[47:0]), .q6(q6[47:0]),
        .cfg(cfg), .go_e(go_e), .st(st_ld));
    assign st = {st_ld[1] | pfault, st_ld[0]};    // fault: loader OR programme (a go while the programme still runs)
    // spare columns of the macro read on the previous edge (the loader's own registered bank select, rebuilt from ce)
    reg  [2:0] bk;
    wire [6:0] cev = {ce6[0], ce5[0], ce4[0], ce3[0], ce2[0], ce1[0], ce0[0]};
    always @(posedge clk[0]) if (|cev) bk <= cev[0] ? 3'd0 : cev[1] ? 3'd1 : cev[2] ? 3'd2 : cev[3] ? 3'd3 :
                                              cev[4] ? 3'd4 : cev[5] ? 3'd5 : 3'd6;
    reg [23:0] sp;
    always @(*) case (bk)
        3'd0: sp = q0[71:48]; 3'd1: sp = q1[71:48]; 3'd2: sp = q2[71:48]; 3'd3: sp = q3[71:48];
        3'd4: sp = q4[71:48]; 3'd5: sp = q5[71:48]; default: sp = q6[71:48];
    endcase
    // row k's spare bits are captured on the edge the loader captures row k's word (cfg shows {c_v, c_a = k} after it)
    reg [23:0] sp_q;
    always @(posedge clk[0]) sp_q <= sp;
    reg [95:0] desc;
    wire       c_v = cfg[53];
    wire [4:0] c_a = cfg[4:0];
    always @(posedge clk[0] or negedge rst_n[0])
        if (!rst_n[0]) desc <= 96'd0;
`ifdef OT_S81_CFG7_BFP_MUT_ROW
        else if (c_v && c_a >= 5'd1 && c_a <= 5'd4) desc[24 * (c_a - 5'd1) +: 24] <= sp_q;   // negative: one row late
`else
        else if (c_v && c_a < 5'd4) desc[24 * c_a +: 24] <= sp_q;
`endif
    ot_s81_bf_prog_seq #(.DELTA(DELTA)) u_prog (.ck(clk[0]), .rst_n(rst_n[0]), .go(go_e[0]), .desc(desc[81:0]),
        .f_prog(f_prog), .fault(pfault));
endmodule
`default_nettype wire
