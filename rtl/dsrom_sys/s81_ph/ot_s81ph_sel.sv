`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CLAUDE S81-PH (2026-10-06): the S81 die SELECTOR slab (dsfd_bk_selector) around the UNCHANGED streaming exact
// top-k ot_hdc_v41x_sel (Q 4, W 16, IW 20, K 512, AW 8).  Contract: results/rtl/s81_ph_20261006/selector/contract.json.
//
// Die lanes (stream 1.2 GHz, valid-only, no back-pressure; the hub end block dsfd_m2l_vr_512x1__hix_<st> delivers
// {fault, live, data 512, valid} in this clock).  One input per scan service (stack SW / SE / NW / NE); each carries
// ONE select quarter (a contiguous, ascending position range of the segment):
//   data[511:508] type, [507:500] tag
//     1 HDR     [19:0] base position, [29:20] k (<= 512), [31:30] qslot (the sel quarter this stack feeds)
//     2 BEAT    [255:0] 16 BF16 scores (lane i at [16i +: 16]), [271:256] lane valid, [272] last of the quarter;
//               lane i is position cur + i, then cur += 16 (masked lanes advance the position too)
//     6 REBASE  [19:0] position of the next beat's lane 0 (a forward jump inside the quarter, e.g. a ring wrap)
// The index is not carried: the slab reconstructs it, so the select arithmetic sees exactly the native in_idx.
// Output vd (vr format: [0] rst_n, [1] valid, [513:2] data) to the VM through the station chain and the VM's ratio CDC
// (dsfd_r2l_vr_512x1__hsel: no w_rdy back) -> at most one word every PACE cycles (PACE 2: 0.6 G words/s into the
// 0.9 GHz reader, depth-4 FIFO never fills):
//     3 IDX     [319:0] 16 x 20-b index, [335:320] lane valid, [351:336] -inf flags, [353:352] qslot,
//               [354] last of the quarter                      (the sel out beats 1:1, quarter 0..3 in order)
//     4 DONE    [9:0] selected count, [10] overflow seen (two replays done), [15:11] sticky fault bits; also sent
//               once after reset (count 0).  A DONE / REP word leaves only when all four sel quarters are ready
//               (in_ready), so every beat the VM causes after receiving it is accepted: the lane needs no ready.
//     5 FAULT   [15:11] fault bits (emitted once when a sticky fault first rises; fail closed)
//     7 REP     [0] replay number: the sel overflowed its line memory; the VM must re-issue the whole segment
//               (all four scans, same beats) once per REP word (the native rep_req contract, routed through the VM)
// Fault bits: [11] overrun (beat while the sel quarter is not ready, or a beat with no open header), [12] format
// (unknown type, qslot claimed twice, position carry past 2^20), [13] k / tag differ between the segment's headers,
// [14] input link fault / beat while the lane is not live, [15] reserved.
// Margin-first: every used die input bit is captured at its pin, STG register stages carry it to the slab centre
// (the 5.27 mm block: <= ~380 um per stage), every die output bit leaves from a flop; reset is one synchronised
// net rst_s[1] (release multicycle 2, as the view SDCs).
// ---------------------------------------------------------------------------

// one input lane: pin register + STG transport stages + decode into the native beat
module ot_s81ph_sel_in #(
    parameter integer STG = 6
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [514:0] lane,
    // decoded, registered
    output reg          b_v,           // a score beat for the sel
    output reg  [15:0]  b_lv,
    output reg  [255:0] b_val,
    output reg  [319:0] b_idx,
    output reg          b_last,
    output reg  [1:0]   b_q,           // its qslot
    output reg          h_v,           // a header (k / tag / qslot)
    output reg  [9:0]   h_k,
    output reg  [7:0]   h_tag,
    output reg  [1:0]   h_q,
    output reg          act,           // a header is open on this lane
    output reg  [1:0]   act_q,
    output reg          e_fmt,         // pulses
    output reg          e_orphan,
    output reg          e_link
);
    // used bits: {fault, live, type 4, tag 8, data [272:0], valid} = 288
    localparam integer UW = 288;
    wire [UW-1:0] u = {lane[514], lane[513], lane[512:501], lane[273:1], lane[0]};
    reg  [UW-1:0] s [0:STG];
    integer i;
    always @(posedge clk) begin
        s[0] <= u;
        for (i = 1; i <= STG; i = i + 1) s[i] <= s[i-1];
    end
    wire [UW-1:0] w = s[STG];
    wire          v    = w[0];
    wire [272:0]  d    = w[273:1];
    wire [7:0]    tag  = w[281:274];
    wire [3:0]    t4   = w[285:282];
    reg  [19:0]   cur;
    wire [20:0]   nxt = {1'b0, cur} + 21'd16;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            b_v <= 1'b0; h_v <= 1'b0; act <= 1'b0; act_q <= 2'd0; cur <= 20'd0;
            e_fmt <= 1'b0; e_orphan <= 1'b0; e_link <= 1'b0;
        end else begin
            b_v <= 1'b0; h_v <= 1'b0; e_fmt <= 1'b0; e_orphan <= 1'b0;
            e_link <= w[UW-1] | (v & ~w[UW-2]);
            if (v) begin
                case (t4)
                    4'd1: begin
                        h_v <= 1'b1; act <= 1'b1; act_q <= d[31:30]; cur <= d[19:0];
                    end
                    4'd6: begin
                        if (!act) e_orphan <= 1'b1;
                        cur <= d[19:0];
                    end
                    4'd2: begin
                        if (!act) e_orphan <= 1'b1;
                        else begin
                            b_v <= 1'b1;
                            cur <= nxt[19:0];
                            if (nxt[20] && !d[272]) e_fmt <= 1'b1;
                            if (d[272]) act <= 1'b0;
                        end
                    end
                    default: e_fmt <= 1'b1;
                endcase
            end
        end
    end
    integer l;
    always @(posedge clk) begin
        b_lv <= d[271:256];
        b_val <= d[255:0];
        b_last <= d[272];
        b_q <= act_q;
`ifdef OT_S81PH_MUT1
        for (l = 0; l < 16; l = l + 1) b_idx[20*l +: 20] <= cur + l[19:0] + ((l == 15) ? 20'd1 : 20'd0);
