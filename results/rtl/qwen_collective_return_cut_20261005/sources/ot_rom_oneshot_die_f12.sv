`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_rom_oneshot_die_f12: 1.2 GHz successor of the per-die one-shot collective engine ot_rom_oneshot_die
// (rtl/rom/ot_rom_oneshot_allreduce.sv, byte-identical and untouched).  Same ports, same records, same
// rank-order arithmetic, same credits (DEPTH words per source), same faults.  HBM-accel fmax closure 2026-10-04.
//
// THE LOOP IT REMOVES.  The original pops a word index when every source FIFO is non-empty, and the pop
// condition reads head_mode = mem[rp] (a DEPTH:1 mux of the FIFO head) in the same cycle: rp -> head mux ->
// head_mode -> pop -> rp/cnt/credit (screen -1,208 ps, 490 MHz at DEPTH 32).  Here every source keeps an
// OUTPUT QUEUE of OQD registered entries in front of its storage: the head, its mode bit and the non-empty
// flag are registers, so pop is an AND of registered flags.
//
//   FIFO_IMPL 0  the original combinational head (for lockstep reference only).
//   FIFO_IMPL 1  flop storage of DEPTH words; a read moves the oldest stored word into the output queue on
//                the edge it issues.
//   FIFO_IMPL 2  SRAM storage (DEPTH 1024): two banks (even / odd word index) of NM ot_sram_1r1w_512x256_m1
//                macros.  Reads leave in order, so consecutive reads alternate banks and a bank's rd_out
//                holds two cycles: the output-queue entry captures it two edges after the read (a two-cycle
//                path, ot_rom_oneshot_die_f12_mc2.sdc, the closed bulk-copy pattern).  OQD = 4 keeps one
//                pop a cycle while the storage holds a backlog (pop -> read -> capture -> head = 4 cycles).
//
// BYPASS.  A pushed word goes straight into the output queue when nothing older is in storage or in flight
// and the queue has room; it is a head the cycle after the push, exactly as in the original.  So a word's
// head cycle is unchanged whenever the queue is not backed up (the remote sources: words pop as they land);
// the local source, which runs ahead of the remotes by the link flight time, refills the queue from storage
// long before the remote words arrive.
//
// ADD_IMPL 0: ot_fp32_add_rne_pipe (LAT 5, ~1.09 GHz SS: fails 0.833 ns).  ADD_IMPL 1: ot_hdc_fp32_add_lat
// LAT 7 (keep-prefix adders, routed SS +40 ps at 0.833 ns), bit-identical arithmetic and error codes; the
// all-reduce latency grows by 2 cycles per rank stage ((N-1) * 2 per collective, fill only, II 1 kept).
// ---------------------------------------------------------------------------
module ot_rom_oneshot_die_f12 #(
    parameter integer N         = 4,
    parameter integer RANK      = 0,
    parameter integer LANES     = 16,
    parameter integer TAGW      = 32,
    parameter integer DEPTH     = 16,
    parameter integer FIFO_IMPL = 1,
    parameter integer ADD_IMPL  = 1,
    parameter integer OQD       = 4,               // output-queue entries (power of two)
    parameter integer ADD_LAT   = (ADD_IMPL != 0) ? 7 : 5,
    parameter integer FW        = 32 * LANES,
    parameter integer PW        = FW + 2 + TAGW,
    parameter integer RB        = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              in_valid,
    output wire              in_ready,
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
    localparam integer DL = (N - 1) * ADD_LAT;
    localparam integer QB = (OQD > 1) ? $clog2(OQD) : 1;
    localparam integer NM = (PW + 255) / 256;           // 256-bit macros per word (FIFO_IMPL 2)

    // -- credits and transmit (unchanged) --------------------------------------------------
    reg  [CB-1:0] cr [0:N-1];
    reg  [N-1:0]  can_tx;
    reg  [CB:0]   cnt [0:N-1];
    integer r;
    // FIFO_IMPL != 0: the credit / local-space conditions are registered flags loaded from the next state
    // (cr_ok[r] == (cr[r] != 0), cr_ok[RANK] == (cnt[RANK] < DEPTH) on every cycle), so in_ready -> fire ->
    // the local FIFO's write enables start at a flop.
    reg  [N-1:0]  cr_ok;
    always @(*) begin
        for (r = 0; r < N; r = r + 1)
            if (FIFO_IMPL != 0)
                can_tx[r] = (r == RANK) ? cr_ok[r] : (cr_ok[r] && tx_ready[r]);
            else
                can_tx[r] = (r == RANK) ? (cnt[r] < DEPTH) : (cr[r] != 0 && tx_ready[r]);
    end
    assign in_ready = &can_tx;
    wire fire = in_valid && in_ready;
    assign tx_valid = fire;
    assign tx_rec = {in_tag, in_mode, in_last, in_data};

    wire [N-1:0] push;
    wire [N*PW-1:0] push_rec;
    genvar g;
    generate
        for (g = 0; g < N; g = g + 1) begin : g_src
            if (g == RANK) begin : g_loc
                assign push[g] = fire;
                assign push_rec[g*PW +: PW] = tx_rec;
            end else begin : g_rem
                assign push[g] = rx_valid[g];
                assign push_rec[g*PW +: PW] = rx_rec[g*PW +: PW];
            end
        end
    endgenerate

    // -- heads -----------------------------------------------------------------------------
    wire [N-1:0]  nonempty;
    wire [PW-1:0] head [0:N-1];
    wire [N-1:0]  hmode;
    wire          pop;
    wire [N-1:0]  ne_nx;                  // next-cycle non-empty of every source (FIFO_IMPL != 0)
    wire          hm_nx;                  // next-cycle head mode of source 0 (FIFO_IMPL != 0)

    generate if (FIFO_IMPL == 0) begin : g_legacy
        reg [PW-1:0] mem [0:N*DEPTH-1];
        reg [DB-1:0] wp [0:N-1];
        reg [DB-1:0] rp [0:N-1];
        for (g = 0; g < N; g = g + 1) begin : g_h
            assign nonempty[g] = (cnt[g] != 0);
            assign head[g] = mem[g*DEPTH + rp[g]];
            assign hmode[g] = head[g][FW + 1];
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin wp[g] <= 0; rp[g] <= 0; end
                else begin
                    if (push[g]) begin mem[g*DEPTH + wp[g]] <= push_rec[g*PW +: PW]; wp[g] <= wp[g] + 1'b1; end
                    if (pop) rp[g] <= rp[g] + 1'b1;
                end
            end
        end
    end else begin : g_oq
        // Every wide select / enable below is a REGISTER, duplicated per 64-bit slice ((* keep *)), loaded from
        // the next state: no FSM decode or pointer fans out to hundreds of data flops in the same cycle.
        localparam integer NSL = (PW + 63) / 64;
        localparam integer PWS = NSL * 64;
        for (g = 0; g < N; g = g + 1) begin : g_h
            reg [PW-1:0] oq [0:OQD-1];
            reg [OQD-1:0] oqm;                  // mode bit of each entry (side copy)
            reg [QB-1:0] oq_rp, oq_ap;          // read pointer; allocation pointer (bypass / read issue order)
            reg [QB:0]   oq_n, res;             // filled entries; allocated entries (filled + reads in flight)
            reg          ne_r, rok;             // registered: oq_n != 0; res < OQD
            reg [DB-1:0] wp, rp_s;
            reg [CB-1:0] scnt;                  // words in storage not yet read
            reg          sne, sfree;            // registered: scnt != 0; scnt != DEPTH
            wire byp_ok;
            wire byp = push[g] && byp_ok;
            wire wst = push[g] && !byp;
            wire rdi = sne && rok;
            wire [CB-1:0] scnt_nx = scnt + (wst ? 1'b1 : 1'b0) - (rdi ? 1'b1 : 1'b0);
            wire          fill_v;
            wire [QB:0]   oq_n_nx = oq_n + (fill_v ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            wire [QB:0]   res_nx  = res + ((byp || rdi) ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
            wire [QB-1:0] oq_rp_n = oq_rp + (pop ? 1'b1 : 1'b0);
            wire [QB-1:0] oq_ap_n = oq_ap + ((byp || rdi) ? 1'b1 : 1'b0);
            wire [DB-1:0] wp_n = wp + (wst ? 1'b1 : 1'b0);
            wire [DB-1:0] rp_s_n = rp_s + (rdi ? 1'b1 : 1'b0);
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    oq_rp <= 0; oq_ap <= 0; oq_n <= 0; res <= 0; ne_r <= 1'b0; rok <= 1'b1;
                    wp <= 0; rp_s <= 0; scnt <= 0; sne <= 1'b0; sfree <= 1'b1;
                end else begin
                    oq_rp <= oq_rp_n; oq_ap <= oq_ap_n;
                    oq_n <= oq_n_nx; ne_r <= (oq_n_nx != 0);
                    res <= res_nx; rok <= (res_nx < OQD);
                    wp <= wp_n; rp_s <= rp_s_n;
                    scnt <= scnt_nx; sne <= (scnt_nx != 0); sfree <= (scnt_nx != DEPTH);
                end
            end
            assign nonempty[g] = ne_r;
            assign ne_nx[g] = (oq_n_nx != 0);
            assign hmode[g] = oqm[oq_rp];
            wire [PWS-1:0] pushp = {{(PWS-PW){1'b0}}, push_rec[g*PW +: PW]};
            wire [PWS-1:0] headp;
            assign head[g] = headp[PW-1:0];
            genvar s, k;
            wire [PWS-1:0] oqp [0:OQD-1];
            for (k = 0; k < OQD; k = k + 1) begin : g_oqp
                assign oqp[k] = {{(PWS-PW){1'b0}}, oq[k]};
            end
            // per-slice registered one-hot copies: free queue slot (write target), queue head
            (* keep *) reg [OQD-1:0] ap1h [0:NSL-1];
            (* keep *) reg [OQD-1:0] rp1h [0:NSL-1];
            for (s = 0; s < NSL; s = s + 1) begin : g_sl
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) begin ap1h[s] <= 1; rp1h[s] <= 1; end
                    else begin
                        ap1h[s] <= (res_nx < OQD) ? (1 << oq_ap_n) : 0;
                        rp1h[s] <= 1 << oq_rp_n;
                    end
                reg [63:0] hs;
                integer kk;
                always @(*) begin
                    hs = 64'd0;
                    for (kk = 0; kk < OQD; kk = kk + 1) hs = hs | ({64{rp1h[s][kk]}} & oqp[kk][64*s +: 64]);
                end
                assign headp[64*s +: 64] = hs;
            end
            if (FIFO_IMPL == 1) begin : g_flop
                reg [PW-1:0] mem [0:DEPTH-1];
                assign byp_ok = !sne && rok;
                assign fill_v = byp || rdi;
                (* keep *) reg [DEPTH-1:0] wp1h [0:NSL-1];   // free storage slot (write target)
                (* keep *) reg [DEPTH-1:0] rs1h [0:NSL-1];   // oldest stored word
                (* keep *) reg [NSL-1:0]   snes;             // copies of sne (queue fill source select)
                wire [PWS-1:0] memq;
                wire [PWS-1:0] memp [0:DEPTH-1];
                for (k = 0; k < DEPTH; k = k + 1) begin : g_mp
                    assign memp[k] = {{(PWS-PW){1'b0}}, mem[k]};
                end
                for (s = 0; s < NSL; s = s + 1) begin : g_ms
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) begin wp1h[s] <= 1; rs1h[s] <= 1; snes[s] <= 1'b0; end
                        else begin
                            wp1h[s] <= (scnt_nx != DEPTH) ? (1 << wp_n) : 0;
                            rs1h[s] <= 1 << rp_s_n;
                            snes[s] <= (scnt_nx != 0);
                        end
                    reg [63:0] ms;
                    integer ii;
                    always @(*) begin
                        ms = 64'd0;
                        for (ii = 0; ii < DEPTH; ii = ii + 1) ms = ms | ({64{rs1h[s][ii]}} & memp[ii][64*s +: 64]);
                    end
                    assign memq[64*s +: 64] = ms;
                    localparam integer SW_ = (64*s + 64 <= PW) ? 64 : PW - 64*s;
                    for (k = 0; k < DEPTH; k = k + 1) begin : g_mw
                        always @(posedge clk) if (wp1h[s][k]) mem[k][64*s +: SW_] <= pushp[64*s +: SW_];
                    end
                    for (k = 0; k < OQD; k = k + 1) begin : g_qw
                        always @(posedge clk) if (ap1h[s][k]) oq[k][64*s +: SW_] <= snes[s] ? memq[64*s +: SW_] : pushp[64*s +: SW_];
                    end
                end
                wire fill_mode = sne ? mem[rp_s][FW + 1] : push_rec[g*PW + FW + 1];
                always @(posedge clk) if (rok) oqm[oq_ap] <= fill_mode;
                if (g == 0) begin : g_hm
                    assign hm_nx = (rok && oq_ap == oq_rp_n) ? fill_mode : oqm[oq_rp_n];
                end
            end else begin : g_sram
                // read latency 2 (two-cycle macro path); nothing bypasses past a read in flight
                reg rd_v, rd_v2, par1, par2;
                reg [QB-1:0] sl1, sl2;
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) begin rd_v <= 1'b0; rd_v2 <= 1'b0; par1 <= 1'b0; par2 <= 1'b0; sl1 <= 0; sl2 <= 0; end
                    else begin
                        rd_v <= rdi; rd_v2 <= rd_v; par1 <= rp_s[0]; par2 <= par1; sl1 <= oq_ap; sl2 <= sl1;
                    end
                end
                assign byp_ok = !sne && !rd_v && !rd_v2 && rok;
                assign fill_v = byp || rd_v2;
                wire [NM*256-1:0] wpad = {{(NM*256-PW){1'b0}}, push_rec[g*PW +: PW]};
                wire [NM*256-1:0] rdo [0:1];
                genvar gb, mb;
                for (gb = 0; gb < 2; gb = gb + 1) begin : g_bank
                    for (mb = 0; mb < NM; mb = mb + 1) begin : g_m
                        ot_sram_1r1w_512x256_m1_r2c2 u_ring (
                            .clk(clk), .r_ce_in(rdi && rp_s[0] == gb), .r_addr_in(rp_s[DB-1:1]),
                            .rd_out(rdo[gb][256*mb +: 256]),
                            .w_ce_in(wst && wp[0] == gb), .w_addr_in(wp[DB-1:1]),
                            .wd_in(wpad[256*mb +: 256]), .w_mask_in({256{1'b1}}),
                            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
                    end
                end
                wire [NM*256-1:0] rsel = par2 ? rdo[1] : rdo[0];
                (* keep *) reg [OQD-1:0] cp1h [0:NSL-1];   // queue slot the macro read lands in (rd_v2 && sl2)
                (* keep *) reg [NSL-1:0]   p2s;              // copies of par2
                for (s = 0; s < NSL; s = s + 1) begin : g_ss
                    always @(posedge clk or negedge rst_n)
                        if (!rst_n) begin cp1h[s] <= 0; p2s[s] <= 1'b0; end
                        else begin cp1h[s] <= rd_v ? (1 << sl1) : 0; p2s[s] <= par1; end
                    localparam integer SW_ = (64*s + 64 <= PW) ? 64 : PW - 64*s;
                    wire [63:0] rs = p2s[s] ? rdo[1][64*s +: 64] : rdo[0][64*s +: 64];
                    for (k = 0; k < OQD; k = k + 1) begin : g_qw
                        always @(posedge clk)
                            if (cp1h[s][k]) oq[k][64*s +: SW_] <= rs[SW_-1:0];
                            else if (ap1h[s][k]) oq[k][64*s +: SW_] <= pushp[64*s +: SW_];
                    end
                end
                always @(posedge clk) begin : p_m
                    integer q;
                    for (q = 0; q < OQD; q = q + 1)
                        if (rd_v2 && sl2 == q) oqm[q] <= rsel[FW + 1];
                        else if (rok && oq_ap == q) oqm[q] <= push_rec[g*PW + FW + 1];
                end
                if (g == 0) begin : g_hm
                    assign hm_nx = (rd_v2 && sl2 == oq_rp_n) ? rsel[FW + 1] :
                                   (rok && oq_ap == oq_rp_n) ? push_rec[g*PW + FW + 1] : oqm[oq_rp_n];
                end
            end
        end
    end endgenerate
    wire head_mode = hmode[0];

    // -- pop: a word index leaves every FIFO at once ---------------------------------------
    reg          g_busy;
    reg  [RB-1:0] g_cnt;
    reg  [15:0]  inflight;
    reg          s0_v, s0_mode, s0_last;
    reg  [FW-1:0] s0_d [0:N-1];
    wire all_ne = &nonempty;
    wire red_out;
    wire pop_red, pop_gat;
    generate if (FIFO_IMPL == 0) begin : g_pop_comb
        assign pop_red = all_ne && !g_busy && !(s0_v && s0_mode) && !head_mode;
        assign pop_gat = all_ne && !g_busy && head_mode && inflight == 0 && !s0_v;
        assign pop = pop_red || pop_gat;
    end else begin : g_pop_reg
        // pop is a REGISTER: the original pop condition evaluated on the next state (non-empty, head mode,
        // gather busy, head-stage valid/mode, inflight == 0), so it equals the original pop on every cycle
        // and its fanout (every head capture, pointer, count and credit) starts at a flop.
        reg pop_r, iz, i1;                       // iz: inflight == 0, i1: inflight == 1
        wire [15:0] infl_nx = inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
        wire g_busy_n = (s0_v && s0_mode) ? (N != 1) : (g_busy ? (g_cnt != N - 1) : 1'b0);
        wire s0m_n = pop ? head_mode : s0_mode;
        wire iz_n = (iz && !pop_red && !red_out) || (i1 && !pop_red && red_out);
        wire pop_n = (&ne_nx) && !g_busy_n && (hm_nx ? (iz_n && !pop) : !(pop && s0m_n));
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin pop_r <= 1'b0; iz <= 1'b1; i1 <= 1'b0; end
            else begin pop_r <= pop_n; iz <= (infl_nx == 0); i1 <= (infl_nx == 1); end
        assign pop = pop_r;
        assign pop_red = pop && !head_mode;
        assign pop_gat = pop && head_mode;
    end endgenerate
    generate
        for (g = 0; g < N; g = g + 1) begin : g_cr
            if (g == RANK) begin : g_l
                assign cr_out[g] = 1'b0;
            end else begin : g_r
                assign cr_out[g] = pop;
            end
        end
    endgenerate

    reg  [CB-1:0] cr_nx [0:N-1];
    reg  [CB:0]   cnt_nx [0:N-1];
    always @(*) begin
        for (r = 0; r < N; r = r + 1) begin
            cr_nx[r] = cr[r] - (fire ? 1'b1 : 1'b0) + (cr_in[r] ? 1'b1 : 1'b0);
            cnt_nx[r] = cnt[r] + (push[r] ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (r = 0; r < N; r = r + 1) begin cr[r] <= DEPTH; cnt[r] <= 0; cr_ok[r] <= 1'b1; end
        end else begin
            for (r = 0; r < N; r = r + 1) begin
                if (r != RANK) begin cr[r] <= cr_nx[r]; cr_ok[r] <= (cr_nx[r] != 0); end
                else cr_ok[r] <= (cnt_nx[r] < DEPTH);
                cnt[r] <= cnt_nx[r];
            end
        end
    end

    // -- head stage --------------------------------------------------------------------------
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s0_v <= 1'b0; s0_mode <= 1'b0; s0_last <= 1'b0;
        end else begin
            s0_v <= pop;
            if (pop) begin s0_mode <= head_mode; s0_last <= head[0][FW]; end
        end
    end
    reg [TAGW:0] s0_t [0:N-1];
    always @(posedge clk) if (pop) for (r = 0; r < N; r = r + 1) begin
        s0_d[r] <= head[r][FW-1:0];
        s0_t[r] <= head[r][PW-1 -: TAGW + 1];
    end
    reg agree;
    always @(*) begin
        agree = 1'b1;
        for (r = 1; r < N; r = r + 1) if (s0_t[r] != s0_t[0]) agree = 1'b0;
    end

    // -- all-reduce ------------------------------------------------------------------------------
    wire red_in = s0_v && !s0_mode;
    wire [FW-1:0] sum  [0:N-1];
    wire [N-1:0]  sv;
    wire [N-1:0]  serr;
    assign sum[0] = s0_d[0];
    assign sv[0] = red_in;
    assign serr[0] = 1'b0;
    generate
        for (g = 1; g < N; g = g + 1) begin : g_stage
            wire [FW-1:0] pg;
            if (g == 1) begin : g_nd
                assign pg = s0_d[1];
            end else begin : g_d
                localparam integer D = (g - 1) * ADD_LAT;
                reg [FW*D-1:0] dl;
                always @(posedge clk) dl <= {dl[FW*(D-1)-1:0], s0_d[g]};
                assign pg = dl[FW*D-1 -: FW];
            end
            reg [ADD_LAT-1:0] edl;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) edl <= 0;
                else edl <= {edl[ADD_LAT-2:0], serr[g-1]};
            wire [LANES-1:0] lv;
            wire [2*LANES-1:0] le;
            genvar l;
            for (l = 0; l < LANES; l = l + 1) begin : g_lane
                if (ADD_IMPL != 0) begin : g_lat
                    ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
                        .clk(clk), .rst_n(rst_n), .valid_in(sv[g-1]),
                        .a(sum[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                        .y(sum[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
                end else begin : g_rne
                    ot_fp32_add_rne_pipe u_add (
                        .clk(clk), .rst_n(rst_n), .valid_in(sv[g-1]),
                        .a(sum[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                        .y(sum[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
                end
            end
            assign sv[g] = lv[0];
            assign serr[g] = (|le) || edl[ADD_LAT-1];
        end
    endgenerate
    reg [DL-1:0] ldl;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) ldl <= 0;
        else ldl <= {ldl[DL-2:0], s0_last};
    assign red_out = sv[N-1];

    // -- all-gather -----------------------------------------------------------------------------
    reg          go_v, go_last;
    reg [FW-1:0] go_d;
    reg [RB-1:0] go_rank;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            g_busy <= 1'b0; g_cnt <= 0; go_v <= 1'b0; go_last <= 1'b0; go_rank <= 0; inflight <= 0;
        end else begin
            go_v <= 1'b0;
            if (s0_v && s0_mode) begin g_busy <= 1'b1; g_cnt <= 0; end
            if (g_busy || (s0_v && s0_mode)) begin
                go_v <= 1'b1;
                go_d <= s0_d[g_busy ? g_cnt : 0];
                go_rank <= g_busy ? g_cnt : 0;
                go_last <= s0_last && (g_busy ? g_cnt : 0) == N - 1;
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

    assign out_valid = red_out || go_v;
    // the output select is a per-64-bit-slice copy of go_v (FIFO_IMPL != 0), so the result word's low lanes
    // (the argmax value the sequencer compares) do not wait for a 512-way select buffer tree
    (* keep *) reg [FW/64-1:0] go_vs;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) go_vs <= 0;
        else go_vs <= {(FW/64){g_busy || (s0_v && s0_mode)}};
    genvar os;
    generate for (os = 0; os < FW / 64; os = os + 1) begin : g_os
        assign out_data[64*os +: 64] = ((FIFO_IMPL != 0) ? go_vs[os] : go_v) ? go_d[64*os +: 64] : sum[N-1][64*os +: 64];
    end endgenerate
    assign out_last  = go_v ? go_last : ldl[DL-1];
    assign out_rank  = go_v ? go_rank : {RB{1'b0}};
    assign out_err   = red_out && serr[N-1];

    // -- faults ---------------------------------------------------------------------------
    reg ovf;
    always @(*) begin
        ovf = 1'b0;
        for (r = 0; r < N; r = r + 1) if (cnt[r] > DEPTH) ovf = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fault <= 1'b0; fault_code <= 3'b0;
        end else begin
            if (out_err) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
            if (s0_v && !agree) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (ovf) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// The package with successor dies (lockstep benches only; links are ot_rom_ucie_link of the original file).
// ---------------------------------------------------------------------------
module ot_rom_oneshot_allreduce_f12 #(
    parameter integer N          = 4,
    parameter integer LANES      = 16,
    parameter integer TAGW       = 32,
    parameter integer DEPTH      = 16,
    parameter integer LAT        = 11,
    parameter integer BPC_NUM    = 3600,
    parameter integer BPC_DEN    = 1,
    parameter integer FIFO_IMPL  = 1,
    parameter integer ADD_IMPL   = 1,
    parameter integer FW         = 32 * LANES,
    parameter integer RB         = (N > 1) ? $clog2(N) : 1
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [N-1:0]      in_valid,
    output wire [N-1:0]      in_ready,
    input  wire [N*FW-1:0]   in_data,
    input  wire [N-1:0]      in_last,
    input  wire [N-1:0]      in_mode,
    input  wire [N*TAGW-1:0] in_tag,
    output wire [N-1:0]      out_valid,
    output wire [N*FW-1:0]   out_data,
    output wire [N-1:0]      out_last,
    output wire [N*RB-1:0]   out_rank,
    output wire [N-1:0]      out_err,
    output wire [N-1:0]      fault,
    output wire [N*3-1:0]    fault_code,
    output reg  [31:0]       link_stalls
);
    localparam integer PW = FW + 2 + TAGW;
    wire [N-1:0]    txv;
    wire [N*PW-1:0] txr;
    wire [N*N-1:0]  txrdy;
    wire [N*N-1:0]  crin;
    wire [N*N-1:0]  rxv;
    wire [N*N*PW-1:0] rxr;
    wire [N*N-1:0]  crout;
    genvar s, t;
    generate
        for (s = 0; s < N; s = s + 1) begin : g_die
            ot_rom_oneshot_die_f12 #(.N(N), .RANK(s), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH),
                                     .FIFO_IMPL(FIFO_IMPL), .ADD_IMPL(ADD_IMPL)) u_die (
                .clk(clk), .rst_n(rst_n),
                .in_valid(in_valid[s]), .in_ready(in_ready[s]), .in_data(in_data[s*FW +: FW]),
                .in_last(in_last[s]), .in_mode(in_mode[s]), .in_tag(in_tag[s*TAGW +: TAGW]),
                .tx_valid(txv[s]), .tx_rec(txr[s*PW +: PW]), .tx_ready(txrdy[s*N +: N]), .cr_in(crin[s*N +: N]),
                .rx_valid(rxv[s*N +: N]), .rx_rec(rxr[s*N*PW +: N*PW]), .cr_out(crout[s*N +: N]),
                .out_valid(out_valid[s]), .out_data(out_data[s*FW +: FW]), .out_last(out_last[s]),
                .out_rank(out_rank[s*RB +: RB]), .out_err(out_err[s]),
                .fault(fault[s]), .fault_code(fault_code[s*3 +: 3]));
            for (t = 0; t < N; t = t + 1) begin : g_to
                if (t == s) begin : g_self
                    assign txrdy[s*N + t] = 1'b1;
                    assign crin[s*N + t] = 1'b0;
                    assign rxv[s*N + t] = 1'b0;
                    assign rxr[(s*N + t)*PW +: PW] = {PW{1'b0}};
                end else begin : g_link
                    ot_rom_ucie_link #(.PW(PW), .LAT(LAT), .FLIT_BYTES(FW / 8), .BPC_NUM(BPC_NUM),
                                       .BPC_DEN(BPC_DEN)) u_link (
                        .clk(clk), .rst_n(rst_n),
                        .in_valid(txv[s]), .in_rec(txr[s*PW +: PW]), .in_ready(txrdy[s*N + t]),
                        .out_valid(rxv[t*N + s]), .out_rec(rxr[(t*N + s)*PW +: PW]),
                        .cr_in(crout[t*N + s]), .cr_out(crin[s*N + t]));
                end
            end
        end
    endgenerate
    integer k;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) link_stalls <= 0;
        else for (k = 0; k < N; k = k + 1) if (in_valid[k] && !in_ready[k]) link_stalls <= link_stalls + 1;
    end
endmodule
