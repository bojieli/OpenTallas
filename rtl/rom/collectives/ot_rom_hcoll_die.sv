`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_rom_hcoll_die: the per-die collective engine of a TP group that spans
// NPKG packages of PD dies (PD = 2: the DS-ROM C5hc TP-8 stage group, 4
// packages x 2 dies; PD = 1: the C1 / PAR2 TP-4 owner dies, one per package).
// Gate record: results/rtl/dsrom_c5hc_collective_gate_20261003.
//
// Physical links (one per port, modelled by ot_w15_link_tx / _rx in the bench):
//   board port j (j = 0..NPKG-2): to the COUNTERPART die (same in-package index
//          L) of remote package rp(j) = j + (j >= MYPKG); the package's board
//          lanes are split into PD counterpart planes.
//   UCIe   (PD = 2 only): to the package partner, NPKG virtual channels:
//          VC0 the die's own records, VC 1+j the records it relays from board
//          port j.
//
// ALL-GATHER (mode 1, bit-transparent, rank order).  A local word goes to the
//   die's own FIFO, to the partner (VC0) and to the 3 counterparts.  A board
//   record from package q is pushed into this die's FIFO for its source rank
//   and, the cycle it lands, relayed over UCIe (VC 1+j) to the partner.  So
//   every FIFO (one per source rank) has exactly one writer.  When all N heads
//   hold a word the index is popped and emitted GW words per beat, rank order.
// ALL-REDUCE (mode 0, the golden's fixed pairwise tree, bit-identical on every
//   die): rank r = PD * package + L holds the r-th aligned subtree of the
//   golden tree (tools/hdc_golden_v41.csum, chunk8: wo_b's 32 chunks, 4 per
//   die), so the remaining levels are
//        y = ((s0 + s1) + (s2 + s3)),   s_p = r_{2p} + r_{2p+1}   (PD = 2)
//   Level 1 (PD = 2): the partners exchange partials over UCIe and both form
//   s_p = add(r_even, r_odd) (same operands, same order, same bits).  Level 2:
//   each die sends s_p to its 3 counterparts, which hold s_p for every other
//   package, and every die forms the tree itself.  No result is broadcast; no
//   reduction order depends on arrival.  PD = 1: s_p is the die's own partial.
//
// Flow control.  A sender transmits only while it holds a credit for the
//   receiving FIFO (board port j: one counter for the counterpart's FIFO; VC0:
//   the partner's FIFO).  A relayed copy uses the original board credit: the
//   relaying die returns that credit only after BOTH its own copy and the
//   partner's relayed copy have been popped (the partner returns a VC 1+j
//   credit to the relayer), so neither FIFO can overflow.  Level-1 sums wait in
//   a skid buffer for board credits; the result FIFO is reserved at pop time.
// FAIL CLOSED: adders raise err on NaN / Inf operands and finite overflow
//   (out_err, fault code bit 0); popped heads that disagree on {tag, mode}
//   fault (bit 1); a push into a full FIFO faults (bit 2).
// ---------------------------------------------------------------------------
module ot_rom_hcoll_die #(
    parameter integer NPKG    = 4,
    parameter integer PD      = 2,
    parameter integer RANK    = 0,
    parameter integer LANES   = 16,
    parameter integer TAGW    = 32,
    parameter integer DEPTH   = 1024,        // words per source FIFO (power of two)
    parameter integer ADD_LAT = 7,           // ot_hdc_fp32_add_lat #(LAT), bit-identical for 3..7
    parameter integer GW      = 4,           // gather words per output beat (divides N)
    parameter integer SK      = 32,          // level-1 skid / result FIFO entries
    parameter integer FW      = 32 * LANES,
    parameter integer PW      = FW + 2 + TAGW, // record {tag, mode, last, data}
    parameter integer N       = NPKG * PD,
    parameter integer NB      = NPKG - 1,
    parameter integer UV      = NPKG          // UCIe VCs: own + one relay per board port
) (
    input  wire              clk,
    input  wire              rst_n,
    // local port (the die's collective DMA)
    input  wire              in_valid,
    output wire              in_ready,
    input  wire [FW-1:0]     in_data,
    input  wire              in_last,
    input  wire              in_mode,        // 0 all-reduce, 1 all-gather
    input  wire [TAGW-1:0]   in_tag,
    // board ports
    output wire [NB-1:0]     b_tx_valid,
    output wire [PW-1:0]     b_tx_rec,
    input  wire [NB-1:0]     b_tx_ready,
    input  wire [NB-1:0]     b_cr_in,
    input  wire [NB-1:0]     b_rx_valid,
    input  wire [NB*PW-1:0]  b_rx_rec,
    output wire [NB-1:0]     b_cr_out,
    // UCIe port (PD = 2)
    output wire [UV-1:0]     u_tx_valid,
    output wire [UV*PW-1:0]  u_tx_rec,
    input  wire              u_tx_ready,     // VC0 gate (relays cannot be refused)
    input  wire [UV-1:0]     u_cr_in,
    input  wire [UV-1:0]     u_rx_valid,
    input  wire [UV*PW-1:0]  u_rx_rec,
    output wire [UV-1:0]     u_cr_out,
    // result
    output wire              out_valid,
    input  wire              out_ready,
    output wire [GW*FW-1:0]  out_data,
    output wire              out_last,
    output wire              out_gather,
    output wire              out_err,
    output reg               fault,
    output reg  [2:0]        fault_code
);
    localparam integer MYPKG = RANK / PD;
    localparam integer L     = RANK % PD;
    localparam integer PARTNER = (PD == 2) ? (RANK ^ 1) : RANK;
    localparam integer NF    = N + 1;                 // FIFO N: own level-2 package sum
    localparam integer OWN2  = N;
    localparam integer DB    = $clog2(DEPTH);
    localparam integer CB    = $clog2(DEPTH + 1);
    localparam integer E     = N / GW;                // gather beats per index
    localparam integer EB    = (E > 1) ? $clog2(E) : 1;
    localparam integer SB    = $clog2(SK + 1);
    localparam integer LAST_B = FW, MODE_B = FW + 1;
    localparam integer OW    = GW * FW + 3;           // result entry {gather, err, last, data}

    initial begin
        if (NPKG != 4) $fatal(1, "ot_rom_hcoll_die: the level-2 tree is written for NPKG = 4");
        if (PD != 1 && PD != 2) $fatal(1, "ot_rom_hcoll_die: PD must be 1 or 2");
        if (N % GW != 0) $fatal(1, "ot_rom_hcoll_die: GW must divide N");
    end

    function automatic integer rp(input integer j);    // remote package of board port j
        rp = j + ((j >= MYPKG) ? 1 : 0);
    endfunction

    genvar g, q;
    integer i;

    // ---- FIFO bookkeeping -----------------------------------------------------------------------------
    wire [NF-1:0]    push;
    wire [NF*PW-1:0] push_rec;
    reg  [NF-1:0]    pop;
    reg  [CB:0]      cnt [0:NF-1];
    reg  [DB-1:0]    wp  [0:NF-1];
    reg  [DB-1:0]    rpt [0:NF-1];
    reg  [PW-1:0]    mem [0:NF*DEPTH-1];
    wire [PW-1:0]    head [0:NF-1];
    wire [NF-1:0]    ne;
    generate for (g = 0; g < NF; g = g + 1) begin : g_hd
        assign head[g] = mem[g*DEPTH + rpt[g]];
        assign ne[g] = cnt[g] != 0;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < NF; i = i + 1) begin cnt[i] <= 0; wp[i] <= 0; rpt[i] <= 0; end
        end else begin
            for (i = 0; i < NF; i = i + 1) begin
                if (push[i]) begin
                    mem[i*DEPTH + wp[i]] <= push_rec[i*PW +: PW];
                    wp[i] <= wp[i] + 1'b1;
                end
                if (pop[i]) rpt[i] <= rpt[i] + 1'b1;
                cnt[i] <= cnt[i] + (push[i] ? 1'b1 : 1'b0) - (pop[i] ? 1'b1 : 1'b0);
            end
        end
    end

    // ---- credits held by this die (sender side) -----------------------------------------------------
    reg [CB-1:0] bcr [0:NB-1];
    reg [CB-1:0] ucr0;

    // ---- level-1 skid (PD = 2, all-reduce) -----------------------------------------------------------
    reg  [PW-1:0] sk_mem [0:SK-1];
    reg  [SB-1:0] sk_cnt, sk_wp, sk_rp;
    wire          sk_ne = sk_cnt != 0;
    wire [PW-1:0] sk_head = sk_mem[sk_rp];
    reg  [SB-1:0] l1_inflight;
    wire          l1_out_v;
    wire [FW-1:0] l1_out_d;
    wire          l1_out_e;
    reg  [ADD_LAT*(TAGW+1)-1:0] l1_meta_dl;       // {tag, last} beside the adders
    wire          board_ok_all;
    reg           board_ok;
    always @(*) begin
        board_ok = 1'b1;
        for (i = 0; i < NB; i = i + 1) if (bcr[i] == 0 || !b_tx_ready[i]) board_ok = 1'b0;
    end
    assign board_ok_all = board_ok;
    wire drain = (PD == 2) && sk_ne && board_ok_all && (cnt[OWN2] < DEPTH);

    // ---- local transmit ------------------------------------------------------------------------------
    wire need_board = in_mode || (PD == 1);
    wire need_ucie  = (PD == 2);
    wire local_ok   = (in_mode || PD == 2) ? (cnt[RANK] < DEPTH) : (cnt[OWN2] < DEPTH);
    wire ucie_ok    = !need_ucie || (ucr0 != 0 && u_tx_ready);
    // a level-1 drain owns the board transmit bundle; a fire that needs no board port (PD = 2 all-reduce: VC0 only)
    // proceeds beside it
    assign in_ready = local_ok && ucie_ok && (!need_board || (board_ok_all && !drain));
    wire fire = in_valid && in_ready;
    wire [PW-1:0] in_rec = {in_tag, in_mode, in_last, in_data};
    wire bsend = (fire && need_board) || drain;
    assign b_tx_valid = bsend ? {NB{1'b1}} : {NB{1'b0}};
    assign b_tx_rec   = drain ? sk_head : in_rec;

    // UCIe: VC0 own records, VC 1+j relayed gather records from board port j
    generate if (PD == 2) begin : g_utx
        assign u_tx_valid[0] = fire;
        assign u_tx_rec[0 +: PW] = in_rec;
        for (g = 0; g < NB; g = g + 1) begin : g_rl
            assign u_tx_valid[1+g] = b_rx_valid[g] && b_rx_rec[g*PW + MODE_B];
            assign u_tx_rec[(1+g)*PW +: PW] = b_rx_rec[g*PW +: PW];
        end
    end else begin : g_noutx
        assign u_tx_valid = {UV{1'b0}};
        assign u_tx_rec = {UV*PW{1'b0}};
    end endgenerate

    // ---- FIFO writers (one per FIFO) -----------------------------------------------------------------
    generate for (g = 0; g < NF; g = g + 1) begin : g_w
        if (g == OWN2) begin : g_own2
            if (PD == 2) begin : g2
                assign push[g] = drain;
                assign push_rec[g*PW +: PW] = sk_head;
            end else begin : g1
                assign push[g] = fire && !in_mode;
                assign push_rec[g*PW +: PW] = in_rec;
            end
        end else if (g == RANK) begin : g_loc
            assign push[g] = fire && (in_mode || PD == 2);
            assign push_rec[g*PW +: PW] = in_rec;
        end else if (PD == 2 && g == PARTNER) begin : g_par
            assign push[g] = u_rx_valid[0];
            assign push_rec[g*PW +: PW] = u_rx_rec[0 +: PW];
        end else if ((g % PD) == L) begin : g_brd
            localparam integer J = (g / PD) - (((g / PD) > MYPKG) ? 1 : 0);
            assign push[g] = b_rx_valid[J];
            assign push_rec[g*PW +: PW] = b_rx_rec[J*PW +: PW];
        end else begin : g_rly
            localparam integer J = (g / PD) - (((g / PD) > MYPKG) ? 1 : 0);
            assign push[g] = u_rx_valid[1+J];
            assign push_rec[g*PW +: PW] = u_rx_rec[(1+J)*PW +: PW];
        end
    end endgenerate

    // ---- result FIFO -----------------------------------------------------------------------------------
    reg  [OW-1:0] of_mem [0:SK-1];
    reg  [SB-1:0] of_cnt, of_wp, of_rp;
    reg  [SB-1:0] l2_inflight;
    reg           of_push;
    reg  [OW-1:0] of_in;
    wire          of_pop = out_valid && out_ready;
    assign out_valid  = of_cnt != 0;
    assign out_data   = of_mem[of_rp][GW*FW-1:0];
    assign out_last   = of_mem[of_rp][GW*FW];
    assign out_err    = out_valid && of_mem[of_rp][GW*FW+1];
    assign out_gather = of_mem[of_rp][GW*FW+2];

    // ---- gather pop / emit -------------------------------------------------------------------------------
    reg          hb_v;
    reg [EB-1:0] beat;
    reg [FW-1:0] hb [0:N-1];
    reg          hb_last;
    reg          g_all;
    always @(*) begin
        g_all = 1'b1;
        for (i = 0; i < N; i = i + 1) if (!ne[i] || !head[i][MODE_B]) g_all = 1'b0;
    end
    wire beat_go = hb_v && (of_cnt + l2_inflight < SK);
    wire last_beat = beat_go && (beat == E - 1);
    wire gpop = g_all && (!hb_v || last_beat) && (l2_inflight == 0) && (l1_inflight == 0);

    // ---- level-1 pop (PD = 2) --------------------------------------------------------------------------
    wire l1pop = (PD == 2) && ne[RANK] && ne[PARTNER] && !head[RANK][MODE_B] && !head[PARTNER][MODE_B] &&
                 (sk_cnt + l1_inflight < SK - 1);
    localparam integer EVEN = (PD == 2) ? (RANK & ~1) : RANK;
    localparam integer ODD  = (PD == 2) ? (RANK | 1) : RANK;

    // ---- level-2 pop -------------------------------------------------------------------------------------
    function automatic integer l2src(input integer p);
        l2src = (p == MYPKG) ? OWN2 : (p * PD + L);
    endfunction
    reg l2_all;
    always @(*) begin
        l2_all = 1'b1;
        for (i = 0; i < NPKG; i = i + 1) if (!ne[l2src(i)] || head[l2src(i)][MODE_B]) l2_all = 1'b0;
    end
    wire l2pop = l2_all && !hb_v && (of_cnt + l2_inflight < SK - 1);

    always @(*) begin
        pop = {NF{1'b0}};
        if (gpop) for (i = 0; i < N; i = i + 1) pop[i] = 1'b1;
        if (l1pop) begin pop[RANK] = 1'b1; pop[PARTNER] = 1'b1; end
        if (l2pop) for (i = 0; i < NPKG; i = i + 1) pop[l2src(i)] = 1'b1;
    end

    // ---- adders --------------------------------------------------------------------------------------------
    // level 1: s = r_even + r_odd
    wire [LANES-1:0] l1v;
    wire [2*LANES-1:0] l1e;
    generate if (PD == 2) begin : g_l1
        for (g = 0; g < LANES; g = g + 1) begin : g_ln
            ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(l1pop),
                .a(head[EVEN][32*g +: 32]), .b(head[ODD][32*g +: 32]), .y(l1_out_d[32*g +: 32]),
                .err(l1e[2*g +: 2]), .valid_out(l1v[g]));
        end
        always @(posedge clk) l1_meta_dl <= {l1_meta_dl[ADD_LAT*(TAGW+1)-(TAGW+1)-1:0],
                                             head[RANK][PW-1 -: TAGW], head[RANK][LAST_B]};
        assign l1_out_v = l1v[0];
        assign l1_out_e = |l1e;
    end else begin : g_nol1
        assign l1v = {LANES{1'b0}};
        assign l1e = {2*LANES{1'b0}};
        assign l1_out_v = 1'b0;
        assign l1_out_d = {FW{1'b0}};
        assign l1_out_e = 1'b0;
        always @(posedge clk) l1_meta_dl <= 0;
    end endgenerate
    wire [TAGW:0] l1_meta = l1_meta_dl[ADD_LAT*(TAGW+1)-1 -: TAGW+1];

    // level 2: ((in0 + in1) + (in2 + in3)) over packages 0..3
    wire [FW-1:0] ab, cd, yy;
    wire [LANES-1:0] abv, cdv, yv;
    wire [2*LANES-1:0] abe, cde, ye;
    generate for (g = 0; g < LANES; g = g + 1) begin : g_l2
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_ab (.clk(clk), .rst_n(rst_n), .valid_in(l2pop),
            .a(head[l2src(0)][32*g +: 32]), .b(head[l2src(1)][32*g +: 32]), .y(ab[32*g +: 32]),
            .err(abe[2*g +: 2]), .valid_out(abv[g]));
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_cd (.clk(clk), .rst_n(rst_n), .valid_in(l2pop),
            .a(head[l2src(2)][32*g +: 32]), .b(head[l2src(3)][32*g +: 32]), .y(cd[32*g +: 32]),
            .err(cde[2*g +: 2]), .valid_out(cdv[g]));
        ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_y (.clk(clk), .rst_n(rst_n), .valid_in(abv[0]),
            .a(ab[32*g +: 32]), .b(cd[32*g +: 32]), .y(yy[32*g +: 32]),
            .err(ye[2*g +: 2]), .valid_out(yv[g]));
    end endgenerate
    reg [2*ADD_LAT-1:0] l2_last_dl;
    reg [ADD_LAT-1:0]   l2_e1_dl;           // level-a errors beside level b
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin l2_last_dl <= 0; l2_e1_dl <= 0; end
        else begin
            l2_last_dl <= {l2_last_dl[2*ADD_LAT-2:0], l2pop && head[l2src(0)][LAST_B]};
            l2_e1_dl <= {l2_e1_dl[ADD_LAT-2:0], abv[0] && ((|abe) || (|cde))};
        end
    end
    wire l2_out_v = yv[0];
    wire l2_out_e = (|ye) || l2_e1_dl[ADD_LAT-1];
    wire l2_out_l = l2_last_dl[2*ADD_LAT-1];

    // ---- tag / mode agreement of every pop -------------------------------------------------------------------
    reg agree;
    always @(*) begin
        agree = 1'b1;
        if (gpop) for (i = 1; i < N; i = i + 1)
            if (head[i][PW-1 -: TAGW+1] != head[0][PW-1 -: TAGW+1]) agree = 1'b0;
        if (l1pop && head[EVEN][PW-1 -: TAGW+1] != head[ODD][PW-1 -: TAGW+1]) agree = 1'b0;
        if (l2pop) for (i = 1; i < NPKG; i = i + 1)
            if (head[l2src(i)][PW-1 -: TAGW+1] != head[l2src(0)][PW-1 -: TAGW+1]) agree = 1'b0;
    end

    // ---- result FIFO input -----------------------------------------------------------------------------------
    always @(*) begin
        of_push = 1'b0;
        of_in = {OW{1'b0}};
        if (beat_go) begin
            of_push = 1'b1;
            of_in[GW*FW+2] = 1'b1;
            of_in[GW*FW] = hb_last && (beat == E - 1);
            for (i = 0; i < GW; i = i + 1) of_in[i*FW +: FW] = hb[beat*GW + i];
        end else if (l2_out_v) begin
            of_push = 1'b1;
            of_in[FW-1:0] = yy;
            of_in[GW*FW] = l2_out_l;
            of_in[GW*FW+1] = l2_out_e;
        end
    end

    // ---- sequential state ------------------------------------------------------------------------------------
    // board credit return: own pops of the counterpart FIFO, matched with the partner's relay credit when the
    // popped record was relayed (a gather record, PD = 2)
    reg [CB+1:0] owe   [0:NB-1];
    reg [CB+1:0] gpend [0:NB-1];
    reg [CB+1:0] rpend [0:NB-1];
    reg [NB-1:0] bco;
    assign b_cr_out = bco;
    reg [UV-1:0] uco;
    assign u_cr_out = uco;
    always @(*) begin
        for (i = 0; i < NB; i = i + 1) bco[i] = owe[i] != 0;
        uco = {UV{1'b0}};
        if (PD == 2) begin
            uco[0] = pop[PARTNER];
            for (i = 0; i < NB; i = i + 1) uco[1+i] = pop[rp(i) * PD + (1 - L)] && (PD == 2);
        end
    end

    reg ovf;
    always @(*) begin
        ovf = 1'b0;
        for (i = 0; i < NF; i = i + 1) if (push[i] && cnt[i] == DEPTH && !pop[i]) ovf = 1'b1;
        if (l1_out_v && sk_cnt == SK) ovf = 1'b1;
        if (of_push && of_cnt == SK && !of_pop) ovf = 1'b1;
    end

    always @(posedge clk or negedge rst_n) begin : seq
        integer j, cf, pg, mt;
        if (!rst_n) begin
            for (j = 0; j < NB; j = j + 1) begin bcr[j] <= DEPTH; owe[j] <= 0; gpend[j] <= 0; rpend[j] <= 0; end
            ucr0 <= DEPTH;
            sk_cnt <= 0; sk_wp <= 0; sk_rp <= 0; l1_inflight <= 0;
            of_cnt <= 0; of_wp <= 0; of_rp <= 0; l2_inflight <= 0;
            hb_v <= 1'b0; beat <= 0; hb_last <= 1'b0;
            fault <= 1'b0; fault_code <= 3'b0;
        end else begin
            for (j = 0; j < NB; j = j + 1) begin
                bcr[j] <= bcr[j] - (bsend ? 1'b1 : 1'b0) + (b_cr_in[j] ? 1'b1 : 1'b0);
                cf = 0; pg = 0; mt = 0;
                if (pop[rp(j) * PD + L]) begin
                    if (PD == 2 && head[rp(j) * PD + L][MODE_B]) pg = 1; else cf = 1;
                end
                if ((gpend[j] + pg) != 0 && (rpend[j] + (u_cr_in[1+j] && PD == 2 ? 1 : 0)) != 0) mt = 1;
                gpend[j] <= gpend[j] + pg - mt;
                rpend[j] <= rpend[j] + ((PD == 2 && u_cr_in[1+j]) ? 1 : 0) - mt;
                owe[j] <= owe[j] + cf + mt - (bco[j] ? 1 : 0);
            end
            if (PD == 2) ucr0 <= ucr0 - (fire ? 1'b1 : 1'b0) + (u_cr_in[0] ? 1'b1 : 1'b0);
            // level-1 skid
            if (l1_out_v) sk_mem[sk_wp] <= {l1_meta[TAGW:1], 1'b0, l1_meta[0], l1_out_d};
            if (l1_out_v) sk_wp <= (sk_wp == SK - 1) ? 0 : sk_wp + 1'b1;
            if (drain) sk_rp <= (sk_rp == SK - 1) ? 0 : sk_rp + 1'b1;
            sk_cnt <= sk_cnt + (l1_out_v ? 1'b1 : 1'b0) - (drain ? 1'b1 : 1'b0);
            l1_inflight <= l1_inflight + (l1pop ? 1'b1 : 1'b0) - (l1_out_v ? 1'b1 : 1'b0);
            // result FIFO
            if (of_push) begin
                of_mem[of_wp] <= of_in;
                of_wp <= (of_wp == SK - 1) ? 0 : of_wp + 1'b1;
            end
            if (of_pop) of_rp <= (of_rp == SK - 1) ? 0 : of_rp + 1'b1;
            of_cnt <= of_cnt + (of_push ? 1'b1 : 1'b0) - (of_pop ? 1'b1 : 1'b0);
            l2_inflight <= l2_inflight + (l2pop ? 1'b1 : 1'b0) - (l2_out_v ? 1'b1 : 1'b0);
            // gather head buffer
            if (gpop) begin
                hb_v <= 1'b1; beat <= 0;
                hb_last <= head[0][LAST_B];
                for (j = 0; j < N; j = j + 1) hb[j] <= head[j][FW-1:0];
            end else if (beat_go) begin
                if (beat == E - 1) hb_v <= 1'b0;
                else beat <= beat + 1'b1;
            end
            // faults
            if ((l1_out_v && l1_out_e) || (l2_out_v && l2_out_e)) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
            if (!agree) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (ovf) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
            if (l2_out_v && beat_go) begin fault <= 1'b1; fault_code[1] <= 1'b1; end    // output collision
        end
    end
endmodule
