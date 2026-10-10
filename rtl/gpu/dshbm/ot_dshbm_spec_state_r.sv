`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dshbm_spec_state_r (hgi-takeover 2026-10-09, drive-0849 core18 -405 ps n -> a_addr): ot_dshbm_spec_state with ONE
// output register stage (dspark_top_m SPECF = 2).  The walker (busy / req_ready, n, the slot registers, the token ring)
// is the original edge for edge; each answer leaves it as {base, t = slot(n) + (p - n), ring R} and the next edge does
// the ring wrap and the base add.  Answers: the original's, one edge later (vs 5 for ot_dshbm_spec_state_f).
// ---------------------------------------------------------------------------
module ot_dshbm_spec_state_r #(
    parameter integer W     = 128,
    parameter integer PMAX  = 8,
    parameter integer WR    = 136,           // window ring (>= W + PMAX for exact rollback)
    parameter integer SR    = 10,            // compressor slot ring (>= r_max + PMAX)
    parameter integer TR    = 16,            // token ring (>= NG + PMAX)
    parameter integer NG    = 4,
    parameter integer NL    = 40,
    parameter integer NST   = 3,
    parameter integer NSRC  = 4,
    parameter [NSRC*4-1:0] RLOG = 16'h0011,  // log2 ratio per source, source c at [4c +: 4]
    parameter integer CKMAX = 1 << 16,       // compressed rows a source
    parameter integer TW    = 17,
    parameter integer AW    = 32
) (
    input  wire            clk,
    input  wire            rst_n,
    // committed position count (set by the control loop: reset, then n += 1 + a a step)
    input  wire            n_set,
    input  wire [31:0]     n_val,
    output reg  [31:0]     n,
    // token history writes (the control loop writes a pass's tokens before it runs)
    input  wire            tw_v,
    input  wire [31:0]     tw_pos,
    input  wire [TW-1:0]   tw_tok,
    // requests
    input  wire            req_v,
    output wire            req_ready,
    input  wire [3:0]      req_kind,
    input  wire [15:0]     req_idx,
    input  wire [31:0]     req_pos,
    // answers
    output reg             a_v,
    output reg  [AW-1:0]   a_addr,
    output reg  [TW-1:0]   a_tok,
    output reg             a_pad,
    output reg             a_last,
    output reg             a_err          // a request outside the rings' reach (would alias): sticky
);
    // stage 1 (the original walker edge): every answer word as {base, t = slot(n) + (p - n), ring}; stage 2: the
    // ring wrap and the base add.  slot(n) and n are sampled together in stage 1, so an n_set between the stages
    // cannot mix old and new state: the a_* stream equals ot_dshbm_spec_state's delayed by exactly one edge.
    reg            u_v, u_last, u_pad, u_err, u_wrap;
    reg  [AW-1:0]  u_base;
    reg  [31:0]    u_t;
    reg  [15:0]    u_r;
    reg  [TW-1:0]  u_tok;
    function automatic [31:0] wrapt(input [31:0] t, input [15:0] R);
        begin
            if ($signed(t) >= $signed({16'd0, R})) wrapt = t - {16'd0, R};
            else if ($signed(t) < 0) wrapt = t + {16'd0, R};
            else wrapt = t;
        end
    endfunction
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_v <= 1'b0; a_last <= 1'b0; a_pad <= 1'b0; a_err <= 1'b0; a_addr <= 0; a_tok <= 0; end
        else begin
            a_v <= u_v; a_last <= u_last; a_pad <= u_pad; if (u_err) a_err <= 1'b1;
            if (u_v) begin
                a_tok <= u_tok;
                a_addr <= u_base + (u_wrap ? AW'(wrapt(u_t, u_r) & 32'hFFFF) : {AW{1'b0}});
            end
        end
    localparam [3:0] K_WIN_WR = 1, K_WIN_RD = 2, K_DSK_WR = 3, K_DSK_RD = 4, K_SLOT_WR = 5, K_SLOT_RD = 6,
                     K_CK_WR = 7, K_IK_RD = 8, K_CK_SEL = 9, K_TOK_RD = 10;
    localparam integer A_WIN = 0;
    localparam integer A_DSK = A_WIN + NL * WR;
    localparam integer A_SLOT = A_DSK + NST * WR;
    localparam integer A_CK = A_SLOT + NSRC * SR;
    // slots of the committed count n in each ring, kept incrementally
    reg [15:0] sw_n, ss_n, st_n;
    function automatic [15:0] wrapd(input [15:0] s, input integer d, input integer R);
        integer t;
        begin
            t = s + d;
            if (t >= R) t = t - R;
            else if (t < 0) t = t + R;
            wrapd = t[15:0];
        end
    endfunction
    integer dn;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n <= 0; sw_n <= 0; ss_n <= 0; st_n <= 0;
        end else if (n_set) begin
            dn = n_val - n;
            n <= n_val;
            if (n_val == 0) begin sw_n <= 0; ss_n <= 0; st_n <= 0; end
            else begin
                sw_n <= wrapd(sw_n, dn, WR); ss_n <= wrapd(ss_n, dn, SR); st_n <= wrapd(st_n, dn, TR);
            end
        end
    end
    // token ring
    reg [TW-1:0] tring [0:TR-1];
    always @(posedge clk)
        if (tw_v) tring[wrapd(st_n, $signed(tw_pos - n), TR)] <= tw_tok;
    // ---- request walker ----
    reg        busy;
    reg [3:0]  kind;
    reg [15:0] idx;
    reg [31:0] p_cur, p_end, p_anchor, p_wrapto, i_cur, i_end;
    reg        p_wrapped, is_dsk;
    reg [3:0]  rl;
    assign req_ready = !busy;
    function automatic [3:0] rlog(input [15:0] c);
        rlog = RLOG[c*4 +: 4];
    endfunction
    // reach check: a slot of position p is valid when n - (ring - PMAX) < p < n + PMAX
    function automatic ok_reach(input [31:0] p, input integer R);
        integer d;
        begin
            d = $signed(p - n);
            ok_reach = (d < PMAX) && (d > -(R - PMAX + 1));
        end
    endfunction
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; u_v <= 1'b0; u_last <= 1'b0; u_pad <= 1'b0; u_err <= 1'b0; u_base <= 0; u_tok <= 0;
            u_t <= 0; u_r <= 0; u_wrap <= 1'b0;
        end else begin
            u_v <= 1'b0; u_last <= 1'b0; u_pad <= 1'b0; u_err <= 1'b0;
            if (!busy && req_v) begin
                kind <= req_kind; idx <= req_idx;
                rl = rlog(req_idx);
                case (req_kind)
                    K_WIN_WR, K_DSK_WR: begin
                        u_v <= 1'b1; u_last <= 1'b1;
                        u_base <= (req_kind == K_WIN_WR ? A_WIN + req_idx * WR : A_DSK + req_idx * WR); u_t <= 32'(sw_n) + (req_pos - n); u_r <= 16'(WR); u_wrap <= 1'b1;
                        if (!ok_reach(req_pos, WR)) u_err <= 1'b1;
                    end
                    K_SLOT_WR: begin
                        u_v <= 1'b1; u_last <= 1'b1;
                        u_base <= A_SLOT + req_idx * SR; u_t <= 32'(ss_n) + (req_pos - n); u_r <= 16'(SR); u_wrap <= 1'b1;
                        if (!ok_reach(req_pos, SR)) u_err <= 1'b1;
                    end
                    K_CK_WR: begin
                        u_v <= 1'b1; u_last <= 1'b1;
                        u_base <= A_CK + req_idx * CKMAX + (req_pos >> rl); u_wrap <= 1'b0;
                    end
                    K_CK_SEL: begin
                        u_v <= 1'b1; u_last <= 1'b1;
                        u_base <= A_CK + req_idx * CKMAX + req_pos; u_wrap <= 1'b0;
                    end
                    K_WIN_RD: begin
                        busy <= 1'b1; is_dsk <= 1'b0;
                        p_cur <= (req_pos + 1 > W) ? req_pos - W + 1 : 0;
                        p_end <= req_pos; p_wrapped <= 1'b1;
                    end
                    K_DSK_RD: begin
                        // ring-slot order: start at the position = 0 mod W, run to the anchor, then wrap
                        // to the oldest position and run to the slot before the start
                        busy <= 1'b1; is_dsk <= 1'b1;
                        p_anchor <= req_pos;
                        if (req_pos + 1 > W) begin
                            p_cur <= req_pos - (req_pos & (W - 1)); p_end <= req_pos;
                            p_wrapped <= ((req_pos & (W - 1)) == W - 1);   // start == oldest: one run
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
                            u_v <= 1'b1; u_last <= 1'b1; u_pad <= 1'b1;
                        end else busy <= 1'b1;
                    end
                    K_TOK_RD: begin
                        busy <= 1'b1; i_cur <= 0; p_cur <= req_pos;
                    end
                    default: begin u_v <= 1'b1; u_last <= 1'b1; u_pad <= 1'b1; u_err <= 1'b1; end
                endcase
            end else if (busy) begin
                u_v <= 1'b1;
                case (kind)
                    K_WIN_RD, K_DSK_RD: begin
                        u_base <= (kind == K_WIN_RD ? A_WIN : A_DSK) + idx * WR; u_t <= 32'(sw_n) + (p_cur - n); u_r <= 16'(WR); u_wrap <= 1'b1;
                        if (!ok_reach(p_cur, WR)) u_err <= 1'b1;
                        if (p_cur == p_end) begin
                            if (p_wrapped) begin busy <= 1'b0; u_last <= 1'b1; end
                            else begin
                                p_wrapped <= 1'b1; p_cur <= p_wrapto;
                                p_end <= p_anchor - (p_anchor & (W - 1)) - 1;
                            end
                        end else p_cur <= p_cur + 1;
                    end
                    K_SLOT_RD: begin
                        u_base <= A_SLOT + idx * SR; u_t <= 32'(ss_n) + (p_cur - n); u_r <= 16'(SR); u_wrap <= 1'b1;
                        if (!ok_reach(p_cur, SR)) u_err <= 1'b1;
                        if (p_cur == p_end) begin busy <= 1'b0; u_last <= 1'b1; end
                        else p_cur <= p_cur + 1;
                    end
                    K_IK_RD: begin
                        u_base <= A_CK + idx * CKMAX + i_cur; u_wrap <= 1'b0;
                        if (i_cur + 1 == i_end) begin busy <= 1'b0; u_last <= 1'b1; end
                        else i_cur <= i_cur + 1;
                    end
                    K_TOK_RD: begin
                        if ($signed(p_cur - i_cur) < 0) begin u_pad <= 1'b1; u_tok <= 0; end
                        else u_tok <= tring[wrapd(st_n, $signed(p_cur - i_cur - n), TR)];
                        if (i_cur == NG - 1) begin busy <= 1'b0; u_last <= 1'b1; end
                        else i_cur <= i_cur + 1;
                    end
                    default: begin busy <= 1'b0; u_last <= 1'b1; end
                endcase
            end
        end
    end
endmodule
