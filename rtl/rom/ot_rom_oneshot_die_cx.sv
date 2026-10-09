`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MARGIN form of ot_rom_oneshot_die (rtl/rom/ot_rom_oneshot_allreduce.sv), the Qwen ROM die's collective engine
// (r21 master qfd_io_collective), for the 2026-10-06/07 closure rules.  Same transactions, same rank-order binary32
// fold, same faults; latency is longer (transaction-level exactness, design simplification rule 1):
//   * every input is captured in a flop at its pin, every output leaves from a flop (register-to-register boundary);
//   * the local port is credit-based (rule 2: no same-cycle cross-block handshake): the sender holds IB credits and
//     in_cr returns one per word taken out of the IB-word input buffer;
//   * each source FIFO has a registered HEAD word (hd / hv): the pop decision reads only flops (hv, the head's mode
//     bit, g_busy, s0_v / s0_mode, inflight == 0), instead of the FIFO counts and the DEPTH:1 read mux;
//   * the adders are ot_hdc_fp32_add_lat at ADD_LAT 7 (the tile's 1.2 GHz-at-SS binary32 adder, same RNE results
//     and error encoding) instead of ot_fp32_add_rne_pipe at 5 (~1.09 GHz at SS);
//   * tx_ready / cr_in are taken from their pin registers (a cycle late): tx_ready is the link layer's registered
//     "may send" (the die link is credit-based end to end; a send against a deasserted tx_ready faults, code bit 2).
// Capacity per source: DEPTH FIFO words + the head register >= the DEPTH credits, so no FIFO can overflow; an
// overflow is still checked and faults.
// ---------------------------------------------------------------------------
module ot_rom_oneshot_die_cx #(
    parameter integer N       = 4,
    parameter integer RANK    = 0,
    parameter integer LANES   = 16,
    parameter integer TAGW    = 32,
    parameter integer DEPTH   = 16,
    parameter integer ADD_LAT = 7,
    parameter integer IB      = 4,
    parameter integer FW      = 32 * LANES,
    parameter integer PW      = FW + 2 + TAGW,
    parameter integer RB      = (N > 1) ? $clog2(N) : 1,
    // PR = 1 (qwen-blocks 2026-10-07; 0 = original): the pop decision is replicated per (source, 128-bit slice) from
    // kept copies of its state flops (each registered from the same next-state as the original), so the head refill
    // and s0 capture enables of a slice come from a local pop; the local word enters its FIFO one edge after it is
    // sent (registered {data}, the occupancy check counts it); tx_rec is captured without an enable.  Transactions,
    // fold order, values and faults unchanged; the local word reaches the head one cycle later.
    // PR = 2 (safe-qwen S-A3, 2026-10-08): the pop / refill decision reaches every (source, 128-bit slice) through a
    // 2-level REGISTERED fanout tree of keep_hierarchy leaves (synthesis cannot merge them: the PR = 1 copies were
    // merged back into hv[0] by Yosys, so PR = 1 routed with one hv fanning out to every head bit, TT -340.7):
    // level 1 = per-source copies of the decision state registered from its next state (as PR = 1), level 2 = the
    // slice's {pop, refill, read index} registered per (source, slice).  The slice head / s0 registers therefore act
    // one edge after the decision, and the s0 consumers (fold input, gather stage, tag check) are re-timed by one
    // edge (+1 cycle per collective word).  The head's mode / last bits stay at control timing (hb_c).  rst_n reaches
    // only per-region reset synchronisers (control, one per source, one per adder stage; 2-edge release).
    // Transactions, fold order, values and faults unchanged.
    parameter integer PR      = 2
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    output wire              in_cr,
    input  wire [FW-1:0]     in_data,
    input  wire              in_last,
    input  wire              in_mode,
    input  wire [TAGW-1:0]   in_tag,
    output wire              tx_valid,
    output wire [PW-1:0]     tx_rec,
    input  wire [N-1:0]      tx_ready,
    input  wire [N-1:0]      cr_in,
    input  wire [N-1:0]      rx_valid,
    input  wire [N*PW-1:0]   rx_rec,
    output wire [N-1:0]      cr_out,
    output wire              out_valid,
    output wire [FW-1:0]     out_data,
    output wire              out_last,
    output wire [RB-1:0]     out_rank,
    output wire              out_err,
    output reg               fault,
    output reg  [2:0]        fault_code
);
    localparam integer DB = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer CB = $clog2(DEPTH + 1);
    localparam integer IA = (IB <= 2) ? 1 : $clog2(IB);
    localparam integer DL = (N - 1) * ADD_LAT;
    integer r;
    // ---- PR = 2: per-region reset synchronisers (rst_n reaches only these) ------------------------------------------
    wire          rst_i;                 // control region
    wire [N-1:0]  rst_k;                 // per source: its slice leaves
    wire [N-1:0]  rst_a;                 // per adder stage (index 1..N-1)
    genvar g;
    generate if (PR >= 2) begin : g_rsr
        (* keep_hierarchy *) ot_coll_cx_rst_leaf u_rc (.clk(clk), .arst_n(rst_n), .q(rst_i));
        for (g = 0; g < N; g = g + 1) begin : g_rr
            (* keep_hierarchy *) ot_coll_cx_rst_leaf u_rk (.clk(clk), .arst_n(rst_n), .q(rst_k[g]));
            (* keep_hierarchy *) ot_coll_cx_rst_leaf u_ra (.clk(clk), .arst_n(rst_n), .q(rst_a[g]));
        end
    end else begin : g_rsd
        assign rst_i = rst_n; assign rst_k = {N{rst_n}}; assign rst_a = {N{rst_n}};
    end endgenerate
    // ---- pin registers -------------------------------------------------------------------------------------------
    reg              iv_q;
    reg [PW-1:0]     irec_q;
    reg [N-1:0]      txr_q, cri_q, rxv_q;
    reg [N*PW-1:0]   rxr_q;
    always @(posedge clk) begin irec_q <= {in_tag, in_mode, in_last, in_data}; rxr_q <= rx_rec; end
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin iv_q <= 1'b0; txr_q <= 0; cri_q <= 0; rxv_q <= 0; end
        else begin iv_q <= in_valid; txr_q <= tx_ready; cri_q <= cr_in; rxv_q <= rx_valid; end
    // ---- local input buffer (IB words, credit per word taken) ----------------------------------------------------
    reg [PW-1:0] ib [0:IB-1];
    reg [IA:0]   iw, ir;
    wire ib_empty = (iw == ir);
    wire ib_full  = (iw[IA-1:0] == ir[IA-1:0]) && (iw[IA] != ir[IA]);
    wire [PW-1:0] ib_head = ib[ir[IA-1:0]];
    always @(posedge clk) if (iv_q && !ib_full) ib[iw[IA-1:0]] <= irec_q;
    // ---- credits and transmit -------------------------------------------------------------------------------------
    reg  [CB-1:0] cr [0:N-1];
    reg  [CB:0]   mcnt [0:N-1];          // words in the source FIFO (head register excluded)
    reg  [N-1:0]  hv;                    // head register valid
    reg  [N-1:0]  can_tx;
    reg           lpv;                   // PR: the local word sent last edge, entering its FIFO now
    reg  [PW-1:0] lpq;
    always @(*) for (r = 0; r < N; r = r + 1)
        can_tx[r] = (r == RANK) ? ((mcnt[r] + hv[r] + ((PR != 0) ? lpv : 1'b0)) < DEPTH) : (cr[r] != 0 && txr_q[r]);
    wire fire = !ib_empty && (&can_tx);
    reg          txv_q, icr_q;
    reg [PW-1:0] txrec_q;
    generate if (PR != 0) begin : g_txr
        always @(posedge clk) begin txrec_q <= ib_head; lpq <= ib_head; end   // tx_rec meaningful only with tx_valid
        always @(posedge clk or negedge rst_i) if (!rst_i) lpv <= 1'b0; else lpv <= fire;
    end else begin : g_txo
        always @(posedge clk) if (fire) txrec_q <= ib_head;
        always @(*) begin lpv = 1'b0; lpq = {PW{1'b0}}; end
    end endgenerate
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin txv_q <= 1'b0; icr_q <= 1'b0; iw <= 0; ir <= 0; end
        else begin
            txv_q <= fire; icr_q <= fire;
            if (iv_q && !ib_full) iw <= iw + 1'b1;
            if (fire) ir <= ir + 1'b1;
        end
    assign tx_valid = txv_q;
    assign tx_rec = txrec_q;
    assign in_cr = icr_q;
    // ---- receive FIFOs with registered heads ----------------------------------------------------------------------
    reg [PW-1:0] mem [0:N*DEPTH-1];
    reg [DB-1:0] wp [0:N-1];
    reg [DB-1:0] rp [0:N-1];
    reg [PW-1:0] hd [0:N-1];
    wire [N-1:0] push;
    wire [N*PW-1:0] push_rec;
    generate for (g = 0; g < N; g = g + 1) begin : g_src
        if (g == RANK) begin : g_loc
            assign push[g] = (PR != 0) ? lpv : fire;
            assign push_rec[g*PW +: PW] = (PR != 0) ? lpq : ib_head;
        end else begin : g_rem
            assign push[g] = rxv_q[g];
            assign push_rec[g*PW +: PW] = rxr_q[g*PW +: PW];
        end
    end endgenerate
    // ---- pop: a word index leaves every head at once ----------------------------------------------------------------
    reg          g_busy;
    reg  [RB-1:0] g_cnt;
    reg  [15:0]  inflight;
    reg          s0_v, s0_mode, s0_last;
    reg  [FW-1:0] s0_d [0:N-1];
    wire [N*PW-1:0] hdf;                 // the head words (PR: assembled from the slice registers)
    reg  [1:0] hb_c;                     // PR = 2: source 0's head {mode, last} at control timing
    wire hmode = (PR >= 2) ? hb_c[1] : hdf[FW + 1];
    wire hlast = (PR >= 2) ? hb_c[0] : hdf[FW];
    wire all_hv = &hv;
    wire pop_red = all_hv && !g_busy && !(s0_v && s0_mode) && !hmode;
    wire pop_gat = all_hv && !g_busy && hmode && inflight == 16'd0 && !s0_v;
    wire pop = pop_red || pop_gat;
    reg [N-1:0] refill;
    always @(*) for (r = 0; r < N; r = r + 1) refill[r] = (mcnt[r] != 0) && (!hv[r] || pop);
    reg cro_q;
    always @(posedge clk or negedge rst_i) if (!rst_i) cro_q <= 1'b0; else cro_q <= pop;
    generate for (g = 0; g < N; g = g + 1) begin : g_cr
        assign cr_out[g] = (g == RANK) ? 1'b0 : cro_q;
    end endgenerate
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin
            for (r = 0; r < N; r = r + 1) begin cr[r] <= DEPTH; mcnt[r] <= 0; wp[r] <= 0; rp[r] <= 0; end
            hv <= 0;
        end else begin
            for (r = 0; r < N; r = r + 1) begin
                if (r != RANK) cr[r] <= cr[r] - (fire ? 1'b1 : 1'b0) + (cri_q[r] ? 1'b1 : 1'b0);
                if (push[r]) begin
                    mem[r*DEPTH + wp[r]] <= push_rec[r*PW +: PW];
                    wp[r] <= wp[r] + 1'b1;
                end
                if (refill[r]) begin
                    if (PR == 0) hd[r] <= mem[r*DEPTH + rp[r]];
                    rp[r] <= rp[r] + 1'b1;
                end
                hv[r] <= refill[r] ? 1'b1 : (pop ? 1'b0 : hv[r]);
                mcnt[r] <= mcnt[r] + (push[r] ? 1'b1 : 1'b0) - (refill[r] ? 1'b1 : 1'b0);
            end
        end
    end
    // ---- head stage ----------------------------------------------------------------------------------------------------
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin s0_v <= 1'b0; s0_mode <= 1'b0; s0_last <= 1'b0; end
        else begin
            s0_v <= pop;
            if (pop) begin s0_mode <= hmode; s0_last <= hlast; end
        end
    end
    always @(posedge clk) if (refill[0]) hb_c <= mem[rp[0]][FW +: 2];
    // PR = 2: the s0 registers are written one edge after the pop; s0_vl / s0_ml / s0_ll re-time their consumers
    reg s0_vl, s0_ml, s0_ll;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin s0_vl <= 1'b0; s0_ml <= 1'b0; s0_ll <= 1'b0; end
        else begin s0_vl <= s0_v; s0_ml <= s0_mode; s0_ll <= s0_last; end
    wire s0_vc = (PR >= 2) ? s0_vl : s0_v;           // consumer-timed s0 valid / mode / last
    wire s0_mc = (PR >= 2) ? s0_ml : s0_mode;
    wire s0_lc = (PR >= 2) ? s0_ll : s0_last;
    reg [TAGW:0] s0_t [0:N-1];
    generate if (PR == 0) begin : g_s0o
        for (g = 0; g < N; g = g + 1) begin : g_hdf
            assign hdf[g*PW +: PW] = hd[g];
        end
        always @(posedge clk) if (pop) for (r = 0; r < N; r = r + 1) begin
            s0_d[r] <= hd[r][FW-1:0];
            s0_t[r] <= hd[r][PW-1 -: TAGW + 1];
        end
    end endgenerate
    reg agree;
    always @(*) begin
        agree = 1'b1;
        for (r = 1; r < N; r = r + 1) if (s0_t[r] != s0_t[0]) agree = 1'b0;
    end
    // ---- all-reduce: ((p0 + p1) + p2) + ... in rank order ----------------------------------------------------------
    wire red_in = s0_vc && !s0_mc;
    wire [FW-1:0] sum  [0:N-1];
    wire [N-1:0]  sv;
    wire [N-1:0]  serr;
    // OT_ONESHOT_M_MUTANT (negative control only): ranks 1 and 2 swap places in the fold, ((p0 + p2) + p1) + p3
    wire [FW-1:0] fsrc [0:N-1];
    generate for (g = 0; g < N; g = g + 1) begin : g_fsrc
`ifdef OT_ONESHOT_M_MUTANT
        assign fsrc[g] = (g == 1 && N > 2) ? s0_d[2] : (g == 2) ? s0_d[1] : s0_d[g];
