`timescale 1ns/1ps
`default_nettype none
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
// Latency per record grows (~14 edges); the rate stays one 32-element beat a cycle (OD 64 covers the longer loop).
// MUT (bench): 1 = assembly takes sector j from lane j ^ 1 of the beat (lane-to-sector map; must FAIL).
module ot_hgi_quant_wide_h #(
    parameter integer NB = 32,
    parameter integer LQ = 16,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          go,
    input  wire [1408:0] cmd,
    output wire          idle,
    output reg           done,
    output reg           fault,
    output wire [32*16-1:0]  wrq,
    input  wire [31:0]       wrq_cr,
    input  wire [32*257-1:0] wrr,
    output wire [32*280-1:0] wwq,
    input  wire [31:0]       wwq_cr,
    input  wire [31:0]       wwq_done,
    output wire              rg_req,
    input  wire              rg_gnt,
    output wire              wg_req,
    input  wire              wg_gnt
);
    localparam integer LD = 4;                  // = ot_hgi_qw_rq production default
    localparam integer OD = 64, OW = 6;         // = SRAM words
    localparam integer SW = $clog2(NB), CW = $clog2(LQ + 1), LW = $clog2(LD);
    wire [2:0] rr_n;                            // 0 control, 1 counters / relays, 2 tiles
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    // ---------------------------------------------------------------- record registers
    reg busy, bad;
    reg [127:0] hdr;
    reg [19:0] m;
    reg [31:0] rs, ws;
    reg [3:0] nsec_last;
    reg [15:0] beats_row;
    reg b1;
    reg [19:0] r_row; reg [15:0] r_left; reg r_last; reg [14:0] r_sec; reg [31:0] r_nrowbase; reg rd_done;
    reg [19:0] w_row; reg [15:0] w_beat; reg [31:0] w_rowbase;
    reg [39:0] sec_done, sec_iss;
    reg p_go; reg [1408:0] p_cmd;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) p_go <= 0; else p_go <= go && !busy;
    always @(posedge clk) if (go && !busy) p_cmd <= cmd;
    assign idle = !busy && !p_go;
    assign rg_req = busy; assign wg_req = busy;
    reg rg_ok, wg_ok;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin rg_ok <= 0; wg_ok <= 0; end
        else begin rg_ok <= busy && rg_gnt; wg_ok <= busy && wg_gnt; end
    // ---------------------------------------------------------------- tiles
    wire [1023:0] gq [0:7];
    wire [31:0] e_push, e_rcr, e_wcr, e_done;
    reg [31:0] hr2, hp2;                        // relayed hit vectors
    reg [14:0] rs2 [0:31]; reg [3:0] sl2 [0:31];
    reg [511:0] wy2; reg [31:0] wv2; reg [3:0] ws2 [0:31]; reg [14:0] wsec2 [0:31];
    genvar q;
    generate for (q = 0; q < 8; q = q + 1) begin : g_q
        wire [59:0] rsec_b, wsec_b; wire [15:0] rsl_b, wsl_b;
        for (genvar i = 0; i < 4; i = i + 1) begin : g_l
            assign rsec_b[i*15 +: 15] = rs2[q*4 + i]; assign rsl_b[i*4 +: 4] = sl2[q*4 + i];
            assign wsec_b[i*15 +: 15] = wsec2[q*4 + i]; assign wsl_b[i*4 +: 4] = ws2[q*4 + i];
        end
        ot_hgi_qw_rq u_rq (.clk(clk), .rst_n(rr_n[2]), .wrr(wrr[q*4*257 +: 4*257]), .wrq(wrq[q*64 +: 64]),
            .wrq_cr(wrq_cr[q*4 +: 4]), .c_hit_r(hr2[q*4 +: 4]), .c_sec(rsec_b), .c_hit_p(hp2[q*4 +: 4]), .c_slot(rsl_b),
            .gq(gq[q]), .e_push(e_push[q*4 +: 4]), .e_rcr(e_rcr[q*4 +: 4]));
        ot_hgi_qw_wq u_wq (.clk(clk), .rst_n(rr_n[2]), .wwq(wwq[q*4*280 +: 4*280]), .wwq_cr(wwq_cr[q*4 +: 4]),
            .wwq_done(wwq_done[q*4 +: 4]), .c_y(wy2), .c_v(wv2[q*4 +: 4]), .c_slot(wsl_b), .c_sec(wsec_b),
            .e_wcr(e_wcr[q*4 +: 4]), .e_done(e_done[q*4 +: 4]));
    end endgenerate
    // event relays (tile face -> centre)
    reg [31:0] ev_push, ev_rcr, ev_wcr, ev_done;
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin ev_push <= 0; ev_rcr <= 0; ev_wcr <= 0; ev_done <= 0; end
        else begin ev_push <= e_push; ev_rcr <= e_rcr; ev_wcr <= e_wcr; ev_done <= e_done; end
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
    wire [2:0] r_nsec = r_last ? nsec_last[2:0] : 3'd4;
    reg [31:0] r_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1)
        r_ok_l[b] = (rcr[b] > CW'(hit_r[b])) && ((lf_r[b] + (LW+1)'(hit_r[b])) < (LW+1)'(LD));
    reg r_cr_ok;
    always @* begin
        r_cr_ok = 1'b1;
        for (integer j = 0; j < 4; j = j + 1) if (j < r_nsec && !r_ok_l[5'(r_sec[4:0] + j)]) r_cr_ok = 1'b0;
    end
    wire r_issue = busy && !bad && rg_ok && !rd_done && r_used < NB && r_cr_ok;
    wire [4:0] h_l = bq_l[r_head]; wire [2:0] h_n = bq_n[r_head];
    reg h_ok;
    always @* begin
        h_ok = r_used != 0;
        for (integer j = 0; j < 4; j = j + 1)
            if (j < h_n && !(lf_n[5'(h_l + j)] > (LW+1)'(hit_p[5'(h_l + j)]))) h_ok = 1'b0;
    end
    wire l_fire = busy && h_ok && resv < OD;
    wire [14:0] w_sec0 = mq_sec[od_h]; wire [2:0] w_n = mq_n[od_h];
    reg w_cr_ok;
    always @* begin
        w_cr_ok = 1'b1;
        for (integer j = 0; j < 4; j = j + 1)
            if (j < w_n && !(wcr[5'(w_sec0 + j)] > CW'(hit_w[5'(w_sec0 + j)]))) w_cr_ok = 1'b0;
    end
    wire w_fire = busy && !bad && wg_ok && od_n != 0 && w_cr_ok;
    function automatic [31:0] lanes(input [4:0] l0, input [2:0] nn);
        lanes = 0;
        for (integer j = 0; j < 4; j = j + 1) if (j < nn) lanes[5'(l0 + j)] = 1'b1;
    endfunction
    // ---------------------------------------------------------------- per-lane sectors / slots (registered, then relayed)
    reg [14:0] rs1 [0:31]; reg [3:0] sl1 [0:31];
    always @(posedge clk)
        for (integer b = 0; b < 32; b = b + 1) begin
            rs1[b] <= r_sec + 15'(5'(b - r_sec[4:0]));
            sl1[b] <= 4'(1) << (2'(b - h_l) ^ ((MUT == 1) ? 2'd1 : 2'd0));
            rs2[b] <= rs1[b]; sl2[b] <= sl1[b];
        end
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin hr2 <= 0; hp2 <= 0; end
        else begin hr2 <= hit_r; hp2 <= hit_p; end
    // ---------------------------------------------------------------- gather: 2-level OR, launch
    reg [1023:0] go_h [0:1]; reg [1023:0] lx;
    reg [3:0] gv; reg launch;
    always @(posedge clk) begin
        for (integer h = 0; h < 2; h = h + 1) go_h[h] <= gq[h*4] | gq[h*4 + 1] | gq[h*4 + 2] | gq[h*4 + 3];
        lx <= go_h[0] | go_h[1];
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin gv <= 0; launch <= 0; end
        else begin gv <= {gv[2:0], |hit_p}; launch <= gv[3]; end
    // ---------------------------------------------------------------- decode tile, result capture, SRAM FIFO
    wire d_vo, d_f, d_df; wire [511:0] d_y;
    ot_hgi_qw_dec u_dec (.clk(clk), .rst_n(rr_n[2]), .v(launch), .header(hdr), .x(lx), .vo(d_vo), .y(d_y),
        .fault(d_f), .decode_fault(d_df));
    reg yc_v, yc_f, yc_df; reg [511:0] yc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin yc_v <= 0; yc_f <= 0; yc_df <= 0; end
        else begin yc_v <= d_vo; yc_f <= d_vo && d_f; yc_df <= d_df; end
    always @(posedge clk) yc <= d_y;
    wire [511:0] od_rd;
    ot_sram_1r1w_64x512_m1_r2c2 u_od (.clk(clk), .r_ce_in(w_fire), .r_addr_in(od_h), .rd_out(od_rd),
        .w_ce_in(yc_v), .w_addr_in(od_t), .wd_in(yc), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // write beat: capture the SRAM read, per-lane valid / slot / sector a cycle later, relay to the write quads
    reg [511:0] wc_y; reg wm_v; reg [14:0] wm_sec; reg [2:0] wm_n;
    reg [31:0] wv1; reg [3:0] ws1 [0:31]; reg [14:0] wsec1 [0:31];
    always @(posedge clk) begin
        wc_y <= od_rd; wy2 <= wc_y;
        wm_sec <= w_sec0; wm_n <= w_n;
        for (integer b = 0; b < 32; b = b + 1) begin
            ws1[b] <= 4'(1) << 2'(b - wm_sec[4:0]); wsec1[b] <= wm_sec + 15'(5'(b - wm_sec[4:0]));
            ws2[b] <= ws1[b]; wsec2[b] <= wsec1[b];
        end
    end
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin wm_v <= 0; wv1 <= 0; wv2 <= 0; end
        else begin
            wm_v <= w_fire;
            for (integer b = 0; b < 32; b = b + 1) wv1[b] <= wm_v && (5'(b - wm_sec[4:0]) < 5'(wm_n));
            wv2 <= wv1;
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
            busy <= 0; bad <= 0; done <= 0; fault <= 0; hdr <= 0; m <= 0; rs <= 0; ws <= 0; nsec_last <= 0; beats_row <= 0;
            b1 <= 0; r_row <= 0; r_left <= 0; r_last <= 0; r_sec <= 0; r_nrowbase <= 0; rd_done <= 0;
            sec_done <= 0; sec_iss <= 0; r_tail <= 0; r_head <= 0; r_used <= 0;
            mq_h <= 0; mq_t <= 0; od_h <= 0; od_t <= 0; od_n <= 0; resv <= 0;
            w_row <= 0; w_beat <= 0; w_rowbase <= 0; hit_r <= 0; hit_p <= 0; hit_w <= 0;
        end else begin
            done <= 0;
            hit_r <= r_issue ? lanes(r_sec[4:0], r_nsec) : 32'd0;
            hit_p <= l_fire ? lanes(h_l, h_n) : 32'd0;
            hit_w <= w_fire ? lanes(w_sec0[4:0], w_n) : 32'd0;
            if (p_go) begin
                busy <= 1; bad <= 0; fault <= 0; hdr <= p_cmd[128:1];
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
                if (yc_f) begin bad <= 1; fault <= 1; end
            end
            if (yc_df) begin bad <= 1; fault <= 1; end
            od_n <= od_n + (OW+1)'(yc_v) - (OW+1)'(w_fire);
            resv <= resv + (OW+1)'(l_fire) - (OW+1)'(w_fire);
            if (w_fire) begin od_h <= od_h + 1'b1; mq_h <= mq_h + 1'b1; sec_iss <= sec_iss + 40'(w_n); end
            sec_done <= sec_done + 40'(dc);
            if (busy && !bad && rd_done && w_row == m && resv == 0 && od_n == 0 && sec_done + 40'(dc) == sec_iss) begin busy <= 0; done <= 1; end
            if (busy && bad && r_used == 0 && od_n == resv && sec_done == sec_iss && dc == 0) begin busy <= 0; done <= 1; end
            if (p_go) begin
                sec_done <= 0; sec_iss <= 0;
                r_tail <= 0; r_head <= 0; r_used <= 0; mq_h <= 0; mq_t <= 0; od_h <= 0; od_t <= 0; od_n <= 0; resv <= 0;
            end
        end
    end
    always @(posedge clk) begin
        if (r_issue) begin bq_l[r_tail] <= r_sec[4:0]; bq_n[r_tail] <= r_nsec; end
        if (l_fire) begin mq_sec[mq_t] <= w_rowbase[17:3] + 15'({w_beat, 2'd0}); mq_n[mq_t] <= h_n; end
    end
    initial if (NB < 8 || (NB & (NB - 1)) != 0 || (LQ & (LQ - 1)) != 0) $fatal(1, "ot_hgi_quant_wide_h: NB / LQ");
endmodule
`default_nettype wire
