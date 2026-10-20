`timescale 1ns/1ps
// S81-IDX3R (10-20, tree MU.BAL.SX.3): dsfd_ctrl_rg3, the regional S81 HBM controller of dsfd_ctrl_rg2 PLUS the client
// face of the NON-INLINE paired index reader dsdv_idx_rg3 (mu7 die: 8 readers in the PHY corner strips, 122 frames).
// dsfd_ctrl_rg2 stays UNCHANGED (in-line idx3 fallback / closed views).  svc_rs <-> controller rq (682 b) / rd (562 b)
// are the rg2 links bit for bit; what is added, per PC p (one reader lane a PC, no lane sharing):
//
//   rrq[46p +: 46]   = {tag10, len 4, addr 30, sl, v}       request lane from the reader (read-only)
//   rrd[272p +: 272] = {data 256, tag10, beat 4, pop, v}    response lane to the reader
//
// STATIC READER SLOTS (owner: static schedule, no credits / backpressure on die links): sl is the reader's window, the
// compiled reader-slot calendar of this PC.  In a reader slot the PC's request input is the reader's (the mux select is
// a registered copy of sl, never a runtime arbitration); svc_rs never issues there.  A slice word that arrives in a
// reader slot is dropped and raises the sticky status fault (a schedule check, not a scheduling mechanism).  Outside the
// reader slots the slice word path is the rg2 path (one 2:1 mux in front of the per-PC pin register, select 0).
//
// READER LANDING FIFO (RFD entries a PC, flop ring, one-hot pointers, <= 2 kb): a reader request lands at the pin
// (+1), is written (+1) and moves into the PC channel in a reader slot when the PC has room (the rg2 per-PC request
// budget DQ, counted HERE where every request is seen: the HBM boundary's elastic take never crosses the die link).
// Each move returns a pop on the response lane; the reader issues only while (issued - pops) < RFD, so over the fixed
// lane latency the FIFO can never overflow (an overflow is a fault).
//
// RETURN DEMUX: a response in the reader-tag range (tag[16:15] = 2'b11; svc_rs uses 00 / 01 / 10) goes to the reader
// lane (registered, +1), all others to rd exactly as rg2.  rk: an owner FIFO (16 entries, 1 bit) records, in order, who
// put each request into the PC channel; the channel's in-order rk is passed to rd only for slice requests.
// Status: rd[561] = rg2's PC chain fault | reader-face fault (slice word in a reader slot, landing FIFO overflow, owner
// FIFO overflow, a reader request outside its window).
// MUT (bench negative controls, define S81CTRL3_MUT=<n>): 1 return demux on tag[16] only, 2 rk not filtered by the owner
// FIFO, 3 reader moves ignore the PC budget, 4 a slice word in a reader slot passes (no fault, reader word lost).
//
// SAFE checklist: pins registered (lane in / out flops; svc pins as rg2); fanout: kept copies for the 341-b input
// select (22 a PC), the landing write enables (2 a entry), the read select (2 a pointer bit), the move decision (one
// copy set a consumer group); depth: a move is the AND of 3 registered flags; storage: RFD x 44 b = 1,056 b a PC (flops,
// < 2 kb); reset: control bits only, 2-stage landing + relay leaves; schedule: static (all latencies fixed, priced).
`default_nettype none
module dsfd_ctrl_rg3 #(
    parameter integer DQ  = 8,     // request buffer entries per PC (the svc's static per-PC request budget)
    parameter integer DR  = 8,     // response landing entries per PC
    parameter integer RFD = 24,    // reader landing FIFO entries per PC (= dsdv_idx_rg3 DQR)
    parameter integer MUT = 0
) (
    input  wire           clk,
    input  wire           ckh,
    input  wire           rst_n,
    input  wire [681:0]   rq,
    output wire [561:0]   rd,
    output wire           ck_o,
    input  wire [91:0]    rrq,       // reader request lanes (PC 0, PC 1)
    output reg  [543:0]   rrd,       // reader response lanes (PC 0, PC 1)
    output wire [1:0]     k_v,
    input  wire [1:0]     k_rdy,
    output wire [59:0]    k_addr,
    output wire [7:0]     k_len,
    output wire [33:0]    k_tag,
    output wire [1:0]     k_we,
    output wire [511:0]   k_wdata,
    output wire [63:0]    k_wstrb,
    input  wire [1:0]     k_wr_done,
    input  wire [1:0]     kr_v,
    output wire [1:0]     kr_rdy,
    input  wire [33:0]    kr_tag,
    input  wire [7:0]     kr_beat,
    input  wire [511:0]   kr_data
);
    initial if (RFD < 2 || RFD > 31 || DQ > 15) $fatal(1, "dsfd_ctrl_rg3: RFD / DQ range");
    localparam integer CW = 5;                       // landing FIFO count width (RFD <= 31)
    // reader-face reset: 2-flop landing + relay leaves (control bits only)
    wire [11:0] rr;
    ot_rst_relay #(.REGIONS(12), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));

    wire [1:0] co0, co1;
    wire [1:0] s_ovf;
    wire [1:0] rflt;                                 // reader-face fault (per PC, sticky)
    genvar p;
    generate for (p = 0; p < 2; p = p + 1) begin : g_pc
        // ------------------------------------------------------------ reader lane pin + landing FIFO write
        reg         lv, lsl;
        reg  [43:0] ld;                              // {tag10, len 4, addr 30}
        (* keep = "true" *) reg [2:0] lvk;           // lane valid copies (write enables / pointer / count)
        always @(posedge clk or negedge rr[6 * p])
            if (!rr[6 * p]) begin lv <= 1'b0; lsl <= 1'b0; lvk <= 3'd0; end
            else begin lv <= rrq[46 * p]; lsl <= rrq[46 * p + 1]; lvk <= {3{rrq[46 * p]}}; end
        always @(posedge clk) ld <= rrq[46 * p + 2 +: 44];
        reg  [43:0] wd;                              // write stage data
        reg         lvw;                             // write stage valid
        (* keep = "true" *) reg [RFD-1:0] wea, web;  // entry write enables (entry halves)
        reg  [RFD-1:0] wp;                           // write pointer (one-hot)
        reg  [RFD-1:0][43:0] ent;
        always @(posedge clk) wd <= ld;
        always @(posedge clk or negedge rr[6 * p + 1])
            if (!rr[6 * p + 1]) begin lvw <= 1'b0; wea <= '0; web <= '0; wp <= RFD'(1); end
            else begin
                lvw <= lvk[2];
                wea <= {RFD{lvk[0]}} & wp; web <= {RFD{lvk[1]}} & wp;
                if (lvk[2]) wp <= {wp[RFD-2:0], wp[RFD-1]};
            end
        integer e;
        always @(posedge clk) for (e = 0; e < RFD; e = e + 1) begin
            if (wea[e]) ent[e][21:0]  <= wd[21:0];
            if (web[e]) ent[e][43:22] <= wd[43:22];
        end
        // ------------------------------------------------------------ move decision (reader slot, FIFO not empty, room)
        (* keep = "true" *) reg [2:0] wnk, nek, rmk;    // window / not-empty / room copies [group]
        (* keep = "true" *) reg [21:0] selk;            // input-select copies (16 bits each): registered sl
        wire [2:0] mv;                               // move decision copies: 0 pointers, 1 counts / owner, 2 lane pop
        assign mv[0] = wnk[0] & nek[0] & rmk[0];
        assign mv[1] = wnk[1] & nek[1] & rmk[1];
        assign mv[2] = wnk[2] & nek[2] & rmk[2];
        (* keep = "true" *) reg [RFD-1:0] rpa, rpb;  // read pointer copies (entry halves)
        reg  [43:0] hw;                              // head word (read every edge)
        reg  [CW-1:0] cnt;                           // landed, not moved
        reg  [3:0]  n;                               // requests in the PC channel (decisions - rk)
        (* keep = "true" *) reg [1:0] dk;            // a move presented to the PC this edge (registered decision)
        reg [43:0] hw_n;
        always @* begin : g_hw
            integer x;
            hw_n = '0;
            for (x = 0; x < RFD; x = x + 1) begin
                hw_n[21:0]  = hw_n[21:0]  | ({22{rpa[x]}} & ent[x][21:0]);
                hw_n[43:22] = hw_n[43:22] | ({22{rpb[x]}} & ent[x][43:22]);
            end
        end
        always @(posedge clk) hw <= hw_n;
        // the slice word's valid at the pin (rg2 path) and the word that enters the PC channel this edge
        wire        sv = rq[341 * p];
        wire        sl_now = selk[0];
        wire        sp = (MUT == 4) && sv;           // MUT 4: slice word priority in a reader slot
        wire        enter_s = sv && (!sl_now || sp); // slice word enters
        wire        rk_w;
        reg  [15:0] own, owp, orp;                   // owner FIFO: 1 = reader, one-hot pointers
        reg  [4:0]  own_n;
        wire        own_h = |(own & orp);
        wire        push = sl_now ? (dk[0] || sp) : sv;
        wire        push_r = sl_now && dk[1] && !sp;
        always @(posedge clk or negedge rr[6 * p + 2])
            if (!rr[6 * p + 2]) begin
                wnk <= 3'd0; nek <= 3'd0; rmk <= 3'b111; selk <= '0; dk <= 2'd0; cnt <= '0; n <= 4'd0;
            end else begin : g_mv
                reg [CW-1:0] c_; reg [4:0] n_;
                wnk <= {3{rrq[46 * p + 1]}}; selk <= {22{lsl}};   // wnk = sl at the pin = selk one edge later
                dk <= {2{mv[1]}};
                c_ = cnt + (lvw ? CW'(1) : CW'(0)) - (mv[1] ? CW'(1) : CW'(0));
                cnt <= c_;
                nek <= {3{c_ != '0}};
                n_ = 5'(n) + (mv[1] ? 5'd1 : 5'd0) + (enter_s ? 5'd1 : 5'd0) - (rk_w ? 5'd1 : 5'd0);
                n <= 4'(n_);
                rmk <= (MUT == 3) ? 3'b111 : {3{n_ < 5'(DQ)}};
            end
        always @(posedge clk or negedge rr[6 * p + 3])
            if (!rr[6 * p + 3]) begin rpa <= RFD'(1); rpb <= RFD'(1); end
            else if (mv[0]) begin rpa <= {rpa[RFD-2:0], rpa[RFD-1]}; rpb <= {rpb[RFD-2:0], rpb[RFD-1]}; end
        // owner FIFO (in order with the channel's rk)
        always @(posedge clk or negedge rr[6 * p + 4])
            if (!rr[6 * p + 4]) begin owp <= 16'd1; orp <= 16'd1; own_n <= 5'd0; end
            else begin
                if (push) owp <= {owp[14:0], owp[15]};
                if (rk_w) orp <= {orp[14:0], orp[15]};
                own_n <= own_n + (push ? 5'd1 : 5'd0) - (rk_w ? 5'd1 : 5'd0);
            end
        integer o;
        always @(posedge clk) for (o = 0; o < 16; o = o + 1) if (push && owp[o]) own[o] <= push_r;
        // ------------------------------------------------------------ the PC channel input: slice word or reader move
        wire [340:0] rdw = {256'd0, 32'd0, 2'b11, hw[43:34], 5'd0, hw[33:30], hw[29:0], 1'b0, dk[0]};
        wire [340:0] rq_pc;
        genvar b;
        for (b = 0; b < 341; b = b + 1) begin : g_mx
            if (MUT == 4) begin : g_m4
                assign rq_pc[b] = (sv || !selk[b / 16]) ? rq[341 * p + b] : rdw[b];
            end else begin : g_n
                assign rq_pc[b] = selk[b / 16] ? rdw[b] : rq[341 * p + b];
            end
        end
        // ------------------------------------------------------------ the rg2 per-PC channel (unchanged)
        wire [1:0] ci = (p == 0) ? 2'b01 : co0;
        wire [1:0] co;
        wire        rv_w, wd_w;
        wire [255:0] rdat;
        wire [16:0]  rtag;
        wire [3:0]   rbeat;
        ot_s81ph_ctrl_pcr #(.DQ(DQ), .DR(DR)) u_pc (
            .cks(clk), .ckh(ckh), .rst(rst_n), .ci(ci), .co(co),
            .rq(rq_pc), .rk(rk_w), .rv(rv_w), .r_data(rdat), .r_tag(rtag), .r_beat(rbeat), .wd(wd_w),
            .s_ovf(s_ovf[p]),
            .k_v(k_v[p]), .k_rdy(k_rdy[p]), .k_addr(k_addr[p*30 +: 30]), .k_len(k_len[p*4 +: 4]),
            .k_tag(k_tag[p*17 +: 17]), .k_we(k_we[p]), .k_wdata(k_wdata[p*256 +: 256]), .k_wstrb(k_wstrb[p*32 +: 32]),
            .k_wr_done(k_wr_done[p]), .kr_v(kr_v[p]), .kr_rdy(kr_rdy[p]), .kr_tag(kr_tag[p*17 +: 17]),
            .kr_beat(kr_beat[p*4 +: 4]), .kr_data(kr_data[p*256 +: 256]));
        // ------------------------------------------------------------ return demux
        wire rtr = (MUT == 1) ? rtag[16] : (rtag[16] & rtag[15]);   // reader-tag range
        assign rd[p*280 +: 280] = {wd_w, (MUT == 2) ? rk_w : (rk_w && !own_h), rv_w && !rtr, rbeat, rtag, rdat};
        always @(posedge clk or negedge rr[6 * p + 5])
            if (!rr[6 * p + 5]) begin rrd[272 * p] <= 1'b0; rrd[272 * p + 1] <= 1'b0; end
            else begin rrd[272 * p] <= rv_w && rtr; rrd[272 * p + 1] <= mv[2]; end
        always @(posedge clk) rrd[272 * p + 2 +: 270] <= {rdat, rtag[14:5], rbeat};
        // ------------------------------------------------------------ reader-face faults (sticky)
        reg f_;
        always @(posedge clk or negedge rr[6 * p + 5])
            if (!rr[6 * p + 5]) f_ <= 1'b0;
            else if ((sv && sl_now && MUT != 4)                     // slice word in a reader slot (MUT 4: no check)
                     || (lvw && cnt == CW'(RFD) && !mv[1])          // landing FIFO overflow
                     || own_n > 5'd16                               // owner FIFO overflow
                     || (lv && !lsl)) f_ <= 1'b1;                   // reader request outside its window
        assign rflt[p] = f_;
        if (p == 0) begin : g_c0 assign co0 = co; end
        else        begin : g_c1 assign co1 = co; end
    end endgenerate
    // regional status register: rg2's chain + the reader-face faults
    wire srst_n;
    ot_s81ph_sync u_srs (.clk(clk), .rst_n(rst_n), .d(1'b1), .q(srst_n));
    reg [1:0] st;
    always @(posedge clk or negedge srst_n)
        if (!srst_n) st <= 2'b00;
        else st <= {co1[1] | rflt[0] | rflt[1], co1[0]};
    assign rd[561:560] = st;
    wire ckn;
    ot_dvrly_ckinv u_ck0 (.a(clk), .y(ckn));
    ot_dvrly_ckinv u_ck1 (.a(ckn), .y(ck_o));
endmodule
`default_nettype wire