`else
        assign fsrc[g] = s0_d[g];
`endif
    end endgenerate
    assign sum[0] = fsrc[0];
    assign sv[0] = red_in;
    assign serr[0] = 1'b0;
    generate
        for (g = 1; g < N; g = g + 1) begin : g_stage
            wire [FW-1:0] pg;
            if (g == 1) begin : g_nd
                assign pg = fsrc[1];
            end else begin : g_d
                localparam integer D = (g - 1) * ADD_LAT;
                reg [FW*D-1:0] dl;
                always @(posedge clk) dl <= {dl[FW*(D-1)-1:0], fsrc[g]};
                assign pg = dl[FW*D-1 -: FW];
            end
            reg [ADD_LAT-1:0] edl;
            always @(posedge clk or negedge rst_a[g])
                if (!rst_a[g]) edl <= 0;
                else edl <= {edl[ADD_LAT-2:0], serr[g-1]};
            wire [LANES-1:0] lv;
            wire [2*LANES-1:0] le;
            genvar l;
            for (l = 0; l < LANES; l = l + 1) begin : g_lane
                ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
                    .clk(clk), .rst_n(rst_a[g]), .valid_in(sv[g-1]),
                    .a(sum[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                    .y(sum[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
            end
            assign sv[g] = lv[0];
            assign serr[g] = (|le) || edl[ADD_LAT-1];
        end
    endgenerate
    reg [DL-1:0] ldl;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) ldl <= 0;
        else ldl <= {ldl[DL-2:0], s0_lc};
    wire red_out = sv[N-1];
    // ---- all-gather --------------------------------------------------------------------------------------------------
    reg          go_v, go_last;
    reg [FW-1:0] go_d;
    reg [RB-1:0] go_rank;
    reg          gc_v, gc_last;          // control-timed gather selection (PR = 2 reads s0_d one edge later)
    reg [RB-1:0] gc_idx;
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin
            g_busy <= 1'b0; g_cnt <= 0; gc_v <= 1'b0; gc_last <= 1'b0; gc_idx <= 0; inflight <= 0;
        end else begin
            gc_v <= 1'b0;
            if (s0_v && s0_mode) begin g_busy <= 1'b1; g_cnt <= 0; end
            if (g_busy || (s0_v && s0_mode)) begin
                gc_v <= 1'b1;
                gc_idx <= g_busy ? g_cnt : 0;
                gc_last <= s0_last && (g_busy ? g_cnt : 0) == N - 1;
                if (g_busy) begin
                    g_cnt <= g_cnt + 1'b1;
                    if (g_cnt == N - 1) g_busy <= 1'b0;
                end else begin
                    g_cnt <= 1;
                    if (N == 1) g_busy <= 1'b0;
                end
            end
            inflight <= inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
        end
    end
    generate if (PR >= 2) begin : g_go2
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin go_v <= 1'b0; go_last <= 1'b0; go_rank <= 0; end
            else begin go_v <= gc_v; go_last <= gc_last; go_rank <= gc_idx; end
        always @(posedge clk) go_d <= s0_d[gc_idx];
    end else begin : g_go1
        // original timing: the selection and the data in the same edge
        reg [RB-1:0] gi;
        always @(*) gi = g_busy ? g_cnt : 0;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin go_v <= 1'b0; go_last <= 1'b0; go_rank <= 0; end
            else begin
                go_v <= 1'b0;
                if (g_busy || (s0_v && s0_mode)) begin
                    go_v <= 1'b1; go_d <= s0_d[gi]; go_rank <= gi; go_last <= s0_last && gi == N - 1;
                end
            end
    end endgenerate
    // ---- registered outputs --------------------------------------------------------------------------------------------
    reg          ov_q, ol_q, oe_q;
    reg [FW-1:0] od_q;
    reg [RB-1:0] ork_q;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin ov_q <= 1'b0; oe_q <= 1'b0; end
        else begin ov_q <= red_out || go_v; oe_q <= red_out && serr[N-1]; end
    always @(posedge clk) begin
        od_q <= go_v ? go_d : sum[N-1];
        ol_q <= go_v ? go_last : ldl[DL-1];
        ork_q <= go_v ? go_rank : {RB{1'b0}};
    end
    assign out_valid = ov_q; assign out_data = od_q; assign out_last = ol_q; assign out_rank = ork_q; assign out_err = oe_q;
    // ---- faults ------------------------------------------------------------------------------------------------------
    reg ovf;
    always @(*) begin
        ovf = iv_q && ib_full;                                   // the sender ignored its credits
        for (r = 0; r < N; r = r + 1) if (mcnt[r] > DEPTH) ovf = 1'b1;
    end
    localparam [N-1:0] SELF = {{(N-1){1'b0}}, 1'b1} << RANK;
    reg txv_d, txbad;     // a send while a link said no (link-layer violation), judged from the pin registers
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin txv_d <= 1'b0; txbad <= 1'b0; end
        else begin txv_d <= txv_q; txbad <= txv_d && !(&(txr_q | SELF)); end
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin fault <= 1'b0; fault_code <= 3'b0; end
        else begin
            if (red_out && serr[N-1]) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
            if (s0_vc && !agree) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (ovf || txbad) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
        end
    end
    // ---- PR: replicated pop -------------------------------------------------------------------------------------------
    generate if (PR == 1) begin : g_s0r
        reg  [N-1:0] hv_n, mnz_n;
        reg          gb_n, hm_n, iz_n;
        reg  [DB-1:0] rp_n [0:N-1];
        reg  [15:0]  inflight_n;
        always @(*) begin
            for (r = 0; r < N; r = r + 1) begin
                hv_n[r] = refill[r] ? 1'b1 : (pop ? 1'b0 : hv[r]);
                mnz_n[r] = (mcnt[r] + (push[r] ? 1'b1 : 1'b0) - (refill[r] ? 1'b1 : 1'b0)) != 0;
                rp_n[r] = rp[r] + (refill[r] ? 1'b1 : 1'b0);
            end
            gb_n = g_busy ? (g_cnt != N - 1) : ((s0_v && s0_mode) ? (N != 1) : 1'b0);
            hm_n = refill[0] ? mem[rp[0]][FW + 1] : hdf[FW + 1];
            inflight_n = inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
            iz_n = (inflight_n == 16'd0);
        end
        localparam integer SLW = 32, NSL = (PW + SLW - 1) / SLW;
        wire [N*PW-1:0] s0f;
        genvar gr, gk;
        for (gr = 0; gr < N; gr = gr + 1) begin : g_r
            for (gk = 0; gk < NSL; gk = gk + 1) begin : g_k
                localparam integer LO = gk * SLW;
                localparam integer SW = (PW - LO < SLW) ? (PW - LO) : SLW;
                (* keep *) reg [N-1:0] hvc;
                (* keep *) reg gbc, s0vc, s0mc, hmc, izc, mnzc;
                (* keep *) reg [DB-1:0] rpc;
                reg [SW-1:0] hdk, s0k;
                always @(posedge clk or negedge rst_i)
                    if (!rst_i) begin hvc <= 0; gbc <= 1'b0; s0vc <= 1'b0; s0mc <= 1'b0; hmc <= 1'b0; izc <= 1'b1;
                                      mnzc <= 1'b0; rpc <= 0; end
                    else begin hvc <= hv_n; gbc <= gb_n; s0vc <= pop; s0mc <= pop ? hmode : s0_mode; hmc <= hm_n;
                               izc <= iz_n; mnzc <= mnz_n[gr]; rpc <= rp_n[gr]; end
                wire popk = (&hvc) && !gbc && ((!(s0vc && s0mc) && !hmc) || (hmc && izc && !s0vc));
                wire refk = mnzc && (!hvc[gr] || popk);
                wire [PW-1:0] mrow = mem[gr*DEPTH + rpc];
                always @(posedge clk) begin
                    if (refk) hdk <= mrow[LO +: SW];
                    if (popk) s0k <= hdk;
                end
                assign hdf[gr*PW + LO +: SW] = hdk;
                assign s0f[gr*PW + LO +: SW] = s0k;
            end
        end
        always @(*) for (r = 0; r < N; r = r + 1) begin
            s0_d[r] = s0f[r*PW +: FW];
            s0_t[r] = s0f[r*PW + PW - 1 -: TAGW + 1];
        end
    end else if (PR >= 2) begin : g_s0r2
        // ---- PR = 2: 2-level registered fanout tree (keep_hierarchy leaves) ------------------------------------------
        initial if (N > 4 || DB > 6) $error("ot_rom_oneshot_die_cx PR=2: N <= 4 and DEPTH <= 64 (fixed-width leaves)");
        reg  [N-1:0] hv_n, mnz_n;
        reg          gb_n, hm_n, iz_n;
        reg  [DB-1:0] rp_n [0:N-1];
        reg  [15:0]  inflight_n;
        always @(*) begin
            for (r = 0; r < N; r = r + 1) begin
                hv_n[r] = refill[r] ? 1'b1 : (pop ? 1'b0 : hv[r]);
                mnz_n[r] = (mcnt[r] + (push[r] ? 1'b1 : 1'b0) - (refill[r] ? 1'b1 : 1'b0)) != 0;
                rp_n[r] = rp[r] + (refill[r] ? 1'b1 : 1'b0);
            end
            gb_n = g_busy ? (g_cnt != N - 1) : ((s0_v && s0_mode) ? (N != 1) : 1'b0);
            hm_n = refill[0] ? mem[rp[0]][FW + 1] : hb_c[1];
            inflight_n = inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
            iz_n = (inflight_n == 16'd0);
        end
        localparam integer SLW = 32, NSL = (PW + SLW - 1) / SLW;
        wire [N*PW-1:0] s0f;
        genvar gr, gk;
        for (gr = 0; gr < N; gr = gr + 1) begin : g_r
            // level 1 (per source): the decision state, registered from its next state (same timing as hv)
            wire [15:0] l1d, l1q;
            wire [3:0]  hv4 = hv_n;
            wire [5:0]  rp6 = rp_n[gr];
            assign l1d = {hv4, gb_n, pop, (pop ? hmode : s0_mode), hm_n, !iz_n, mnz_n[gr], rp6};
            (* keep_hierarchy *) ot_coll_cx_dup16 u_l1 (.clk(clk), .arst_n(rst_k[gr]), .d(l1d), .q(l1q));
            wire [N-1:0] hvc = l1q[12 +: N];
            wire gbc = l1q[11], s0vc = l1q[10], s0mc = l1q[9], hmc = l1q[8], izc = !l1q[7], mnzc = l1q[6];
            wire [DB-1:0] rpc = l1q[DB-1:0];
            wire popk = (&hvc) && !gbc && ((!(s0vc && s0mc) && !hmc) || (hmc && izc && !s0vc));
            wire refk = mnzc && (!hvc[gr] || popk);
            wire [7:0] l2d = {popk, refk, l1q[5:0]};
            for (gk = 0; gk < NSL; gk = gk + 1) begin : g_k
                localparam integer LO = gk * SLW;
                localparam integer SW = (PW - LO < SLW) ? (PW - LO) : SLW;
                // The data and its capture controls share a kept32-bit leaf.
                // This is placement partitioning, not reliability duplication.
                wire [31:0] mr = {{(32-SW){1'b0}}, mem[gr*DEPTH + l2d[DB-1:0]][LO +: SW]};
                wire [31:0] hdk, s0k;
                (* keep_hierarchy *) ot_coll_cx_slice32 u_slice (
                    .clk(clk),.arst_n(rst_k[gr]),.ctl(l2d),
                    .row(mr),.head(hdk),.stage(s0k));
                assign hdf[gr*PW + LO +: SW] = hdk[SW-1:0];
                assign s0f[gr*PW + LO +: SW] = s0k[SW-1:0];
            end
        end
        always @(*) for (r = 0; r < N; r = r + 1) begin
            s0_d[r] = s0f[r*PW +: FW];
            s0_t[r] = s0f[r*PW + PW - 1 -: TAGW + 1];
        end
    end endgenerate
endmodule

// PR = 2 leaves: fixed widths and no parameters (Yosys 0.68 asserts re-elaborating a parameterised keep_hierarchy
// module), instantiated with keep_hierarchy so synthesis keeps every copy.
module ot_coll_cx_rst_leaf (input wire clk, input wire arst_n, output wire q);
    (* async_reg = "true" *) reg [1:0] s;
    always @(posedge clk or negedge arst_n) if (!arst_n) s <= 2'b00; else s <= {s[0], 1'b1};
    assign q = s[1];
endmodule
module ot_coll_cx_dup16 (input wire clk, input wire arst_n, input wire [15:0] d, output reg [15:0] q);
    always @(posedge clk or negedge arst_n) if (!arst_n) q <= 16'd0; else q <= d;
endmodule
module ot_coll_cx_dup8 (input wire clk, input wire arst_n, input wire [7:0] d, output reg [7:0] q);
    always @(posedge clk or negedge arst_n) if (!arst_n) q <= 8'd0; else q <= d;
endmodule

(* keep_hierarchy *)
module ot_coll_cx_slice32(input wire clk, arst_n,
    input wire [7:0] ctl,input wire [31:0] row,
    output reg [31:0] head,stage);
    reg [7:0] ctl_q;
    reg [31:0] row_q;
    always @(posedge clk) row_q <= row;
    always @(posedge clk or negedge arst_n)
        if(!arst_n) ctl_q<=0; else ctl_q<=ctl;
    always @(posedge clk) begin
        if(ctl_q[6]) head<=row_q;
        if(ctl_q[7]) stage<=head;
    end
endmodule
