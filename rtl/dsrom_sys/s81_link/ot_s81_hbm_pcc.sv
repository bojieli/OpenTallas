`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_hbm_pcc (s81-die-rtl-bind 2026-10-14, die item F10 / HBM): the per-pseudo-channel HBM3E MEMORY CONTROLLER of
// the S81 die's HBM macro -- real RTL (owner rule 08:05: the PHY's analog core may be a behavioural model, its digital
// controller layer may not).  It replaces the controller half of the 'PHY + controller abstract'
// ot_hbm3e_phy_v41x_aw30_e8p5 (whose functional stand-in rtl/chip/ot_chip_v41x_hbm3e_phy.sv is a simulation model).
//
// Host side (the macro's K / W port, unchanged protocol): request {addr (sector = 32 B), len sectors, tag, we, wdata,
// wstrb} valid / ready (QD-deep queue); response per read sector {tag, beat = sector index, data} valid / ready, in
// request order; wr_done pulse per write request (last sector's data on the DFI).
// DRAM side (DFI-like, to the PHY + device model): one command a cycle {ACT row | RD col | WR col + wdata/wstrb | PRE |
// REFpb} with bank; read data returns tCL later (the controller tracks it by issue order).
// Address map (sector s): col = s[4:0] (1 KB page = 32 sectors), bank = s[8:5] (4 bank groups x 4), row = s[AW-1:9].
// Policy: in-order, open page; per-bank refresh: one REFpb every TREFI_PB cycles, round robin over the 16 banks (the
// bank is precharged first; a refresh that is due takes priority over the next access).
// Timing (controller cycles, parameters): tRCD, tRP, tRAS, tRTP, tWR (after the write data), tCCD_S / tCCD_L (other /
// same bank group), tRRD, tFAW (4 ACTs), tWTR / tRTW turnarounds, tRFCpb, tCL / tWL.  A read is issued only with room
// in the response queue for it (reads in flight + queued <= RQD): kr_rdy back-pressure never drops data.
// MUT 1: RD/WR one cycle inside tRCD after ACT -- the device model's timing checker must flag it.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_hbm_pcc #(
    parameter integer AW = 30, LENW = 4, TAGW = 17, BEATW = 4, QD = 8, RQD = 32,
    parameter integer TRCD = 14, TRP = 14, TRAS = 33, TRTP = 5, TWR = 16, TCCDS = 2, TCCDL = 4, TRRD = 4, TFAW = 16,
    parameter integer TWTR = 8, TRTW = 6, TRFC = 160, TREFI_PB = 240, TCL = 14, TWL = 6,
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              q_v,
    output wire              q_rdy,
    input  wire [AW-1:0]     q_addr,
    input  wire [LENW-1:0]   q_len,
    input  wire [TAGW-1:0]   q_tag,
    input  wire              q_we,
    input  wire [255:0]      q_wdata,
    input  wire [31:0]       q_wstrb,
    output reg               wr_done,
    output wire              r_v,
    input  wire              r_rdy,
    output wire [TAGW-1:0]   r_tag,
    output wire [BEATW-1:0]  r_beat,
    output wire [255:0]      r_data,
    // DFI-like command / data to the PHY + device
    output reg  [2:0]        d_cmd,       // 0 NOP, 1 ACT, 2 RD, 3 WR, 4 PRE, 5 REFpb
    output reg  [3:0]        d_bank,
    output reg  [AW-10:0]    d_row,
    output reg  [4:0]        d_col,
    output reg  [255:0]      d_wdata,
    output reg  [31:0]       d_wstrb,
    input  wire              d_rv,        // read data valid (tCL after RD)
    input  wire [255:0]      d_rdata,
    output reg  [31:0]       n_ref,
    output reg  [31:0]       n_rd
);
    localparam integer RW = AW - 9, QW = AW + LENW + TAGW + 1 + 256 + 32;
    localparam integer TRCD_E = (MUT == 1) ? TRCD - 2 : TRCD;     // (the timers are one cycle conservative)
    // ---------------- request queue
    reg  [QW-1:0] rq [0:QD-1];
    reg  [$clog2(QD):0] rn; reg [$clog2(QD)-1:0] rw, rr;
    wire pop;
    assign q_rdy = rn < QD;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rn <= 0; rw <= 0; rr <= 0; end
        else begin
            if (q_v && q_rdy) begin rq[rw] <= {q_addr, q_len, q_tag, q_we, q_wdata, q_wstrb}; rw <= rw + 1'b1; end
            if (pop) rr <= rr + 1'b1;
            rn <= rn + (q_v && q_rdy) - pop;
        end
    wire [QW-1:0] h = rq[rr];
    wire          hv = rn != 0;
    wire [AW-1:0] h_addr = h[QW-1 -: AW];
    wire [LENW-1:0] h_len = h[QW-1-AW -: LENW];
    wire [TAGW-1:0] h_tag = h[QW-1-AW-LENW -: TAGW];
    wire          h_we = h[288];
    wire [255:0]  h_wd = h[287:32];
    wire [31:0]   h_ws = h[31:0];
    reg  [LENW-1:0] si;                   // sector index within the head request
    wire [AW-1:0] sa = h_addr + si;
    wire [3:0]    sb = sa[8:5];
    wire [RW-1:0] sr = sa[AW-1:9];
    wire [4:0]    sc = sa[4:0];
    // ---------------- bank state + timers (count down to 0 = allowed)
    reg          bo [0:15]; reg [RW-1:0] brow [0:15];
    reg  [7:0]   t_act [0:15], t_cas [0:15], t_pre [0:15];
    reg  [3:0]   t_ccd_s; reg [3:0] t_ccd_l [0:3]; reg [3:0] t_rrd; reg [4:0] t_wtr, t_rtw;
    reg  [7:0]   faw [0:3];               // cycles since the last 4 ACTs (saturating)
    wire         faw_ok = faw[3] >= TFAW;
    // ---------------- refresh scheduler
    reg  [9:0]   ref_t; reg ref_due; reg [3:0] ref_b;
    // ---------------- read return tracking
    reg  [TAGW+BEATW-1:0] fl [0:RQD-1]; reg [$clog2(RQD):0] fln; reg [$clog2(RQD)-1:0] flw, flr;
    reg  [$clog2(RQD):0] rcnt;            // response queue occupancy
    wire rq_room = (fln + rcnt) < RQD;
    // ---------------- command decision
    reg [2:0] cmd; reg [3:0] cb;
    wire want_ref = ref_due;
    wire hit = bo[sb] && brow[sb] == sr;
    always @* begin
        cmd = 3'd0; cb = sb;
        if (want_ref) begin
            cb = ref_b;
            if (bo[ref_b]) begin if (t_pre[ref_b] == 0) cmd = 3'd4; end
            else if (t_act[ref_b] == 0) cmd = 3'd5;
        end else if (hv) begin
            if (hit) begin
                if (t_cas[sb] == 0 && t_ccd_s == 0 && t_ccd_l[sb[3:2]] == 0) begin
                    if (h_we && t_rtw == 0) cmd = 3'd3;
                    else if (!h_we && t_wtr == 0 && rq_room) cmd = 3'd2;
                end
            end else if (bo[sb]) begin
                if (t_pre[sb] == 0) cmd = 3'd4;
            end else if (t_act[sb] == 0 && t_rrd == 0 && faw_ok) cmd = 3'd1;
        end
    end
    wire cas = (cmd == 3'd2 || cmd == 3'd3) && !want_ref;
    wire last_sec = (si == h_len - 1'b1);
    assign pop = cas && last_sec;
    integer i;
    function automatic [7:0] mx(input [7:0] a, input integer b); mx = (a > b) ? a : b[7:0]; endfunction
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (i = 0; i < 16; i = i + 1) begin bo[i] <= 1'b0; t_act[i] <= 0; t_cas[i] <= 0; t_pre[i] <= 0; end
            for (i = 0; i < 4; i = i + 1) begin t_ccd_l[i] <= 0; faw[i] <= 8'hFF; end
            t_ccd_s <= 0; t_rrd <= 0; t_wtr <= 0; t_rtw <= 0; si <= 0;
            ref_t <= 0; ref_due <= 1'b0; ref_b <= 0; d_cmd <= 0; wr_done <= 1'b0; n_ref <= 0; n_rd <= 0;
        end else begin
            // timers
            for (i = 0; i < 16; i = i + 1) begin
                if (t_act[i] != 0) t_act[i] <= t_act[i] - 1'b1;
                if (t_cas[i] != 0) t_cas[i] <= t_cas[i] - 1'b1;
                if (t_pre[i] != 0) t_pre[i] <= t_pre[i] - 1'b1;
            end
            for (i = 0; i < 4; i = i + 1) if (t_ccd_l[i] != 0) t_ccd_l[i] <= t_ccd_l[i] - 1'b1;
            for (i = 0; i < 4; i = i + 1) if (faw[i] != 8'hFF) faw[i] <= faw[i] + 1'b1;
            if (t_ccd_s != 0) t_ccd_s <= t_ccd_s - 1'b1;
            if (t_rrd != 0) t_rrd <= t_rrd - 1'b1;
            if (t_wtr != 0) t_wtr <= t_wtr - 1'b1;
            if (t_rtw != 0) t_rtw <= t_rtw - 1'b1;
            ref_t <= ref_t + 1'b1;
            if (ref_t == TREFI_PB - 1) begin ref_t <= 0; ref_due <= 1'b1; end
            wr_done <= 1'b0;
            d_cmd <= cmd; d_bank <= cb; d_row <= sr; d_col <= sc; d_wdata <= h_wd; d_wstrb <= h_ws;
            case (cmd)
                3'd1: begin   // ACT
                    bo[cb] <= 1'b1; brow[cb] <= sr;
                    t_cas[cb] <= TRCD_E; t_pre[cb] <= TRAS; t_rrd <= TRRD;
                    faw[0] <= 8'd1; faw[1] <= faw[0]; faw[2] <= faw[1]; faw[3] <= faw[2];
                end
                3'd2: begin   // RD
                    t_ccd_s <= TCCDS; t_ccd_l[cb[3:2]] <= TCCDL; t_pre[cb] <= mx(t_pre[cb], TRTP); t_rtw <= TRTW;
                    si <= last_sec ? {LENW{1'b0}} : si + 1'b1; n_rd <= n_rd + 1;
                end
                3'd3: begin   // WR
                    t_ccd_s <= TCCDS; t_ccd_l[cb[3:2]] <= TCCDL; t_pre[cb] <= mx(t_pre[cb], TWL + 2 + TWR);
                    t_wtr <= TWL + 2 + TWTR;
                    si <= last_sec ? {LENW{1'b0}} : si + 1'b1;
                    if (last_sec) wr_done <= 1'b1;
                end
                3'd4: begin   // PRE
                    bo[cb] <= 1'b0; t_act[cb] <= TRP;
                end
                3'd5: begin   // REFpb
                    t_act[cb] <= TRFC; ref_due <= 1'b0; ref_b <= ref_b + 1'b1; n_ref <= n_ref + 1;
                end
                default: ;
            endcase
        end
    // ---------------- read return: issue-order tags, response queue
    reg  [TAGW+BEATW+256-1:0] rsp [0:RQD-1]; reg [$clog2(RQD)-1:0] rsw, rsr;
    wire rpop = r_v && r_rdy;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fln <= 0; flw <= 0; flr <= 0; rcnt <= 0; rsw <= 0; rsr <= 0; end
        else begin
            if (cmd == 3'd2) begin fl[flw] <= {h_tag, BEATW'(si)}; flw <= flw + 1'b1; end
            if (d_rv) begin rsp[rsw] <= {fl[flr], d_rdata}; rsw <= rsw + 1'b1; flr <= flr + 1'b1; end
            if (rpop) rsr <= rsr + 1'b1;
            fln <= fln + (cmd == 3'd2) - d_rv;
            rcnt <= rcnt + d_rv - rpop;
        end
    assign r_v = rcnt != 0;
    assign {r_tag, r_beat, r_data} = rsp[rsr];
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81_hbm3e_dev_bm: BEHAVIOURAL HBM3E PHY + DRAM pseudo-channel (the analog PHY / device the owner rule allows as a
// model): executes the DFI commands, returns read data TCL cycles after RD, keeps the array (sparse, simulation), and
// CHECKS the JEDEC-style timing the controller must keep (sticky 'viol' + the first violation code):
//   1 RD/WR to a closed bank or another row, 2 tRCD, 3 tRP / tRFC (ACT too early), 4 tRAS / tRTP / tWR (PRE too early),
//   5 tCCD, 6 tRRD, 7 tFAW, 8 ACT to an open bank, 9 REF to an open bank.  Not a synthesis target.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_hbm3e_dev_bm #(
    parameter integer AW = 30, TRCD = 14, TRP = 14, TRAS = 33, TRTP = 5, TWR = 16, TCCDS = 2, TCCDL = 4, TRRD = 4,
    parameter integer TFAW = 16, TRFC = 160, TCL = 14, TWL = 6
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [2:0]    d_cmd,
    input  wire [3:0]    d_bank,
    input  wire [AW-10:0] d_row,
    input  wire [4:0]    d_col,
    input  wire [255:0]  d_wdata,
    input  wire [31:0]   d_wstrb,
    output reg           d_rv,
    output reg  [255:0]  d_rdata,
    output reg           viol,
    output reg  [3:0]    viol_code
);
    reg [255:0] mem [longint];
    longint now;
    longint a_act [0:15], a_pre [0:15], a_cas [0:15], a_rd [0:15], a_wr [0:15], a_ref [0:15];
    longint l_cas, l_cas_bg [0:3], l_act, acts [0:3];
    reg op [0:15]; reg [AW-10:0] orow [0:15];
    reg [255:0] pipe_d [0:63]; reg pipe_v [0:63];
    integer i;
    task automatic bad(input [3:0] c); begin if (!viol) viol_code <= c; viol <= 1'b1; end endtask
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            now = 0; viol <= 1'b0; viol_code <= 0; d_rv <= 1'b0; l_cas = -100; l_act = -100;
            for (i = 0; i < 16; i = i + 1) begin op[i] = 1'b0; a_act[i] = -1000; a_pre[i] = -1000; a_rd[i] = -1000; a_wr[i] = -1000; a_ref[i] = -1000; end
            for (i = 0; i < 4; i = i + 1) begin l_cas_bg[i] = -100; acts[i] = -1000; end
            for (i = 0; i < 64; i = i + 1) pipe_v[i] = 1'b0;
        end else begin : step
            longint key; reg rd_new; reg [255:0] rd_dat;
            now = now + 1; rd_new = 1'b0; rd_dat = 256'd0;
            key = {d_row, d_bank, d_col};
            case (d_cmd)
                3'd1: begin
                    if (op[d_bank]) bad(8);
                    if (now - a_pre[d_bank] < TRP || now - a_ref[d_bank] < TRFC) bad(3);
                    if (now - l_act < TRRD) bad(6);
                    if (now - acts[3] < TFAW) bad(7);
                    op[d_bank] = 1'b1; orow[d_bank] = d_row; a_act[d_bank] = now; l_act = now;
                    acts[3] = acts[2]; acts[2] = acts[1]; acts[1] = acts[0]; acts[0] = now;
                end
                3'd2, 3'd3: begin
                    if (!op[d_bank] || orow[d_bank] != d_row) bad(1);
                    if (now - a_act[d_bank] < TRCD) bad(2);
                    if (now - l_cas < TCCDS || now - l_cas_bg[d_bank[3:2]] < TCCDL) bad(5);
                    l_cas = now; l_cas_bg[d_bank[3:2]] = now;
                    if (d_cmd == 3'd2) begin
                        a_rd[d_bank] = now; rd_new = 1'b1; rd_dat = mem.exists(key) ? mem[key] : 256'd0;
                    end else begin : wr
                        reg [255:0] o; integer b;
                        a_wr[d_bank] = now;
                        o = mem.exists(key) ? mem[key] : 256'd0;
                        for (b = 0; b < 32; b = b + 1) if (d_wstrb[b]) o[8*b +: 8] = d_wdata[8*b +: 8];
                        mem[key] = o;
                    end
                end
                3'd4: begin
                    if (now - a_act[d_bank] < TRAS || now - a_rd[d_bank] < TRTP || now - a_wr[d_bank] < TWL + 2 + TWR) bad(4);
                    op[d_bank] = 1'b0; a_pre[d_bank] = now;
                end
                3'd5: begin
                    if (op[d_bank]) bad(9);
                    if (now - a_pre[d_bank] < TRP || now - a_ref[d_bank] < TRFC) bad(3);
                    a_ref[d_bank] = now;
                end
                default: ;
            endcase
            // read data TCL cycles after RD
            d_rv <= pipe_v[TCL - 1]; d_rdata <= pipe_d[TCL - 1];
            for (i = 63; i > 0; i = i - 1) begin pipe_v[i] = pipe_v[i - 1]; pipe_d[i] = pipe_d[i - 1]; end
            pipe_v[0] = rd_new; pipe_d[0] = rd_dat;
        end
endmodule
