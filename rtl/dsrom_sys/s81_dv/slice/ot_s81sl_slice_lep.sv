`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// RTL-BUILD-S81 (owner 0dv 2026-10-18): the END-SLICE link endpoint master (p4j end_slice_lep: s_0S / s_0N = W end,
// s_7S / s_7N = E end; residual row 1: lt_lk_{WS,WN,ES,EN}{0,1} 8 x 512 b had no producer).
//
// Function (SPEC 0b-p4i "end-slice link endpoints"; SPEC l.217 "the end slices' outward E/W ring port carries the PHY
// link lanes along the street"): the tier LINE simply continues across the die edge.  A line beat that reaches an end
// slice with hops > 1 is forwarded by the unchanged ring stop (ot_s81sl_rstop) out of the slice's OUTWARD port
// (W end: ro_w, E end: ro_e); here that port feeds two reliable UCIe link lanes instead of a neighbour.  The peer die's
// end slice presents the beat on its outward input (ri_w / ri_e), where its ring stop delivers it (hops 1) or forwards
// it inward (hops - 1) exactly like a neighbour's beat: cross-die all-gather rows (XQ / XB) join the mesh stream at the
// end slice, all-reduce partials ride to the owning slice, which keeps the fixed fold order ((p0+p1)+(p2+p3)).
// The compiler addresses an off-die destination by hop count (col + 1 + remote hops for a W-bound beat).
//
// Structure (cluster, wires only; every function in a hardened child with its own clock root):
//   ot_s81sl_slice            the vector slice cluster, UNCHANGED (HB = 0, C1)
//   ot_s81sl_lep              link-port leaf (this file): outward-port pin flops, per-lane TX landing FIFOs, RX pair
//                             re-assembly, lane-receive enables, the fault collector
//   dsfd_coll_lane_w / _e x2  the hardened collective link lane tile (ot_s81ph_link_ep reliable link layer: seq, CRC-32,
//                             go-back-N replay, credits + ot_s81ph_link_gbx 512-b beat format), unchanged
//   A 1,104-b ring beat = 2 link flits of 552 b (FLIT_BYTES 69): low half [551:0] on lane 0, high half [1103:552] on
//   lane 1; the flit's `last` bit carries the beat-sequence parity (checked at re-assembly).
// Flow control exists ONLY at this off-die boundary (owner 10-14: flow control kept at SerDes / d2d incl. cross-die
// collectives): the ring side is static (a valid beat on ro is pushed the same cycle; a full landing FIFO is a sticky
// fault: the compiler keeps the off-die rate <= the lane rate 456/596 * 1023/1024 = 0.764 beats/cycle with bursts
// <= DT / (1 - 0.764) = ~2,170 back-to-back beats at DT = 512), the lane side is the link layer's valid/ready + credits.
//
// Ports (lepw = W end; lepe = E end mirrors ri_e/ro_e <-> ri_w/ro_w):
//   tx0 / tx1 [511:0]   -> ot_pdie_ucie tx (lt_lk_<side><tier>{0,1})
//   rx0 / rx1 [513:0]   <- {ot_pdie_ucie st[1:0] = {live, fault}, rx[511:0]} (lr_lk_*; the plan lane is 512 b: + 2 st)
//   tf [1:0]            forwarded lane clocks (to the PHY macro side)
//   ch_b                static strap: 0 = UCIe lane timeout basis, 1 = board lane
//   all other ports     = ot_s81sl_slice (inward line port, V rung, band port (mode-unused at HB 0), x chains, return
//                         lanes, forwarded clocks)
// The lane rx word {fault, live, beat, valid} of dsfd_coll_lane_*: valid = the lep's registered lane-receive enable
// (1 from the cycle after reset release): ot_pdie_ucie's rate matcher presents a beat EVERY cycle (an IDLE beat 512'b10
// when its FIFO is empty, skipped by the gearbox), and the gearbox qualifies beats with `live` itself.
// Mutants (bench only): OT_S81SL_LEP_MUT_SWAP (halves swapped onto the lanes), OT_S81SL_LEP_MUT_NOPAIR (re-assembly
// releases on lane 0 alone), OT_S81SL_LEP_MUT_NOOVF (landing-FIFO overflow not flagged).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_lep #(
    parameter integer DT = 512,        // TX landing FIFO depth per lane (flits; SRAM macro depth)
    parameter integer DR = 4,          // RX re-assembly FIFO depth per lane (flits, flops)
    parameter integer SRAM = 1         // 1: TX storage in SRAM macros (0: flops, same cycle behaviour)
) (
    input  wire            clk,
    input  wire            rst_n,
    // slice outward line port
    input  wire [1103:0]   ro,
    output reg  [1103:0]   ri,
    // link lanes (dsfd_coll_lane_* core side: lo = to link, li = from link)
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output reg  [1:0]      rxv,        // lane receive enables (the lane rx word's valid bit)
    // fault collector: slice fault, lane faults {meso, gearbox, endpoint}
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    output reg             fault
);
    localparam integer H = 552;
    localparam integer AT = $clog2(DT), AR = $clog2(DR);
    // regional reset: own synchroniser on this leaf's clock root
    reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    always @(posedge clk or negedge rn) if (!rn) rxv <= 2'b00; else rxv <= 2'b11;

    // ---------------------------------------------------------------- outward-port pin flops
    reg rov; reg [1103:0] roq;
    always @(posedge clk or negedge rn) if (!rn) rov <= 1'b0; else rov <= ro[0];
    always @(posedge clk) roq <= ro;
    reg sq;                                            // beat-sequence parity (TX)
    always @(posedge clk or negedge rn) if (!rn) sq <= 1'b0; else if (rov) sq <= ~sq;
`ifdef OT_S81SL_LEP_MUT_SWAP
    wire [H-1:0] hf0 = roq[2*H-1:H], hf1 = roq[H-1:0];