`else
        for (l = 0; l < 16; l = l + 1) b_idx[20*l +: 20] <= cur + l[19:0];
`endif
        h_k <= d[29:20];
        h_tag <= tag;
        h_q <= d[31:30];
    end
endmodule

// one quarter's line memory: 256 lines x 16 lanes x 37 b = 592 b on three 256 x 256 1R1W macros (read-before-write,
// rd_out holds between reads: the sel's synchronous-read contract)
module ot_s81ph_sel_mem (
    input  wire         clk,
    input  wire         we,
    input  wire [7:0]   waddr,
    input  wire [591:0] wdata,
    input  wire         re,
    input  wire [7:0]   raddr,
    output wire [591:0] rdata
);
    wire [767:0] wd = {176'd0, wdata};
    wire [767:0] rd;
    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : g_m
        ot_sram_1r1w_256x256_m2_r2c2 u_m (.clk(clk), .r_ce_in(re), .r_addr_in(raddr), .rd_out(rd[256*g +: 256]),
            .w_ce_in(we), .w_addr_in(waddr), .wd_in(wd[256*g +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate
    assign rdata = rd[591:0];
endmodule

// the slab core: crossbar (input lane -> sel quarter by its header's qslot), the sel, the line memories, the quarter
// merger and the paced output word
module ot_s81ph_sel_core #(
    parameter integer STG  = 6,
    parameter integer PACE = 2
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [4*515-1:0] lanes,     // {NE, NW, SE, SW}
    output reg           o_v,
    output reg  [511:0]  o_d,
    output wire [15:0]   dbg_fault
);
    localparam integer Q = 4, W = 16, IW = 20, K = 512, AW = 8, KW = 10, EW = 37;
    wire [Q-1:0] b_v, b_last, h_v, act, e_fmt, e_orphan, e_link;
    wire [Q*16-1:0] b_lv;
    wire [Q*256-1:0] b_val;
    wire [Q*320-1:0] b_idx;
    wire [Q*2-1:0] b_q, h_q, act_q;
    wire [Q*10-1:0] h_k;
    wire [Q*8-1:0] h_tag;
    genvar g;
    generate for (g = 0; g < Q; g = g + 1) begin : g_in
        ot_s81ph_sel_in #(.STG(STG)) u_in (.clk(clk), .rst_n(rst_n), .lane(lanes[515*g +: 515]),
            .b_v(b_v[g]), .b_lv(b_lv[16*g +: 16]), .b_val(b_val[256*g +: 256]), .b_idx(b_idx[320*g +: 320]),
            .b_last(b_last[g]), .b_q(b_q[2*g +: 2]), .h_v(h_v[g]), .h_k(h_k[10*g +: 10]), .h_tag(h_tag[8*g +: 8]),
            .h_q(h_q[2*g +: 2]), .act(act[g]), .act_q(act_q[2*g +: 2]), .e_fmt(e_fmt[g]), .e_orphan(e_orphan[g]),
            .e_link(e_link[g]));
    end endgenerate

    // ---- crossbar into the sel ports (registered)
    reg  [Q-1:0]        x_v, x_last;
    reg  [Q*W-1:0]      x_lv;
    reg  [Q*W*16-1:0]   x_val;
    reg  [Q*W*IW-1:0]   x_idx;
    wire [Q-1:0]        s_ready;
    reg                 seg_open;
    reg  [KW-1:0]       seg_k;
    reg  [7:0]          seg_tag;
    reg  [4:0]          flt;
    reg                 e_coll, e_kt, e_over;
    integer q, s;
    // AND-OR crossbar (combinational), registered into the sel ports
    reg  [Q*W-1:0]      c_lv;
    reg  [Q*W*16-1:0]   c_val;
    reg  [Q*W*IW-1:0]   c_idx;
    reg  [Q-1:0]        c_last;
    always @(*) begin
        c_lv = 0; c_val = 0; c_idx = 0; c_last = 0;
        for (q = 0; q < Q; q = q + 1)
            for (s = 0; s < Q; s = s + 1)
`ifdef OT_S81PH_MUT2
                if (b_v[s] && s == q) begin
`else
                if (b_v[s] && b_q[2*s +: 2] == q[1:0]) begin
`endif
                    c_lv[W*q +: W] = c_lv[W*q +: W] | b_lv[16*s +: 16];
                    c_val[256*q +: 256] = c_val[256*q +: 256] | b_val[256*s +: 256];
                    c_idx[320*q +: 320] = c_idx[320*q +: 320] | b_idx[320*s +: 320];
                    c_last[q] = c_last[q] | b_last[s];
                end
    end
    always @(posedge clk) begin
        x_lv <= c_lv; x_val <= c_val; x_idx <= c_idx; x_last <= c_last;
    end
    reg [Q-1:0] xv_n;
    always @(*) begin
        for (q = 0; q < Q; q = q + 1) begin
            xv_n[q] = 1'b0;
            for (s = 0; s < Q; s = s + 1)
`ifdef OT_S81PH_MUT2
                if (b_v[s] && s == q) xv_n[q] = 1'b1;
`else
                if (b_v[s] && b_q[2*s +: 2] == q[1:0]) xv_n[q] = 1'b1;
`endif
        end
    end
    // qslot collision: two open lanes claim one quarter
    reg coll_n;
    always @(*) begin
        coll_n = 1'b0;
        for (s = 0; s < Q; s = s + 1)
            for (q = s + 1; q < Q; q = q + 1)
                if (act[s] && act[q] && act_q[2*s +: 2] == act_q[2*q +: 2]) coll_n = 1'b1;
    end

    // ---- the select (unchanged)
    wire [Q-1:0]        o_valid, o_last;
    reg  [Q-1:0]        o_ready;
    wire [Q*W-1:0]      o_lv, o_ninf;
    wire [Q*W*16-1:0]   o_val;
    wire [Q*W*IW-1:0]   o_idx;
    wire [Q-1:0]        m_we, m_re;
    wire [Q*AW-1:0]     m_wa, m_ra;
    wire [Q*W*EW-1:0]   m_wd, m_rd;
    wire                rep_req, ovf, busy;
    ot_hdc_v41x_sel #(.Q(Q), .W(W), .IW(IW), .K(K), .AW(AW)) u_sel (.clk(clk), .rst_n(rst_n),
        .in_valid(x_v), .in_ready(s_ready), .in_last(x_last), .in_lv(x_lv), .in_val(x_val), .in_idx(x_idx),
        .in_k(seg_k), .out_valid(o_valid), .out_ready(o_ready), .out_last(o_last), .out_lv(o_lv), .out_val(o_val),
        .out_idx(o_idx), .out_ninf(o_ninf), .mem_we(m_we), .mem_waddr(m_wa), .mem_wdata(m_wd), .mem_re(m_re),
        .mem_raddr(m_ra), .mem_rdata(m_rd), .rep_req(rep_req), .ovf(ovf), .busy(busy), .stats());
    generate for (g = 0; g < Q; g = g + 1) begin : g_mem
        ot_s81ph_sel_mem u_mem (.clk(clk), .we(m_we[g]), .waddr(m_wa[AW*g +: AW]), .wdata(m_wd[W*EW*g +: W*EW]),
            .re(m_re[g]), .raddr(m_ra[AW*g +: AW]), .rdata(m_rd[W*EW*g +: W*EW]));
    end endgenerate

    // ---- segment state, faults
    reg        ovf_seen;
    reg  [1:0] rep_pend;
    reg        rep_n;
    reg  [1:0] cq;           // quarter being drained
    reg        done_pend;
    reg  [9:0] cnt;
    reg  [4:0] flt_rep;      // fault bits already reported
    reg  [$clog2(PACE+1)-1:0] pc;
    wire       slot = (pc == 0);
    wire [4:0] flt_new = flt & ~flt_rep;
    // popcount of a beat's lane valids
    function automatic [4:0] pop16(input [15:0] x);
        integer j; begin pop16 = 0; for (j = 0; j < 16; j = j + 1) pop16 = pop16 + x[j]; end
    endfunction
    always @(*) begin
        o_ready = {Q{1'b0}};
        if (slot && !(|flt_new) && rep_pend == 0 && !done_pend)
`ifdef OT_S81PH_MUT3
            o_ready[cq ^ 2'd1] = 1'b1;
`else
            o_ready[cq] = 1'b1;
`endif
    end
    wire take = |(o_valid & o_ready);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            x_v <= {Q{1'b0}}; seg_open <= 1'b0; seg_k <= {KW{1'b0}}; seg_tag <= 8'd0; flt <= 5'd0;
            ovf_seen <= 1'b0; rep_pend <= 2'd0; rep_n <= 1'b0; cq <= 2'd0; done_pend <= 1'b1; cnt <= 10'd0;
            flt_rep <= 5'd0; pc <= 0; o_v <= 1'b0; o_d <= 512'd0; e_coll <= 1'b0; e_kt <= 1'b0; e_over <= 1'b0;
        end else begin
            // beats into the sel: a beat on a quarter that is not ready is an overrun (dropped, fail closed)
            x_v <= xv_n;
            e_over <= |(x_v & ~s_ready) | (|e_orphan);
            e_coll <= coll_n;
            // headers: the first opens the segment and fixes k / tag; every later one must agree
            e_kt <= 1'b0;
            begin : hdr
                integer t; reg op; reg [KW-1:0] kk; reg [7:0] tt;
                op = seg_open; kk = seg_k; tt = seg_tag;
                for (t = 0; t < Q; t = t + 1)
                    if (h_v[t]) begin
                        if (!op) begin op = 1'b1; kk = h_k[10*t +: 10]; tt = h_tag[8*t +: 8]; end
                        else if (h_k[10*t +: 10] != kk || h_tag[8*t +: 8] != tt) e_kt <= 1'b1;
                    end
                seg_open <= op; seg_k <= kk; seg_tag <= tt;
            end
            flt <= flt | {1'b0, |e_link, e_kt, (|e_fmt) | e_coll, e_over};
            if (ovf) ovf_seen <= 1'b1;
            // output word (one every PACE cycles): FAULT > REP > IDX > DONE
            pc <= (pc == PACE - 1) ? 0 : pc + 1'b1;
            o_v <= 1'b0;
            if (rep_req) rep_pend <= rep_pend + 1'b1;
            if (slot) begin
                if (|flt_new) begin
                    o_v <= 1'b1; o_d <= {4'd5, seg_tag, 484'd0, flt, 11'd0};
                    flt_rep <= flt;
                end else if (rep_pend != 0 && &s_ready) begin
                    o_v <= 1'b1; o_d <= {4'd7, seg_tag, 499'd0, rep_n};
                    rep_n <= ~rep_n;
                    rep_pend <= rep_pend - 1'b1 + (rep_req ? 1'b1 : 1'b0);
                end else if (take) begin
                    o_v <= 1'b1;
                    o_d <= {4'd3, seg_tag, 145'd0, o_last[cq], cq, o_ninf[W*cq +: W], o_lv[W*cq +: W], o_idx[W*IW*cq +: W*IW]};
                    cnt <= cnt + pop16(o_lv[W*cq +: W]);
                    if (o_last[cq]) begin
                        cq <= cq + 1'b1;
                        if (cq == 2'd3) done_pend <= 1'b1;
                    end
                end else if (done_pend && &s_ready) begin
                    o_v <= 1'b1; o_d <= {4'd4, seg_tag, 484'd0, flt, ovf_seen, cnt};
                    done_pend <= 1'b0; cnt <= 10'd0; ovf_seen <= 1'b0; seg_open <= 1'b0; rep_n <= 1'b0;
                end
            end
        end
    end
    assign dbg_fault = {11'd0, flt};
endmodule
