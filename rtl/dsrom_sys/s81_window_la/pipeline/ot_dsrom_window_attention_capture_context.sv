`timescale 1ns/1ps
// Physical first-consumer cut of the actual H16/D512/TD32/NL4 attention
// engine. Arithmetic and scheduler outputs are timed boundary inputs.
// E1 and R0 declarations/capture blocks below are copied verbatim from the
// actual engine and tile. No extra edge, substituted arithmetic or done pulse.
// Staging binds the existing full 68-macro physical branch and its own views.
// This measurement module does not wire the parked native S81 path.
module ot_dsrom_window_attention_capture_context (
    input wire clk, rst_n,
    input wire act,
    input wire [15:0] wptr, T,
    input wire kv_v,
    output wire kv_ready,
    input wire [3:0] kv_m,
    input wire [16959:0] kv_w,
    input wire [7:0] rd_addr,
    input wire [15:0] r0_qk, r0_qk_s,
    input wire rd_qk_s, pv_e, q_go, p_go, p_w2v,
    input wire [7:0] pl_word, q_cnt,
    input wire [1:0] nb_p, pl_bank, nb_q, q_bank, e_iss_bank, rd_bank_s,
    input wire [511:0] p_w_i,
    input wire [8191:0] q_w,
    input wire [36863:0] tr_col,
    input wire e_iss_final,
    input wire [15:0] e_iss_blk,
    input wire [7:0] e_iss_c,
    output wire [70655:0] r0_captures,
    output wire [35:0] e_tags
);
    localparam integer D=512, TD=32, NL=4, NT=64, S=16,
        GW=265, ROWW=4240, PWORDS=1, BW=2, MLEV=5;
    // Actual ILV=0/NSTAGE=1 kv_ready expression, with controller registers
    // act/T/wptr retained at their existing timed boundary, not recaptured.
    assign kv_ready = act && (wptr < T);
    wire kv_go = kv_v && kv_ready;
    wire [NL*ROWW-1:0] rd_q_qk;
    ot_hdc_v41x_attn_staging #(.D(D), .NL(NL), .TROWS(640), .SRAM_MACRO(1)) u_stage (
        .clk(clk), .wr_en({NL{kv_go}} & kv_m), .wr_addr(8'(wptr / NL)), .wr_data(kv_w),
        .rd_addr(rd_addr), .rd_data(rd_q_qk));
    function automatic [17:0] elem(input [GW-1:0] gw, input integer x, input pad);
        begin
            if (gw[264]) elem = {pad, 1'b1, 4'd0, gw[4*x +: 4], gw[128 + 8*(x/16) +: 8]};
            else         elem = {pad, 1'b0, gw[8*x +: 8], gw[263:256]};
        end
    endfunction

    reg              e_ld_v, e_ld_mode, e_ld_w2v;
    reg [BW-1:0]     e_ld_bank;
    reg [7:0]        e_ld_grp;
    reg [PWORDS*TD*16-1:0] e_p_w;
    reg [D*16-1:0]   e_q_w;
    reg              e_iv, e_pv;
    reg [BW-1:0]     e_ibank;
    reg [NT*TD*18-1:0] e_ib_c;         // REPL = 0: one E register for the issue operands
    wire [NT*TD*18-1:0] e_ib;          // REPL = 1: per-tile registers (g_tr[*].g_rx.e_ib_t)
    // tags carried to the outputs
    reg [15:0]       e_row0;
    reg [NL-1:0]     e_mask;
    reg              e_fin;
    reg [MLEV-1:0]   e_blk;
    reg [7:0]        e_c;

    wire [NT*TD*18-1:0] qk_ib;
    genvar gl, gs, gk;
    generate
        for (gl = 0; gl < NL; gl = gl + 1) begin : g_qkl
            for (gs = 0; gs < S; gs = gs + 1) begin : g_qks
                for (gk = 0; gk < TD; gk = gk + 1) begin : g_qke
                    assign qk_ib[((gl*S + gs)*TD + gk)*18 +: 18] =
                        elem(rd_q_qk[gl*ROWW + ((gs*TD + gk) / 32) * GW +: GW], (gs*TD + gk) % 32,
                             ((r0_qk + gl) >= T));
                end
            end
        end
    endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin e_ld_v <= 1'b0; e_iv <= 1'b0; e_pv <= 1'b0; end
        else begin
            e_ld_v <= q_go || p_go;
            e_iv <= rd_qk_s || pv_e;
            e_pv <= pv_e;
        end
    end
    integer li;
    always @(posedge clk) begin
        e_ld_mode <= p_go;
        e_ld_w2v <= p_go && p_w2v;
        e_ld_bank <= p_go ? ((pl_word == 0) ? nb_p : pl_bank) : ((q_cnt == 0) ? nb_q : q_bank);
        e_ld_grp <= p_go ? pl_word : q_cnt;
        e_p_w <= p_w_i;
        e_q_w <= q_w;
        e_ibank <= pv_e ? e_iss_bank : rd_bank_s;
        e_ib_c <= pv_e ? tr_col : qk_ib;
        e_row0 <= r0_qk_s;
        for (li = 0; li < NL; li = li + 1) e_mask[li] <= (r0_qk_s + li) < T;
        e_fin <= e_iss_final;
        e_blk <= e_iss_blk[MLEV-1:0];
        e_c <= e_iss_c;
    end
    assign e_ib = e_ib_c;
    assign e_tags = {e_pv, e_row0, e_mask, e_fin, e_blk, e_c, e_ld_v};
    generate
        for (gk = 0; gk < NT; gk = gk + 1) begin : g_t
            localparam integer SL = gk % S;
            wire [PWORDS*TD*16-1:0] ld_w = e_ld_mode ? e_p_w : (PWORDS*TD*16)'(e_q_w[SL*TD*16 +: TD*16]);
            wire ld_v=e_ld_v, ld_mode=e_ld_mode, ld_w2v=e_ld_w2v, iv=e_iv;
            wire [BW-1:0] ld_bank=e_ld_bank, ibank=e_ibank;
            wire [7:0] ld_grp=e_ld_grp;
            wire [TD*18-1:0] ib=e_ib[gk*TD*18 +: TD*18];
    // -- R0: boundary registers
    reg              r_ld_v, r_ld_mode;
    reg [BW-1:0]     r_ld_bank;
    reg [7:0]        r_ld_grp;
    reg [PWORDS*TD*16-1:0] r_ld_w;
    reg              r_ld_w2v;
    reg              r_iv;
    reg [BW-1:0]     r_ibank;
    reg [TD*18-1:0]  r_ib;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin r_ld_v <= 1'b0; r_iv <= 1'b0; end
        else begin r_ld_v <= ld_v; r_iv <= iv; end
    end
    always @(posedge clk) begin
        r_ld_mode <= ld_mode; r_ld_bank <= ld_bank; r_ld_grp <= ld_grp; r_ld_w <= ld_w; r_ld_w2v <= ld_w2v;
        r_ibank <= ibank; r_ib <= ib;
    end

            assign r0_captures[gk*1104 +: 1104] =
                {r_ld_v, r_ld_mode, r_ld_bank, r_ld_grp, r_ld_w, r_ld_w2v, r_iv, r_ibank, r_ib};
        end
    endgenerate
endmodule
