`timescale 1ns/1ps
`default_nettype none
// ix2 control tile (hbm-redesign-idx 2026-10-13): operand check, frame FSM, frame start beat fs, fault collection.
// start (pulse) and run (level) are the only control the other tiles take; each registers them at its own pin.
// Operand faults as ot_hgi_idx_index_w, with ONE stricter rule: keep_en needs C.stride a multiple of 64 words
// (8 sectors, so a value sector is on the lane of its id sector); the reference needs 32 words.
module ot_hgi_idx_ix2_ct (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go_i,
    input  wire [11:0]   k_i,
    input  wire          cand_en_i, keep_en_i,
    input  wire [31:0]   n_i,
    input  wire [6:0]    rank_i,
    input  wire [19:0]   pos_i,
    input  wire [2:0]    a_lo_i,
    input  wire [5:0]    cs_lo_i,
    input  wire [1:0]    ev,
    input  wire [7:0]    ln_idle,
    input  wire          qa_done, qa_bad, pk_done, pk_bad, wp_idle,
    output reg           start,
    output reg           run,
    output reg           flush,
    output reg  [89:0]   fs,
    output reg           rg_req,
    output reg           done,
    output reg           fault
);
    localparam [1:0] S_IDLE = 2'd0, S_RUN = 2'd1, S_FLUSH = 2'd2;
    reg rs1, rn;
    always @(posedge clk or negedge rst_n) if (!rst_n) {rn, rs1} <= 2'b00; else {rn, rs1} <= {rs1, 1'b1};
    reg go; reg [11:0] k; reg cand_en, keep_en; reg [31:0] n; reg [6:0] rank; reg [19:0] pos; reg [2:0] a_lo; reg [5:0] cs_lo;
    reg [1:0] ev_q; reg [7:0] idle_q; reg qd_q, qb_q, pd_q, pb_q, wi_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin go <= 1'b0; ev_q <= 2'd0; idle_q <= 8'd0; qd_q <= 1'b0; qb_q <= 1'b0; pd_q <= 1'b0; pb_q <= 1'b0; wi_q <= 1'b0; end
        else begin go <= go_i; ev_q <= ev; idle_q <= ln_idle; qd_q <= qa_done; qb_q <= qa_bad; pd_q <= pk_done; pb_q <= pk_bad;
            wi_q <= wp_idle; end
    always @(posedge clk) begin
        k <= k_i; cand_en <= cand_en_i; keep_en <= keep_en_i; n <= n_i; rank <= rank_i; pos <= pos_i; a_lo <= a_lo_i;
        cs_lo <= cs_lo_i;
    end
    reg [1:0] st; reg sel_done, fs_pend, rd_all; reg [3:0] fw;
    wire illegal = k == 12'd0 || k > 12'd512 || n > 32'd10944 || rank >= 7'd96 || a_lo != 3'd0 || (keep_en && cs_lo != 6'd0);
    always @(posedge clk) if (fs_pend) fs[89:1] <= {keep_en, cand_en, k[9:0], n[13:0], rank, pos, 4'd0, 32'd0};
    always @(posedge clk or negedge rn)
        if (!rn) begin
            st <= S_IDLE; start <= 1'b0; run <= 1'b0; flush <= 1'b0; fs[0] <= 1'b0; rg_req <= 1'b0; done <= 1'b0; fault <= 1'b0;
            sel_done <= 1'b0; fs_pend <= 1'b0; rd_all <= 1'b0; fw <= 4'd0;
        end else begin
            start <= 1'b0; flush <= 1'b0; fs[0] <= 1'b0; done <= 1'b0; fault <= 1'b0;
            rd_all <= &idle_q;
            if (ev_q[0] && st != S_IDLE) sel_done <= 1'b1;
            case (st)
                S_IDLE: if (go) begin
                    if (illegal) fault <= 1'b1;
                    else begin st <= S_RUN; start <= 1'b1; run <= 1'b1; rg_req <= 1'b1; fs_pend <= 1'b1; sel_done <= 1'b0; fw <= 4'd0; end
                end
                S_RUN: begin
                    if (fs_pend) begin fs_pend <= 1'b0; fs[0] <= 1'b1; end
                    if (fw != 4'd6) fw <= fw + 4'd1;                     // status pins of the previous frame have cleared
                    if (rd_all && fw == 4'd6) rg_req <= 1'b0;
                    if (ev_q[1] || qb_q || pb_q) begin st <= S_IDLE; fault <= 1'b1; run <= 1'b0; rg_req <= 1'b0; end
                    else if (sel_done && pd_q && qd_q && rd_all && fw == 4'd6) begin st <= S_FLUSH; flush <= 1'b1; fw <= 4'd0; end
                end
                S_FLUSH: begin
                    if (wi_q) begin st <= S_IDLE; done <= 1'b1; run <= 1'b0; rg_req <= 1'b0; end
                end
                default: st <= S_IDLE;
            endcase
        end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_hgi_idx_ix2_kc: ONE hardened leaf = the frame control (ot_hgi_idx_ix2_ct, 169 flops: glue, no tile of its own)
// + the keep bitmaps (ot_hgi_idx_ix2_ks).  Wires only; start / run leave the leaf from ct's flops and feed ks's pin
// flops inside it.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_idx_ix2_kc (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go_i,
    input  wire [11:0]   k_i,
    input  wire          cand_en_i, keep_en_i,
    input  wire [31:0]   n_i,
    input  wire [6:0]    rank_i,
    input  wire [19:0]   pos_i,
    input  wire [2:0]    a_lo_i,
    input  wire [5:0]    cs_lo_i,
    input  wire [1:0]    ev,
    input  wire [7:0]    ln_idle,
    input  wire          qa_done, qa_bad, pk_done, pk_bad, wp_idle,
    output wire          start,
    output wire          run,
    output wire          flush,
    output wire [89:0]   fs,
    output wire          rg_req,
    output wire          done,
    output wire          fault,
    input  wire [1:0]    ks_v,
    input  wire [21:0]   ks_ord,
    input  wire [7:0]    c_done,
    output wire [344:0]  kin,
    output wire          kin_sent
);
    ot_hgi_idx_ix2_ct u_ct (.clk(clk), .rst_n(rst_n), .go_i(go_i), .k_i(k_i), .cand_en_i(cand_en_i), .keep_en_i(keep_en_i),
        .n_i(n_i), .rank_i(rank_i), .pos_i(pos_i), .a_lo_i(a_lo_i), .cs_lo_i(cs_lo_i), .ev(ev), .ln_idle(ln_idle),
        .qa_done(qa_done), .qa_bad(qa_bad), .pk_done(pk_done), .pk_bad(pk_bad), .wp_idle(wp_idle),
        .start(start), .run(run), .flush(flush), .fs(fs), .rg_req(rg_req), .done(done), .fault(fault));
    ot_hgi_idx_ix2_ks u_ks (.clk(clk), .rst_n(rst_n), .start(start), .run(run), .keep_en_i(keep_en_i), .ks_v(ks_v),
        .ks_ord(ks_ord), .c_done(c_done), .kin(kin), .kin_sent(kin_sent));
endmodule
`default_nettype wire
