`timescale 1ns/1ps
`default_nettype none
// HEAD leaf (el1013-hbm-quant-split) of the wires-only parent ot_hgi_quant_wide_h: control, gather tail, decoder, result
// SRAM; lane faces, rq/wq quads and the pair gather are in 4 x ot_hgi_qw_lg2.  Original header follows.
// FUSED.QDQ_* wide engine, hierarchical physical structure (el1011-hbm-fq, 2026-10-11, owner textbook audit).
// Same ports, arithmetic, beat order and VM lane-group protocol as ot_hgi_quant_wide (its header holds the record / beat /
// fast-path rules), so O is word-identical; only the cycle structure differs.  The flat engines failed the textbook
// classes (one clock tree over 109k sinks / 820 um, datapath resets and shared selects fanning to thousands of flops,
// a 32 x 512-b flop FIFO read through one 32:1 mux, 9-45% utilisation).  Here:
//   * 8 hardened read quads (ot_hgi_qw_rq: lane pin flops, response FIFOs, gather register, request flops) on the read
//     face, 8 hardened write quads (ot_hgi_qw_wq: write relay + lane flops) on the write face, the decode hardened with
//     registered seams (ot_hgi_qw_dec); each tile has its own clock tree;
//   * the centre keeps only control: issue / pop / write decisions on 32-bit hit vectors (counters take them one edge
//     later and every decision subtracts the unapplied hit -- exact accounting), per-lane sectors and one-hot slots
//     computed here and registered (no shared select fanout in a tile), tile events returning through relay flops;
//   * every seam that can exceed ~500 um gets a relay register (requests, pops, write beats, events, a 2-level gather OR);
//   * the result FIFO is a 64 x 512 SRAM (ot_sram_1r1w_64x512_m1_r2c2) with a capture flop on its read port;
//   * retire counts done events through a registered popcount.
// Command relay, registered status pins and per-half write-beat relays (physical spec 10-11). Latency per record grows (~16 edges); the rate stays one 32-element beat a cycle (OD 64 covers the longer loop).
// Registered face (el1011-hbm-fq 10-12, class 3: ha/hb-adc3fb5d8 EARLY_FAIL_HOLD, 5 pin flops of 9,734 inputs): every input
// port is captured by a pure face flop (no logic, no reset, no enable) and every child pin / centre cone is fed from face
// or staging flops only; every output port is driven by a pure face flop.  Reset: rst_n is sampled by a face flop that
// feeds the reset relay (assert then needs one clock edge; release as before plus one).  Cost: +1 cycle on go (idle drops
// two cycles after go -- ot_hgi_quant_unit WQ=2 waits one more state), +1 on each read request / response / credit,
// +1 on each write beat / credit / done, +1 on the grants; rate unchanged.
// MUT (bench): 1 = assembly takes sector j from lane j ^ 1 of the beat (lane-to-sector map; must FAIL).
module ot_hgi_qw_hh #(
    parameter integer NB = 32,
    parameter integer LQ = 16,
    parameter integer MUT = 0,
    // decoder track: 0 = ot_hgi_qw_dec (one tile, g_d1.u_dec), 1 = ot_hgi_qw_dec3 (dxl/dbq/daq tiles, g_d3.u_dec)
`ifdef OT_QW_DEC3
    parameter integer DEC3 = 1
`else
    parameter integer DEC3 = 0
