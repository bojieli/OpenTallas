`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Near-HBM (shoreline) attention for the Qwen3-8B ROM die at TP4: ONE HBM STACK'S ENGINE.  NEW, DEFAULT-OFF: nothing
// in the shipped core instantiates it; it is built and gated by rtl/test/nearhbm/ (exact gate) only.
//
// Shape per die: 8 query heads, 2 KV heads (GQA 4), head_dim 128, FP8 E4M3 KV (1 B, no scale), context <= 8192.
// The golden is tools/hdc_golden.py decode_token_tp / attend at G = 6144 (attn_splits = (128, 512)); the partitioned
// order this unit computes is tools/qwen_nearhbm_attn_ref.py, proven bit-identical to the golden there.
//
// KV striping: position t lives in stack S = (t mod 512) div 128.  Inside the stack t = {k[3:0], S[1:0], r[6:0]}:
// round k = t div 512, residue r; local index idx = {k, r} (0..2047); residue group gam = r div 8, slot j = r mod 8.
//
// Passes (one layer):
//   K pass   (g = 0 then 1)  every engine takes local rows idx = E, E+R, ...: 512 lanes form the exact products
//            bf16(q[4g+h][d]) x K[t][d], four 7-level pairwise adder trees and x 1/sqrt(128) give
//            the 4 scores, written to the score memory; per-engine running max.
//   max      the stack reports its local maxima, the hub returns M (order-free max over the 4 stacks).
//   exp pass (g)  quad Q takes residue groups gam = Q, Q+R, ...: e = exp(s - M) (4 pipes), bf16(e) written to the e
//            memory, and the 8-position Z chunks (8 contiguous positions = 8 residues of one round) summed
//            sequentially from +0 in an 8-slot adder loop (one chain per round, a 64-position tile transposed in time).
//   Z tree   per 128-position block (k): the 16 chunk sums of the block, pairwise (Z levels 1-4) -> the hub.
//   V pass   (g)  engine E takes residue groups gam = E, E+R, ...; its 8 lane-loop slots are the 8 residues of the group and
//            each slot's lane-adder loop (ADD_LAT + pad to 8 cycles) IS the chunk accumulator: chunk c = positions
//            t = c mod 512 in increasing t, from +0, add(acc, V x bf16(e)) (the product exact).  A finished chunk
//            stays in its loop (recirculated: add(acc, +0) = acc exactly) until the stack tree takes it.
//   P.V tree the stack's 128 residues in order through one 512-wide bank: P.V levels 1-7 -> the hub (levels 8-9).
// Every padding term is +0 and no sum is ever -0, so the zero-padded trees are the golden's trees.
//
// Arithmetic: ot_qwen_nearhbm_prod (the exact BF16 x E4M3 product, proven on all 2^24 operand pairs), ot_hdc_fp32_add_lat
// (ADD_LAT, bit-identical to the qualified add), ot_hdc_fp32_mul_lat (MUL_LAT), ot_qwen_nearhbm_exp_p / _recip_p
// (ot_hdc_exp_q / ot_hdc_recip_q on the SS-1.2 GHz units; equal to them on all 2^32 inputs).  The lane's sequential sum is add(acc, mul(v, e)),
// the golden's own two operations (the product is exact, so no fused rounding question arises).
// ---------------------------------------------------------------------------------------------------------------------

// FP32 a > b for finite operands that are never -0 (every unit here canonicalises zeros to +0)
module ot_nhb_fgt (input wire [31:0] a, input wire [31:0] b, output wire gt);
    assign gt = (a[31] != b[31]) ? !a[31] : (!a[31] ? (a[30:0] > b[30:0]) : (a[30:0] < b[30:0]));
endmodule

// synchronous FIFO, registered output, no reset on data
module ot_nhb_fifo #(parameter integer W = 32, parameter integer D = 16) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         push,
    input  wire [W-1:0] din,
    input  wire         pop,
    output wire [W-1:0] dout,
    output wire         nonempty,
    output reg  [$clog2(D+1)-1:0] count
);
    localparam integer AW = (D > 1) ? $clog2(D) : 1;
    reg [W-1:0] mem [0:D-1];
    reg [AW-1:0] rp, wp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rp <= 0; wp <= 0; count <= 0; end
        else begin
            if (push) wp <= (wp == D - 1) ? 0 : wp + 1;
            if (pop) rp <= (rp == D - 1) ? 0 : rp + 1;
            count <= count + (push ? 1 : 0) - (pop ? 1 : 0);
        end
    end
    always @(posedge clk) if (push) mem[wp] <= din;
    assign dout = mem[rp];
    assign nonempty = (count != 0);
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// One row engine: 4 heads x HD lanes, one KV row per cycle.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_row_engine #(
    parameter integer HD = 128,
    parameter integer S = 0,             // stack index 0..3
    parameter integer R = 1,             // row engines in the stack
    parameter integer E = 0,             // this engine
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 32,           // row / e FIFO depth = outstanding-request credit
    parameter [31:0]  SCALE = 32'h3DB504F3
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,        // layer start (T stable from here)
    input  wire [13:0]          T,            // context length 1..8192 (positions 0..T-1)
    input  wire [2:0]           cyc8,         // global slot counter
    input  wire                 q_ready,      // q registers loaded
    input  wire [8*HD*16-1:0]   q_bf16,       // q[h][d] at [(h*HD+d)*16 +: 16]
    input  wire [31:0]          exp_done,     // {g1 gam15..0, g0 gam15..0}: e of group written
    // HBM row requests (in order) and responses (in request order)
    output reg                  req_valid,
    output reg                  req_v,        // 0 K row, 1 V row
    output reg                  req_g,
    output reg  [12:0]          req_t,
    input  wire                 rsp_valid,
    input  wire [HD*8-1:0]      rsp_data,
    // e memory read (data one cycle later)
    output reg                  er_valid,
    output reg  [11:0]          er_addr,      // {g, idx}
    input  wire [63:0]          er_data,
    // scores
    output wire                 sc_valid,
    output wire [11:0]          sc_addr,      // {g, idx}
    output wire [127:0]         sc_data,
    output reg  [2*4*32-1:0]    lmax,         // running max [g][h]
    output reg  [1:0]           lmax_any,
    // P.V leaves
    output wire                 lf_valid,
    output wire                 lf_g,
    output wire [3:0]           lf_gam,
    output wire [2:0]           lf_slot,
    output wire [4*HD*32-1:0]   lf_data,
    input  wire                 lf_take,
    output reg                  k_done,       // every K row consumed
    output reg                  v_done,       // every V chunk issued (leaves may still be pending)
    output reg                  fault,
    // cycle markers for the bench
    output reg                  ev_k_first,
    output reg                  ev_v_first
);
    localparam integer LN = 4 * HD;
    localparam integer LV = $clog2(HD);
    localparam integer KDRAIN = (LV - 1) * ADD_LAT + 1;   // a K row's tree leaves the lane adders
    localparam integer KDEPTH = 4 + LV * ADD_LAT + MUL_LAT;     // product, lane adder (level 1), levels 2..LV, scale
    localparam [1:0]   SB = S;

    // ---- stack geometry ----------------------------------------------------------------------------------------------
    wire [13:0] base_s = 14'd128 * S;
    wire        any_s = (T > base_s);
    wire [13:0] rem = T - base_s;                                        // positions at or after this stack's base
    wire [4:0]  gmax = !any_s ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));   // nonempty groups
    // positions in this stack: 128 per full 512 round, plus the partial round's share
    wire [13:0] tail = {5'd0, T[8:0]};
    wire [13:0] part = (tail > base_s) ? ((tail - base_s > 14'd128) ? 14'd128 : (tail - base_s)) : 14'd0;
    wire [11:0] n_s = {T[13:9], 7'd0} + part[11:0];
    function automatic [13:0] tpos(input [3:0] k, input [6:0] r);
        tpos = {1'b0, k, SB, r};
    endfunction
    function automatic [3:0] klast(input [3:0] gam);     // last round of residue group gam (group nonempty)
        reg [13:0] b;
        begin
            b = base_s + {7'd0, gam, 3'd0};
            klast = (T - 14'd1 - b) >> 9;
        end
    endfunction

    // ---- request generator -------------------------------------------------------------------------------------------
    reg        rg_run, rg_vph, rg_g;
    reg [11:0] rg_idx;                                  // K: local index
    reg [4:0]  rg_gam;
    reg [3:0]  rg_k;
    reg [2:0]  rg_j;
    reg [$clog2(DQ+1)-1:0] credit_used;
    wire       consume;                                 // a row popped this cycle
    wire [13:0] rg_vt = tpos(rg_k, {rg_gam[3:0], rg_j});
    wire       rg_k_ok = rg_run && !rg_vph && (rg_idx < n_s);
    wire       rg_v_valid_row = (rg_vt < T);
    wire       rg_v_gate = exp_done[{rg_g, rg_gam[3:0]}];
    wire       has_credit = (credit_used < DQ);
    reg        issue;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rg_run <= 1'b0; rg_vph <= 1'b0; rg_g <= 1'b0; rg_idx <= 0; rg_gam <= 0; rg_k <= 0; rg_j <= 0;
            req_valid <= 1'b0; er_valid <= 1'b0; credit_used <= 0;
        end else begin
            req_valid <= 1'b0; er_valid <= 1'b0;
            issue = 1'b0;
            if (start) begin
                rg_run <= 1'b1; rg_vph <= 1'b0; rg_g <= 1'b0; rg_idx <= E; rg_gam <= E; rg_k <= 0; rg_j <= 0;
            end else if (rg_run && !rg_vph) begin
                if (rg_idx < n_s) begin
                    if (has_credit) begin
                        issue = 1'b1;
                        req_valid <= 1'b1; req_v <= 1'b0; req_g <= rg_g;
                        req_t <= tpos(rg_idx[10:7], rg_idx[6:0]);
                        rg_idx <= rg_idx + R;
                    end
                end else if (!rg_g) begin
                    rg_g <= 1'b1; rg_idx <= E;
                end else begin
                    rg_vph <= 1'b1; rg_g <= 1'b0; rg_gam <= E; rg_k <= 0; rg_j <= 0;
                end
            end else if (rg_run && rg_vph) begin
                if (rg_gam < gmax) begin
                    if (!rg_v_valid_row || (rg_v_gate && has_credit)) begin
                        if (rg_v_valid_row) begin
                            issue = 1'b1;
                            req_valid <= 1'b1; req_v <= 1'b1; req_g <= rg_g; req_t <= rg_vt[12:0];
                            er_valid <= 1'b1; er_addr <= {rg_g, rg_k, rg_gam[3:0], rg_j};
                        end
                        rg_j <= rg_j + 3'd1;
                        if (rg_j == 3'd7) begin
                            if (rg_k == klast(rg_gam[3:0])) begin
                                rg_k <= 0;
                                rg_gam <= rg_gam + R;
                            end else rg_k <= rg_k + 4'd1;
                        end
                    end
                end else if (!rg_g) begin
                    rg_g <= 1'b1; rg_gam <= E; rg_k <= 0; rg_j <= 0;
                end else rg_run <= 1'b0;
            end
            credit_used <= credit_used + (issue ? 1 : 0) - (consume ? 1 : 0);
        end
    end

    // ---- row and e FIFOs ---------------------------------------------------------------------------------------------
    wire [HD*8-1:0] row;
    wire            row_ne;
    wire [$clog2(DQ+1)-1:0] row_cnt, e_cnt;
    reg             er_pend;
    wire [63:0]     e_word;
    wire            e_ne;
    always @(posedge clk or negedge rst_n) if (!rst_n) er_pend <= 1'b0; else er_pend <= er_valid;
    ot_nhb_fifo #(.W(HD*8), .D(DQ)) u_rows (.clk(clk), .rst_n(rst_n), .push(rsp_valid), .din(rsp_data),
                                             .pop(consume), .dout(row), .nonempty(row_ne), .count(row_cnt));
    wire pop_e;
    ot_nhb_fifo #(.W(64), .D(DQ)) u_e (.clk(clk), .rst_n(rst_n), .push(er_pend), .din(er_data),
                                        .pop(pop_e), .dout(e_word), .nonempty(e_ne), .count(e_cnt));

    // ---- consumption: K pass -----------------------------------------------------------------------------------------
    reg        c_vph, c_g, c_fin;
    reg [11:0] c_idx;
    reg [4:0]  c_gam;
    reg [3:0]  c_k;
    reg [2:0]  c_j;
    reg [7:0]  pend;                                    // slot holds a finished chunk (blocks the slot)
    reg [7:0]  arm;                                     // ... and its final value has reached the loop output
    reg [7:0]  pend_g;
    reg [3:0]  pend_gam [0:7];
    reg        c_started;
    wire       k_issue = c_started && !c_vph && !c_fin && (c_idx < n_s) && row_ne && q_ready;
    // V pass
    wire [13:0] c_vt = tpos(c_k, {c_gam[3:0], c_j});
    wire        c_vrow = (c_vt < T);
    reg  [7:0]  kdrain;                                 // cycles since the last K issue, saturating
    wire        v_here = c_started && c_vph && !c_fin && (c_gam < gmax) && (c_j == cyc8) && (kdrain >= KDRAIN);
    // The loop value of slot s is at the pad output fb when cyc8 = s + 4 (product LAT 4 + adder LAT + pad = 12 cycles
    // after the issue at slot s's turn).  A slot's last issue sets pend; one offer turn later (arm) the value in fb is
    // final, and it is offered to the tree each turn until taken.  The slot takes no new chain while pend is set.
    wire [2:0]  os = cyc8 - 3'd4;
    wire        offer = pend[os] && arm[os];
    wire        take = offer && lf_take;
    wire        slot_ok = (c_k != 4'd0) || !pend[cyc8];
    wire        data_ok = !c_vrow || (row_ne && e_ne);
    wire        v_issue = v_here && slot_ok && data_ok;
    wire        v_pop = v_issue && c_vrow;
    assign consume = k_issue || v_pop;
    assign pop_e = v_pop;
    wire        v_last_k = (c_k == klast(c_gam[3:0]));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) kdrain <= 8'd255;
        else if (k_issue) kdrain <= 8'd0;
        else if (kdrain != 8'd255) kdrain <= kdrain + 8'd1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            c_started <= 1'b0; c_vph <= 1'b0; c_g <= 1'b0; c_fin <= 1'b0; c_idx <= 0; c_gam <= 0; c_k <= 0; c_j <= 0;
            pend <= 8'd0; arm <= 8'd0; pend_g <= 8'd0; k_done <= 1'b0; v_done <= 1'b0; ev_k_first <= 1'b0; ev_v_first <= 1'b0;
        end else begin
            ev_k_first <= 1'b0; ev_v_first <= 1'b0;
            if (start) begin
                c_started <= 1'b1; c_vph <= 1'b0; c_g <= 1'b0; c_fin <= 1'b0; c_idx <= E; c_gam <= E; c_k <= 0;
                c_j <= 0; pend <= 8'd0; arm <= 8'd0; k_done <= 1'b0; v_done <= 1'b0;
            end else if (c_started && !c_fin) begin
                if (!c_vph) begin
                    if (c_idx < n_s) begin
                        if (k_issue) begin
                            c_idx <= c_idx + R;
                            if (c_idx == E && !c_g) ev_k_first <= 1'b1;
                        end
                    end else if (!c_g) begin
                        c_g <= 1'b1; c_idx <= E;
                    end else begin
                        c_vph <= 1'b1; c_g <= 1'b0; c_gam <= E; c_k <= 0; c_j <= 0; k_done <= 1'b1;
                    end
                end else begin
                    if (c_gam < gmax) begin
                        if (v_issue) begin
                            if (c_k == 0 && c_j == 0 && c_gam == E && !c_g) ev_v_first <= 1'b1;
                            c_j <= c_j + 3'd1;
                            if (c_j == 3'd7) begin
                                if (v_last_k) begin c_k <= 0; c_gam <= c_gam + R; end
                                else c_k <= c_k + 4'd1;
                            end
                        end
                    end else if (!c_g) begin
                        c_g <= 1'b1; c_gam <= E; c_k <= 0; c_j <= 0;
                    end else begin
                        c_fin <= 1'b1; v_done <= 1'b1;
                    end
                end
            end
            // pending leaves: set by the last-round issue, armed one offer turn later, cleared when the tree takes it
            if (pend[os] && !arm[os]) arm[os] <= 1'b1;
            if (take) begin pend[os] <= 1'b0; arm[os] <= 1'b0; end
            if (v_issue && v_last_k) begin
                pend[cyc8] <= 1'b1; arm[cyc8] <= 1'b0; pend_g[cyc8] <= c_g; pend_gam[cyc8] <= c_gam[3:0];
            end
        end
    end

    // ---- the lanes ---------------------------------------------------------------------------------------------------
    // Each lane: the exact product unit (ot_qwen_nearhbm_prod, LAT 4) and one adder (ADD_LAT) whose output, padded to
    // 8 cycles, is the lane's loop.
    // K pass: the head's whole 7-level score tree runs on its 128 lane adders -- level 1 node i on even lane 2i
    //   (p[2i] + p[2i+1]); level l >= 2 node i on odd lane 2 (base(l) + i) + 1, base(l) = sum_{k=2}^{l-1} HD / 2^k
    //   (63 of the 64 odd lanes).  Every node has its own adder, so rows stream at one per cycle.
    // V pass: acc = add(acc, p) -- +0 instead of acc on a chunk's first position, +0 instead of p on a recirculation
    //   (add(acc, +0) = acc exactly: the adder's zero-operand bypass).  A V issue waits until the last K row's tree
    //   has left the lane adders (KDRAIN cycles), so the two uses never meet in one adder.
    localparam integer PLAT = 4;
    wire [LN*32-1:0] p_y, l_y, fb;
    wire [LN-1:0]    p_vo, p_f, l_vo, l_f;
    wire kd, vd, czd;
    ot_hdc_delay #(.W(3), .D(PLAT), .RESET(1)) u_ctl (.clk(clk), .rst_n(rst_n),
        .d({k_issue, v_issue && c_vrow, v_issue && (c_k == 4'd0)}), .q({kd, vd, czd}));
    // kl[l]: a K row's level-l nodes are being formed (level 1 = kd)
    wire [LV:1] kl;
    assign kl[1] = kd;
    genvar l;
    generate for (l = 2; l <= LV; l = l + 1) begin : g_kl
        ot_hdc_delay #(.W(1), .D(ADD_LAT), .RESET(1)) u_kl (.clk(clk), .rst_n(rst_n), .d(kl[l-1]), .q(kl[l]));
    end endgenerate
    function automatic integer tbase(input integer lev);      // first odd-lane slot of level lev (>= 2)
        integer k;
        begin
            tbase = 0;
            for (k = 2; k < lev; k = k + 1) tbase = tbase + (HD >> k);
        end
    endfunction
    function automatic integer tlev(input integer m);          // level held by odd-lane slot m (0 = unused)
        integer k;
        begin
            tlev = 0;
            for (k = LV; k >= 2; k = k - 1) if (m >= tbase(k) && m < tbase(k) + (HD >> k)) tlev = k;
        end
    endfunction
    function automatic integer tnode(input integer lev, input integer idx);   // lane (within the head) of node (lev, idx)
        tnode = (lev == 1) ? 2 * idx : 2 * (tbase(lev) + idx) + 1;
    endfunction
    genvar h, d;
    generate
        for (h = 0; h < 4; h = h + 1) begin : g_h
            for (d = 0; d < HD; d = d + 1) begin : g_d
                localparam integer L = h * HD + d;
                localparam integer TL = (d % 2 == 0) ? 1 : tlev((d - 1) / 2);         // tree level of this lane
                localparam integer TI = (d % 2 == 0) ? d / 2 : (d - 1) / 2 - tbase(TL > 1 ? TL : 2);
                wire [15:0] qv = c_g ? q_bf16[(4 + h) * HD * 16 + d * 16 +: 16] : q_bf16[h * HD * 16 + d * 16 +: 16];
                wire [15:0] ev = e_word[16*h +: 16];
                ot_qwen_nearhbm_prod u_p (.clk(clk), .rst_n(rst_n), .valid_in(k_issue || (v_issue && c_vrow)),
                    .a(k_issue ? qv : ev), .k(row[8*d +: 8]), .y(p_y[32*L +: 32]), .fault(p_f[L]), .valid_out(p_vo[L]));
                wire [31:0] va = czd ? 32'd0 : fb[32*L +: 32];
                wire [31:0] vb = vd ? p_y[32*L +: 32] : 32'd0;
                wire [31:0] la, lb;
                wire        kt;
                if (TL == 1) begin : g_l1
                    assign kt = kl[1];
                    assign la = kt ? p_y[32*L +: 32] : va;
                    assign lb = kt ? p_y[32*(L+1) +: 32] : vb;
                end else if (TL >= 2) begin : g_ln
                    localparam integer LA = h * HD + tnode(TL - 1, 2 * TI);
                    localparam integer LB = h * HD + tnode(TL - 1, 2 * TI + 1);
                    assign kt = kl[TL];
                    assign la = kt ? l_y[32*LA +: 32] : va;
                    assign lb = kt ? l_y[32*LB +: 32] : vb;
                end else begin : g_free
                    assign kt = 1'b0;
                    assign la = va;
                    assign lb = vb;
                end
                wire [1:0] err;
                ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_a (.clk(clk), .rst_n(rst_n), .valid_in(kt || vd), .a(la), .b(lb),
                    .y(l_y[32*L +: 32]), .err(err), .valid_out(l_vo[L]));
                assign l_f[L] = l_vo[L] && (err != 2'd0);
                ot_hdc_delay #(.W(32), .D(8 - ADD_LAT)) u_pad (.clk(clk), .rst_n(rst_n), .d(l_y[32*L +: 32]),
                                                               .q(fb[32*L +: 32]));
            end
        end
    endgenerate
    assign lf_valid = offer;
    assign lf_g = pend_g[os];
    assign lf_gam = pend_gam[os];
    assign lf_slot = os;
    assign lf_data = fb;

    // ---- K pass: the root (level LV) x SCALE, tags ----------------------------------------------------------------------
    wire kroot;                                        // the lane adders' root output is a K row's tree sum
    wire [11:0] tag_sc;
    ot_hdc_delay #(.W(1), .D(ADD_LAT), .RESET(1)) u_kvm (.clk(clk), .rst_n(rst_n), .d(kl[LV]), .q(kroot));
    ot_hdc_delay #(.W(12), .D(KDEPTH)) u_tag (.clk(clk), .rst_n(rst_n),
                                              .d({c_g, c_idx[10:0]}), .q(tag_sc));
    wire [3:0] sv;
    wire [3:0] tf;
    wire [3:0] tree_fault = 4'd0;                      // the tree adders are the lane adders (their faults: l_f)
    generate
        for (h = 0; h < 4; h = h + 1) begin : g_root
            localparam integer LR = h * HD + tnode(LV, 0);
            wire [1:0] merr;
            ot_hdc_fp32_mul_lat #(.LAT(MUL_LAT)) u_scale (
                .clk(clk), .rst_n(rst_n), .valid_in(kroot), .a(l_y[32*LR +: 32]), .b(SCALE),
                .y(sc_data[32*h +: 32]), .err(merr), .valid_out(sv[h]));
            assign tf[h] = sv[h] && (merr != 2'd0);
        end
    endgenerate
    assign sc_valid = sv[0];
    assign sc_addr = tag_sc;

    // running max per [g][h] of this engine's scores
    wire [3:0] gtv;
    generate
        for (h = 0; h < 4; h = h + 1) begin : g_mx
            ot_nhb_fgt u_gt (.a(sc_data[32*h +: 32]), .b(lmax[32*(4*tag_sc[11] + h) +: 32]), .gt(gtv[h]));
        end
    endgenerate
    // product refusals (K or V issues) and the lane adders' faults
    wire mac_fault = (|(p_f & p_vo)) || (|l_f);
    integer hh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin lmax <= 0; lmax_any <= 2'b00; fault <= 1'b0; end
        else begin
            if (start) begin lmax_any <= 2'b00; fault <= 1'b0; end
            else begin
                if (sc_valid) begin
                    for (hh = 0; hh < 4; hh = hh + 1)
                        if (!lmax_any[tag_sc[11]] || gtv[hh]) lmax[32*(4*tag_sc[11] + hh) +: 32] <= sc_data[32*hh +: 32];
                    lmax_any[tag_sc[11]] <= 1'b1;
                end
                if ((|tf) || (|tree_fault) || mac_fault) fault <= 1'b1;
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Exp quad: e = exp(s - M) for the 4 heads of one position per cycle, bf16(e) to the e memory, and the Z chunks.
// Residue group gam (8 residues) is processed as tiles of 64 positions (8 rounds x 8 residues): cycle n of a tile is
// round k = 8 tau + n mod 8, residue j = n div 8, so chunk (k, gam) -- the 8 contiguous positions 512k + 128S + 8gam
// + j -- receives its j-th element every 8 cycles and the 8-cycle adder loop (ADD_LAT + pad) sums it sequentially.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_exp_quad #(
    parameter integer S = 0,
    parameter integer R = 1,
    parameter integer Q = 0,
    parameter integer ADD_LAT = 7
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,
    input  wire [13:0]  T,
    input  wire [1:0]   go,               // pass g may start: scores of g written and M of g received
    input  wire [255:0] M,                // [g][h]
    output reg          rd_valid,
    output reg  [11:0]  rd_addr,
    input  wire [127:0] rd_data,          // one cycle after rd_valid
    output wire         ew_valid,
    output wire [11:0]  ew_addr,
    output wire [63:0]  ew_data,
    output wire         zw_valid,
    output wire         zw_g,
    output wire [3:0]   zw_k,
    output wire [3:0]   zw_gam,
    output wire [127:0] zw_data,
    output wire         gd_valid,         // group finished (every e and chunk of it written)
    output wire         gd_g,
    output wire [3:0]   gd_gam,
    output reg  [1:0]   qdone,
    output reg          fault,
    output reg          ev_first
);
    localparam integer SFU_LA = 7, SFU_LM = 6;          // ot_qwen_nearhbm_exp_p: binary32 steps that close at SS 1.2 GHz
    localparam integer XD = 7 * SFU_LM + 8 * SFU_LA + 4;  // its depth: 102 (ot_hdc_exp_q, LAT 3 / 3: 49)
    localparam integer D = 1 + ADD_LAT + XD;
    localparam integer PAD = 8 - ADD_LAT;
    localparam [1:0] SB = S;
    wire [13:0] base_s = 14'd128 * S;
    wire        any_s = (T > base_s);
    wire [13:0] rem = T - base_s;
    wire [4:0]  gmax = !any_s ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));
    function automatic [3:0] klast(input [3:0] gam);
        reg [13:0] b;
        begin
            b = base_s + {7'd0, gam, 3'd0};
            klast = (T - 14'd1 - b) >> 9;
        end
    endfunction

    // sequencer
    reg       run, sg, active, tau, wait_drain;
    reg [4:0] gam;
    reg [5:0] n;
    reg [7:0] drain;
    wire      last_tile = (tau == 1'b1) || (klast(gam[3:0]) < 4'd8);
    wire [3:0] k_now = {tau, n[2:0]};
    wire [13:0] t_now = {1'b0, k_now, SB, gam[3:0], n[5:3]};
    // tag: {valid_pos, first, last_elem, last_group, g, idx(11), k(4), gam(4)}
    localparam integer TW = 4 + 1 + 11 + 4 + 4;
    reg [TW-1:0] tag0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; sg <= 1'b0; active <= 1'b0; tau <= 1'b0; gam <= 0; n <= 0; rd_valid <= 1'b0;
            qdone <= 2'b00; wait_drain <= 1'b0; drain <= 0; ev_first <= 1'b0;
        end else begin
            rd_valid <= 1'b0; ev_first <= 1'b0;
            if (start) begin
                run <= 1'b1; sg <= 1'b0; active <= 1'b0; qdone <= 2'b00; wait_drain <= 1'b0;
            end else if (run) begin
                if (wait_drain) begin
                    // the pass's last group-done marker has landed when the drain counter expires
                    if (drain == 0) begin
                        wait_drain <= 1'b0; qdone[sg] <= 1'b1;
                        if (sg) run <= 1'b0; else sg <= 1'b1;
                    end else drain <= drain - 8'd1;
                end else if (!active) begin
                    if (go[sg]) begin
                        active <= 1'b1; gam <= Q; tau <= 1'b0; n <= 0;
                        if (!sg) ev_first <= 1'b1;
                    end
                end else if (gam >= gmax) begin
                    active <= 1'b0; wait_drain <= 1'b1; drain <= D + 10;
                end else begin
                    rd_valid <= 1'b1;
                    rd_addr <= {sg, k_now, gam[3:0], n[5:3]};
                    tag0 <= {t_now < T, n[5:3] == 3'd0, n[5:3] == 3'd7, last_tile && n == 6'd63, sg,
                             k_now, gam[3:0], n[5:3], k_now, gam[3:0]};
                    n <= n + 6'd1;
                    if (n == 6'd63) begin
                        if (last_tile) begin tau <= 1'b0; gam <= gam + R; end
                        else tau <= 1'b1;
                    end
                end
            end
        end
    end
    // tag at the read data (+1)
    reg [TW-1:0] tag1;
    reg          v1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) v1 <= 1'b0; else v1 <= rd_valid;
    end
    always @(posedge clk) tag1 <= tag0;
    wire pv1 = v1 && tag1[TW-1];                       // a position < T
    // subtract M, exp
    wire [TW:0] tagD;
    ot_hdc_delay #(.W(TW+1), .D(ADD_LAT + XD)) u_tag (.clk(clk), .rst_n(rst_n), .d({v1, tag1}), .q(tagD));
    wire [127:0] e;
    wire [3:0] sf, xf;
    genvar h;
    generate
        for (h = 0; h < 4; h = h + 1) begin : g_h
            wire [31:0] mm = M[32*(4*tag1[TW-5] + h) +: 32];
            wire [31:0] x;
            wire [1:0] err;
            wire vo, xvo;
            ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_sub (
                .clk(clk), .rst_n(rst_n), .valid_in(pv1), .a(pv1 ? rd_data[32*h +: 32] : 32'd0),
                .b(pv1 ? {~mm[31], mm[30:0]} : 32'd0), .y(x), .err(err), .valid_out(vo));
            assign sf[h] = vo && (err != 2'd0);
            ot_qwen_nearhbm_exp_p #(.LA(SFU_LA), .LM(SFU_LM)) u_exp (.clk(clk), .rst_n(rst_n), .v(vo), .x(x),
                .y(e[32*h +: 32]), .vo(xvo), .fault(xf[h]));
        end
    endgenerate
    wire        vD = tagD[TW];
    wire        posD = vD && tagD[TW-1];
    wire        firstD = tagD[TW-2];
    // e write: bf16 RNE of e
    function automatic [15:0] bf16(input [31:0] x);
        bf16 = x[31:16] + ((x[15] && (x[14:0] != 15'd0 || x[16])) ? 16'd1 : 16'd0);
    endfunction
    assign ew_valid = posD;
    assign ew_addr = {tagD[TW-5], tagD[18:8]};
    assign ew_data = {bf16(e[127:96]), bf16(e[95:64]), bf16(e[63:32]), bf16(e[31:0])};
    // Z chains: chunk (k, gam) element j at its 8-cycle slot; element 0 starts from +0; positions >= T add +0
    wire [127:0] zy, zfb;
    wire [3:0] zf;
    generate
        for (h = 0; h < 4; h = h + 1) begin : g_z
            wire [1:0] err;
            wire vo;
            ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_chain (
                .clk(clk), .rst_n(rst_n), .valid_in(vD), .a(firstD ? 32'd0 : zfb[32*h +: 32]),
                .b(posD ? e[32*h +: 32] : 32'd0), .y(zy[32*h +: 32]), .err(err), .valid_out(vo));
            assign zf[h] = vo && (err != 2'd0);
            ot_hdc_delay #(.W(32), .D(PAD)) u_pad (.clk(clk), .rst_n(rst_n), .d(zy[32*h +: 32]), .q(zfb[32*h +: 32]));
        end
    endgenerate
    // a chunk is complete 8 cycles after its last element issued
    wire [TW:0] tagZ;
    ot_hdc_delay #(.W(TW+1), .D(8)) u_tz (.clk(clk), .rst_n(rst_n), .d(tagD), .q(tagZ));
    assign zw_valid = tagZ[TW] && tagZ[TW-3];
    assign zw_g = tagZ[TW-5];
    assign zw_k = tagZ[7:4];
    assign zw_gam = tagZ[3:0];
    assign zw_data = zfb;
    assign gd_valid = tagZ[TW] && tagZ[TW-4];
    assign gd_g = tagZ[TW-5];
    assign gd_gam = tagZ[3:0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) fault <= 1'b0;
        else if (start) fault <= 1'b0;
        else if ((|sf) || (posD && (|xf)) || (|zf)) fault <= 1'b1;
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Z tree: per 128-position block (k), the 16 chunk sums of residue groups gam = 0..15 (+0 for a chunk at or past T),
// pairwise ((c0 + c1) + (c2 + c3)) ... = Z levels 1-4.  Level-synchronous over every block, ZW adders per head.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_ztree #(
    parameter integer S = 0,
    parameter integer R = 1,
    parameter integer ADD_LAT = 7,
    parameter integer ZW = 4
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          start,
    input  wire [13:0]   T,
    input  wire [R-1:0]  zw_valid,
    input  wire [R-1:0]  zw_g,
    input  wire [4*R-1:0] zw_k,
    input  wire [4*R-1:0] zw_gam,
    input  wire [128*R-1:0] zw_data,
    input  wire [1:0]    go,              // every quad finished pass g
    output wire          mo_valid,        // block sum (or zdone) message
    output wire          mo_done,         // 1: zdone(g)
    output wire          mo_g,
    output wire [1:0]    mo_hh,
    output wire [3:0]    mo_k,
    output wire [31:0]   mo_data,
    input  wire          mo_ready,
    output reg           fault
);
    wire [13:0] base_s = 14'd128 * S;
    wire        any_s = (T > base_s);
    wire [4:0]  nblk = !any_s ? 5'd0 : (((T - base_s - 14'd1) >> 9) + 14'd1);
    reg [31:0] zc [0:2047];                      // {g, h, k, gam}
    reg [31:0] w [0:1023];                       // {h, k, i}
    integer r_, h_;
    always @(posedge clk) begin
        for (r_ = 0; r_ < R; r_ = r_ + 1)
            if (zw_valid[r_])
                for (h_ = 0; h_ < 4; h_ = h_ + 1)
                    zc[{zw_g[r_], h_[1:0], zw_k[4*r_ +: 4], zw_gam[4*r_ +: 4]}] <= zw_data[128*r_ + 32*h_ +: 32];
    end
    // level-synchronous tree; w holds node i of block k of head h at {h, k, i}
    reg        run, sg, busy, sending;
    reg [2:0]  lvl;                              // 1..4
    reg [8:0]  p;                                // pair index k * m + i
    reg [3:0]  wt;
    reg [6:0]  so;                               // send index {k, h}
    wire [4:0] m = 5'd16 >> lvl;
    wire [8:0] npair = nblk * m;
    reg [ZW-1:0] iv;
    reg [7:0]  ia [0:ZW-1];
    reg [ZW*4*32-1:0] oa, ob;
    integer z, hh2;
    reg [8:0] pz;
    reg [3:0] kk;
    reg [2:0] ii;
    reg [13:0] cb;
    always @* begin
        for (z = 0; z < ZW; z = z + 1) begin
            pz = p + z;
            iv[z] = busy && !sending && (pz < npair) && (wt == 0);
            kk = (lvl == 3'd1) ? pz[6:3] : (lvl == 3'd2) ? pz[5:2] : (lvl == 3'd3) ? pz[4:1] : pz[3:0];
            ii = (lvl == 3'd1) ? pz[2:0] : (lvl == 3'd2) ? {1'b0, pz[1:0]} : (lvl == 3'd3) ? {2'b0, pz[0]} : 3'd0;
            ia[z] = {kk, 1'b0, ii};
            cb = base_s + {kk, 9'd0} + {7'd0, ii, 4'd0};             // the chunk 2i at 8 * (2i)
            for (hh2 = 0; hh2 < 4; hh2 = hh2 + 1) begin
                if (lvl == 3'd1) begin
                    oa[32*(4*z + hh2) +: 32] = (cb < T) ? zc[{sg, hh2[1:0], kk, ii, 1'b0}] : 32'd0;
                    ob[32*(4*z + hh2) +: 32] = (cb + 14'd8 < T) ? zc[{sg, hh2[1:0], kk, ii, 1'b1}] : 32'd0;
                end else begin
                    oa[32*(4*z + hh2) +: 32] = w[{hh2[1:0], kk, ii, 1'b0}];
                    ob[32*(4*z + hh2) +: 32] = w[{hh2[1:0], kk, ii, 1'b1}];
                end
            end
        end
    end
    // operand register: the 2,048-entry chunk reads and the zero mask get their own cycle
    reg [ZW-1:0] iv_r;
    reg [ZW*4*32-1:0] oa_r, ob_r;
    reg [ZW*8-1:0] ia_r;
    always @(posedge clk or negedge rst_n) if (!rst_n) iv_r <= 0; else iv_r <= iv;
    always @(posedge clk) begin
        oa_r <= oa; ob_r <= ob;
        for (z = 0; z < ZW; z = z + 1) ia_r[8*z +: 8] <= ia[z];
    end
    wire [ZW*4*32-1:0] oy;
    wire [ZW*4-1:0] ovo, oerr;
    wire [ZW*9-1:0] wi;
    genvar gz, gh;
    generate
        for (gz = 0; gz < ZW; gz = gz + 1) begin : g_z
            ot_hdc_delay #(.W(9), .D(ADD_LAT), .RESET(1)) u_i (.clk(clk), .rst_n(rst_n), .d({iv_r[gz], ia_r[8*gz +: 8]}),
                                                               .q(wi[9*gz +: 9]));
            for (gh = 0; gh < 4; gh = gh + 1) begin : g_h
                wire [1:0] err;
                ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
                    .clk(clk), .rst_n(rst_n), .valid_in(iv_r[gz]), .a(oa_r[32*(4*gz+gh) +: 32]), .b(ob_r[32*(4*gz+gh) +: 32]),
                    .y(oy[32*(4*gz+gh) +: 32]), .err(err), .valid_out(ovo[4*gz+gh]));
                assign oerr[4*gz+gh] = ovo[4*gz+gh] && (err != 2'd0);
            end
        end
    endgenerate
    integer zz, hq;
    always @(posedge clk) begin
        for (zz = 0; zz < ZW; zz = zz + 1)
            if (wi[9*zz + 8])
                for (hq = 0; hq < 4; hq = hq + 1)
                    w[{hq[1:0], wi[9*zz + 4 +: 4], wi[9*zz +: 4]}] <= oy[32*(4*zz + hq) +: 32];
    end
    wire [6:0] nsend = {nblk, 2'b00};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; sg <= 1'b0; busy <= 1'b0; sending <= 1'b0; lvl <= 3'd1; p <= 0; wt <= 0; so <= 0;
            fault <= 1'b0;
        end else begin
            if (|oerr) fault <= 1'b1;
            if (start) begin run <= 1'b1; sg <= 1'b0; busy <= 1'b0; sending <= 1'b0; fault <= 1'b0; end
            else if (run) begin
                if (!busy) begin
                    if (go[sg]) begin busy <= 1'b1; lvl <= 3'd1; p <= 0; wt <= 0; sending <= 1'b0; end
                end else if (!sending) begin
                    if (wt != 0) begin
                        wt <= wt - 4'd1;
                        if (wt == 4'd1) begin
                            if (lvl == 3'd4) begin sending <= 1'b1; so <= 0; end
                            else begin lvl <= lvl + 3'd1; p <= 0; end
                        end
                    end else if (p + ZW >= npair) begin
                        p <= 0; wt <= ADD_LAT + 3;            // drain the level (operand register + adder)
                    end else p <= p + ZW;
                end else if (mo_ready) begin
                    if (so < nsend) so <= so + 7'd1;
                    else begin
                        busy <= 1'b0; sending <= 1'b0;
                        if (sg) run <= 1'b0; else sg <= 1'b1;
                    end
                end
            end
        end
    end
    assign mo_valid = busy && sending;
    assign mo_done = (so >= nsend);
    assign mo_g = sg;
    assign mo_k = so[5:2];
    assign mo_hh = so[1:0];
    assign mo_data = w[{so[1:0], so[5:2], 4'd0}];
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// P.V tree: the stack's residues r = 0, 1, 2, ... in order (residue group r div 8 is engine (r div 8) mod R's, slot
// r mod 8), through one LN-wide adder bank: the streaming pairwise tree (pending left node per level) = P.V levels 1-7.
// The bank issues at most one vector add a cycle; an arriving result that completes a pair always issues, a leaf waits
// (stays in its engine's loop) when it would collide.  Past the last nonempty residue every leaf is +0, so the flush
// carries each pending left node up unchanged (x + 0 = x) and adds it to the carry from below.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_pvtree #(
    parameter integer HD = 128,
    parameter integer S = 0,
    parameter integer R = 1,
    parameter integer ADD_LAT = 7
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [13:0]       T,
    input  wire [2:0]        cyc8,
    input  wire [R-1:0]      lf_valid,
    input  wire [R-1:0]      lf_g,
    input  wire [4*R-1:0]    lf_gam,
    input  wire [3*R-1:0]    lf_slot,
    input  wire [4*HD*32*R-1:0] lf_data,
    output wire [R-1:0]      take,
    output reg               pv_valid,
    output reg               pv_g,
    output reg  [5:0]        pv_beat,       // 16 values a beat
    output reg  [511:0]      pv_data,
    output reg  [1:0]        done,
    output reg               fault,
    output reg               ev_last_leaf
);
    localparam integer LN = 4 * HD;
    localparam integer NL = 7;                         // levels: 128 residues
    localparam integer NBEAT = LN / 16;
    wire [13:0] base_s = 14'd128 * S;
    wire        any_s = (T > base_s);
    wire [13:0] rem = T - base_s;
    wire [4:0]  gmax = !any_s ? 5'd0 : ((rem >= 14'd128) ? 5'd16 : ((rem + 14'd7) >> 3));
    wire [7:0]  nlv = {gmax, 3'b000};

    reg               run, tg, flushing, serial;
    reg [7:0]         rho;
    reg [$clog2(R+1)-1:0] ep;
    reg [LN*32-1:0]   P [0:NL-1];
    reg [NL-1:0]      Pv;
    reg [LN*32-1:0]   root, carry;
    reg               root_v, carry_v, fl_wait;
    reg [2:0]         fl;
    reg [5:0]         sb;
    reg [4:0]         inflight;
    // bank result tags: {valid, flush, level}
    wire [4:0]        tag_o;
    wire [LN*32-1:0]  y;
    wire [LN-1:0]     yvo;
    wire [LN-1:0]     yerr;
    wire              arr_v = tag_o[4] && !tag_o[3];
    wire              arr_fl = tag_o[4] && tag_o[3];
    wire [2:0]        arr_l = tag_o[2:0] + 3'd1;      // level of the arriving node
    wire              arr_issue = arr_v && (arr_l < NL) && Pv[arr_l];
    wire [LN*32-1:0]  leaf = lf_data[LN*32*ep +: LN*32];
    wire              offer = run && !flushing && !serial && (rho < nlv) && (lf_slot[3*ep +: 3] == rho[2:0]) && lf_valid[ep] &&
                              (lf_g[ep] == tg) && (lf_gam[4*ep +: 4] == rho[6:3]);
    wire              leaf_ok = offer && (!Pv[0] || !arr_issue);
    wire              leaf_issue = leaf_ok && Pv[0];
    wire              fl_issue = flushing && !fl_wait && (fl < NL) && Pv[fl] && carry_v;
    genvar gr;
    generate for (gr = 0; gr < R; gr = gr + 1) begin : g_take
        assign take[gr] = leaf_ok && (ep == gr);
    end endgenerate
    // bank
    wire              b_issue = arr_issue || leaf_issue || fl_issue;
    wire [LN*32-1:0]  b_a = arr_issue ? P[arr_l] : (leaf_issue ? P[0] : P[fl]);
    wire [LN*32-1:0]  b_b = arr_issue ? y : (leaf_issue ? leaf : carry);
    wire [2:0]        b_l = arr_issue ? arr_l : (leaf_issue ? 3'd0 : fl);
    ot_hdc_delay #(.W(5), .D(ADD_LAT), .RESET(1)) u_tag (.clk(clk), .rst_n(rst_n),
                                                         .d({b_issue, fl_issue && !arr_issue && !leaf_issue, b_l}),
                                                         .q(tag_o));
    genvar i;
    generate for (i = 0; i < LN; i = i + 1) begin : g_bank
        wire [1:0] err;
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
            .clk(clk), .rst_n(rst_n), .valid_in(b_issue), .a(b_a[32*i +: 32]), .b(b_b[32*i +: 32]),
            .y(y[32*i +: 32]), .err(err), .valid_out(yvo[i]));
        assign yerr[i] = yvo[i] && (err != 2'd0);
    end endgenerate

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            run <= 1'b0; tg <= 1'b0; flushing <= 1'b0; serial <= 1'b0; rho <= 0; ep <= 0; Pv <= 0; root_v <= 1'b0;
            carry_v <= 1'b0; fl_wait <= 1'b0; fl <= 0; sb <= 0; inflight <= 0; pv_valid <= 1'b0; done <= 2'b00;
            fault <= 1'b0; ev_last_leaf <= 1'b0;
        end else begin
            pv_valid <= 1'b0; ev_last_leaf <= 1'b0;
            if (|yerr) fault <= 1'b1;
            if (fl_issue && (arr_issue || leaf_issue)) fault <= 1'b1;    // cannot happen: flush only when idle
            inflight <= inflight + (b_issue ? 5'd1 : 5'd0) - (tag_o[4] ? 5'd1 : 5'd0);
            if (start) begin
                run <= 1'b1; tg <= 1'b0; flushing <= 1'b0; serial <= 1'b0; rho <= 0; ep <= 0; Pv <= 0; root_v <= 1'b0;
                carry_v <= 1'b0; fl_wait <= 1'b0; done <= 2'b00; fault <= 1'b0;
            end else if (run) begin
                // arriving results of the streaming tree
                if (arr_v) begin
                    if (arr_l == NL) begin root <= y; root_v <= 1'b1; end
                    else if (Pv[arr_l]) Pv[arr_l] <= 1'b0;
                    else begin P[arr_l] <= y; Pv[arr_l] <= 1'b1; end
                end
                // leaves
                if (leaf_ok) begin
                    if (Pv[0]) Pv[0] <= 1'b0;
                    else begin P[0] <= leaf; Pv[0] <= 1'b1; end
                    if (rho + 8'd1 == nlv && tg) ev_last_leaf <= 1'b1;   // the last leaf of the g = 1 pass
                    rho <= rho + 8'd1;
                    if (rho[2:0] == 3'd7) ep <= (ep == R - 1) ? 0 : ep + 1;
                end
                // end of pass: flush (fewer than 128 leaves), then serialise the root
                if (!flushing && !serial && rho == nlv && inflight == 0 && !b_issue && !tag_o[4]) begin
                    if (root_v) begin serial <= 1'b1; sb <= 0; end
                    else begin flushing <= 1'b1; fl <= 0; carry_v <= 1'b0; fl_wait <= 1'b0; end
                end
                if (flushing) begin
                    if (fl_wait) begin
                        if (arr_fl) begin carry <= y; fl_wait <= 1'b0; fl <= fl + 3'd1; end
                    end else if (fl == NL) begin
                        root <= carry_v ? carry : {LN*32{1'b0}};
                        root_v <= 1'b1; flushing <= 1'b0; serial <= 1'b1; sb <= 0;
                    end else if (Pv[fl]) begin
                        Pv[fl] <= 1'b0;
                        if (carry_v) fl_wait <= 1'b1;
                        else begin carry <= P[fl]; carry_v <= 1'b1; fl <= fl + 3'd1; end
                    end else fl <= fl + 3'd1;
                end
                if (serial) begin
                    pv_valid <= 1'b1; pv_g <= tg; pv_beat <= sb; pv_data <= root[512*sb +: 512];
                    if (sb == NBEAT - 1) begin
                        serial <= 1'b0; root_v <= 1'b0; done[tg] <= 1'b1;
                        if (tg) run <= 1'b0;
                        else begin tg <= 1'b1; rho <= 0; ep <= 0; end
                    end else sb <= sb + 6'd1;
                end
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The stack: R row engines, R exp quads, the score / e memories, the Z tree, the P.V tree, and the link ports.
//   in : q beats (512 b: 32 BF16, h-major, 32 beats), M messages (hub -> stack sideband)
//   out: P.V partial beats (512 b), sideband messages: lmax (type 0), Z block sum (type 1), Z done (type 2)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_attn_stack #(
    parameter integer HD = 128,
    parameter integer S = 0,
    parameter integer R = 1,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter integer DQ = 32,
    parameter integer ZW = 4,
    parameter [31:0]  SCALE = 32'h3DB504F3
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [13:0]       T,
    input  wire              q_valid,
    input  wire [5:0]        q_beat,
    input  wire [511:0]      q_data,
    output wire [R-1:0]      req_valid,
    output wire [R-1:0]      req_v,
    output wire [R-1:0]      req_g,
    output wire [13*R-1:0]   req_t,
    input  wire [R-1:0]      rsp_valid,
    input  wire [HD*8*R-1:0] rsp_data,
    input  wire              mi_valid,
    input  wire              mi_g,
    input  wire [1:0]        mi_hh,
    input  wire [31:0]       mi_data,
    output reg               so_valid,
    output reg  [1:0]        so_type,
    output reg               so_g,
    output reg  [1:0]        so_hh,
    output reg  [3:0]        so_k,
    output reg               so_any,
    output reg  [31:0]       so_data,
    output wire              pv_valid,
    output wire              pv_g,
    output wire [5:0]        pv_beat,
    output wire [511:0]      pv_data,
    output wire [1:0]        pv_done,
    output wire              fault,
    output wire [15:0]       ev                // cycle markers for the bench
);
    localparam integer LN = 4 * HD;
    localparam integer NQB = 8 * HD * 16 / 512;   // q beats
    reg [2:0] cyc8;
    always @(posedge clk or negedge rst_n) if (!rst_n) cyc8 <= 3'd0; else cyc8 <= cyc8 + 3'd1;

    wire [13:0] base_s = 14'd128 * S;
    wire [13:0] tail = {5'd0, T[8:0]};
    wire [13:0] part = (tail > base_s) ? ((tail - base_s > 14'd128) ? 14'd128 : (tail - base_s)) : 14'd0;
    wire [11:0] n_s = {T[13:9], 7'd0} + part[11:0];

    // q registers
    reg [8*HD*16-1:0] qr;
    reg [6:0] qcnt;
    wire q_ready = (qcnt == NQB);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) qcnt <= 0;
        else if (start) qcnt <= 0;
        else if (q_valid) qcnt <= qcnt + 7'd1;
    end
    always @(posedge clk) if (q_valid) qr[512*q_beat +: 512] <= q_data;

    // memories: scores {g, idx} x 4 FP32, e {g, idx} x 4 BF16
    reg [127:0] sc_mem [0:4095];
    reg [63:0]  e_mem  [0:4095];

    // M from the hub
    reg [255:0] M;
    reg [2:0]   mcnt0, mcnt1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin mcnt0 <= 0; mcnt1 <= 0; end
        else if (start) begin mcnt0 <= 0; mcnt1 <= 0; end
        else if (mi_valid) begin
            M[32*(4*mi_g + mi_hh) +: 32] <= mi_data;
            if (mi_g) mcnt1 <= mcnt1 + 3'd1; else mcnt0 <= mcnt0 + 3'd1;
        end
    end

    // engines
    wire [R-1:0] sc_valid, er_valid, lf_valid, lf_g, k_done, v_done, e_fault, ev_kf, ev_vf, take;
    wire [12*R-1:0] sc_addr, er_addr;
    wire [128*R-1:0] sc_data;
    reg  [64*R-1:0] er_data;
    wire [256*R-1:0] lmax;
    wire [2*R-1:0] lmax_any;
    wire [4*R-1:0] lf_gam;
    wire [3*R-1:0] lf_slot;
    wire [LN*32*R-1:0] lf_data;
    reg  [31:0] exp_done;
    genvar e;
    generate for (e = 0; e < R; e = e + 1) begin : g_e
        wire rv, rvv, rg;
        wire [12:0] rt;
        ot_qwen_nearhbm_row_engine #(.HD(HD), .S(S), .R(R), .E(e), .ADD_LAT(ADD_LAT),
                                     .MUL_LAT(MUL_LAT), .DQ(DQ), .SCALE(SCALE)) u_eng (
            .clk(clk), .rst_n(rst_n), .start(start), .T(T), .cyc8(cyc8), .q_ready(q_ready), .q_bf16(qr),
            .exp_done(exp_done), .req_valid(rv), .req_v(rvv), .req_g(rg), .req_t(rt), .rsp_valid(rsp_valid[e]),
            .rsp_data(rsp_data[HD*8*e +: HD*8]), .er_valid(er_valid[e]), .er_addr(er_addr[12*e +: 12]),
            .er_data(er_data[64*e +: 64]), .sc_valid(sc_valid[e]), .sc_addr(sc_addr[12*e +: 12]),
            .sc_data(sc_data[128*e +: 128]), .lmax(lmax[256*e +: 256]), .lmax_any(lmax_any[2*e +: 2]),
            .lf_valid(lf_valid[e]), .lf_g(lf_g[e]), .lf_gam(lf_gam[4*e +: 4]), .lf_slot(lf_slot[3*e +: 3]),
            .lf_data(lf_data[LN*32*e +: LN*32]),
            .lf_take(take[e]), .k_done(k_done[e]), .v_done(v_done[e]), .fault(e_fault[e]),
            .ev_k_first(ev_kf[e]), .ev_v_first(ev_vf[e]));
        assign req_valid[e] = rv; assign req_v[e] = rvv; assign req_g[e] = rg; assign req_t[13*e +: 13] = rt;
    end endgenerate

    // score writes, K-pass completion per g
    reg [11:0] scnt0, scnt1;
    integer r_;
    reg [11:0] add0, add1;
    always @* begin
        add0 = 0; add1 = 0;
        for (r_ = 0; r_ < R; r_ = r_ + 1) if (sc_valid[r_]) begin
            if (sc_addr[12*r_ + 11]) add1 = add1 + 1; else add0 = add0 + 1;
        end
    end
    always @(posedge clk) begin
        for (r_ = 0; r_ < R; r_ = r_ + 1) if (sc_valid[r_]) sc_mem[sc_addr[12*r_ +: 12]] <= sc_data[128*r_ +: 128];
        for (r_ = 0; r_ < R; r_ = r_ + 1) er_data[64*r_ +: 64] <= e_mem[er_addr[12*r_ +: 12]];
    end
    reg [1:0] kdone;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin scnt0 <= 0; scnt1 <= 0; kdone <= 2'b00; end
        else if (start) begin scnt0 <= 0; scnt1 <= 0; kdone <= 2'b00; end
        else begin
            scnt0 <= scnt0 + add0; scnt1 <= scnt1 + add1;
            if (scnt0 == n_s) kdone[0] <= 1'b1;
            if (scnt1 == n_s) kdone[1] <= 1'b1;
        end
    end
    // local max over the engines (order-free)
    reg [255:0] smax;
    reg [1:0]   sany;
    reg [31:0]  cand;
    reg         first;
    integer gg, hq, rr;
    always @* begin
        smax = 0; sany = 0;
        for (gg = 0; gg < 2; gg = gg + 1)
            for (hq = 0; hq < 4; hq = hq + 1) begin
                first = 1'b1;
                for (rr = 0; rr < R; rr = rr + 1)
                    if (lmax_any[2*rr + gg]) begin
                        cand = lmax[256*rr + 32*(4*gg + hq) +: 32];
                        if (first || fgt_f(cand, smax[32*(4*gg + hq) +: 32])) smax[32*(4*gg + hq) +: 32] = cand;
                        first = 1'b0;
                    end
            end
        for (gg = 0; gg < 2; gg = gg + 1)
            for (rr = 0; rr < R; rr = rr + 1) sany[gg] = sany[gg] | lmax_any[2*rr + gg];
    end
    function automatic fgt_f(input [31:0] a, input [31:0] b);
        fgt_f = (a[31] != b[31]) ? !a[31] : (!a[31] ? (a[30:0] > b[30:0]) : (a[30:0] < b[30:0]));
    endfunction

    // exp quads
    wire [1:0] qgo = {kdone[1] && (mcnt1 == 3'd4), kdone[0] && (mcnt0 == 3'd4)};
    wire [R-1:0] rd_valid, ew_valid, zw_valid, zw_g, gd_valid, gd_g, q_fault, ev_xf;
    wire [12*R-1:0] rd_addr, ew_addr;
    reg  [128*R-1:0] rd_data;
    wire [64*R-1:0] ew_data;
    wire [4*R-1:0] zw_k, zw_gam, gd_gam;
    wire [128*R-1:0] zw_data;
    wire [2*R-1:0] qdone;
    generate for (e = 0; e < R; e = e + 1) begin : g_q
        ot_qwen_nearhbm_exp_quad #(.S(S), .R(R), .Q(e), .ADD_LAT(ADD_LAT)) u_q (
            .clk(clk), .rst_n(rst_n), .start(start), .T(T), .go(qgo), .M(M), .rd_valid(rd_valid[e]),
            .rd_addr(rd_addr[12*e +: 12]), .rd_data(rd_data[128*e +: 128]), .ew_valid(ew_valid[e]),
            .ew_addr(ew_addr[12*e +: 12]), .ew_data(ew_data[64*e +: 64]), .zw_valid(zw_valid[e]), .zw_g(zw_g[e]),
            .zw_k(zw_k[4*e +: 4]), .zw_gam(zw_gam[4*e +: 4]), .zw_data(zw_data[128*e +: 128]),
            .gd_valid(gd_valid[e]), .gd_g(gd_g[e]), .gd_gam(gd_gam[4*e +: 4]), .qdone(qdone[2*e +: 2]),
            .fault(q_fault[e]), .ev_first(ev_xf[e]));
    end endgenerate
    always @(posedge clk) begin
        for (r_ = 0; r_ < R; r_ = r_ + 1) rd_data[128*r_ +: 128] <= sc_mem[rd_addr[12*r_ +: 12]];
        for (r_ = 0; r_ < R; r_ = r_ + 1) if (ew_valid[r_]) e_mem[ew_addr[12*r_ +: 12]] <= ew_data[64*r_ +: 64];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) exp_done <= 0;
        else if (start) exp_done <= 0;
        else for (r_ = 0; r_ < R; r_ = r_ + 1) if (gd_valid[r_]) exp_done[{gd_g[r_], gd_gam[4*r_ +: 4]}] <= 1'b1;
    end
    reg [1:0] xdone;
    always @* begin
        xdone = 2'b11;
        for (r_ = 0; r_ < R; r_ = r_ + 1) xdone = xdone & qdone[2*r_ +: 2];
    end

    // Z tree
    wire zm_valid, zm_done, zm_g, z_fault;
    wire [1:0] zm_hh;
    wire [3:0] zm_k;
    wire [31:0] zm_data;
    reg zm_ready;
    ot_qwen_nearhbm_ztree #(.S(S), .R(R), .ADD_LAT(ADD_LAT), .ZW(ZW)) u_zt (
        .clk(clk), .rst_n(rst_n), .start(start), .T(T), .zw_valid(zw_valid), .zw_g(zw_g), .zw_k(zw_k),
        .zw_gam(zw_gam), .zw_data(zw_data), .go(xdone), .mo_valid(zm_valid), .mo_done(zm_done), .mo_g(zm_g),
        .mo_hh(zm_hh), .mo_k(zm_k), .mo_data(zm_data), .mo_ready(zm_ready), .fault(z_fault));

    // P.V tree
    wire t_fault, ev_ll;
    ot_qwen_nearhbm_pvtree #(.HD(HD), .S(S), .R(R), .ADD_LAT(ADD_LAT)) u_pv (
        .clk(clk), .rst_n(rst_n), .start(start), .T(T), .cyc8(cyc8), .lf_valid(lf_valid), .lf_g(lf_g),
        .lf_gam(lf_gam), .lf_slot(lf_slot), .lf_data(lf_data), .take(take), .pv_valid(pv_valid), .pv_g(pv_g), .pv_beat(pv_beat),
        .pv_data(pv_data), .done(pv_done), .fault(t_fault), .ev_last_leaf(ev_ll));

    // sideband out: lmax first (critical), then the Z tree's messages
    reg [1:0] lsent;            // lmax of g sent
    reg [2:0] lh;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin so_valid <= 1'b0; lsent <= 2'b00; lh <= 0; end
        else begin
            so_valid <= 1'b0;
            if (start) begin lsent <= 2'b00; lh <= 0; end
            else if ((kdone[0] && !lsent[0]) || (kdone[1] && lsent[0] && !lsent[1])) begin
                so_valid <= 1'b1; so_type <= 2'd0; so_g <= lsent[0]; so_hh <= lh[1:0]; so_k <= 0;
                so_any <= sany[lsent[0]]; so_data <= smax[32*(4*lsent[0] + lh[1:0]) +: 32];
                if (lh == 3'd3) begin lh <= 0; lsent[lsent[0]] <= 1'b1; end else lh <= lh + 3'd1;
            end else if (zm_valid) begin
                so_valid <= 1'b1; so_type <= zm_done ? 2'd2 : 2'd1; so_g <= zm_g; so_hh <= zm_hh; so_k <= zm_k;
                so_any <= 1'b1; so_data <= zm_data;
            end
        end
    end
    always @* zm_ready = !((kdone[0] && !lsent[0]) || (kdone[1] && lsent[0] && !lsent[1]));

    assign fault = (|e_fault) || (|q_fault) || z_fault || t_fault;
    assign ev = {ev_ll, pv_valid && pv_beat == 0 && pv_g, |ev_xf, kdone[1], kdone[0], |ev_vf, |ev_kf, q_ready,
                 xdone[1], xdone[0], &k_done, &v_done, 4'd0};
endmodule
