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
    parameter integer DELTA = 0,
    parameter integer LAYOUT = 0,
    parameter integer PINREG = 0
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
    wire [6:0] ce_local;
    wire [5:0] cfg_local;
    wire go_local;
    ot_s81_cfg7_seq_bf_local #(.NSEG(NSEG), .PHW(PHW), .NROM(NROM), .LAYOUT(LAYOUT), .LOCAL_COPY(PINREG != 0), .PINREG(PINREG)) u_ld (.clk(clk), .rst_n(rst_n), .lc(lc), .a(a),
        .ce0(ce0), .ce1(ce1), .ce2(ce2), .ce3(ce3), .ce4(ce4), .ce5(ce5), .ce6(ce6),
        .q0(q0[47:0]), .q1(q1[47:0]), .q2(q2[47:0]), .q3(q3[47:0]), .q4(q4[47:0]), .q5(q5[47:0]), .q6(q6[47:0]),
        .cfg(cfg), .go_e(go_e), .st(st_ld), .ce_local(ce_local), .cfg_local(cfg_local), .go_local(go_local));
    // PINREG = 1 (S-ELEM-PQ 2026-10-16, owner rule 19:50 "register every pin"; native audit of the cfg7 pr2 view: the
    // rst_n port -> async clears was capture 303 ps): the loader is the PINREG 1 / LAYOUT 1 tile (inputs +1, a/ce +2,
    // cfg/go_e/st +4 from lc); here the spare columns q*[71:48] are captured in pin flops (the loader's q pin-flop edge),
    // the bank select follows them one edge later, and the spare word waits one more edge so that row k's spare bits
    // still meet cfg {c_v, c_a = k} (cfg leaves the loader's output flop 2 edges after its q pin flop).  st is
    // re-registered after the programme-fault OR (+1 edge on st only); f_prog leaves u_prog's own flops.  The
    // producer's flops reset from their own ot_rst_relay (release 3 edges after the port, as the loader's).
    // Exact: lockstep gate tb_ot_s81_cfg7_seq_bfp.sv +define+TB_BFP_PINREG; negative controls OT_S81_CFG7_BFP_MUT_ROW
    // and OT_S81_CFG7_BFP_MUT_SPDL (spare word one edge early) must FAIL.  PINREG = 0 is byte-for-byte unchanged.
    wire rn;
    wire [71:48] s0, s1, s2, s3, s4, s5, s6;
    generate if (PINREG != 0) begin : g_pr
        wire [0:0] rr_;
        ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk[0]), .rst_n_in(rst_n[0]), .rst_n(rr_));
        assign rn = rr_[0];
        reg [71:48] s0_r, s1_r, s2_r, s3_r, s4_r, s5_r, s6_r;
        always @(posedge clk[0]) begin
            s0_r <= q0[71:48]; s1_r <= q1[71:48]; s2_r <= q2[71:48]; s3_r <= q3[71:48];
            s4_r <= q4[71:48]; s5_r <= q5[71:48]; s6_r <= q6[71:48];
        end
        assign s0 = s0_r; assign s1 = s1_r; assign s2 = s2_r; assign s3 = s3_r; assign s4 = s4_r; assign s5 = s5_r;
        assign s6 = s6_r;
        reg [1:0] st_r;
        always @(posedge clk[0] or negedge rn) if (!rn) st_r <= 2'd0; else st_r <= {st_ld[1] | pfault, st_ld[0]};
        assign st = st_r;
    end else begin : g_pr0
        assign rn = rst_n[0];
        assign s0 = q0[71:48]; assign s1 = q1[71:48]; assign s2 = q2[71:48]; assign s3 = q3[71:48];
        assign s4 = q4[71:48]; assign s5 = q5[71:48]; assign s6 = q6[71:48];
        assign st = {st_ld[1] | pfault, st_ld[0]};    // fault: loader OR programme (a go while the programme still runs)
    end endgenerate
    // spare columns of the macro read on the previous edge (the loader's own registered bank select, rebuilt from ce)
    reg  [2:0] bk, bk_d;
    wire [6:0] cev = ce_local;
    always @(posedge clk[0]) if (|cev) bk <= cev[0] ? 3'd0 : cev[1] ? 3'd1 : cev[2] ? 3'd2 : cev[3] ? 3'd3 :
                                              cev[4] ? 3'd4 : cev[5] ? 3'd5 : 3'd6;
    always @(posedge clk[0]) bk_d <= bk;
    wire [2:0] bks = (PINREG != 0) ? bk_d : bk;
    reg [23:0] sp;
    always @(*) case (bks)
        3'd0: sp = s0; 3'd1: sp = s1; 3'd2: sp = s2; 3'd3: sp = s3;
        3'd4: sp = s4; 3'd5: sp = s5; default: sp = s6;
    endcase
    // row k's spare bits are captured on the edge the loader captures row k's word (cfg shows {c_v, c_a = k} after it)
    reg [23:0] sp_q, sp_q2;
    always @(posedge clk[0]) begin sp_q <= sp; sp_q2 <= sp_q; end
`ifdef OT_S81_CFG7_BFP_MUT_SPDL
    wire [23:0] sp_a = sp_q;                                          // negative control: spare word one edge early
`else
    wire [23:0] sp_a = (PINREG != 0) ? sp_q2 : sp_q;
`endif
    reg [95:0] desc;
    wire       c_v = cfg_local[5];
    wire [4:0] c_a = cfg_local[4:0];
    always @(posedge clk[0] or negedge rn)
        if (!rn) desc <= 96'd0;
`ifdef OT_S81_CFG7_BFP_MUT_ROW
        else if (c_v && c_a >= 5'd1 && c_a <= 5'd4) desc[24 * (c_a - 5'd1) +: 24] <= sp_a;   // negative: one row late
`else
        else if (c_v && c_a < 5'd4) desc[24 * c_a +: 24] <= sp_a;
`endif
    ot_s81_bf_prog_seq #(.DELTA(DELTA)) u_prog (.ck(clk[0]), .rst_n(rn), .go(go_local), .desc(desc[81:0]),
        .f_prog(f_prog), .fault(pfault));
endmodule
`default_nettype wire