`endif
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [1408:0] cmd,
    output reg           idle,
    output reg           done,
    output reg           fault,
    // lane-group leaves (4 x ot_hgi_qw_lg2): every output below is a register of this head, every input a leaf register
    output wire [3:0]        l_rst_n,
    output wire [31:0]       l_hit_r, l_hit_p, l_wv,
    output wire [32*15-1:0]  l_rs, l_wsec,
    output wire [32*4-1:0]   l_sl, l_ws,
    output wire [511:0]      l_wy,
    input  wire [4*1024-1:0] l_gp,
    input  wire [31:0]       l_push, l_rcr, l_wcr, l_done,
    output reg               rg_req,
    input  wire              rg_gnt,
    output reg               wg_req,
    input  wire              wg_gnt
);
    localparam integer LD = 4;                  // = ot_hgi_qw_rq production default
    localparam integer OD = 64, OW = 6;         // = SRAM words
    localparam integer SW = $clog2(NB), CW = $clog2(LQ + 1), LW = $clog2(LD);
    // ---------------------------------------------------------------- face flops (pure: no logic, reset or enable)
    reg f_rst, f_go, f_rg, f_wg;
    reg [1408:0] f_cmd;
    always @(posedge clk) begin
        f_rst <= rst_n; f_go <= go; f_cmd <= cmd; f_rg <= rg_gnt; f_wg <= wg_gnt;
    end
    wire [6:0] rr_n;                            // 0 control, 1 counters / relays, 2 decoder tiles, 3..6 lane-group leaves
    ot_rst_relay #(.REGIONS(7)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    assign l_rst_n = rr_n[6:3];
    // ---------------------------------------------------------------- record registers
    reg busy, bad, c_done, c_fault;            // centre done / fault (registered again at the pins)
    reg [127:0] hdr;
    reg [19:0] m;
    reg [31:0] rs, ws;
    reg [3:0] nsec_last;
    reg [15:0] beats_row;
    reg b1;
    reg [19:0] r_row; reg [15:0] r_left; reg r_last; reg [14:0] r_sec; reg [31:0] r_nrowbase; reg rd_done;
    reg [19:0] w_row; reg [15:0] w_beat; reg [31:0] w_rowbase;
    reg [39:0] sec_done, sec_iss;
    // command: face flops, then a relay into the centre (the face is ~350 um from the control).  The command words shift
    // unconditionally (no 1,409-flop enable): p_cmd is the command of the f_go cycle whenever p_go is set.
    reg p_go, p_go0; reg [1408:0] p_cmd, p_cmd0;
    wire take = f_go && !busy && !p_go0 && !p_go;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin p_go0 <= 0; p_go <= 0; end
        else begin p_go0 <= take; p_go <= p_go0; end
    always @(posedge clk) begin p_cmd0 <= f_cmd; p_cmd <= p_cmd0; end
    // registered status outputs (idle may only lag: it drops two cycles after go and rises a cycle after busy falls)
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin idle <= 1'b1; done <= 0; fault <= 0; rg_req <= 0; wg_req <= 0; end
        else begin
            idle <= !take && !p_go0 && !p_go && !busy;
            done <= c_done; fault <= c_fault; rg_req <= busy; wg_req <= busy;
        end
    reg rg_ok, wg_ok;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin rg_ok <= 0; wg_ok <= 0; end
        else begin rg_ok <= busy && f_rg; wg_ok <= busy && f_wg; end
    // ---------------------------------------------------------------- tiles
    wire [1023:0] gp [0:3];                    // leaf pair gather registers
    wire [31:0] e1_push = l_push, e1_rcr = l_rcr, e1_wcr = l_wcr, e1_done = l_done;   // leaf output registers
    genvar gi;
    generate for (gi = 0; gi < 4; gi = gi + 1) begin : g_gp assign gp[gi] = l_gp[gi*1024 +: 1024]; end endgenerate
    // event relays (tile face -> centre): two stages (a corner quad of the 778 x 691 cluster is ~560 um from the centre
    // counters); a later event only returns a credit / count later, so every decision stays conservative and exact.
    reg [31:0] ev_push, ev_rcr, ev_wcr, ev_done;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin
            ev_push <= 0; ev_rcr <= 0; ev_wcr <= 0; ev_done <= 0;
        end else begin
            ev_push <= e1_push; ev_rcr <= e1_rcr; ev_wcr <= e1_wcr; ev_done <= e1_done;
        end
    // ---------------------------------------------------------------- counters (take last cycle's hit vectors)
    reg [CW-1:0] rcr [0:31], wcr [0:31];
    reg [LW:0] lf_n [0:31], lf_r [0:31];
    reg [31:0] hit_r, hit_p, hit_w;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) for (integer b = 0; b < 32; b = b + 1) begin rcr[b] <= LQ[CW-1:0]; wcr[b] <= LQ[CW-1:0]; lf_n[b] <= 0; lf_r[b] <= 0; end
        else for (integer b = 0; b < 32; b = b + 1) begin
            rcr[b] <= rcr[b] + CW'(ev_rcr[b]) - CW'(hit_r[b]);
            wcr[b] <= wcr[b] + CW'(ev_wcr[b]) - CW'(hit_w[b]);
            lf_n[b] <= lf_n[b] + (LW+1)'(ev_push[b]) - (LW+1)'(hit_p[b]);
            lf_r[b] <= lf_r[b] + (LW+1)'(hit_r[b]) - (LW+1)'(hit_p[b]);
        end
    // issued-beat FIFO, meta FIFO
    reg [4:0] bq_l [0:NB-1]; reg [2:0] bq_n [0:NB-1];
    reg [SW-1:0] r_tail, r_head; reg [SW:0] r_used;
    reg [14:0] mq_sec [0:OD-1]; reg [2:0] mq_n [0:OD-1]; reg [OW-1:0] mq_h, mq_t;
    reg [OW-1:0] od_h, od_t; reg [OW:0] od_n, resv;
    // ---------------------------------------------------------------- decisions
    // el1011-hbm-fq 10-11 (class 5, ha/hb-d63ee120c od_h -> sec_iss / u_od.r_ce 17 levels): every credit decision is a
    // 32-lane vector AND (one-hot lane window from a register), no 32:1 lane muxes; the write head (sector, count, lane
    // window) is a lookahead register; the result-FIFO SRAM read is issued from a register one edge after w_fire.
    function automatic [31:0] lanes(input [4:0] l0, input [2:0] nn);
        lanes = 0;
        for (integer j = 0; j < 4; j = j + 1) if (j < nn) lanes[5'(l0 + j)] = 1'b1;
    endfunction
    wire [2:0] r_nsec = r_last ? nsec_last[2:0] : 3'd4;
    reg [31:0] r_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1)
        r_ok_l[b] = (rcr[b] > CW'(hit_r[b])) && ((lf_r[b] + (LW+1)'(hit_r[b])) < (LW+1)'(LD));
    wire r_cr_ok = &(~lanes(r_sec[4:0], r_nsec) | r_ok_l);
    wire r_issue = busy && !bad && rg_ok && !rd_done && r_used < NB && r_cr_ok;
    // read head lookahead (el1011-hbm-fq 10-12, qw_h3_ref-f2h CTS SS r_head -> bq mux -> lanes -> l_fire -> mq_sec, 20
    // levels): hh_* = entry r_head of bq, registered.  Both candidates for the next head (r_head, r_head + 1) are read
    // from bq in parallel, with a bypass when r_issue writes that slot this edge (only possible when it is the head:
    // r_used == 0 for r_head, r_used == 1 for r_head + 1); l_fire / p_go only pick between them at the end.  Exact: a
    // live head slot (r_used != 0) is never rewritten (r_issue needs r_used < NB), so hh == bq[r_head] whenever used.
    reg [4:0] hh_l; reg [2:0] hh_n; reg [31:0] hh_ln;
    wire [4:0] h_l = hh_l; wire [2:0] h_n = hh_n;
    reg [31:0] h_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1) h_ok_l[b] = lf_n[b] > (LW+1)'(hit_p[b]);
    wire h_ok = (r_used != 0) && &(~hh_ln | h_ok_l);
    wire l_fire = busy && h_ok && resv < OD;
    // write head lookahead: hd_* = meta of entry od_h, re-read every edge for the next od_h.  Exact: an entry counts in od_n
    // only after its gather/decode/capture pipeline (>= 5 edges after its meta write), so mq is settled when hd reads it.
    reg [14:0] hd_sec; reg [2:0] hd_n; reg [31:0] hd_ln;
    wire [14:0] w_sec0 = hd_sec; wire [2:0] w_n = hd_n;
    reg [31:0] w_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1) w_ok_l[b] = wcr[b] > CW'(hit_w[b]);
    wire w_cr_ok = &(~hd_ln | w_ok_l);
    wire w_fire = busy && !bad && wg_ok && od_n != 0 && w_cr_ok;
    wire [SW-1:0] r_head1 = r_head + 1'b1;
    wire c0_b = r_issue && (r_used == 0), c1_b = r_issue && (r_used == 1);
    wire [4:0] c0_l = c0_b ? r_sec[4:0] : bq_l[r_head];  wire [2:0] c0_n = c0_b ? r_nsec : bq_n[r_head];
    wire [4:0] c1_l = c1_b ? r_sec[4:0] : bq_l[r_head1]; wire [2:0] c1_n = c1_b ? r_nsec : bq_n[r_head1];
    wire [31:0] c0_ln = lanes(c0_l, c0_n), c1_ln = lanes(c1_l, c1_n);
    always @(posedge clk) begin
        // p_go: r_head -> 0 with r_used 0; the next issue writes slot 0 with r_used == 0 and bypasses into hh
        if (l_fire && !p_go) begin hh_l <= c1_l; hh_n <= c1_n; hh_ln <= c1_ln; end
        else begin hh_l <= c0_l; hh_n <= c0_n; hh_ln <= c0_ln; end
    end
    wire [OW-1:0] od_hn = p_go ? {OW{1'b0}} : (w_fire ? od_h + 1'b1 : od_h);
    always @(posedge clk) begin
        hd_sec <= mq_sec[od_hn]; hd_n <= mq_n[od_hn]; hd_ln <= lanes(mq_sec[od_hn][4:0], mq_n[od_hn]);
    end
    // registered SRAM read issue (next to u_od): rf_* = w_fire / od_h / head meta one edge later
    reg rf_v; reg [OW-1:0] rf_a; reg [14:0] rf_sec; reg [2:0] rf_n;
    always @(posedge clk) begin rf_a <= od_h; rf_sec <= w_sec0; rf_n <= w_n; end
    // ---------------------------------------------------------------- per-lane sectors / slots (registered, then relayed)
    reg [14:0] rs1 [0:31]; reg [3:0] sl1 [0:31];
    always @(posedge clk)
        for (integer b = 0; b < 32; b = b + 1) begin
            rs1[b] <= r_sec + 15'(5'(b - r_sec[4:0]));
            sl1[b] <= 4'(1) << (2'(b - h_l) ^ ((MUT == 1) ? 2'd1 : 2'd0));
        end
    // ---------------------------------------------------------------- gather: registered OR2 tree, launch
    // (el1011-hbm-fq 10-12, qw_h3_ref-f2h CTS SS -382.8: the 4-way OR across a 2 x 2 block of rq tiles into go_h was one
    // stage over ~300 um of 1,024-bit wire.)  Now every stage is one OR2 of two neighbours: gp[k] = the two side-by-side
    // tiles of row k (registered between them), go_h[h] = two adjacent rows, lx = the two halves next to the decoder.
    // +1 edge of gather latency; gv follows (5 deep).
    reg [1023:0] gpf [0:3]; reg [1023:0] lx;
    reg [4:0] gv; reg launch;
    always @(posedge clk) begin
        for (integer h = 0; h < 4; h = h + 1) gpf[h] <= gp[h];     // el1013 seam rule: pure head pin flop per leaf
        lx <= (gpf[0] | gpf[1]) | (gpf[2] | gpf[3]);               // former go_h OR2 folded into this stage (same latency)
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin gv <= 0; launch <= 0; end
        else begin gv <= {gv[3:0], |hit_p}; launch <= gv[4]; end
    // ---------------------------------------------------------------- decode tile, result capture, SRAM FIFO
    wire d_vo, d_f, d_df; wire [511:0] d_y;
    generate if (DEC3 != 0) begin : g_d3
        // track B (el1011-hbm-fq 10-12): the decoder as three hardened tiles (dxl / dbq / daq), same ports and timing
        ot_hgi_qw_dec3 u_dec (.clk(clk), .rst_n(rr_n[2]), .v(launch), .header(hdr), .x(lx), .vo(d_vo), .y(d_y),
            .fault(d_f), .decode_fault(d_df));
    end else begin : g_d1
        ot_hgi_qw_dec u_dec (.clk(clk), .rst_n(rr_n[2]), .v(launch), .header(hdr), .x(lx), .vo(d_vo), .y(d_y),
            .fault(d_f), .decode_fault(d_df));
    end endgenerate
    reg yc_v, yc_f, yc_df; reg [511:0] yc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin yc_v <= 0; yc_f <= 0; yc_df <= 0; end
        else begin yc_v <= d_vo; yc_f <= d_vo && d_f; yc_df <= d_df; end
    always @(posedge clk) yc <= d_y;
    wire [511:0] od_rd;
    ot_sram_1r1w_64x512_m1_r2c2 u_od (.clk(clk), .r_ce_in(rf_v), .r_addr_in(rf_a), .rd_out(od_rd),
        .w_ce_in(yc_v), .w_addr_in(od_t), .wd_in(yc), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // write beat: capture the SRAM read, per-lane valid / slot / sector a cycle later, relay to the write quads
    reg [511:0] wc_y; reg wm_v; reg [14:0] wm_sec; reg [2:0] wm_n;
    reg [31:0] wv1; reg [3:0] ws1 [0:31]; reg [14:0] wsec1 [0:31];
    always @(posedge clk) begin
        wc_y <= od_rd;
        wm_sec <= rf_sec; wm_n <= rf_n;
        for (integer b = 0; b < 32; b = b + 1) begin
            ws1[b] <= 4'(1) << 2'(b - wm_sec[4:0]); wsec1[b] <= wm_sec + 15'(5'(b - wm_sec[4:0]));
        end
    end
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin rf_v <= 0; wm_v <= 0; wv1 <= 0; end
        else begin
            rf_v <= w_fire; wm_v <= rf_v;
            for (integer b = 0; b < 32; b = b + 1) wv1[b] <= wm_v && (5'(b - wm_sec[4:0]) < 5'(wm_n));
        end
    // retire: registered popcount of done events
    reg [5:0] dc;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) dc <= 0;
        else begin : pc
            reg [5:0] c; c = 0;
            for (integer b = 0; b < 32; b = b + 1) c = c + 6'(ev_done[b]);
            dc <= c;
        end
    // ---------------------------------------------------------------- central control
    always @(posedge clk or negedge rr_n[0]) begin
        if (!rr_n[0]) begin
            busy <= 0; bad <= 0; c_done <= 0; c_fault <= 0; hdr <= 0; m <= 0; rs <= 0; ws <= 0; nsec_last <= 0; beats_row <= 0;
            b1 <= 0; r_row <= 0; r_left <= 0; r_last <= 0; r_sec <= 0; r_nrowbase <= 0; rd_done <= 0;
            sec_done <= 0; sec_iss <= 0; r_tail <= 0; r_head <= 0; r_used <= 0;
            mq_h <= 0; mq_t <= 0; od_h <= 0; od_t <= 0; od_n <= 0; resv <= 0;
            w_row <= 0; w_beat <= 0; w_rowbase <= 0; hit_r <= 0; hit_p <= 0; hit_w <= 0;
        end else begin
            c_done <= 0;
            hit_r <= r_issue ? lanes(r_sec[4:0], r_nsec) : 32'd0;
            hit_p <= l_fire ? hh_ln : 32'd0;
            hit_w <= w_fire ? hd_ln : 32'd0;
            if (p_go) begin
                busy <= 1; bad <= 0; c_fault <= 0; hdr <= p_cmd[128:1];
                m <= p_cmd[129 + 256 + 68 +: 20];
                rs <= p_cmd[129 + 256 + 88 +: 32]; ws <= p_cmd[1153 + 88 +: 32];
                r_sec <= p_cmd[129 + 256 + 8 + 3 +: 15];
                r_nrowbase <= p_cmd[129 + 256 + 8 +: 32] + p_cmd[129 + 256 + 88 +: 32];
                w_rowbase <= p_cmd[1153 + 8 +: 32];
                beats_row <= 16'((p_cmd[129 + 256 + 48 +: 20] + 20'd31) >> 5);
                r_left <= 16'((p_cmd[129 + 256 + 48 +: 20] + 20'd31) >> 5);
                b1 <= p_cmd[129 + 256 + 48 +: 20] <= 20'd32;
                r_last <= p_cmd[129 + 256 + 48 +: 20] <= 20'd32;
                nsec_last <= (p_cmd[129 + 256 + 48 +: 5] == 5'd0) ? 4'd4 : 4'(p_cmd[129 + 256 + 51 +: 2]);
                r_row <= 0; rd_done <= 0; w_row <= 0; w_beat <= 0;
            end
            if (r_issue) begin
                r_tail <= r_tail + 1'b1;
                if (r_last) begin
                    r_row <= r_row + 1; r_sec <= r_nrowbase[17:3]; r_nrowbase <= r_nrowbase + rs;
                    r_left <= beats_row; r_last <= b1;
                    if (r_row + 1 == m) rd_done <= 1;
                end else begin
                    r_sec <= r_sec + 15'd4; r_left <= r_left - 1'b1; r_last <= (r_left == 16'd2);
                end
            end
            if (l_fire) begin
                r_head <= r_head + 1'b1; mq_t <= mq_t + 1'b1;
                if (w_beat + 16'd1 == beats_row) begin w_beat <= 0; w_row <= w_row + 1; w_rowbase <= w_rowbase + ws; end
                else w_beat <= w_beat + 1;
            end
            r_used <= r_used + (SW+1)'(r_issue) - (SW+1)'(l_fire);
            if (yc_v) begin
                od_t <= od_t + 1'b1;
                if (yc_f) begin bad <= 1; c_fault <= 1; end
            end
            if (yc_df) begin bad <= 1; c_fault <= 1; end
            od_n <= od_n + (OW+1)'(yc_v) - (OW+1)'(w_fire);
            resv <= resv + (OW+1)'(l_fire) - (OW+1)'(w_fire);
            if (w_fire) begin od_h <= od_h + 1'b1; mq_h <= mq_h + 1'b1; sec_iss <= sec_iss + 40'(w_n); end
            sec_done <= sec_done + 40'(dc);
            if (busy && !bad && rd_done && w_row == m && resv == 0 && od_n == 0 && sec_done + 40'(dc) == sec_iss) begin busy <= 0; c_done <= 1; end
            if (busy && bad && r_used == 0 && od_n == resv && sec_done == sec_iss && dc == 0) begin busy <= 0; c_done <= 1; end
            if (p_go) begin
                sec_done <= 0; sec_iss <= 0;
                r_tail <= 0; r_head <= 0; r_used <= 0; mq_h <= 0; mq_t <= 0; od_h <= 0; od_t <= 0; od_n <= 0; resv <= 0;
            end
        end
    end
    // meta write one edge after l_fire (mw_*: l_fire only loads a few control flops, not the 64-entry write enables).
    // Exact: hd reads an entry only once it counts in od_n, >= 6 edges after this write.
    reg mw_v; reg [OW-1:0] mw_a; reg [14:0] mw_sec; reg [2:0] mw_n;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) mw_v <= 0; else mw_v <= l_fire;
    always @(posedge clk) begin mw_a <= mq_t; mw_sec <= w_rowbase[17:3] + 15'({w_beat, 2'd0}); mw_n <= h_n; end
    always @(posedge clk) begin
        if (r_issue) begin bq_l[r_tail] <= r_sec[4:0]; bq_n[r_tail] <= r_nsec; end
        if (mw_v) begin mq_sec[mw_a] <= mw_sec; mq_n[mw_a] <= mw_n; end
    end
    // leaf-facing outputs: stage-1 registers of the former two-stage relays (stage 2 is the leaf pin register)
    generate for (gi = 0; gi < 32; gi = gi + 1) begin : g_lo
        assign l_rs[gi*15 +: 15] = rs1[gi]; assign l_sl[gi*4 +: 4] = sl1[gi];
        assign l_ws[gi*4 +: 4] = ws1[gi]; assign l_wsec[gi*15 +: 15] = wsec1[gi];
    end endgenerate
    assign l_hit_r = hit_r; assign l_hit_p = hit_p; assign l_wv = wv1; assign l_wy = wc_y;
    initial if (NB < 8 || (NB & (NB - 1)) != 0 || (LQ & (LQ - 1)) != 0) $fatal(1, "ot_hgi_quant_wide_h: NB / LQ");
endmodule
`default_nettype wire
