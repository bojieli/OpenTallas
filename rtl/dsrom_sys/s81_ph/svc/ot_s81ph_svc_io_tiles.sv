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

// pin-registered input queue (r3b, svcio_ad a0_v -> skid enables +14 ps at 10 levels from the pin): every input bit
// is captured in a flop at the pin, then a 4-entry register FIFO; ready = the FIFO's registered room2 (>= 2 free:
// covers the word in the pin register), so the producer's valid/ready contract is unchanged, latency +2.
module ot_s81ph_inq #(parameter integer W = 512) (
    input wire clk, input wire rst_n,
    input wire i_v, input wire [W-1:0] i_d, output wire i_r,
    output wire o_v, output wire [W-1:0] o_d, input wire o_r);
    reg pv; reg [W-1:0] pd;
    always @(posedge clk or negedge rst_n) if (!rst_n) pv <= 1'b0; else pv <= i_v && i_r;   // the word the producer saw accepted
    always @(posedge clk) pd <= i_d;
    wire room, flt;
    ot_s81ph_rfifo #(.W(W), .D(4), .R2RST(0)) u_f (.clk(clk), .rst_n(rst_n), .push(pv), .wd(pd), .pop(o_v && o_r), .hv(o_v), .hd(o_d),
        .room(room), .room2(i_r), .fault(flt));
endmodule

// gaps-design 2026-10-08 (svcio_q lbc-tt TT -11.3 / FF +14.1: the q_q register -> q_q pin paths carry the FF hold
// padding of the die-link hold budget, and the q_q flop sits at the end of a 3-stage chain pulled toward the q input pins):
// OSTG = 1 adds an output pin register stage (q_rep -> q_o -> q_q, all kept) so the q_q flop is free to sit at its own
// output pin and the pin path is clk->q + padding only.  Cost: +1 cycle on the svc q path (OSTG = 0 is the adopted r3).
module dsfd_svcio_q #(parameter integer OSTG = 0) (input wire [0:0] ck, input wire [0:0] rst, input wire [514:0] q, output reg [2059:0] q_q);
    reg [514:0] q_p;
    (* keep *) reg [514:0] q_rep [0:3];
    wire [2059:0] q_src;
    integer g;
    always @(posedge ck[0]) begin
        q_p <= q;
        for (g = 0; g < 4; g = g + 1) q_rep[g] <= q_p;
        q_q <= q_src;
    end
    generate if (OSTG != 0) begin : g_ostg
        (* keep *) reg [2059:0] q_o;
        integer h;
        always @(posedge ck[0]) for (h = 0; h < 4; h = h + 1) q_o[515*h +: 515] <= q_rep[h];
        assign q_src = q_o;
    end else begin : g_direct
        assign q_src = {q_rep[3], q_rep[2], q_rep[1], q_rep[0]};
    end endgenerate
    wire unused_rst = rst[0];
endmodule

module dsfd_svcio_od (
    input wire [0:0] ck, input wire [0:0] rst,
    input wire [3:0] od_v, input wire [2047:0] od_d, output wire [3:0] od_r,
    output reg [513:0] od, output wire [0:0] of, output reg [0:0] bad);
    wire rn; ot_s81ph_rsync u_rs (.ck(ck[0]), .rst(rst[0]), .rn(rn));
    wire m_v, m_bad; wire [511:0] m_d;
`ifdef SVCIO_OD_NOINQ
    ot_s81ph_fmerge #(.N(4)) u_m (.clk(ck[0]), .rst_n(rn), .s_v(od_v), .s_d(od_d), .s_r(od_r), .o_v(m_v), .o_d(m_d), .bad(m_bad));
`else
    // REDESIGN-S81 2026-10-08 (TT + consistent link budget -22.5 / TT re-STA -27.4: od_v pin -> 3 logic -> u_k.d1):
    // every quadrant input through a pin-registered queue (ot_s81ph_inq, as dsfd_svcio_ad r3b), then the merge.
    // +2 cycles on the od path; od_r = the queue's registered room2 (producer valid/ready contract unchanged).
    wire [3:0] q0_v, q0_r; wire [2047:0] q0_d;
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_iq
        ot_s81ph_inq u_iq (.clk(ck[0]), .rst_n(rn), .i_v(od_v[gq]), .i_d(od_d[512*gq +: 512]), .i_r(od_r[gq]),
            .o_v(q0_v[gq]), .o_d(q0_d[512*gq +: 512]), .o_r(q0_r[gq]));
    end endgenerate
    ot_s81ph_fmerge #(.N(4)) u_m (.clk(ck[0]), .rst_n(rn), .s_v(q0_v), .s_d(q0_d), .s_r(q0_r), .o_v(m_v), .o_d(m_d), .bad(m_bad));
`endif
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
    // r3b: every quadrant input through a pin-registered queue (ot_s81ph_inq), then the r2 merge / skid
    wire [3:0] q0_v, q0_r; wire [2047:0] q0_d; wire q1_v, q1_r; wire [511:0] q1_d;
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_iq
        ot_s81ph_inq u_iq (.clk(ck[0]), .rst_n(rn), .i_v(a0_v[gq]), .i_d(a0_d[512*gq +: 512]), .i_r(a0_r[gq]),
            .o_v(q0_v[gq]), .o_d(q0_d[512*gq +: 512]), .o_r(q0_r[gq]));
    end endgenerate
    ot_s81ph_inq u_iq1 (.clk(ck[0]), .rst_n(rn), .i_v(a1_v[0]), .i_d(a1_d), .i_r(a1_r[0]), .o_v(q1_v), .o_d(q1_d), .o_r(q1_r));
    ot_s81ph_fmerge #(.N(4)) u_m (.clk(ck[0]), .rst_n(rn), .s_v(q0_v), .s_d(q0_d), .s_r(q0_r), .o_v(m_v), .o_d(m_d), .bad(m_bad));
    ot_s81ph_skid #(.W(512)) u_k1 (.clk(ck[0]), .rst_n(rn), .i_v(q1_v), .i_d(q1_d), .i_r(q1_r), .o_v(k1_v), .o_d(k1_d), .o_r(1'b1));
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
module ot_s81ph_svc_io_t (
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
    dsfd_svcio_od u_od (.ck(ck), .rst(rst), .od_v(od_v), .od_d(od_d), .od_r(od_r), .od(od), .of(of), .bad(bad_od));
    dsfd_svcio_ad u_ad (.ck(ck), .rst(rst), .a0_v(a0_v), .a0_d(a0_d), .a0_r(a0_r), .a1_v(a1_v), .a1_d(a1_d), .a1_r(a1_r),
        .fi(bad_od), .ad(ad), .af(af), .fault(fault));
    dsfd_svcio_x  u_x  (.ck(ck), .rst(rst), .x_v(x_v), .x_d(x_d), .x_r(x_r), .xd(xd), .xf(xf));
endmodule
