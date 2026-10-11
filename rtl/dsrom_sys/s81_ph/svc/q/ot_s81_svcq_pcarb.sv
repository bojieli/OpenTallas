`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// CLAUDE s81-svcq-1011: per-pseudo-channel HBM arbiter of an S81 scan-service slab, between the slab's engines and
// the 32 dsfd_svc_pc tiles (-> dsfd_ctrl_pc -> PHY K port).  PC side = the ctrl contract (results/rtl/s81_ph_20261006/
// ctrl/contract.json): request word rq 341 b {[340:85] wdata, [84:53] wstrb, [52:36] tag 17, [35:32] len, [31:2] sector
// address (every sector of a read in this PC), [1] we, [0] v}, DQ request credits per PC returned on rk pulses,
// responses {rv, beat, tag, data} VALID-ONLY (taken the cycle presented), write completions wd (untagged pulses).
// Engine side, three client kinds (all valid/ready, the ot_hdc_v41x_idx_hbm per-PC protocol):
//   A  per-PC port (index key stream ot_hdc_v41x_idx_kstream_ring): reads, 16-b tag   -> tag {0, a_tag[15:0]}
//   B  per-PC port (WINDOW stream ot_dsrom_window_stream_la_s81): reads, 12-b tag      -> tag {1, 4'd0, b_tag}
//   G  NG routed ports (window K-port writer/reader, owned-row fetch): reads and one-sector masked writes, 12-b tag,
//      steered to pc_of(addr) = ((s >> 2) ^ (s >> 7) ^ (s >> 12)) mod 32 (the stack model / PHY map)  -> {1, k+1, tag}
// Per PC: round robin over the 2 + NG sources presenting a request for this PC; a request issues when a credit is
// held and, for a read, LANDING room for its len beats is RESERVED (resv + len <= DR): the response FIFO (DR beats)
// can then never overflow although the PC side has no back-pressure, while every client keeps its own ready.  The
// request leaves from a flop (rq), one per PC per cycle.  Responses are routed by tag; G ports take one beat a cycle
// (round robin over the PCs whose FIFO head is theirs).  Writes: wd pulses retire a per-PC FIFO of writer ids (a PC
// completes writes in order) and are re-issued as one g_wr_done pulse per port per cycle (counter).
// Checks (sticky fault): rv into a full FIFO, wd with no write outstanding, response tag of no client, credit
// overflow, a G read whose sectors leave its PC.
// ---------------------------------------------------------------------------
module ot_s81_svcq_pcarb #(
    parameter integer NPC = 32,
    parameter integer NG = 12,
    parameter integer DQ = 8,
    parameter integer DR = 64,
    parameter integer AW = 30
) (
    input  wire                 clk,
    input  wire                 rst_n,
    // A: per-PC (index stream)
    input  wire [NPC-1:0]       a_v,
    output wire [NPC-1:0]       a_rdy,
    input  wire [NPC*AW-1:0]    a_addr,
    input  wire [NPC*4-1:0]     a_len,
    input  wire [NPC*16-1:0]    a_tag,
    output wire [NPC-1:0]       a_rsp_v,
    input  wire [NPC-1:0]       a_rsp_rdy,
    output wire [NPC*16-1:0]    a_rsp_tag,
    output wire [NPC*4-1:0]     a_rsp_beat,
    output wire [NPC*256-1:0]   a_rsp_data,
    // B: per-PC (window stream)
    input  wire [NPC-1:0]       b_v,
    output wire [NPC-1:0]       b_rdy,
    input  wire [NPC*AW-1:0]    b_addr,
    input  wire [NPC*4-1:0]     b_len,
    input  wire [NPC*12-1:0]    b_tag,
    output wire [NPC-1:0]       b_rsp_v,
    input  wire [NPC-1:0]       b_rsp_rdy,
    output wire [NPC*12-1:0]    b_rsp_tag,
    output wire [NPC*4-1:0]     b_rsp_beat,
    output wire [NPC*256-1:0]   b_rsp_data,
    // G: routed ports
    input  wire [NG-1:0]        g_v,
    output wire [NG-1:0]        g_rdy,
    input  wire [NG*AW-1:0]     g_addr,
    input  wire [NG*4-1:0]      g_len,
    input  wire [NG*12-1:0]     g_tag,
    input  wire [NG-1:0]        g_we,
    input  wire [NG*256-1:0]    g_wdata,
    input  wire [NG*32-1:0]     g_wstrb,
    output reg  [NG-1:0]        g_wr_done,
    output wire [NG-1:0]        g_rsp_v,
    input  wire [NG-1:0]        g_rsp_rdy,
    output wire [NG*12-1:0]     g_rsp_tag,
    output wire [NG*4-1:0]      g_rsp_beat,
    output wire [NG*256-1:0]    g_rsp_data,
    // PC side
    output reg  [NPC*341-1:0]   rq,
    input  wire [NPC-1:0]       rk,
    input  wire [NPC-1:0]       rv,
    input  wire [NPC*17-1:0]    r_tag,
    input  wire [NPC*4-1:0]     r_beat,
    input  wire [NPC*256-1:0]   r_data,
    input  wire [NPC-1:0]       wd,
    output reg                  fault,
    output reg  [4:0]           fault_code
);
    localparam integer NS = 2 + NG;                 // sources per PC
    localparam integer SW = $clog2(NS);
    localparam integer RW = $clog2(DR);
    localparam integer CW = $clog2(DQ + 1);
    function automatic [4:0] pc_of(input [AW-1:0] s);
        pc_of = 5'((s >> 2) ^ (s >> 7) ^ (s >> 12));
    endfunction
    // ---------------- G steering ----------------
    wire [4:0] g_pc [0:NG-1];
    wire [NG-1:0] g_bad;
    genvar gk;
    generate for (gk = 0; gk < NG; gk = gk + 1) begin : g_st
        wire [AW-1:0] a0 = g_addr[gk*AW +: AW];
        wire [AW-1:0] al = a0 + AW'(g_len[gk*4 +: 4]) - 1'b1;
        assign g_pc[gk] = pc_of(a0);
        assign g_bad[gk] = g_v[gk] && !g_we[gk] && (g_len[gk*4 +: 4] == 0 || pc_of(al) != pc_of(a0) || (a0 >> 2) != (al >> 2));
    end endgenerate

    // ---------------- per-PC issue ----------------
    reg [CW-1:0] cred [0:NPC-1];
    reg [RW:0] resv [0:NPC-1];
    reg [SW-1:0] rr [0:NPC-1];
    reg [NS-1:0] want [0:NPC-1];
    reg [NS-1:0] gnt [0:NPC-1];
    reg [NPC-1:0] pc_go;
    reg [SW-1:0] pick [0:NPC-1];
    integer p, s, k, idx;
    reg found;
    function automatic [3:0] src_len(input integer pp, input integer ss);
        if (ss == 0) src_len = a_len[pp*4 +: 4];
        else if (ss == 1) src_len = b_len[pp*4 +: 4];
        else src_len = g_len[(ss-2)*4 +: 4];
    endfunction
    function automatic bit src_we(input integer ss);
        src_we = (ss >= 2) ? g_we[ss-2] : 1'b0;
    endfunction
    always @(*) begin
        for (p = 0; p < NPC; p = p + 1) begin
            want[p] = 0;
            want[p][0] = a_v[p];
            want[p][1] = b_v[p];
            for (k = 0; k < NG; k = k + 1) want[p][2+k] = g_v[k] && !g_bad[k] && g_pc[k] == 5'(p);
            gnt[p] = 0; found = 1'b0; pick[p] = 0;
            for (s = 0; s < NS; s = s + 1) begin
                idx = (32'(rr[p]) + s) % NS;
                if (!found && want[p][idx] && cred[p] != 0 &&
                    (src_we(idx) || 32'(resv[p]) + 32'(src_len(p, idx)) <= DR)) begin
                    found = 1'b1; pick[p] = SW'(idx); gnt[p][idx] = 1'b1;
                end
            end
            pc_go[p] = found;
        end
    end
    genvar gp;
    generate for (gp = 0; gp < NPC; gp = gp + 1) begin : g_ar
        assign a_rdy[gp] = gnt[gp][0];
        assign b_rdy[gp] = gnt[gp][1];
    end endgenerate
    reg [NG-1:0] g_rdy_c;
    always @(*) begin
        g_rdy_c = 0;
        for (k = 0; k < NG; k = k + 1) g_rdy_c[k] = gnt[g_pc[k]][2+k];
    end
    assign g_rdy = g_rdy_c;

    // ---------------- per-PC landing FIFO + writer-id FIFO ----------------
    reg [16:0] lq_tag [0:NPC-1][0:DR-1];
    reg [3:0] lq_beat [0:NPC-1][0:DR-1];
    reg [255:0] lq_dat [0:NPC-1][0:DR-1];
    reg [RW:0] lw [0:NPC-1], lr [0:NPC-1];
    reg [3:0] wq [0:NPC-1][0:DQ-1];
    reg [CW-1:0] wqw [0:NPC-1], wqr [0:NPC-1];
    wire [NPC-1:0] h_v;
    wire [16:0] h_tag [0:NPC-1];
    generate for (gp = 0; gp < NPC; gp = gp + 1) begin : g_h
        assign h_v[gp] = lw[gp] != lr[gp];
        assign h_tag[gp] = lq_tag[gp][lr[gp][RW-1:0]];
        assign a_rsp_v[gp] = h_v[gp] && !h_tag[gp][16];
        assign a_rsp_tag[gp*16 +: 16] = h_tag[gp][15:0];
        assign a_rsp_beat[gp*4 +: 4] = lq_beat[gp][lr[gp][RW-1:0]];
        assign a_rsp_data[gp*256 +: 256] = lq_dat[gp][lr[gp][RW-1:0]];
        assign b_rsp_v[gp] = h_v[gp] && h_tag[gp][16] && h_tag[gp][15:12] == 4'd0;
        assign b_rsp_tag[gp*12 +: 12] = h_tag[gp][11:0];
        assign b_rsp_beat[gp*4 +: 4] = lq_beat[gp][lr[gp][RW-1:0]];
        assign b_rsp_data[gp*256 +: 256] = lq_dat[gp][lr[gp][RW-1:0]];
    end endgenerate
    // G response select: per port, round robin over the PCs whose head is theirs
    reg [4:0] grr [0:NG-1];
    reg [NG-1:0] gsel_v;
    reg [4:0] gsel [0:NG-1];
    reg [NPC-1:0] gpop;
    always @(*) begin
        gpop = 0;
        for (k = 0; k < NG; k = k + 1) begin
            gsel_v[k] = 1'b0; gsel[k] = 0;
            for (s = 0; s < NPC; s = s + 1) begin
                idx = (32'(grr[k]) + s) % NPC;
                if (!gsel_v[k] && h_v[idx] && h_tag[idx][16] && h_tag[idx][15:12] == 4'(k + 1)) begin
                    gsel_v[k] = 1'b1; gsel[k] = 5'(idx);
                end
            end
            if (gsel_v[k] && g_rsp_rdy[k]) gpop[gsel[k]] = 1'b1;
        end
    end
    generate for (gk = 0; gk < NG; gk = gk + 1) begin : g_gr
        assign g_rsp_v[gk] = gsel_v[gk];
        assign g_rsp_tag[gk*12 +: 12] = h_tag[gsel[gk]][11:0];
        assign g_rsp_beat[gk*4 +: 4] = lq_beat[gsel[gk]][lr[gsel[gk]][RW-1:0]];
        assign g_rsp_data[gk*256 +: 256] = lq_dat[gsel[gk]][lr[gsel[gk]][RW-1:0]];
    end endgenerate
    wire [NPC-1:0] pop = (a_rsp_v & a_rsp_rdy) | (b_rsp_v & b_rsp_rdy) | gpop;

    // ---------------- write-done re-issue counters ----------------
    reg [4:0] wdc [0:NG-1];
    reg [5:0] wd_add [0:NG-1];
    always @(*) begin
        for (k = 0; k < NG; k = k + 1) wd_add[k] = 0;
        for (p = 0; p < NPC; p = p + 1)
            if (wd[p] && wqw[p] != wqr[p]) wd_add[wq[p][wqr[p] % DQ]] = wd_add[wq[p][wqr[p] % DQ]] + 1'b1;
    end

    reg [16:0] tg; reg [AW-1:0] ad; reg [3:0] ln;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (p = 0; p < NPC; p = p + 1) begin
                cred[p] <= CW'(DQ); resv[p] <= 0; rr[p] <= 0; lw[p] <= 0; lr[p] <= 0; wqw[p] <= 0; wqr[p] <= 0;
                rq[p*341] <= 1'b0;
            end
            for (k = 0; k < NG; k = k + 1) begin grr[k] <= 0; wdc[k] <= 0; end
            g_wr_done <= 0; fault <= 0; fault_code <= 0;
        end else begin
            for (p = 0; p < NPC; p = p + 1) begin
                // issue
                rq[p*341] <= pc_go[p];
                if (pc_go[p]) begin
                    s = 32'(pick[p]);
                    if (s == 0) begin tg = {1'b0, a_tag[p*16 +: 16]}; ad = a_addr[p*AW +: AW]; ln = a_len[p*4 +: 4]; end
`ifdef SVCQS_MUT_BTAG
                    else if (s == 1) begin tg = {1'b1, 4'd1, b_tag[p*12 +: 12]}; ad = b_addr[p*AW +: AW]; ln = b_len[p*4 +: 4]; end  // mutant: window stream tag -> G0
