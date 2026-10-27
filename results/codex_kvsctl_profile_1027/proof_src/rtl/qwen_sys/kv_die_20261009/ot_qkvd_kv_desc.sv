`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// qwen-1010 2026-10-10: KV-die stream descriptor issuer (core clock, beside qkd_seq).  Closes the full-system gap found at
// 23:20: no KV-die RTL issued the per-layer stream descriptor / go to the HBM controller heads (ot_qwen_ctrl_pc_head
// cmd 0 {n, row} / cmd 1 go); only tb_hbm_stream_bw drove them.
//
// Per layer L of a token at position count T the issuer sends two words to every controller of the die (through one
// ot_async_fifo per stack and the hclk chain of ot_qkvd_kcmd_tap stations, which turn {T, layer} into each PC's own
// {n, row}):  DESC {layer, T}, then GO {layer} when the CTL ATTN of that layer arrives (attn_v).
//
// TIMED PRE-HINT.  The stream bench (tb_hbm_stream_bw CONS 1 WR_EN 1 WSETP 0) needs the descriptor at the controllers
// ~320 hclk before the go (hint 320 -> worst 1,085 ns, all 8 refresh phases; hint 0 -> 1,345 ns > the 1,165 ns step;
// posting at the previous stream's end, or early-post + PULLIN, refresh-starves the stream: 2,242 / 1,342 ns).  The ROM
// schedule is static, so the ATTN spacing is known: the issuer posts DESC (L+1) at t_attn(L) + P - LEAD, where P is
// the measured spacing of the previous identical step (layer -> layer: P_mid; layer NL-1 -> layer 0 of the next token:
// P_tok), seeded from the static-schedule CSRs p_mid_init / p_tok_init until measured.  If an ATTN arrives before its
// descriptor was posted (cold start, a stall upstream), the issuer posts DESC then GO at once (= hint 0: slower, exact).
// A posted descriptor that does not match the arriving ATTN cannot be retracted from the controllers: sticky fault.
//
// FLOW CONTROL.  Words leave through k_v / k_ready (the CDC FIFO's write side).  No per-PC credits: at most OUTST layers
// are posted and not finished (done_v = a layer's last row consumed), so every controller head FIFO holds at most
// 2 x OUTST words (<= 4 < its 8 entries); the head faults on an overflow, which this bound makes impossible.
//
// MUT (bench only): 1 = no pre-hint (descriptor at the ATTN), 2 = LEAD / 4, 3 = the descriptor's layer + 1 (wrong row).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kv_desc #(
    parameter integer NL    = 36,
    parameter integer LEAD  = 450,        // core cycles: DESC ahead of the ATTN: 320 hclk (393 core) + the trunk / CDC / chain
    parameter integer GLEAD = 80,         // core cycles: GO ahead of the ATTN = the trunk + CDC + station-chain latency, so the
                                          // go lands at the controllers when the ATTN reaches qkd_seq (an early go only
                                          // pre-fills the landing FIFOs under their credits; the KV merge substitutes row T-1)
    parameter integer OUTST = 2,
    parameter integer TW    = 20,
    parameter integer MUT   = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [TW-1:0] p_mid_init,      // static-schedule CSRs (core cycles between ATTNs); 0 = unknown
    input  wire [TW-1:0] p_tok_init,
    input  wire          attn_v,          // CTL ATTN consumed by qkd_seq
    input  wire [5:0]    attn_layer,
    input  wire [13:0]   attn_T,
    input  wire          done_v,          // a layer finished
    output reg           k_v,
    output reg  [31:0]   k_d,             // {op[1:0], 10'b0, layer[5:0], T[13:0]}; op 0 DESC, 1 GO
    input  wire          k_ready,
    output reg           fault
);
    localparam integer LD = (MUT == 2) ? LEAD / 4 : LEAD;
    // registered inputs (the ATTN / done strobes come from qkd_seq / the hub across the centre)
    reg          a_v, d_v;
    reg  [5:0]   a_l;
    reg  [13:0]  a_T;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin a_v <= 1'b0; d_v <= 1'b0; end else begin a_v <= attn_v; d_v <= done_v; end
    always @(posedge clk) begin a_l <= attn_layer; a_T <= attn_T; end

    reg  [TW-1:0] now, t_last, p_mid, p_tok, tmr;
    reg           pm_ok, pt_ok, last_ok, tv;
    reg  [5:0]    l_last;
    reg           pred_ok, posted;        // prediction (pl, pT) valid; its DESC already sent
    reg  [TW-1:0] gtmr;
    reg           gtv, gposted;           // the predicted GO's timer; GO already sent
    reg  [5:0]    pl;
    reg  [13:0]   pT;
    reg  [2:0]    outst;
    // two-word output queue (DESC, GO), one word a cycle
    reg  [31:0]   q0, q1;
    reg  [1:0]    qn;
    reg           gw, gw_d;               // a GO waiting for a queue slot (gw_d: its DESC too: degrade path)
    reg  [5:0]    gw_l;
    reg  [13:0]   gw_T;

    wire [5:0]    wl = (MUT == 3) ? pl + 6'd1 : pl;
    wire [TW-1:0] p_next_mid = pm_ok ? p_mid : p_mid_init;
    wire [TW-1:0] p_next_tok = pt_ok ? p_tok : p_tok_init;
    function automatic [31:0] wdesc(input [5:0] l, input [13:0] t);
        wdesc = {2'd0, 10'd0, ((MUT == 3) ? l + 6'd1 : l), t};
    endfunction
    function automatic [31:0] wgo(input [5:0] l, input [13:0] t);
        wgo = {2'd1, 10'd0, l, t};
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            now <= 0; t_last <= 0; p_mid <= 0; p_tok <= 0; tmr <= 0; pm_ok <= 0; pt_ok <= 0; last_ok <= 0; tv <= 0;
            l_last <= 0; pred_ok <= 0; posted <= 0; pl <= 0; pT <= 0; outst <= 0; qn <= 0; q0 <= 0; q1 <= 0;
            gw <= 0; gw_d <= 0; gw_l <= 0; gw_T <= 0; k_v <= 0; k_d <= 0; fault <= 0; gtmr <= 0; gtv <= 0; gposted <= 0;
        end else begin : step
            reg [1:0]  n;
            reg [31:0] r0, r1;
            reg        post_desc, post_go;
            reg [2:0]  o;
            reg [TW-1:0] p;
            n = qn; r0 = q0; r1 = q1; o = outst;
            now <= now + 1'b1;
            // ---- output: one word a cycle to the CDC FIFO --------------------------------------------------------
            k_v <= 1'b0;
            if (k_ready && n != 0) begin
                k_v <= 1'b1; k_d <= r0; r0 = r1; n = n - 1'b1;
            end
            if (d_v && o != 0) o = o - 1'b1;
            // ---- a waiting GO first (order: DESC L, GO L, DESC L+1, ...) ------------------------------------------
            if (gw) begin
                if (gw_d && n == 0 && o < OUTST) begin
                    r0 = wdesc(gw_l, gw_T); r1 = wgo(gw_l, gw_T); n = 2'd2; o = o + 1'b1; gw <= 1'b0;
                end else if (!gw_d && n != 2) begin
                    if (n == 0) r0 = wgo(gw_l, gw_T); else r1 = wgo(gw_l, gw_T);
                    n = n + 1'b1; gw <= 1'b0;
                end
            end
            // ---- timer: auto-post the predicted descriptor ---------------------------------------------------------
            if (tv && tmr != 0) tmr <= tmr - 1'b1;
            post_desc = (MUT != 1) && tv && tmr == 0 && pred_ok && !posted && !gw && (o < OUTST) && (n != 2);
            if (post_desc) begin
                if (n == 0) r0 = {2'd0, 10'd0, wl, pT}; else r1 = {2'd0, 10'd0, wl, pT};
                n = n + 1'b1; o = o + 1'b1; posted <= 1'b1; tv <= 1'b0;
            end
            if (gtv && gtmr != 0) gtmr <= gtmr - 1'b1;
            post_go = (MUT != 1) && gtv && gtmr == 0 && pred_ok && (posted || post_desc) && !gposted && !gw && (n != 2);
            if (post_go) begin
                if (n == 0) r0 = wgo(pl, pT); else r1 = wgo(pl, pT);
                n = n + 1'b1; gposted <= 1'b1; gtv <= 1'b0;
            end
            // ---- ATTN arrival ---------------------------------------------------------------------------------------
            if (a_v) begin
                if (last_ok && a_l == 6'd0 && l_last == 6'(NL - 1)) begin p_tok <= now - t_last; pt_ok <= 1'b1; end
                if (last_ok && a_l == l_last + 6'd1)               begin p_mid <= now - t_last; pm_ok <= 1'b1; end
                t_last <= now; l_last <= a_l; last_ok <= 1'b1;
                if (gw) fault <= 1'b1;                                   // an ATTN while the previous GO still waits
                if (pred_ok && (posted || post_desc)) begin
                    if (a_l != pl || a_T != pT) fault <= 1'b1;          // a posted descriptor cannot be retracted
                    if (gposted || post_go) begin
                        // the predicted GO is already on its way
                    end else if (n != 2) begin
                        if (n == 0) r0 = wgo(a_l, a_T); else r1 = wgo(a_l, a_T);
                        n = n + 1'b1;
                    end else begin gw <= 1'b1; gw_d <= 1'b0; gw_l <= a_l; gw_T <= a_T; end
                end else if (n == 0 && o < OUTST) begin                  // degrade: DESC then GO now
                    r0 = wdesc(a_l, a_T); r1 = wgo(a_l, a_T); n = 2'd2; o = o + 1'b1;
                end else begin
                    gw <= 1'b1; gw_d <= 1'b1; gw_l <= a_l; gw_T <= a_T;
                end
                // next prediction from the previous identical step (the static schedule makes them equal)
                posted <= 1'b0;
                if (a_l == 6'(NL - 1)) begin pl <= 6'd0; pT <= a_T + 14'd1; end
                else begin pl <= a_l + 6'd1; pT <= a_T; end
                p = (a_l == 6'(NL - 1)) ? p_next_tok : p_next_mid;
                pred_ok <= (p != 0);
                tv      <= (p != 0);
                tmr     <= (p > TW'(LD) + 1) ? p - TW'(LD) - 1'b1 : '0;
                gposted <= 1'b0;
                gtv     <= (p != 0);
                gtmr    <= (p > TW'(GLEAD) + 1) ? p - TW'(GLEAD) - 1'b1 : '0;
            end
            q0 <= r0; q1 <= r1; qn <= n; outst <= o;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// One station of the per-stack hclk command chain: registered forward to the next station and a registered,
// converted copy to its controller head (abutted to the head's cmd pins).  DESC {layer, T} -> the PC's own descriptor
// {n, row}: the PC {q, G} (G = t[2:0] of the positions it holds) of stack ST holds, per layer, 4 sectors (K/V x 2 heads)
// of every position t < T with t[2:0] = G and t[8:7] = ST (CONTRACT map), so
//   n = 4 * (16 * (T >> 9) + (m >> 3) + ((m & 7) > G)),  m = clamp((T & 511) - 128 * ST, 0, 128);  row = ROW0 + layer.
// GO -> cmd 1.  Two register stages (input, output); the arithmetic sits between them.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_kcmd_tap #(
    parameter integer G    = 0,
    parameter integer ST   = 0,
    parameter integer ROW0 = 0
) (
    input  wire        clk,               // the stack's hclk
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_d,
    output reg         o_v,               // to the next station
    output reg  [31:0] o_d,
    output reg         c_v,               // to the controller head (cmd_v / cmd)
    output reg  [31:0] c_d
);
    reg        v_q;
    reg [31:0] d_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v_q <= 1'b0; o_v <= 1'b0; c_v <= 1'b0; end
        else begin v_q <= i_v; o_v <= i_v; c_v <= v_q; end
    wire [13:0] T  = d_q[13:0];
    wire [5:0]  L  = d_q[19:14];
    wire signed [10:0] mr = $signed({2'b0, T[8:0]}) - 11'sd128 * ST;
    wire [7:0]  m  = (mr < 0) ? 8'd0 : (mr > 128) ? 8'd128 : mr[7:0];
    wire [8:0]  c  = {T[13:9], 4'b0} + {4'b0, m[7:3]} + ((m[2:0] > G) ? 9'd1 : 9'd0);
    wire [10:0] n  = {c, 2'b0};
    always @(posedge clk) begin
        d_q <= i_d; o_d <= i_d;
        c_d <= (d_q[31:30] == 2'd0) ? {2'd0, n, 19'(ROW0 + L)} : {2'd1, 30'd0};
    end
endmodule
