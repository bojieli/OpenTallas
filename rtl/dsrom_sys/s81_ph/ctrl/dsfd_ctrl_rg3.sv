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
    initial if (RFD < 4 || RFD > 31 || RFD % 2 != 0 || DQ > 11 || DQ < 2) $fatal(1, "dsfd_ctrl_rg3: RFD / DQ range");
    localparam integer CW = 5;                       // landing FIFO count width (RFD <= 31)
    localparam integer NWC = 4;                      // landing write-enable copies a entry (11 bits each)
    localparam integer NRC = 4;                      // read-pointer copies (11 bits of the head word each)
    localparam integer NMV = 2 * NRC + 2;            // move-decision copies: 2 a read-pointer copy (half each), counts, pop
    localparam integer OQ = 12;                      // owner FIFO entries (>= DQ + the channel's pin / write stages)
    // reader-face reset: the regional leaf lands in 2 flops (u_srs), then relay leaves (control bits only)
    wire srst_n;
    ot_s81ph_sync u_srs (.clk(clk), .rst_n(rst_n), .d(1'b1), .q(srst_n));
    localparam integer RL = 11;                      // reset leaves a PC (<= ~25 control flops each)
    wire [2*RL-1:0] rr;
    wire [1:0] rt;                                   // 2-level forest: srst_n -> 2 PC roots -> RL leaves each
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rt (.clk(clk), .rst_n_in(srst_n), .rst_n(rt));
    ot_rst_relay #(.REGIONS(RL), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr0 (.clk(clk), .rst_n_in(rt[0]), .rst_n(rr[RL-1:0]));
    ot_rst_relay #(.REGIONS(RL), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr1 (.clk(clk), .rst_n_in(rt[1]), .rst_n(rr[2*RL-1:RL]));

    wire [1:0] co0, co1;
    wire [1:0] s_ovf;
    wire [1:0] rflt;                                 // reader-face fault (per PC, sticky)
    genvar p;
    generate for (p = 0; p < 2; p = p + 1) begin : g_pc
        // ------------------------------------------------------------ reader lane pin + landing FIFO write
        reg         lv, lsl;
        reg         lvw;                             // write stage valid
        reg  [43:0] ld;                              // {tag10, len 4, addr 30}
        (* keep = "true" *) reg [NWC+1:0] lvk;       // lane valid copies: NWC write-enable groups, 2 pointer halves
        always @(posedge clk or negedge rr[RL * p])
            if (!rr[RL * p]) begin lv <= 1'b0; lsl <= 1'b0; lvk <= '0; lvw <= 1'b0; end
            else begin lv <= rrq[46 * p]; lsl <= rrq[46 * p + 1]; lvk <= {(NWC+2){rrq[46 * p]}}; lvw <= lvk[NWC]; end
        always @(posedge clk) ld <= rrq[46 * p + 2 +: 44];
        reg  [43:0] wd;                              // write stage data
        (* keep = "true" *) reg [NWC*RFD-1:0] wec;   // entry write enables: wec[RFD c + e], copy c = bits 11 c +: 11
        reg  [RFD-1:0] wp;                           // write pointer (one-hot)
        reg  [44*RFD-1:0] ent;                       // entry e = ent[44 e +: 44]
        always @(posedge clk) wd <= ld;
        integer e, c;
        // write enables carry no reset (lvk is reset: they settle to 0 one edge into the reset; a stray power-on write
        // lands in an entry that is not counted)
        always @(posedge clk) for (c = 0; c < NWC; c = c + 1) wec[RFD * c +: RFD] <= {RFD{lvk[c]}} & wp;
        always @(posedge clk or negedge rr[RL * p + 1])
            if (!rr[RL * p + 1]) wp <= RFD'(1);
            else for (e = 0; e < RFD; e = e + 1) if (lvk[NWC + (e >= RFD / 2 ? 1 : 0)]) wp[e] <= wp[(e + RFD - 1) % RFD];
        always @(posedge clk) for (e = 0; e < RFD; e = e + 1) for (c = 0; c < NWC; c = c + 1)
            if (wec[RFD * c + e]) ent[44 * e + 11 * c +: 11] <= wd[11 * c +: 11];
        // ------------------------------------------------------------ move decision (reader slot, FIFO not empty, room)
        (* keep = "true" *) reg [NMV-1:0] wnk, nek, rmk;  // window / not-empty / room copies [group]
        (* keep = "true" *) reg [21:0] selk;            // input-select copies (16 bits each): registered sl
        (* keep = "true" *) reg [1:0]  sln;             // registered sl for the control terms
        wire [NMV-1:0] mv = wnk & nek & rmk;         // move decision copies
        (* keep = "true" *) reg [NRC*RFD-1:0] rpc;   // read pointer copies rpc[RFD c + x], copy c reads bits 11 c +: 11
        reg  [43:0] hw;                              // head word (read every edge)
        reg  [CW-1:0] cnt;                           // landed, not moved
        reg  [3:0]  n;                               // requests in the PC channel (decisions + slice words - rk)
        (* keep = "true" *) reg [1:0] dk;            // a move presented to the PC this edge (registered decision)
        reg [43:0] hw_n;
        always @* begin : g_hw
            integer x, y;
            hw_n = '0;
            for (x = 0; x < RFD; x = x + 1) for (y = 0; y < NRC; y = y + 1)
                hw_n[11 * y +: 11] = hw_n[11 * y +: 11] | ({11{rpc[RFD * y + x]}} & ent[44 * x + 11 * y +: 11]);
        end
        always @(posedge clk) hw <= hw_n;
        // the slice word's valid at the pin: one load into the channel mux; the accounting uses registered terms
        wire        sv = rq[341 * p];
        wire        sp = (MUT == 4) && sv;           // MUT 4: slice word priority in a reader slot
        wire        rk_w;
        reg         ent_q;                           // a slice word entered the channel last edge (counted one late)
        reg         hit_q;                           // a slice word arrived in a reader slot last edge
        (* keep = "true" *) reg [2:0] psh;           // owner push copies (pointer, entries, count), one edge late
        reg         psh_v;                           // owner bit of that push (1 = reader)
        (* keep = "true" *) reg [1:0] rkq;           // rk one edge late (owner pops)
        reg  [OQ-1:0] own, owp, orp;                 // owner FIFO: 1 = reader, one-hot pointers
        reg  [4:0]  own_n;
        reg         own_hr;                          // owner of the request the channel's rk returns this edge
        // selk carries no reset (lsl is reset: 0 one edge into the reset, while the channel is held in reset too)
        always @(posedge clk) selk <= {22{lsl}};
        wire [CW-1:0] c_n = cnt + (lvw ? CW'(1) : CW'(0)) - (mv[2 * NRC] ? CW'(1) : CW'(0));
        // the slice word of last edge is counted now: one entry of margin (DQ - 1) covers it
        wire [4:0]    n_n = 5'(n) + (mv[2 * NRC] ? 5'd1 : 5'd0) + (ent_q ? 5'd1 : 5'd0) - (rk_w ? 5'd1 : 5'd0);
        always @(posedge clk or negedge rr[RL * p + 2])
            if (!rr[RL * p + 2]) begin wnk <= '0; nek <= '0; end
            else begin wnk <= {NMV{rrq[46 * p + 1]}}; nek <= {NMV{c_n != '0}}; end   // wnk = sl at the pin = selk one edge later
        always @(posedge clk or negedge rr[RL * p + 3])
            if (!rr[RL * p + 3]) begin rmk <= '1; sln <= 2'd0; dk <= 2'd0; cnt <= '0; n <= 4'd0; end
            else begin
                sln <= {2{lsl}}; dk <= {2{mv[2 * NRC]}}; cnt <= c_n; n <= 4'(n_n);
                rmk <= (MUT == 3) ? '1 : {NMV{n_n < 5'(DQ - 1)}};
            end
        always @(posedge clk or negedge rr[RL * p + 4])
            if (!rr[RL * p + 4]) begin ent_q <= 1'b0; hit_q <= 1'b0; psh <= 3'd0; psh_v <= 1'b0; end
            else begin
                ent_q <= sv && (!sln[0] || sp);
                hit_q <= sv && sln[0];
                psh <= {3{sln[0] ? (dk[0] || sp) : sv}};
                psh_v <= sln[0] && dk[1] && !sp;
            end
        genvar gy;
        for (gy = 0; gy < NRC; gy = gy + 1) begin : g_rp            // one reset leaf a read-pointer copy
            integer x2;
            always @(posedge clk or negedge rr[RL * p + 5 + gy])
                if (!rr[RL * p + 5 + gy]) rpc[RFD * gy +: RFD] <= RFD'(1);
                else for (x2 = 0; x2 < RFD; x2 = x2 + 1)
                    if (mv[2 * gy + (x2 >= RFD / 2 ? 1 : 0)]) rpc[RFD * gy + x2] <= rpc[RFD * gy + (x2 + RFD - 1) % RFD];
        end
        // owner FIFO (in order with the channel's rk; push and pop one edge late, the rk owner precomputed)
        wire [OQ-1:0] orp1 = rkq[0] ? {orp[OQ-2:0], orp[OQ-1]} : orp;    // head after the pending pop
        wire [OQ-1:0] orp2 = {orp1[OQ-2:0], orp1[OQ-1]};
        always @(posedge clk or negedge rr[RL * p + 9])
            if (!rr[RL * p + 9]) begin owp <= OQ'(1); rkq <= 2'd0; own_hr <= 1'b0; end
            else begin
                if (psh[0]) owp <= {owp[OQ-2:0], owp[OQ-1]};
                rkq <= {2{rk_w}};
                own_hr <= rk_w ? |(own & orp2) : |(own & orp1);
            end
        always @(posedge clk or negedge rr[RL * p + 10])
            if (!rr[RL * p + 10]) begin orp <= OQ'(1); own_n <= 5'd0; end
            else begin
                if (rkq[0]) orp <= {orp[OQ-2:0], orp[OQ-1]};
                own_n <= own_n + (psh[2] ? 5'd1 : 5'd0) - (rkq[1] ? 5'd1 : 5'd0);
            end
        integer o;
        always @(posedge clk) for (o = 0; o < OQ; o = o + 1) if (psh[1] && owp[o]) own[o] <= psh_v;
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
        assign rd[p*280 +: 280] = {wd_w, (MUT == 2) ? rk_w : (rk_w && !own_hr), rv_w && !rtr, rbeat, rtag, rdat};
        always @(posedge clk or negedge rr[RL * p + 4])
            if (!rr[RL * p + 4]) begin rrd[272 * p] <= 1'b0; rrd[272 * p + 1] <= 1'b0; end
            else begin rrd[272 * p] <= rv_w && rtr; rrd[272 * p + 1] <= mv[2 * NRC + 1]; end
        always @(posedge clk) rrd[272 * p + 2 +: 270] <= {rdat, rtag[14:5], rbeat};
        // ------------------------------------------------------------ reader-face faults (sticky)
        reg f_;
        always @(posedge clk or negedge rr[RL * p + 4])
            if (!rr[RL * p + 4]) f_ <= 1'b0;
            else if ((hit_q && MUT != 4)                            // slice word in a reader slot (MUT 4: no check)
                     || (lvw && cnt == CW'(RFD) && !mv[2 * NRC])    // landing FIFO overflow
                     || own_n > 5'(OQ)                              // owner FIFO overflow
                     || (lv && !lsl)) f_ <= 1'b1;                   // reader request outside its window
        assign rflt[p] = f_;
        if (p == 0) begin : g_c0 assign co0 = co; end
        else        begin : g_c1 assign co1 = co; end
    end endgenerate
    // regional status register: rg2's chain + the reader-face faults
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
