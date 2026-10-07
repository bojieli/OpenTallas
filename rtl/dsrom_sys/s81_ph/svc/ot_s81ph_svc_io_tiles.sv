`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE S81-PH svc IO hub r3 (OWNER FAIL-FAST STRUCTURAL, 2026-10-06 21:00): the 1080 x 129.6-um IO hub dsfd_svc_io
// (svcio_m2: SS -180 on q -> q_p with 10 buffer levels from the pin, od_v / a0_v -> merge skids -161 / -158, x_d -159;
// FF -65 on every output; clock tree over 1.08 mm) is split into FOUR small tiles, each placed AT its own die pin group:
//   dsfd_svcio_q   q pin register -> 4 kept replicas -> q_q (one per quadrant)
//   dsfd_svcio_od  od frame-atomic merge of the 4 quadrant streams (2-slot skids) -> od + forwarded clock of
//   dsfd_svcio_ad  a0 merge + a1 skid -> ad + af; fault = sticky (a0 malformed header | od tile's fault, registered)
//   dsfd_svcio_x   x skid -> xd + xf
// Functions are the r2 ones (ot_s81ph_fmerge / ot_s81ph_skid / q replicas, ot_s81ph_svc_io.sv) unchanged; each tile
// synchronises the die reset itself.  Cost: fault +2 cycles (od-side malformed header, status only); data paths
// unchanged.  ot_s81ph_svc_io_t = the composition (bench target, same ports as ot_s81ph_svc_io).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_rsync (input wire ck, input wire rst, output wire rn);
    reg [1:0] rst_s;                         // rst_s[1]: the margin SDC's rst_mcp2 cell name
    always @(posedge ck or negedge rst) if (!rst) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    assign rn = rst_s[1];
endmodule

module dsfd_svcio_q (input wire [0:0] ck, input wire [0:0] rst, input wire [514:0] q, output reg [2059:0] q_q);
    reg [514:0] q_p;
    (* keep *) reg [514:0] q_rep [0:3];
    integer g;
    always @(posedge ck[0]) begin
        q_p <= q;
        for (g = 0; g < 4; g = g + 1) begin q_rep[g] <= q_p; q_q[515*g +: 515] <= q_rep[g]; end
    end
    wire unused_rst = rst[0];
endmodule

module dsfd_svcio_od #(parameter integer MARGIN=0) (
    input wire [0:0] ck, input wire [0:0] rst,
    input wire [3:0] od_v, input wire [2047:0] od_d, output wire [3:0] od_r,
    output reg [513:0] od, output wire [0:0] of, output reg [0:0] bad);
    wire rn; ot_s81ph_rsync u_rs (.ck(ck[0]), .rst(rst[0]), .rn(rn));
    wire m_v, m_bad; wire [511:0] m_d;
    generate if (MARGIN) begin : g_margin
        ot_s81ph_fmerge_margin #(.N(4)) u_m (.clk(ck[0]), .rst_n(rn), .s_v(od_v), .s_d(od_d), .s_r(od_r), .o_v(m_v), .o_d(m_d), .bad(m_bad));
    end else begin : g_legacy
    ot_s81ph_fmerge #(.N(4)) u_m (.clk(ck[0]), .rst_n(rn), .s_v(od_v), .s_d(od_d), .s_r(od_r), .o_v(m_v), .o_d(m_d), .bad(m_bad));
    end endgenerate
    always @(posedge ck[0]) od <= {m_d, m_v & rn, rn};
    always @(posedge ck[0] or negedge rn) if (!rn) bad <= 1'b0; else bad <= m_bad;
    ot_fwd_clk_inv u_of (.a(ck[0]), .y(of[0]));
endmodule

module dsfd_svcio_ad (
    input wire [0:0] ck, input wire [0:0] rst,
    input wire [3:0] a0_v, input wire [2047:0] a0_d, output wire [3:0] a0_r,
    input wire [0:0] a1_v, input wire [511:0] a1_d, output wire [0:0] a1_r,
    input wire [0:0] fi,                     // od tile's sticky fault (flop there)
    output reg [1025:0] ad, output wire [0:0] af, output reg [0:0] fault);
    wire rn; ot_s81ph_rsync u_rs (.ck(ck[0]), .rst(rst[0]), .rn(rn));
    wire m_v, m_bad, k1_v; wire [511:0] m_d, k1_d;
    ot_s81ph_fmerge #(.N(4)) u_m (.clk(ck[0]), .rst_n(rn), .s_v(a0_v), .s_d(a0_d), .s_r(a0_r), .o_v(m_v), .o_d(m_d), .bad(m_bad));
    ot_s81ph_skid #(.W(512)) u_k1 (.clk(ck[0]), .rst_n(rn), .i_v(a1_v[0]), .i_d(a1_d), .i_r(a1_r[0]), .o_v(k1_v), .o_d(k1_d), .o_r(1'b1));
    always @(posedge ck[0]) ad <= {k1_d, k1_v & rn, m_d, m_v & rn};
    reg fi_q;
    always @(posedge ck[0] or negedge rn) if (!rn) begin fi_q <= 1'b0; fault <= 1'b0; end
                                          else begin fi_q <= fi[0]; if (m_bad || fi_q) fault <= 1'b1; end
    ot_fwd_clk_inv u_af (.a(ck[0]), .y(af[0]));
endmodule

module dsfd_svcio_x (
    input wire [0:0] ck, input wire [0:0] rst,
    input wire [0:0] x_v, input wire [511:0] x_d, output wire [0:0] x_r,
    output reg [513:0] xd, output wire [0:0] xf);
    wire rn; ot_s81ph_rsync u_rs (.ck(ck[0]), .rst(rst[0]), .rn(rn));
    wire kx_v; wire [511:0] kx_d;
    ot_s81ph_skid #(.W(512)) u_kx (.clk(ck[0]), .rst_n(rn), .i_v(x_v[0]), .i_d(x_d), .i_r(x_r[0]), .o_v(kx_v), .o_d(kx_d), .o_r(1'b1));
    always @(posedge ck[0]) xd <= {kx_d, kx_v & rn, rn};
    ot_fwd_clk_inv u_xf (.a(ck[0]), .y(xf[0]));
endmodule

// composition (same ports as ot_s81ph_svc_io NQ 4 + the forwarded clocks)
module ot_s81ph_svc_io_t #(parameter integer OD_MARGIN=0) (
    input  wire ck, rst, input wire [514:0] q,
    output wire [513:0] od, output wire [513:0] xd, output wire [1025:0] ad, output wire fault,
    output wire [2059:0] q_q,
    input  wire [3:0] od_v, input wire [2047:0] od_d, output wire [3:0] od_r,
    input  wire [3:0] a0_v, input wire [2047:0] a0_d, output wire [3:0] a0_r,
    input  wire a1_v, input wire [511:0] a1_d, output wire a1_r,
    input  wire x_v, input wire [511:0] x_d, output wire x_r,
    output wire of, output wire xf, output wire af);
    wire bad_od;
    dsfd_svcio_q  u_q  (.ck(ck), .rst(rst), .q(q), .q_q(q_q));
    dsfd_svcio_od #(.MARGIN(OD_MARGIN)) u_od (.ck(ck), .rst(rst), .od_v(od_v), .od_d(od_d), .od_r(od_r), .od(od), .of(of), .bad(bad_od));
    dsfd_svcio_ad u_ad (.ck(ck), .rst(rst), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r),
        .fi(bad_od), .ad(ad), .af(af), .fault(fault));
    dsfd_svcio_x  u_x  (.ck(ck), .rst(rst), .x_v(x_v), .x_d(x_d), .x_r(x_r), .xd(xd), .xf(xf));
endmodule
