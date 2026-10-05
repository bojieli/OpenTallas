// Additive default-off token source-edge successor. Address pipeline unchanged.
// Original failed spec3 source retained; no published timing credit is inherited.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// 1.2 GHz SS successor of ot_dshbm_spec_state (same ports, same parameters; opt-in, nothing
// instantiates it unless ot_dshbm_dspark_top FAST = 1).
//
// The as-built block computes every answer word in the cycle it issues it:
//   addr = A + idx * R + wrapd(slot(n), p - n, R)       (a 32-bit subtract, a 32-bit add, a
//                                                        compare-and-wrap and the base add in series)
// plus the reach compares, and keeps slot(n) with the same chain on n_set (-965 ps routed at SS).
//
// Here the request walker (busy / req_ready, the position and index walk) is the original FSM
// unchanged, but each answer beat leaves it as a DESCRIPTOR {position, index, n, kind}, and a
// 5-stage pipeline evaluates the original formulas bit for bit, every 32-bit add on a keep-prefix
// adder (ot_hdc_ksadd_k; ABC re-ripples a plain + in context):
//   S1  pi = p (- i for the token ring), the base product idx * R, the token pad sign
//   S2  d = pi - n, base = A + idx * R
//   S3  t = slot + d (the slot registers are read HERE), the reach compares on d
//   S4  wrap(t): t - R / t + R / t by the signed compares (16-bit results)
//   S5  addr = base + wrap(t) (or the compressed-row offset); token-ring read; a_* registered.
// The slot registers follow n_set three edges late (dn = n_val - n; slot + dn; wrap), which is
// exactly the S3 read offset, so every beat sees the slot values the original would have used.
// Token-ring writes go through 5 stages too, so reads and writes keep their order.
// Result: the a_* stream equals the original's delayed by 5 cycles (req_ready, n: unchanged).
// Constraint (the DSpark loop meets it: every n_set is separated by an engine command):
// n_set edges at least 3 cycles apart.
// ---------------------------------------------------------------------------
module ot_dshbm_spec_state_f_token_edge #(
    parameter integer TOKEN_EDGE_FIX = 0,
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
    reg        u1_v, u1_z, u2_v, u2_z, u3_v, u3_z;
    reg [31:0] u1_dn, u2_tw, u2_ts, u2_tt;
    reg [15:0] u3_w, u3_s, u3_t;
    wire [31:0] dn_c, tw_c, ts_c, tt_c;
    ot_hdc_ksadd_k #(.W(32)) a_dn (.a(n_val), .b(~n), .cin(1'b1), .s(dn_c), .cout());
    ot_hdc_ksadd_k #(.W(32)) a_tw (.a({16'd0, sw_n}), .b(u1_dn), .cin(1'b0), .s(tw_c), .cout());
    ot_hdc_ksadd_k #(.W(32)) a_ts (.a({16'd0, ss_n}), .b(u1_dn), .cin(1'b0), .s(ts_c), .cout());
    ot_hdc_ksadd_k #(.W(32)) a_tt (.a({16'd0, st_n}), .b(u1_dn), .cin(1'b0), .s(tt_c), .cout());
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n <= 0; sw_n <= 0; ss_n <= 0; st_n <= 0;
            u1_v <= 1'b0; u2_v <= 1'b0; u3_v <= 1'b0; u1_z <= 1'b0; u2_z <= 1'b0; u3_z <= 1'b0;
        end else begin
            u1_v <= n_set; u2_v <= u1_v; u3_v <= u2_v;
            if (n_set) begin n <= n_val; u1_z <= (n_val == 0); u1_dn <= dn_c; end
            u2_z <= u1_z; u3_z <= u2_z;
            u2_tw <= tw_c; u2_ts <= ts_c; u2_tt <= tt_c;
            u3_w <= wrapfix(u2_tw, WR); u3_s <= wrapfix(u2_ts, SR); u3_t <= wrapfix(u2_tt, TR);
            if (u3_v) begin
                if (u3_z) begin sw_n <= 0; ss_n <= 0; st_n <= 0; end
                else begin sw_n <= u3_w; ss_n <= u3_s; st_n <= u3_t; end
            end
        end
    end
    // Token writes have no ready/ACK: tw_v commits at THIS source edge.
    // Reset preserves ring memory, so it cannot cancel an already accepted write.
    // Token-only origin follows original n_set timing; address origins stay retimed.
    reg [15:0] st_token_n;
    reg [TW-1:0] tring [0:TR-1];
    reg [TW-1:0] d0_token, s1_token, s2_token, s3_token, s4_token;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) st_token_n <= 0;
        else if (TOKEN_EDGE_FIX && n_set)
            st_token_n <= (n_val == 0) ? 16'd0 : wrapfix({16'd0, st_token_n} + (n_val - n), TR);
    end
    always @(posedge clk) if (TOKEN_EDGE_FIX) begin
        s1_token <= d0_token; s2_token <= s1_token;
        s3_token <= s2_token; s4_token <= s3_token;
    end
    // ---- request walker: the original FSM, emitting descriptors ----
    reg        busy;
    reg [3:0]  kind;
    reg [15:0] idx;
    reg [31:0] p_cur, p_end, p_anchor, p_wrapto, i_cur, i_end;
    reg [31:0] i_cur1;                       // i_cur + 1, kept (the walk's index compare is i_cur1 == i_end)
    wire [31:0] p_inc, i_inc;
    ot_hdc_inc_k #(.W(32)) a_pinc (.a(p_cur), .inc(1'b1), .y(p_inc), .co());
    ot_hdc_inc_k #(.W(32)) a_iinc (.a(i_cur1), .inc(1'b1), .y(i_inc), .co());
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
                        i_cur <= 0; i_cur1 <= 1; i_end <= (req_pos + 1) >> rl;
                        if (((req_pos + 1) >> rl) == 0) begin
                            d0_v <= 1'b1; d0_last <= 1'b1; d0_pad <= 1'b1;
                        end else busy <= 1'b1;
                    end
                    K_TOK_RD: begin
                        busy <= 1'b1; i_cur <= 0; i_cur1 <= 1; p_cur <= req_pos;
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
                        end else p_cur <= p_inc;
                    end
                    K_SLOT_RD: begin
                        d0_upd <= 1'b1; d0_c <= C_SLOT;
                        if (p_cur == p_end) begin busy <= 1'b0; d0_last <= 1'b1; end
                        else p_cur <= p_inc;
                    end
                    K_IK_RD: begin
                        d0_upd <= 1'b1; d0_c <= C_CK; d0_off <= i_cur;
                        if (i_cur1 == i_end) begin busy <= 1'b0; d0_last <= 1'b1; end
                        else begin i_cur <= i_cur1; i_cur1 <= i_inc; end
                    end
                    K_TOK_RD: begin
                        if (TOKEN_EDGE_FIX)
                            d0_token <= ($signed(p_cur - i_cur) < 0) ? {TW{1'b0}} :
                                tring[wrapfix({16'd0, st_token_n} + (p_cur - i_cur - n), TR)];
                        d0_c <= C_TOK;
                        if (i_cur == NG - 1) begin busy <= 1'b0; d0_last <= 1'b1; end
                        else begin i_cur <= i_cur1; i_cur1 <= i_inc; end
                    end
                    default: begin busy <= 1'b0; d0_last <= 1'b1; end
                endcase
            end
        end
    end
    // ---- S1: p - i (token ring), base product ----
    reg        s1_v, s1_last, s1_pad, s1_err, s1_upd, s1_tneg;
    reg [2:0]  s1_c;
    reg [31:0] s1_pi, s1_n, s1_bm, s1_off;
    wire [31:0] pi_c;
    ot_hdc_ksadd_k #(.W(32)) a_pi (.a(d0_p), .b(~d0_i), .cin(1'b1), .s(pi_c), .cout());
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_v <= 1'b0; s1_last <= 1'b0; s1_pad <= 1'b0; s1_err <= 1'b0; s1_upd <= 1'b0; s1_c <= C_NONE; end
        else begin
            s1_v <= d0_v; s1_last <= d0_last; s1_pad <= d0_pad; s1_err <= d0_err; s1_upd <= d0_upd; s1_c <= d0_c;
            s1_off <= d0_off; s1_n <= d0_n;
            s1_pi <= (d0_c == C_TOK) ? pi_c : d0_p;
            s1_tneg <= pi_c[31];
            case (d0_c)
                C_WIN, C_DSK: s1_bm <= d0_idx * WR;
                C_SLOT:       s1_bm <= d0_idx * SR;
                default:      s1_bm <= d0_idx * CKMAX;
            endcase
        end
    end
    // ---- S2: d = pi - n, base = A + idx * R ----
    reg        s2_v, s2_last, s2_pad, s2_err, s2_upd, s2_tneg;
    reg [2:0]  s2_c;
    reg [31:0] s2_d, s2_base, s2_off;
    wire [31:0] d_c, base_c;
    reg  [31:0] a_sel;
    always @(*)
        case (s1_c)
            C_WIN:   a_sel = A_WIN;
            C_DSK:   a_sel = A_DSK;
            C_SLOT:  a_sel = A_SLOT;
            default: a_sel = A_CK;
        endcase
    ot_hdc_ksadd_k #(.W(32)) a_d (.a(s1_pi), .b(~s1_n), .cin(1'b1), .s(d_c), .cout());
    ot_hdc_ksadd_k #(.W(32)) a_b (.a(a_sel), .b(s1_bm), .cin(1'b0), .s(base_c), .cout());
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s2_v <= 1'b0; s2_last <= 1'b0; s2_pad <= 1'b0; s2_err <= 1'b0; s2_upd <= 1'b0; s2_c <= C_NONE; end
        else begin
            s2_v <= s1_v; s2_last <= s1_last; s2_pad <= s1_pad; s2_err <= s1_err; s2_upd <= s1_upd; s2_c <= s1_c;
            s2_off <= s1_off; s2_tneg <= s1_tneg; s2_d <= d_c; s2_base <= base_c;
        end
    end
    // ---- S3: t = slot + d (slot read here), reach ----
    reg        s3_v, s3_last, s3_pad, s3_err, s3_upd, s3_tneg, s3_reach;
    reg [2:0]  s3_c;
    reg [31:0] s3_t, s3_base, s3_off;
    reg [15:0] slot_sel;
    always @(*)
        case (s2_c)
            C_WIN, C_DSK: slot_sel = sw_n;
            C_SLOT:       slot_sel = ss_n;
            default:      slot_sel = st_n;
        endcase
    wire [31:0] t_c;
    ot_hdc_ksadd_k #(.W(32)) a_t (.a({16'd0, slot_sel}), .b(s2_d), .cin(1'b0), .s(t_c), .cout());
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s3_v <= 1'b0; s3_last <= 1'b0; s3_pad <= 1'b0; s3_err <= 1'b0; s3_upd <= 1'b0; s3_c <= C_NONE; end
        else begin
            s3_v <= s2_v; s3_last <= s2_last; s3_pad <= s2_pad; s3_err <= s2_err; s3_upd <= s2_upd; s3_c <= s2_c;
            s3_off <= s2_off; s3_tneg <= s2_tneg; s3_base <= s2_base; s3_t <= t_c;
            // ok_reach: n - (ring - PMAX) < p < n + PMAX, as d = p - n
            if (s2_c == C_SLOT) s3_reach <= ($signed(s2_d) < PMAX) && ($signed(s2_d) > -(SR - PMAX + 1));
            else                s3_reach <= ($signed(s2_d) < PMAX) && ($signed(s2_d) > -(WR - PMAX + 1));
        end
    end
    // ---- S4: wrap ----
    reg        s4_v, s4_last, s4_pad, s4_err, s4_upd, s4_tneg;
    reg [2:0]  s4_c;
    reg [15:0] s4_slot;
    reg [31:0] s4_base, s4_off;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s4_v <= 1'b0; s4_last <= 1'b0; s4_pad <= 1'b0; s4_err <= 1'b0; s4_upd <= 1'b0; s4_c <= C_NONE; end
        else begin
            s4_v <= s3_v; s4_last <= s3_last; s4_pad <= s3_pad; s4_upd <= s3_upd; s4_c <= s3_c;
            s4_base <= s3_base; s4_off <= s3_off; s4_tneg <= s3_tneg;
            s4_err <= s3_err || ((s3_c == C_WIN || s3_c == C_DSK || s3_c == C_SLOT) && !s3_reach);
            case (s3_c)
                C_WIN, C_DSK: s4_slot <= wrapfix(s3_t, WR);
                C_SLOT:       s4_slot <= wrapfix(s3_t, SR);
                default:      s4_slot <= wrapfix(s3_t, TR);
            endcase
        end
    end
    // ---- token ring: writes through 5 stages as well ----
    reg          w0_v, w1_v, w2_v, w3_v, w4_v;
    reg [31:0]   w0_p, w0_n, w1_p, w1_n, w2_d, w3_t;
    reg [15:0]   w4_slot;
    reg [TW-1:0] w0_k, w1_k, w2_k, w3_k, w4_k;
    wire [31:0]  wd_c, wt_c;
    ot_hdc_ksadd_k #(.W(32)) a_wd (.a(w1_p), .b(~w1_n), .cin(1'b1), .s(wd_c), .cout());
    ot_hdc_ksadd_k #(.W(32)) a_wt (.a({16'd0, st_n}), .b(w2_d), .cin(1'b0), .s(wt_c), .cout());
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin w0_v <= 1'b0; w1_v <= 1'b0; w2_v <= 1'b0; w3_v <= 1'b0; w4_v <= 1'b0; end
        else begin
            w0_v <= tw_v; w1_v <= w0_v; w2_v <= w1_v; w3_v <= w2_v; w4_v <= w3_v;
        end
    end
    always @(posedge clk) begin
        w0_p <= tw_pos; w0_n <= n; w0_k <= tw_tok;
        w1_p <= w0_p; w1_n <= w0_n; w1_k <= w0_k;          // aligns the slot read with the S3 read
        w2_d <= wd_c; w2_k <= w1_k;
        w3_t <= wt_c; w3_k <= w2_k;
        w4_slot <= wrapfix(w3_t, TR); w4_k <= w3_k;
        if (TOKEN_EDGE_FIX) begin
            // Identical write-before-reset persistence/read-before-write NBA order
            // to the original token port; no reset-conditioned write grant.
            if (tw_v) tring[wrapfix({16'd0, st_token_n} + (tw_pos - n), TR)] <= tw_tok;
        end else if (w4_v) tring[w4_slot] <= w4_k;
    end
    // ---- S5: answer ----
    wire [31:0] addr_c;
    ot_hdc_ksadd_k #(.W(32)) a_a (.a(s4_base), .b((s4_c == C_CK) ? s4_off : {16'd0, s4_slot}), .cin(1'b0), .s(addr_c), .cout());
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a_v <= 1'b0; a_last <= 1'b0; a_pad <= 1'b0; a_err <= 1'b0; a_addr <= 0; a_tok <= 0;
        end else begin
            a_v <= s4_v; a_last <= s4_last;
            a_pad <= s4_pad || (s4_c == C_TOK && s4_tneg);
            if (s4_err) a_err <= 1'b1;
            if (s4_upd) a_addr <= addr_c;
            if (s4_c == C_TOK) a_tok <= TOKEN_EDGE_FIX ? s4_token : (s4_tneg ? {TW{1'b0}} : tring[s4_slot]);
        end
    end
endmodule
