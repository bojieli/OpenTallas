`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen TP8 vector memory, bit-plane x transport: the leaves AROUND the plane (claude/qwen-tp8-vm-rtl, 2026-10-13).
// ot_qfd_vm_xplane.sv left three things in the parent that have no physical owner: (1) the plane control and me were
// broadcast in ONE edge to 32 plane leaves / 328 relay leaves / 8 regions; (2) line (NX * 32 = 65,536 flops, a 14:1
// constant-source mux per entry) and (3) x_q (65,536 flops, the 2^sp replication) were parent soft logic.
//
//   ot_qfd_vm_fan_t     one stage of a registered fan-out tree: a W-bit register at the pin, its q wired to <= ~32
//                       loads (<= 4 child leaves of <= 8 pins each, or the next fan stages).  EN = 0: free-running
//                       (the me tree itself: me enters the tree K + 1 edges early and leaves it as every leaf's me_e).
//                       EN = 1: engine-enabled (control words: tapped K engine edges early in the parent's seam
//                       queue, so K stages land them on the original edge).  No replicated outputs, no logic.
//   ot_qfd_vm_xline_t   ONE BIT POSITION of line and of the x_q replication stage.  line[c] takes bv[(c * DV) % BEAT]
//                       of descriptor DV and x_q[i] takes line[i mod 2^sp]: both move whole elements, so bit p never
//                       meets another bit position (the same cut as rot1 / rot2 / bv).  Pin flops on the bv plane
//                       and on both control words, line, then the registered replication q.  q is the flat x_q
//                       plane delayed by EXACTLY one engine edge when c_* = the parent's s6_* and o_* = co_*.
//   ot_qfd_vm_xqface_t  the x_q register AT THE CONSUMER FACE: W bits of x_q (element-major slice), engine-enabled.
//                       xline q -> XQR x ot_qfd_vm_xrelay_t -> this leaf; x_q = xline q + XQR + 1 engine edges.
// x latency: + 1 (xline pin flop) + XQR + 1 (face) engine edges on top of the plane transport; the parent schedules
// against XVM - (XQR + 2) internally, so the consumer's XVM grows by XQR + 2.  Control latency: 0 (tapped early).
// MUT (negative controls): fan 1 = transparent (one edge short); xline 1 = line source one element off, 2 = the
// 2^sp write bound ignored, 3 = replication mask one bit wide; xqface 1 = free-running (ignores me).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_fan_t #(
    parameter integer W = 1,
    parameter integer EN = 0,
    parameter integer MEREG = 1,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         me_e,           // EN = 1 only (tie 0 when EN = 0)
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    wire me;
    generate if (EN != 0 && MEREG != 0) begin : g_mr
        (* keep = "true", dont_touch = "true" *) reg me_r;
        always @(posedge clk) me_r <= me_e;
        assign me = me_r;
    end else begin : g_mp
        assign me = (EN != 0) ? me_e : 1'b1;
    end endgenerate
    (* keep = "true", dont_touch = "true" *) reg [W-1:0] r;
    always @(posedge clk) if (me) r <= d;
    assign q = (MUT == 1) ? d : r;
endmodule

module ot_qfd_vm_xline_t #(
    parameter integer NRB = 64,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer BMAX = 8,
    parameter integer ND = 14,
    parameter [ND*8-1:0] DSET = {8'd96, 8'd64, 8'd48, 8'd32, 8'd24, 8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0},
    parameter integer MEREG = 1,
    parameter integer MUT = 0,
    parameter integer SELECT_ONLY = 0
) (
    input  wire                        clk,
    input  wire                        me_e,
    input  wire [(NRB-1)*16-1:0]       d,       // bv plane (ot_qfd_vm_xplane_t q)
    input  wire                        c_v,     // line write: the parent's s6_bv / s6_d / s6_j / s6_sp (aligned with d)
    input  wire [ND-1:0]               c_d,
    input  wire [$clog2(BMAX):0]       c_j,
    input  wire [3:0]                  c_sp,
    input  wire                        o_v,     // x_q capture: the parent's co_v / co_sp
    input  wire [3:0]                  o_sp,
    output wire [(1<<SMAX)-1:0]        line_data,
    output reg  [(1<<SMAX)-1:0]        q        // x_q plane, one engine edge after the flat x_q
);
    localparam integer BEAT = (NRB - 1) * 16;
    localparam integer NX = 1 << SMAX;
    localparam integer LB = $clog2(BMAX) + 1;
    // Fan-out inside the leaf: the me replica and the control pin flops are kept once per GE = 128 line entries (the
    // pins then load NG = NX / 128 flops each, 16 at SMAX 11; every copy drives 128 entries).  Pure replication.
    localparam integer GE = 128;
    localparam integer NG = (NX + GE - 1) / GE;
    wire [NG-1:0] me;
    generate if (MEREG != 0) begin : g_mr
        (* keep = "true", dont_touch = "true" *) reg [NG-1:0] me_r;
        always @(posedge clk) me_r <= {NG{me_e}};
        assign me = me_r;
    end else begin : g_mp
        assign me = {NG{me_e}};
    end endgenerate
    reg [BEAT-1:0] pd;
    (* keep = "true", dont_touch = "true" *) reg [NG-1:0]    pv, ov;
    (* keep = "true", dont_touch = "true" *) reg [NG*ND-1:0] pdd;
    (* keep = "true", dont_touch = "true" *) reg [NG*LB-1:0] pj;
    (* keep = "true", dont_touch = "true" *) reg [NG*4-1:0]  psp, osp;
    integer i, gi;
    always @(posedge clk) begin
        for (i = 0; i < BEAT; i = i + 1) if (me[(i * NG) / BEAT]) pd[i] <= d[i];
        for (gi = 0; gi < NG; gi = gi + 1) if (me[gi]) begin
            pv[gi] <= c_v; pdd[gi*ND +: ND] <= c_d; pj[gi*LB +: LB] <= c_j; psp[gi*4 +: 4] <= c_sp;
            ov[gi] <= o_v; osp[gi*4 +: 4] <= o_sp;
        end
    end
    // line and the replication stage: one ot_qfd_vm_xline_grp per GE = 128 entries (PLAN 2026-10-13).  As ONE module the
    // 2,048 x (14 + 17) per-entry terms kept the ORFS yosys front end in elaboration for > 15 minutes in every form tried
    // (per-entry generate scopes, one procedural if-chain, straight-line vector loops); a group module has 128 entries
    // and elaborates in seconds, NG = 16 parameterisations.  Same expressions, same flops, same edges.
    wire [NX-1:0] line;
    assign line_data = line;
    wire [NX-1:0] qw;
    genvar gg;
    generate for (gg = 0; gg < NG; gg = gg + 1) begin : g_grp
        localparam integer NE = (NX - gg * GE < GE) ? (NX - gg * GE) : GE;
        ot_qfd_vm_xline_grp #(.NRB(NRB), .SMAX(SMAX), .BMAX(BMAX), .ND(ND), .DSET(DSET), .BASE(gg * GE), .NE(NE), .MUT(MUT), .NO_Q(SELECT_ONLY)) u_g (
            .clk(clk), .me(me[gg]), .pd(pd), .pv(pv[gg]), .pdd(pdd[gg*ND +: ND]), .pj(pj[gg*LB +: LB]), .psp(psp[gg*4 +: 4]),
            .ov(ov[gg]), .osp(osp[gg*4 +: 4]), .line_all(line), .line(line[gg*GE +: NE]), .q(qw[gg*GE +: NE]));
    end endgenerate
    always @* q = qw;
endmodule

// NE entries BASE .. BASE + NE - 1 of line and of the x_q replication stage of one bit position (see ot_qfd_vm_xline_t).
// line[c] takes bv[(c * DV) % BEAT] of beat (c * DV) / BEAT of descriptor DV (the LAST hit of DSET wins) when c < 2^sp;
// x_q[c] takes line[c mod 2^sp] through one CONSTANT line entry per sp value (17 with the mutant's + 1).
module ot_qfd_vm_xline_grp #(
    parameter integer NRB = 64,
    parameter integer SMAX = 11,
    parameter integer BMAX = 8,
    parameter integer ND = 14,
    parameter [ND*8-1:0] DSET = {8'd96, 8'd64, 8'd48, 8'd32, 8'd24, 8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0},
    parameter integer BASE = 0,
    parameter integer NE = 128,
    parameter integer MUT = 0,
    parameter integer NO_Q = 0
) (
    input  wire                     clk,
    input  wire                     me,
    input  wire [(NRB-1)*16-1:0]    pd,
    input  wire                     pv,
    input  wire [ND-1:0]            pdd,
    input  wire [$clog2(BMAX):0]    pj,
    input  wire [3:0]               psp,
    input  wire                     ov,
    input  wire [3:0]               osp,
    input  wire [(1<<SMAX)-1:0]     line_all,
    output reg  [NE-1:0]            line,
    output reg  [NE-1:0]            q
);
    localparam integer BEAT = (NRB - 1) * 16;
    wire [4:0] osw = {1'b0, osp} + ((MUT == 3) ? 5'd1 : 5'd0);
    reg [NE-1:0] pick, anyhit, qn;
    integer e, dd, sv;
    always @* begin
        for (e = 0; e < NE; e = e + 1) begin
            pick[e] = 1'b0; anyhit[e] = 1'b0;
            for (dd = 0; dd < ND; dd = dd + 1)
                if ((((BASE + e) * DSET[dd*8 +: 8]) / BEAT < BMAX) && pdd[dd] && (pj == ((BASE + e) * DSET[dd*8 +: 8]) / BEAT)) begin
                    pick[e] = pd[(((BASE + e) * DSET[dd*8 +: 8]) % BEAT + ((MUT == 1 && BASE + e == 5) ? 1 : 0)) % BEAT];
                    anyhit[e] = 1'b1;
                end
            qn[e] = 1'b0;
            for (sv = 0; sv <= 16; sv = sv + 1)
                if (osw == sv) qn[e] = line_all[(BASE + e) & ((1 << sv) - 1)];
        end
    end
    always @(posedge clk) begin
        for (e = 0; e < NE; e = e + 1) begin
            if (me && pv && anyhit[e] && ((BASE + e) < (1 << psp) || MUT == 2)) line[e] <= pick[e];
            if (NO_Q == 0 && me && ov) q[e] <= qn[e];
        end
    end
endmodule

module ot_qfd_vm_xqface_t #(
    parameter integer W = 1024,
    parameter integer MEREG = 1,
    parameter integer MUT = 0
) (
    input  wire         clk,
    input  wire         me_e,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    wire me;
    generate if (MEREG != 0) begin : g_mr
        (* keep = "true", dont_touch = "true" *) reg me_r;
        always @(posedge clk) me_r <= me_e;
        assign me = me_r;
    end else begin : g_mp
        assign me = me_e;
    end endgenerate
    always @(posedge clk) if (me || MUT == 1) q <= d;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_xcol_t (PLAN 2026-10-13): ONE BIT POSITION of the whole x read as ONE hardened leaf = ot_qfd_vm_xplane_t
// (pin flop, rot1, rot2, bv) feeding ot_qfd_vm_xline_t (line, x_q replication) -- instances and wires only.
// Why one leaf: as two leaves the 1,008-b bv plane of every bit position was a die net between abutting leaves; in
// the band it took a third of every 260-um window (plan: 0.5994 with the lanes) and forced the line leaf between the
// plane and one region row.  Inside one leaf it is M2-M5 wiring, and the lanes land on BOTH faces: d[NRB*8-1:0]
// (the lower region row's banks, port d_lo) on S, d[NRB*16-1:NRB*8] (d_hi) on N; q (x_q plane, 2^SMAX b) leaves on
// W (q_lo) / E (q_hi).  Ports = the union of the two leaves, the two buses split per face; ONE me_e (every replica of both samples it); cycle behaviour unchanged.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_xcol_t #(
    parameter integer NRB = 64,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer BMAX = 8,
    parameter integer ND = 14,
    parameter [ND*8-1:0] DSET = {8'd96, 8'd64, 8'd48, 8'd32, 8'd24, 8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0},
    parameter integer MEREG = 1,
    parameter integer PMUT = 0,                 // ot_qfd_vm_xplane_t MUT
    parameter integer LMUT = 0                  // ot_qfd_vm_xline_t MUT
) (
    input  wire                        clk,
    input  wire                        me_e,
    input  wire [NRB*8-1:0]            d_lo,    // bit p of every element of banks 0 .. NRB/2-1 (the lower region row): S face
    input  wire [NRB*8-1:0]            d_hi,    // ... of banks NRB/2 .. NRB-1 (the upper region row): N face
    input  wire [$clog2(NRB)+3:0]      c_a,     // plane control (see ot_qfd_vm_xplane_t)
    input  wire [$clog2((NRB-1)*16+1)-1:0] c_nv,
    input  wire                        c_v,     // line / x_q control (see ot_qfd_vm_xline_t)
    input  wire [ND-1:0]               c_d,
    input  wire [$clog2(BMAX):0]       c_j,
    input  wire [3:0]                  c_sp,
    input  wire                        o_v,
    input  wire [3:0]                  o_sp,
    output wire [(1<<(SMAX-1))-1:0]    q_lo,    // x_q plane, elements 0 .. 2^(SMAX-1)-1: W face
    output wire [(1<<(SMAX-1))-1:0]    q_hi     // elements 2^(SMAX-1) .. 2^SMAX-1: E face
);
    wire [(NRB-1)*16-1:0] bv;
    wire [NRB*16-1:0]     d = {d_hi, d_lo};
    wire [(1<<SMAX)-1:0]  q;
    assign {q_hi, q_lo} = q;
    ot_qfd_vm_xplane_t #(.NRB(NRB), .MEREG(MEREG), .MUT(PMUT)) u_p (.clk(clk), .me_e(me_e), .d(d), .c_a(c_a), .c_nv(c_nv), .q(bv));
    ot_qfd_vm_xline_t #(.NRB(NRB), .SMIN(SMIN), .SMAX(SMAX), .BMAX(BMAX), .ND(ND), .DSET(DSET), .MEREG(MEREG), .MUT(LMUT)) u_l (
        .clk(clk), .me_e(me_e), .d(bv), .c_v(c_v), .c_d(c_d), .c_j(c_j), .c_sp(c_sp), .o_v(o_v), .o_sp(o_sp), .q(q));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_fantree: a registered fan-out tree of ot_qfd_vm_fan_t leaves and WIRES ONLY (no logic, no flop of its own):
// K levels; the last level has NLAST nodes, level l has ceil(nodes(l + 1) / FO) nodes (so the root level is one node
// when NLAST <= FO^(K-1); otherwise the port fans to the root-level nodes).  Node n of level l is fed by node
// floor(n * nodes(l-1) / nodes(l)) of the level above; sink s (NS of them, W bits each) by last-level node
// floor(s * NLAST / NS).  Fan-out per registered bit: <= FO child leaves, <= ceil(NS / NLAST) sinks.
// EN = 1 (control words): node (l, n) takes me_e[l * NLAST + n]; fed a word tapped K engine edges early it lands on the
// original edge.  EN = 0 (the me tree): free-running, fed me (K + 1) edges early it leaves as every sink's me_e.
// MUTL / MUTI: node (MUTL, MUTI) is transparent (negative control).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_fantree #(
    parameter integer W = 1,
    parameter integer K = 1,
    parameter integer NLAST = 8,
    parameter integer FO = 4,
    parameter integer NS = 32,
    parameter integer EN = 0,
    parameter integer MEREG = 1,
    parameter integer MUTL = -1,
    parameter integer MUTI = 0
) (
    input  wire                 clk,
    input  wire [K*NLAST-1:0]   me_e,
    input  wire [W-1:0]         d,
    output wire [NS*W-1:0]      q
);
    function automatic integer nn(input integer lv);
        integer v, j;
        begin
            v = NLAST;
            for (j = lv; j < K - 1; j = j + 1) v = (v + FO - 1) / FO;
            nn = v;
        end
    endfunction
    genvar l, n, s;
    generate
        for (l = 0; l < K; l = l + 1) begin : g_l
            localparam integer N = nn(l);
            localparam integer NP = (l == 0) ? 1 : nn(l - 1);
            wire [N*W-1:0] o;
            for (n = 0; n < N; n = n + 1) begin : g_n
                wire [W-1:0] di;
                if (l == 0) begin : g_root
                    assign di = d;
                end else begin : g_br
                    assign di = g_l[l-1].o[((n * NP) / N)*W +: W];
                end
                ot_qfd_vm_fan_t #(.W(W), .EN(EN), .MEREG(MEREG), .MUT((MUTL == l && MUTI == n) ? 1 : 0)) u_f (.clk(clk),
                    .me_e((EN != 0) ? me_e[l*NLAST + n] : 1'b0), .d(di), .q(o[n*W +: W]));
            end
        end
        for (s = 0; s < NS; s = s + 1) begin : g_s
            assign q[s*W +: W] = g_l[K-1].o[((s * NLAST) / NS)*W +: W];
        end
    endgenerate
endmodule