`else
    wire [H-1:0] hf0 = roq[H-1:0], hf1 = roq[2*H-1:H];
`endif

    // ---------------------------------------------------------------- TX landing FIFOs (one per lane)
    // Storage: ot_s81ph_mem1r1w SRAM = 1 (5 x ot_sram_1r1w_512x128_m4_r2c2 a lane, registered write port WREG = 1,
    // registered read), DT entries; a 2-entry flop output buffer (ob0 / ob1) drives lo_v / lo_d from flops.  A read is
    // issued only when its word will find a free output slot (static occupancy count, no combinational ready path).
    wire [1:0] ovf;
    wire [1:0] lo_v, lo_r = {lo1_r, lo0_r};
    wire [2*(H+1)-1:0] lo_d;
    genvar t;
    generate for (t = 0; t < 2; t = t + 1) begin : g_tx
        reg [AT-1:0] wp, rp; reg [AT:0] n;
        reg inf; reg [1:0] obn; reg obv; reg [H:0] ob0, ob1; reg of;
        wire [H:0] q;
        wire hs = obv && lo_r[t];
        wire [1:0] base = obn - (hs ? 2'd1 : 2'd0);
        wire iss = n != 0 && (base + (inf ? 2'd1 : 2'd0)) <= 2'd1;
        wire wr = rov && (n != DT || iss);
        ot_s81ph_mem1r1w #(.W(H + 1), .DEPTH(DT), .SRAM(SRAM), .WREG(1)) u_m (.clk(clk), .rst_n(rn), .we(wr), .wa(wp),
            .wd({sq, (t == 0) ? hf0 : hf1}), .re(iss), .ra(rp), .q(q));
        always @(posedge clk or negedge rn)
            if (!rn) begin wp <= 0; rp <= 0; n <= 0; inf <= 1'b0; obn <= 2'd0; obv <= 1'b0; of <= 1'b0; end
            else begin
                if (wr) wp <= (wp == DT - 1) ? 0 : wp + 1'b1;
                if (iss) rp <= (rp == DT - 1) ? 0 : rp + 1'b1;
                n <= n + (wr ? 1'b1 : 1'b0) - (iss ? 1'b1 : 1'b0);
                inf <= iss;
                obn <= base + (inf ? 2'd1 : 2'd0);
                obv <= (base + (inf ? 2'd1 : 2'd0)) != 2'd0;
