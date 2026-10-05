// Isolated preserved Claude control-family snapshot. Defaults remain off.
// FAST state/router paths remain experimental and physically unqualified.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// 1.2 GHz SS successor of ot_dshbm_spec_state (same ports, same parameters; opt-in, nothing
// instantiates it unless ot_dshbm_dspark_top_ctl_snapshot FAST = 1).
//
// The as-built block computes every answer word in the cycle it issues it:
//   addr = A + idx * R + wrapd(slot(n), p - n, R)       (a 32-bit subtract, a 32-bit add, a
//                                                        compare-and-wrap and the base add in series)
// plus the reach compares, and keeps slot(n) with the same chain on n_set (-965 ps routed at SS).
//
// Here the request walker (busy / req_ready, the position and index walk) is the original FSM
// unchanged, but each answer beat leaves it as a DESCRIPTOR {position, index, n, kind}, and a
// 4-stage pipeline evaluates the original formulas bit for bit:
//   S1  d = p - n (- i for the token ring), the base product idx * R, the token pad sign
//   S2  t = slot + d (slot register read HERE), base + A, the reach compares on d
//   S3  wrap(t): t - R / t + R / t by the signed compares
//   S4  addr = base + wrap(t) (or the compressed-row offset); token-ring read; a_* registered.
// The slot registers follow n_set two edges late (dn = n_val - n; slot + dn; wrap), which is
// exactly the S2 read offset, so every beat sees the slot values the original would have used.
// Token-ring writes go through the same 4 stages, so reads and writes keep their order.
// Result: the a_* stream equals the original's delayed by 4 cycles (req_ready, n: unchanged).
// Constraint (the DSpark loop meets it: n_set is >= 2 cycles apart): no n_set on two
// consecutive edges.
// ---------------------------------------------------------------------------
module ot_dshbm_spec_state_f_ctl_snapshot #(
    parameter integer W     = 128,
    parameter integer PMAX  = 8,
    parameter integer WR    = 136,
    parameter integer SR    = 10,
    parameter integer TR    = 16,
    parameter integer NG    = 4,
    parameter integer NL    = 40,
    parameter integer NST   = 3,
    parameter integer NSRC  = 4,
    parameter [NSRC*4-1:0] RLOG = 16'h0011,
    parameter integer CKMAX = 1 << 16,
    parameter integer TW    = 17,
    parameter integer AW    = 32
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            n_set,
    input  wire [31:0]     n_val,
    output reg  [31:0]     n,
    input  wire            tw_v,
    input  wire [31:0]     tw_pos,
    input  wire [TW-1:0]   tw_tok,
    input  wire            req_v,
    output wire            req_ready,
    input  wire [3:0]      req_kind,
    input  wire [15:0]     req_idx,
    input  wire [31:0]     req_pos,
    output reg             a_v,
    output reg  [AW-1:0]   a_addr,
    output reg  [TW-1:0]   a_tok,
    output reg             a_pad,
    output reg             a_last,
    output reg             a_err
);
    localparam [3:0] K_WIN_WR = 1, K_WIN_RD = 2, K_DSK_WR = 3, K_DSK_RD = 4, K_SLOT_WR = 5, K_SLOT_RD = 6,
                     K_CK_WR = 7, K_IK_RD = 8, K_CK_SEL = 9, K_TOK_RD = 10;
    localparam integer A_WIN = 0;
    localparam integer A_DSK = A_WIN + NL * WR;
    localparam integer A_SLOT = A_DSK + NST * WR;
    localparam integer A_CK = A_SLOT + NSRC * SR;
    // descriptor classes
    localparam [2:0] C_NONE = 0, C_WIN = 1, C_DSK = 2, C_SLOT = 3, C_CK = 4, C_TOK = 5;
    function automatic [3:0] rlog(input [15:0] c);
        rlog = RLOG[c*4 +: 4];
    endfunction
    // wrapd's second half: t is s + d (32-bit two's complement, as the original's integer)
    function automatic [15:0] wrapfix(input [31:0] t, input integer R);
        if ($signed(t) >= R) wrapfix = t - R;
        else if ($signed(t) < 0) wrapfix = t + R;
        else wrapfix = t[15:0];
    endfunction
    // ---- n and the slots of n (slots two edges late) ----
    reg [15:0] sw_n, ss_n, st_n;
    reg        u1_v, u1_z, u2_v, u2_z;
    reg [31:0] u1_dn, u2_tw, u2_ts, u2_tt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n <= 0; sw_n <= 0; ss_n <= 0; st_n <= 0; u1_v <= 1'b0; u2_v <= 1'b0; u1_z <= 1'b0; u2_z <= 1'b0;
        end else begin
            u1_v <= n_set; u2_v <= u1_v;
            if (n_set) begin n <= n_val; u1_z <= (n_val == 0); u1_dn <= n_val - n; end
            u2_z <= u1_z;
            u2_tw <= {16'd0, sw_n} + u1_dn; u2_ts <= {16'd0, ss_n} + u1_dn; u2_tt <= {16'd0, st_n} + u1_dn;
            if (u2_v) begin
                if (u2_z) begin sw_n <= 0; ss_n <= 0; st_n <= 0; end
                else begin sw_n <= wrapfix(u2_tw, WR); ss_n <= wrapfix(u2_ts, SR); st_n <= wrapfix(u2_tt, TR); end
            end
        end
    end
    // ---- request walker: the original FSM, emitting descriptors ----
    reg        busy;
    reg [3:0]  kind;
    reg [15:0] idx;
    reg [31:0] p_cur, p_end, p_anchor, p_wrapto, i_cur, i_end;
    reg        p_wrapped, is_dsk;
    reg [3:0]  rl;
    assign req_ready = !busy;
    // descriptor (stage 0)
    reg        d0_v, d0_last, d0_pad, d0_err, d0_upd;
    reg [2:0]  d0_c;
    reg [15:0] d0_idx;
    reg [31:0] d0_p, d0_i, d0_n, d0_off;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; d0_v <= 1'b0; d0_last <= 1'b0; d0_pad <= 1'b0; d0_err <= 1'b0; d0_upd <= 1'b0; d0_c <= C_NONE;
        end else begin
            d0_v <= 1'b0; d0_last <= 1'b0; d0_pad <= 1'b0; d0_err <= 1'b0; d0_upd <= 1'b0; d0_c <= C_NONE;
            d0_n <= n;
            if (!busy && req_v) begin
                kind <= req_kind; idx <= req_idx;
                rl = rlog(req_idx);
                d0_idx <= req_idx; d0_p <= req_pos;
                case (req_kind)
                    K_WIN_WR, K_DSK_WR: begin
                        d0_v <= 1'b1; d0_last <= 1'b1; d0_upd <= 1'b1; d0_c <= (req_kind == K_WIN_WR) ? C_WIN : C_DSK;
                    end
                    K_SLOT_WR: begin d0_v <= 1'b1; d0_last <= 1'b1; d0_upd <= 1'b1; d0_c <= C_SLOT; end
                    K_CK_WR: begin
                        d0_v <= 1'b1; d0_last <= 1'b1; d0_upd <= 1'b1; d0_c <= C_CK; d0_off <= req_pos >> rl;
                    end
                    K_CK_SEL: begin d0_v <= 1'b1; d0_last <= 1'b1; d0_upd <= 1'b1; d0_c <= C_CK; d0_off <= req_pos; end
                    K_WIN_RD: begin
                        busy <= 1'b1; is_dsk <= 1'b0;
                        p_cur <= (req_pos + 1 > W) ? req_pos - W + 1 : 0;
                        p_end <= req_pos; p_wrapped <= 1'b1;
                    end
                    K_DSK_RD: begin
                        busy <= 1'b1; is_dsk <= 1'b1;
                        p_anchor <= req_pos;
                        if (req_pos + 1 > W) begin
                            p_cur <= req_pos - (req_pos & (W - 1)); p_end <= req_pos;
                            p_wrapped <= ((req_pos & (W - 1)) == W - 1);
                            p_wrapto <= req_pos - W + 1;
                        end else begin
                            p_cur <= 0; p_end <= req_pos; p_wrapped <= 1'b1;
                        end
                    end
                    K_SLOT_RD: begin
                        busy <= 1'b1;
                        p_cur <= req_pos - (req_pos & ((32'd1 << rl) - 1)); p_end <= req_pos;
                    end
                    K_IK_RD: begin
                        i_cur <= 0; i_end <= (req_pos + 1) >> rl;
                        if (((req_pos + 1) >> rl) == 0) begin
                            d0_v <= 1'b1; d0_last <= 1'b1; d0_pad <= 1'b1;
                        end else busy <= 1'b1;
                    end
                    K_TOK_RD: begin
                        busy <= 1'b1; i_cur <= 0; p_cur <= req_pos;
                    end
                    default: begin d0_v <= 1'b1; d0_last <= 1'b1; d0_pad <= 1'b1; d0_err <= 1'b1; end
                endcase
            end else if (busy) begin
                d0_v <= 1'b1; d0_idx <= idx; d0_p <= p_cur; d0_i <= i_cur;
                case (kind)
                    K_WIN_RD, K_DSK_RD: begin
                        d0_upd <= 1'b1; d0_c <= (kind == K_WIN_RD) ? C_WIN : C_DSK;
                        if (p_cur == p_end) begin
                            if (p_wrapped) begin busy <= 1'b0; d0_last <= 1'b1; end
                            else begin
                                p_wrapped <= 1'b1; p_cur <= p_wrapto;
                                p_end <= p_anchor - (p_anchor & (W - 1)) - 1;
                            end
                        end else p_cur <= p_cur + 1;
                    end
                    K_SLOT_RD: begin
                        d0_upd <= 1'b1; d0_c <= C_SLOT;
                        if (p_cur == p_end) begin busy <= 1'b0; d0_last <= 1'b1; end
                        else p_cur <= p_cur + 1;
                    end
                    K_IK_RD: begin
                        d0_upd <= 1'b1; d0_c <= C_CK; d0_off <= i_cur;
                        if (i_cur + 1 == i_end) begin busy <= 1'b0; d0_last <= 1'b1; end
                        else i_cur <= i_cur + 1;
                    end
                    K_TOK_RD: begin
                        d0_c <= C_TOK;
                        if (i_cur == NG - 1) begin busy <= 1'b0; d0_last <= 1'b1; end
                        else i_cur <= i_cur + 1;
                    end
                    default: begin busy <= 1'b0; d0_last <= 1'b1; end
                endcase
            end
        end
    end
    // ---- S1: differences, base product ----
    reg        s1_v, s1_last, s1_pad, s1_err, s1_upd, s1_tneg;
    reg [2:0]  s1_c;
    reg [31:0] s1_d, s1_bm, s1_off;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s1_last <= 1'b0; s1_pad <= 1'b0; s1_err <= 1'b0; s1_upd <= 1'b0; s1_c <= C_NONE; end
        else begin
            s1_v <= d0_v; s1_last <= d0_last; s1_pad <= d0_pad; s1_err <= d0_err; s1_upd <= d0_upd; s1_c <= d0_c;
            s1_off <= d0_off;
            s1_d <= (d0_c == C_TOK) ? d0_p - d0_i - d0_n : d0_p - d0_n;
            s1_tneg <= $signed(d0_p - d0_i) < 0;
            case (d0_c)
                C_WIN, C_DSK: s1_bm <= d0_idx * WR;
                C_SLOT:       s1_bm <= d0_idx * SR;
                default:      s1_bm <= d0_idx * CKMAX;
            endcase
        end
    end
    // ---- S2: slot + d (slot read here), base + A, reach ----
    reg        s2_v, s2_last, s2_pad, s2_err, s2_upd, s2_tneg, s2_reach;
    reg [2:0]  s2_c;
    reg [31:0] s2_t, s2_base, s2_off;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s2_v <= 1'b0; s2_last <= 1'b0; s2_pad <= 1'b0; s2_err <= 1'b0; s2_upd <= 1'b0; s2_c <= C_NONE; end
        else begin
            s2_v <= s1_v; s2_last <= s1_last; s2_pad <= s1_pad; s2_err <= s1_err; s2_upd <= s1_upd; s2_c <= s1_c;
            s2_off <= s1_off; s2_tneg <= s1_tneg;
            case (s1_c)
                C_WIN, C_DSK: s2_t <= {16'd0, sw_n} + s1_d;
                C_SLOT:       s2_t <= {16'd0, ss_n} + s1_d;
                default:      s2_t <= {16'd0, st_n} + s1_d;
            endcase
            case (s1_c)
                C_WIN:   s2_base <= A_WIN + s1_bm;
                C_DSK:   s2_base <= A_DSK + s1_bm;
                C_SLOT:  s2_base <= A_SLOT + s1_bm;
                default: s2_base <= A_CK + s1_bm;
            endcase
            // ok_reach: n - (ring - PMAX) < p < n + PMAX, as d = p - n
            if (s1_c == C_SLOT) s2_reach <= ($signed(s1_d) < PMAX) && ($signed(s1_d) > -(SR - PMAX + 1));
            else                s2_reach <= ($signed(s1_d) < PMAX) && ($signed(s1_d) > -(WR - PMAX + 1));
        end
    end
    // ---- S3: wrap ----
    reg        s3_v, s3_last, s3_pad, s3_err, s3_upd, s3_tneg;
    reg [2:0]  s3_c;
    reg [15:0] s3_slot;
    reg [31:0] s3_base, s3_off;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s3_v <= 1'b0; s3_last <= 1'b0; s3_pad <= 1'b0; s3_err <= 1'b0; s3_upd <= 1'b0; s3_c <= C_NONE; end
        else begin
            s3_v <= s2_v; s3_last <= s2_last; s3_pad <= s2_pad; s3_upd <= s2_upd; s3_c <= s2_c;
            s3_base <= s2_base; s3_off <= s2_off; s3_tneg <= s2_tneg;
            s3_err <= s2_err || ((s2_c == C_WIN || s2_c == C_DSK || s2_c == C_SLOT) && !s2_reach);
            case (s2_c)
                C_WIN, C_DSK: s3_slot <= wrapfix(s2_t, WR);
                C_SLOT:       s3_slot <= wrapfix(s2_t, SR);
                default:      s3_slot <= wrapfix(s2_t, TR);
            endcase
        end
    end
    // ---- token ring: writes through the same stages ----
    reg [TW-1:0] tring [0:TR-1];
    reg          w0_v, w1_v, w2_v, w3_v;
    reg [31:0]   w0_p, w0_n, w1_d, w2_t;
    reg [15:0]   w3_slot;
    reg [TW-1:0] w0_k, w1_k, w2_k, w3_k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin w0_v <= 1'b0; w1_v <= 1'b0; w2_v <= 1'b0; w3_v <= 1'b0; end
        else begin
            w0_v <= tw_v; w1_v <= w0_v; w2_v <= w1_v; w3_v <= w2_v;
        end
    end
    always @(posedge clk) begin
        w0_p <= tw_pos; w0_n <= n; w0_k <= tw_tok;
        w1_d <= w0_p - w0_n; w1_k <= w0_k;
        w2_t <= {16'd0, st_n} + w1_d; w2_k <= w1_k;
        w3_slot <= wrapfix(w2_t, TR); w3_k <= w2_k;
        if (w3_v) tring[w3_slot] <= w3_k;
    end
    // ---- S4: answer ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_v <= 1'b0; a_last <= 1'b0; a_pad <= 1'b0; a_err <= 1'b0; a_addr <= 0; a_tok <= 0;
        end else begin
            a_v <= s3_v; a_last <= s3_last;
            a_pad <= s3_pad || (s3_c == C_TOK && s3_tneg);
            if (s3_err) a_err <= 1'b1;
            if (s3_upd) a_addr <= s3_base + ((s3_c == C_CK) ? s3_off : {16'd0, s3_slot});
            if (s3_c == C_TOK) a_tok <= s3_tneg ? {TW{1'b0}} : tring[s3_slot];
        end
    end
endmodule
