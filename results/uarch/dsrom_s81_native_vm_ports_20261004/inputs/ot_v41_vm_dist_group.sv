`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One LANE GROUP of the distributed vector memory (rtl/chip/ot_v41_vm_dist.sv;
// spec results/floorplan/v41_vm_dist_spec.json).  The group owns the elements e
// with e mod NG == gid: local word w = e / NG, bank w[3 +: LNB], row
// w >> (3 + LNB), column w[2:0] (RW = 8 elements a row).  It holds NB banks
// (ot_v41_vm_dist_bank), each NRC read replicas of one 1R1W row macro.
//
// Reads.  Every request of the list carries a class (0..5: A, B, C, D operand
// streams, G gather index, X tree read).  In each cycle a class gets one row of
// each bank (its replica's port); a class that asks for a second row of a bank
// in the same cycle violates the read rule: the request is served by an
// overflow port and counted (mon_rconf).  Reads are registered: data return the
// cycle after the request, as from the flat memory.
//
// Writes.  The group's writes of a cycle are merged by row (a later write of the
// list wins on the same element: the flat memory's statement order) into masked
// row writes; one row a bank a cycle is the macro's port, the rest is write-
// buffer traffic: mon_wextra counts rows beyond the port, mon_occ_max the
// deepest the per-bank buffer gets (occupancy += rows - 1, floored at 0) -- the
// depth the spec's arbiter needs.  Data are exact either way (the spec's
// buffer forwards to readers).
//
// A cycle that needs more overflow ports / write slots than NOVF / NWP raises
// the sticky fault: the data would be wrong, so the run must fail.
// ---------------------------------------------------------------------------
module ot_v41_vm_dist_group #(
    parameter integer NG   = 128,
    parameter integer VMA  = 19,
    parameter integer NB   = 2,
    parameter integer RW   = 8,
    parameter integer NRC  = 6,         // read classes = replicas
    parameter integer NOVF = 48,        // overflow read ports a bank
    parameter integer NWP  = 32,        // row writes a bank a cycle (write-buffer traffic included)
    parameter integer NRD  = 16,
    parameter integer NWR  = 16,
    // derived
    parameter integer LNG  = (NG > 1) ? $clog2(NG) : 0,
    parameter integer GW   = (LNG > 0) ? LNG : 1,
    parameter integer LWA  = VMA - LNG,
    parameter integer LNB  = (NB > 1) ? $clog2(NB) : 0,
    parameter integer RA   = LWA - 3 - LNB,
    parameter integer NP   = NRC + NOVF
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [GW-1:0]        gid,
    input  wire [NRD-1:0]       rd_re,
    input  wire [NRD*VMA-1:0]   rd_addr,
    input  wire [NRD*3-1:0]     rd_cls,
    output reg  [NRD*32-1:0]    rd_q,
    input  wire [NWR-1:0]       wr_we,
    input  wire [NWR*VMA-1:0]   wr_addr,
    input  wire [NWR*32-1:0]    wr_data,
    // monitors (cumulative since reset)
    output reg  [NRC*32-1:0]    mon_rconf,      // extra rows, per read class
    output reg  [31:0]          mon_rconf_cyc,  // cycles with any read-rule violation
    output reg  [31:0]          mon_wextra,     // row writes beyond one a bank a cycle
    output reg  [15:0]          mon_wrows_max,  // most rows one bank took in one cycle
    output reg  [15:0]          mon_occ_max,    // deepest write buffer (rows)
    output reg                  fault
);
    localparam integer ROWS = 1 << RA;

    // ---- banks --------------------------------------------------------------------------------------
    reg  [NP-1:0]        p_re   [0:NB-1];
    reg  [NP*RA-1:0]     p_row  [0:NB-1];
    reg  [2:0]           p_cls  [0:NB-1][0:NP-1];
    wire [NP*RW*32-1:0]  p_q    [0:NB-1];
    reg  [NWP-1:0]       w_v    [0:NB-1];
    reg  [NWP*RA-1:0]    w_row  [0:NB-1];
    reg  [NWP*RW*32-1:0] w_dat  [0:NB-1];
    reg  [NWP*RW-1:0]    w_msk  [0:NB-1];
    genvar gb;
    generate for (gb = 0; gb < NB; gb = gb + 1) begin : g_bank
        ot_v41_vm_dist_bank #(.ROWS(ROWS), .RA(RA), .RW(RW), .NP(NP), .NWP(NWP)) u_bank (
            .clk(clk), .re(p_re[gb]), .raddr(p_row[gb]), .q(p_q[gb]),
            .we(w_v[gb]), .waddr(w_row[gb]), .wdata(w_dat[gb]), .wmask(w_msk[gb]));
    end endgenerate

    // ---- read port assignment (this cycle's requests) -----------------------------------------------
    reg [NRD-1:0]       a_v;
    reg [7:0]           a_b    [0:NRD-1];
    reg [7:0]           a_p    [0:NRD-1];
    reg [2:0]           a_col  [0:NRD-1];
    reg [NRC*16-1:0]    c_conf;
    reg                 c_rovf;
    integer r, p, b, c, fnd;
    reg [VMA-1:0] ad;
    reg [LWA-1:0] w;
    reg [RA-1:0]  row;
    always @(*) begin
        for (b = 0; b < NB; b = b + 1) begin
            p_re[b] = 0; p_row[b] = 0;
            for (p = 0; p < NP; p = p + 1) p_cls[b][p] = 3'd0;
        end
        c_conf = 0; c_rovf = 1'b0; a_v = 0;
        for (r = 0; r < NRD; r = r + 1) begin
            a_b[r] = 0; a_p[r] = 0; a_col[r] = 0;
            ad = rd_addr[r*VMA +: VMA];
            if (rd_re[r] && (LNG == 0 || ad[GW-1:0] == gid)) begin
                w = LWA'(ad >> LNG);
                b = (NB > 1) ? 32'((w >> 3) & LWA'(NB - 1)) : 0;
                row = RA'(w >> (3 + LNB));
                c = 32'(rd_cls[r*3 +: 3]);
                a_v[r] = 1'b1; a_b[r] = 8'(b); a_col[r] = w[2:0];
                if (!p_re[b][c]) begin
                    p_re[b][c] = 1'b1; p_row[b][c*RA +: RA] = row; a_p[r] = 8'(c);
                end else if (p_row[b][c*RA +: RA] == row) begin
                    a_p[r] = 8'(c);
                end else begin
                    // a second row of this bank for this class: an overflow port (shared by the class's requests
                    // for that row)
                    fnd = -1;
                    for (p = NRC; p < NP; p = p + 1)
                        if (fnd < 0 && p_re[b][p] && p_cls[b][p] == 3'(c) && p_row[b][p*RA +: RA] == row) fnd = p;
                    if (fnd < 0) begin
                        for (p = NRC; p < NP; p = p + 1)
                            if (fnd < 0 && !p_re[b][p]) fnd = p;
                        if (fnd >= 0) begin
                            p_re[b][fnd] = 1'b1; p_row[b][fnd*RA +: RA] = row; p_cls[b][fnd] = 3'(c);
                            c_conf[c*16 +: 16] = c_conf[c*16 +: 16] + 16'd1;
                        end
                    end
                    if (fnd < 0) c_rovf = 1'b1;
                    else a_p[r] = 8'(fnd);
                end
            end
        end
    end

    // ---- write merge (this cycle's writes, in list order) ------------------------------------------
    reg [15:0] w_n [0:NB-1];
    reg        c_wovf;
    integer q, s, fw;
    reg [VMA-1:0] wa;
    reg [LWA-1:0] ww;
    reg [RA-1:0]  wrow;
    integer wb;
    always @(*) begin
        c_wovf = 1'b0;
        for (wb = 0; wb < NB; wb = wb + 1) begin
            w_v[wb] = 0; w_row[wb] = 0; w_dat[wb] = 0; w_msk[wb] = 0; w_n[wb] = 0;
        end
        for (q = 0; q < NWR; q = q + 1) begin
            wa = wr_addr[q*VMA +: VMA];
            if (wr_we[q] && (LNG == 0 || wa[GW-1:0] == gid)) begin
                ww = LWA'(wa >> LNG);
                wb = (NB > 1) ? 32'((ww >> 3) & LWA'(NB - 1)) : 0;
                wrow = RA'(ww >> (3 + LNB));
                fw = -1;
                for (s = 0; s < NWP; s = s + 1)
                    if (fw < 0 && w_v[wb][s] && w_row[wb][s*RA +: RA] == wrow) fw = s;
                if (fw < 0) begin
                    for (s = 0; s < NWP; s = s + 1)
                        if (fw < 0 && !w_v[wb][s]) fw = s;
                    if (fw >= 0) begin
                        w_v[wb][fw] = 1'b1; w_row[wb][fw*RA +: RA] = wrow; w_n[wb] = w_n[wb] + 16'd1;
                    end
                end
                if (fw < 0) c_wovf = 1'b1;
                else begin
                    w_msk[wb][fw*RW + 32'(ww[2:0])] = 1'b1;
                    w_dat[wb][fw*RW*32 + 32*32'(ww[2:0]) +: 32] = wr_data[q*32 +: 32];
                end
            end
        end
    end

    // ---- registered request map and read data ------------------------------------------------------
    reg [NRD-1:0]  m_v;
    reg [7:0]      m_b   [0:NRD-1];
    reg [7:0]      m_p   [0:NRD-1];
    reg [2:0]      m_col [0:NRD-1];
    integer rr;
    always @(posedge clk) begin
        m_v <= a_v;
        for (rr = 0; rr < NRD; rr = rr + 1) begin m_b[rr] <= a_b[rr]; m_p[rr] <= a_p[rr]; m_col[rr] <= a_col[rr]; end
    end
    integer ro;
    always @(*) begin
        rd_q = 0;
        for (ro = 0; ro < NRD; ro = ro + 1)
            if (m_v[ro]) rd_q[ro*32 +: 32] = p_q[m_b[ro]][(32'(m_p[ro]) * RW + 32'(m_col[ro])) * 32 +: 32];
    end

    // ---- monitors -----------------------------------------------------------------------------------
    reg [15:0] occ [0:NB-1];
    reg        any_conf;
    reg [31:0] wx_sum;
    reg [15:0] wr_mx, oc_mx;
    integer mc, mb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mon_rconf <= 0; mon_rconf_cyc <= 0; mon_wextra <= 0; mon_wrows_max <= 0; mon_occ_max <= 0;
            fault <= 1'b0;
            for (mb = 0; mb < NB; mb = mb + 1) occ[mb] <= 0;
        end else begin
            any_conf = 1'b0;
            for (mc = 0; mc < NRC; mc = mc + 1) begin
                mon_rconf[mc*32 +: 32] <= mon_rconf[mc*32 +: 32] + 32'(c_conf[mc*16 +: 16]);
                if (c_conf[mc*16 +: 16] != 0) any_conf = 1'b1;
            end
            if (any_conf) mon_rconf_cyc <= mon_rconf_cyc + 1;
            wx_sum = 0; wr_mx = mon_wrows_max; oc_mx = mon_occ_max;
            for (mb = 0; mb < NB; mb = mb + 1) begin
                if (w_n[mb] > 1) wx_sum = wx_sum + 32'(w_n[mb] - 16'd1);
                if (w_n[mb] > wr_mx) wr_mx = w_n[mb];
                occ[mb] <= (occ[mb] + w_n[mb] > 0) ? occ[mb] + w_n[mb] - 16'd1 : 16'd0;
                if (occ[mb] > oc_mx) oc_mx = occ[mb];
            end
            mon_wextra <= mon_wextra + wx_sum; mon_wrows_max <= wr_mx; mon_occ_max <= oc_mx;
            if (c_rovf || c_wovf) fault <= 1'b1;
        end
    end
endmodule