`else
                    else if (s == 1) begin tg = {1'b1, 4'd0, b_tag[p*12 +: 12]}; ad = b_addr[p*AW +: AW]; ln = b_len[p*4 +: 4]; end
`endif
                    else begin tg = {1'b1, 4'(s - 1), g_tag[(s-2)*12 +: 12]}; ad = g_addr[(s-2)*AW +: AW]; ln = g_len[(s-2)*4 +: 4]; end
                    rq[p*341 + 1] <= src_we(s);
                    rq[p*341 + 2 +: 30] <= 30'(ad);
                    rq[p*341 + 32 +: 4] <= src_we(s) ? 4'd1 : ln;
                    rq[p*341 + 36 +: 17] <= tg;
                    rq[p*341 + 53 +: 32] <= (s >= 2) ? g_wstrb[(s-2)*32 +: 32] : 32'd0;
                    rq[p*341 + 85 +: 256] <= (s >= 2) ? g_wdata[(s-2)*256 +: 256] : 256'd0;
                    rr[p] <= SW'((s + 1) % NS);
                    if (src_we(s)) begin wq[p][wqw[p] % DQ] <= 4'(s - 2); wqw[p] <= wqw[p] + 1'b1; end
                end
                cred[p] <= cred[p] - CW'(pc_go[p]) + CW'(rk[p]);
                if (rk[p] && !pc_go[p] && cred[p] == CW'(DQ)) begin fault <= 1; fault_code[3] <= 1; end
                resv[p] <= resv[p] + ((pc_go[p] && !src_we(32'(pick[p]))) ? (RW+1)'(src_len(p, 32'(pick[p]))) : '0)
                           - (RW+1)'(pop[p]);
                // landing
                if (rv[p]) begin
                    if (lw[p] - lr[p] >= (RW+1)'(DR)) begin fault <= 1; fault_code[0] <= 1; end
                    lq_tag[p][lw[p][RW-1:0]] <= r_tag[p*17 +: 17];
                    lq_beat[p][lw[p][RW-1:0]] <= r_beat[p*4 +: 4];
                    lq_dat[p][lw[p][RW-1:0]] <= r_data[p*256 +: 256];
                    lw[p] <= lw[p] + 1'b1;
                    if (r_tag[p*17 + 16] && r_tag[p*17 + 12 +: 4] > 4'(NG)) begin fault <= 1; fault_code[2] <= 1; end
                end
                if (pop[p]) lr[p] <= lr[p] + 1'b1;
                if (wd[p]) begin
                    if (wqw[p] == wqr[p]) begin fault <= 1; fault_code[1] <= 1; end
                    else wqr[p] <= wqr[p] + 1'b1;
                end
            end
            for (k = 0; k < NG; k = k + 1) begin
                if (gsel_v[k] && g_rsp_rdy[k]) grr[k] <= 5'((32'(gsel[k]) + 1) % NPC);
                g_wr_done[k] <= (wdc[k] != 0) || (wd_add[k] != 0);
                wdc[k] <= wdc[k] + 5'(wd_add[k]) - 5'((wdc[k] != 0) || (wd_add[k] != 0));
                if (g_bad[k]) begin fault <= 1; fault_code[4] <= 1; end
            end
        end
    end
endmodule