`ifndef OT_S81SL_LEP_MUT_NOOVF
                if (rov && n == DT && !iss) of <= 1'b1;
`endif
            end
        always @(posedge clk) begin
            if (hs) ob0 <= ob1;
            if (inf) begin if (base == 2'd0) ob0 <= q; else ob1 <= q; end
        end
        assign lo_v[t] = obv; assign lo_d[t * (H + 1) +: H + 1] = ob0; assign ovf[t] = of;
    end endgenerate
    assign lo0_v = lo_v[0]; assign lo0_d = lo_d[H:0];
    assign lo1_v = lo_v[1]; assign lo1_d = lo_d[2*H+1:H+1];

    // ---------------------------------------------------------------- RX pair re-assembly
    wire [1:0] li_v = {li1_v, li0_v}; wire [2*(H+1)-1:0] li_d = {li1_d, li0_d};
    wire [1:0] rne; wire [2*(H+1)-1:0] rhd; wire [1:0] lir;
`ifdef OT_S81SL_LEP_MUT_NOPAIR
    wire rel = rne[0];
`else
    wire rel = rne[0] && rne[1];
`endif
    generate for (t = 0; t < 2; t = t + 1) begin : g_rx
        // li handshake captured at the pin (hq / dq flops), written one edge later; m counts written + in-flight
        // entries, so the registered ready r never admits more than DR
        reg [H:0] mem [0:DR-1];
        reg [AR-1:0] wp, rp; reg [AR:0] n, m; reg r, hq; reg [H:0] dq;
        wire hs = li_v[t] && r;
        wire pop = rel && n != 0;
        wire [AR:0] mx = m + (hs ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
        always @(posedge clk or negedge rn)
            if (!rn) begin wp <= 0; rp <= 0; n <= 0; m <= 0; r <= 1'b0; hq <= 1'b0; end
            else begin
                hq <= hs;
                if (hq) wp <= (wp == DR - 1) ? 0 : wp + 1'b1;
                if (pop) rp <= (rp == DR - 1) ? 0 : rp + 1'b1;
                n <= n + (hq ? 1'b1 : 1'b0) - (pop ? 1'b1 : 1'b0);
                m <= mx;
                r <= mx < DR;
            end
        always @(posedge clk) begin dq <= li_d[t * (H + 1) +: H + 1]; if (hq) mem[wp] <= dq; end
        assign rne[t] = n != 0; assign rhd[t * (H + 1) +: H + 1] = mem[rp]; assign lir[t] = r;
    end endgenerate
    assign li0_r = lir[0]; assign li1_r = lir[1];
    wire [H:0] h0 = rhd[H:0], h1 = rhd[2*H+1:H+1];
    reg perr;
    always @(posedge clk or negedge rn)
        if (!rn) begin ri <= 1104'd0; perr <= 1'b0; end
        else begin
            ri <= rel ? {h1[H-1:0], h0[H-1:0]} : 1104'd0;
            // a released pair must be one beat: equal sequence parity, and the low half carries the beat valid
            if (rel && (h0[H] != h1[H] || !h0[0])) perr <= 1'b1;
        end

    // ---------------------------------------------------------------- fault collector (sticky)
    reg slq; reg [5:0] lfq;
    always @(posedge clk or negedge rn)
        if (!rn) begin slq <= 1'b0; lfq <= 6'd0; fault <= 1'b0; end
        else begin
            slq <= sl_f; lfq <= {l1_f, l0_f};
            if ((|ovf) || perr || slq || (|lfq)) fault <= 1'b1;
        end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// The end-slice cluster: slice + lep + 2 link lanes.  SIDE 0 = W end (outward = ri_w / ro_w), 1 = E end.  The die
// masters are the parameter-free tops below (one per outward face: pin plans differ, as dsfd_coll_lane_w / _e).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_slice_lep #(
    parameter integer SIDE = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_n,         // inward line port (from / to the inward neighbour)
    output wire [1103:0]   ro_n,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [1103:0]   bi,   output wire [1103:0] bo,
    output wire [4*1104-1:0] xc,
    input  wire [8*70-1:0] rt,
    output wire [15:0]     ck_line,
    output wire [1:0]      ck_v,
    output wire [15:0]     ck_xc,
    output wire [7:0]      ck_rt,
    input  wire            ch_b,
    output wire [511:0]    tx0, output wire [511:0] tx1,
    input  wire [513:0]    rx0, input  wire [513:0] rx1,
    output wire [1:0]      tf,
    output wire            fault
);
    wire [1103:0] lro, lri; wire sf;
    wire l0v, l0r, l1v, l1r, i0v, i0r, i1v, i1r; wire [552:0] l0d, l1d, i0d, i1d; wire [2:0] f0, f1; wire [1:0] rxv;
    generate if (SIDE == 0) begin : g_w
        ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(lri), .ri_e(ri_n), .ro_e(ro_n), .ro_w(lro),
            .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
            .ck_rt(ck_rt), .fault(sf));
        dsfd_coll_lane_w u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx0[512], rx0[513], rx0[511:0], rxv[0]}),
            .tx(tx0), .tf(tf[0]), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_w u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx1[512], rx1[513], rx1[511:0], rxv[1]}),
            .tx(tx1), .tf(tf[1]), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    end else begin : g_e
        ot_s81sl_slice u_sl (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_w(ri_n), .ri_e(lri), .ro_e(lro), .ro_w(ro_n),
            .vi(vi), .vo(vo), .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc),
            .ck_rt(ck_rt), .fault(sf));
        dsfd_coll_lane_e u_ln0 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx0[512], rx0[513], rx0[511:0], rxv[0]}),
            .tx(tx0), .tf(tf[0]), .lo_v(l0v), .lo_r(l0r), .lo_d(l0d), .li_v(i0v), .li_r(i0r), .li_d(i0d), .flt(f0));
        dsfd_coll_lane_e u_ln1 (.ck(clk), .rs(rst_n), .chb(ch_b), .rx({rx1[512], rx1[513], rx1[511:0], rxv[1]}),
            .tx(tx1), .tf(tf[1]), .lo_v(l1v), .lo_r(l1r), .lo_d(l1d), .li_v(i1v), .li_r(i1r), .li_d(i1d), .flt(f1));
    end endgenerate
    ot_s81sl_lep u_lep (.clk(clk), .rst_n(rst_n), .ro(lro), .ri(lri),
        .lo0_v(l0v), .lo0_r(l0r), .lo0_d(l0d), .lo1_v(l1v), .lo1_r(l1r), .lo1_d(l1d),
        .li0_v(i0v), .li0_r(i0r), .li0_d(i0d), .li1_v(i1v), .li1_r(i1r), .li1_d(i1d), .rxv(rxv),
        .sl_f(sf), .l0_f(f0), .l1_f(f1), .fault(fault));
endmodule

// die masters (dsdv_slice_lepw: s_0S / s_0N; dsdv_slice_lepe: s_7S / s_7N)
module ot_s81sl_slice_lepw (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_e, output wire [1103:0] ro_e,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf, output wire fault
);
    ot_s81sl_slice_lep #(.SIDE(0)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_e), .ro_n(ro_e), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .ch_b(ch_b),
        .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1), .tf(tf), .fault(fault));
endmodule
module ot_s81sl_slice_lepe (
    input  wire clk, input wire rst_n, input wire [3:0] sid,
    input  wire [1103:0] ri_w, output wire [1103:0] ro_w,
    input  wire [275:0] vi, output wire [275:0] vo, input wire [1103:0] bi, output wire [1103:0] bo,
    output wire [4*1104-1:0] xc, input wire [8*70-1:0] rt,
    output wire [15:0] ck_line, output wire [1:0] ck_v, output wire [15:0] ck_xc, output wire [7:0] ck_rt,
    input  wire ch_b, output wire [511:0] tx0, output wire [511:0] tx1, input wire [513:0] rx0, input wire [513:0] rx1,
    output wire [1:0] tf, output wire fault
);
    ot_s81sl_slice_lep #(.SIDE(1)) u (.clk(clk), .rst_n(rst_n), .sid(sid), .ri_n(ri_w), .ro_n(ro_w), .vi(vi), .vo(vo),
        .bi(bi), .bo(bo), .xc(xc), .rt(rt), .ck_line(ck_line), .ck_v(ck_v), .ck_xc(ck_xc), .ck_rt(ck_rt), .ch_b(ch_b),
        .tx0(tx0), .tx1(tx1), .rx0(rx0), .rx1(rx1), .tf(tf), .fault(fault));
endmodule
