`timescale 1ns/1ps
// Unified compiler-slot lane supersedes the diagnostic two-FIFO BF transport.
`ifdef DSFD_PQ_STATIC_X2
`define DSFD_PQ_HAS_BF_X2
`else
`ifdef DSFD_PQ_BF_X2
`define DSFD_PQ_HAS_BF_X2
`define DSFD_PQ_DIAG_BF_X2
`endif
`endif
// ---------------------------------------------------------------------------------------------------------------------
// dsfd_sp_pq_n (s81-die-rtl-bind 2026-10-14): the S81 layer-die PQ core slot under the --rtl-bind die netlist, as a
// wires-only CLUSTER over
//   u_core  ot_s81_pq_core_native   the production PQ core (PHW 10 / SAW 14 / KMAX 6144 / R 128), itself a wires-only
//                                   cluster of hardened leaves; its leaf set is chosen by the OT_PQ_* defines of the die
//                                   RTL manifest (physical/s81_die_rtl/layer1.f), its clock entries pass straight to die
//                                   pins (the die delivers phi - R at each)
//   the three ROM macros (die instances pqrom0..2, ot_rom_4096x72_m8) abut the core's E face and ARE the core's
//                                   "two-cycle synchronous ROM": address launched by a core flop at edge t, sampled
//                                   by the macro at t + 1 (rd_out <= word), captured by the core at t + 2 -- no
//                                   register here (one would make it three cycles: DSFD_PQ_ROM_MUT_REG, the bench's
//                                   negative control)
// DSFD_PQ_STATIC_X2 selects the actual static successor: xw/xe[1100:0]
// {BF low536 extension, legacy564 payload, valid}, one common clock/valid and
// one cycle latency at full rate; xws/xes are historical observation inputs,
// with no effect on data, validity, faults or progress. No FIFO-ready rule is
// used in this mode. Without the define, the legacy/diagnostic transports below
// remain for historical comparisons.
//   u_lane  dsfd_pq_lx              the x lane: the q-family fields of the native 1,634-b broadcast f_bus packed into the
//                                   die's 564-b lane word {cc 15 | x1 266 | x0 283} + valid, registered at the pins, one
//                                   copy per lane start block (W / E); lane-FIFO overrun is a sticky fault into the core
// Die ports (every one is a leaf pin; no logic at this level):
//   clock entries ck_ctl ck_qb ck_fault ck_aq ck_ix ck_bc (+ the split leaves' entries) ck_lane; rst (async, low)
//   f_iss[92:0]  issuer  {f_fault, i_fmt 2, i_ops 19, i_obase 19, i_xps 19, i_xbase 19, i_np 3, i_ph 10, go}
//   t_iss[38:0]  status  {ev_tag 2, ev_end, ev_go, phase_cycles 32, fault, idle, ready}
//   t_vm[19:0]   x read request {x_addr 19, x_re}          f_vm[2048:0]  x read return {x_q 2048, x_rv}
//   ra0/ra1 [11:0], ra2 [13:0], rc0/rc1/rc2: ROM macro address / enable;  rq0 / rq1 [63:0], rq2 [47:0]: macro data (rd_out)
//   t_cnt[457:0] = mdr (per-tag return configuration replica, to the count-only return leaves)
//   f_cnt[203:0] = {q2f 12, ga 192} from them
//   xw / xe [564:0] lane words to the hx_W / hx_E start blocks, xws / xes [2:0] their status {0, w_live, w_rdy}
// The BF16 family of f_bus (go_bf, xb_* = 1,068 b) has NO die lane here (the x lane carries the q family): those core
// outputs are open, and the BF fronts' xb pins are reported unconnected by tools/die_port_bind.py -- the BF transport
// is a die decision (union lane 1,085 b on BF frames, or a serial BF beat), not hidden.
// ROM use: the phase ROMs hold 2 x 1024 phases (PHW 9) in rows 0..2047 of a 4,096-row macro, the banked stream ROM 16,384 rows (four4096-row macros):
// the unused address MSBs are tied 0 at this level; the macros read every cycle (ce tied 1: the core has no enable).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_sp_pq_n (
    input  wire          ck_ctl, ck_qb, ck_fault,
`ifdef OT_PQ_QB_PIPE
    input wire ck_qb_align,
`endif
`ifdef OT_PQ_QB_PHYS_SPLIT
    input  wire [3:0]    ck_qb_aux,
`endif
    input  wire [1:0]    ck_aq,
`ifdef OT_PQ_AQ_PHYS_SPLIT
    input  wire [15:0]   ck_aq_aux,
`endif
    input  wire [3:0]    ck_ix,
`ifdef OT_PQ_IX_PHYS_SPLIT
`ifdef OT_PQ_IX_BANK_SPLIT
    input  wire [31:0]   ck_ix_read,
`else
    input  wire [15:0]   ck_ix_read,
`endif
`endif
`ifdef OT_PQ_BC_SLICED
    input  wire [15:0]   ck_bc,
`else
    input  wire [3:0]    ck_bc,
`endif
    input  wire          ck_lane,
    input  wire          rst,
    input  wire [92:0]   f_iss,
`ifdef OT_PQ_CTL_STATIC
    input wire calendar_v,input wire[74:0] calendar_action,
    output wire stream_end_v,output wire[1:0] stream_end_tag,
`endif
    output wire [38:0]   t_iss,
    output wire [19:0]   t_vm,
    input  wire [2048:0] f_vm,
    output wire [11:0]   ra0, ra1,
    output wire [13:0]   ra2,
    output wire          rc0, rc1, rc2,
    input  wire [63:0]   rq0, rq1,
    input  wire [47:0]   rq2,
    output wire [457:0]  t_cnt,
    input  wire [203:0]  f_cnt,
`ifdef DSFD_PQ_STATIC_X2
    output wire [1100:0] xw, xe,
`else
    output wire [564:0]  xw, xe,
`endif
    input  wire [2:0]    xws, xes
`ifdef DSFD_PQ_DIAG_BF_X2
    ,output wire [536:0] x2w, x2e
    ,input wire [2:0] x2ws, x2es
`endif
);
    wire [10:0]    pa0, pa1;
    wire [13:0]   sa;
    wire [63:0]   pq0, pq1;
    wire [47:0]   sq;
    wire [1633:0] f_bus;
    wire          f_fault_c;
    ot_s81_pq_core_native u_core (
        .ck_ctl(ck_ctl), .ck_qb(ck_qb), .ck_fault(ck_fault),
`ifdef OT_PQ_QB_PIPE
        .ck_qb_align(ck_qb_align),
`endif
`ifdef OT_PQ_QB_PHYS_SPLIT
        .ck_qb_aux(ck_qb_aux),
`endif
        .ck_aq(ck_aq),
`ifdef OT_PQ_AQ_PHYS_SPLIT
        .ck_aq_aux(ck_aq_aux),
`endif
        .ck_ix(ck_ix),
`ifdef OT_PQ_IX_PHYS_SPLIT
        .ck_ix_read(ck_ix_read),
`endif
        .ck_bc(ck_bc),
`ifdef OT_PQ_CTL_STATIC
        .calendar_v(calendar_v),.calendar_action(calendar_action),
        .stream_end_v(stream_end_v),.stream_end_tag(stream_end_tag),
`endif
        .rst_n(rst), .go(f_iss[0]), .i_ph(f_iss[10:1]), .i_np(f_iss[13:11]), .i_xbase(f_iss[32:14]),
        .i_xps(f_iss[51:33]), .i_obase(f_iss[70:52]), .i_ops(f_iss[89:71]), .i_fmt(f_iss[91:90]),
        .ready(t_iss[0]), .idle(t_iss[1]), .x_re(t_vm[0]), .x_addr(t_vm[19:1]), .x_rv(f_vm[0]), .x_q(f_vm[2048:1]),
        .q2f_i(f_cnt[203:192]), .ga_i(f_cnt[191:0]), .mdr_o(t_cnt),
        .f_fault(f_fault_c), .fault(t_iss[2]), .phase_cycles(t_iss[34:3]), .ev_go(t_iss[35]), .ev_end(t_iss[36]),
        .ev_tag(t_iss[38:37]), .f_bus(f_bus),
        .rom_pa0(pa0), .rom_pa1(pa1), .rom_pq0(pq0), .rom_pq1(pq1), .rom_sa(sa), .rom_sq(sq));
    // ROM macros: address MSBs / enables are constant ties (phase rows2048..4095 unused; stream addr14 selects four real4096 banks)
    assign ra0 = {1'b0, pa0};
    assign ra1 = {1'b0, pa1};
    assign ra2 = sa;
    assign {rc0, rc1, rc2} = 3'b111;
`ifdef DSFD_PQ_ROM_MUT_REG
    // negative control only: a relay stage on the ROM data (three-cycle ROM) must FAIL the die-slot bench
    reg [63:0] pq0_q, pq1_q; reg [47:0] sq_q;
    always @(posedge ck_lane) begin pq0_q <= rq0; pq1_q <= rq1; sq_q <= rq2; end
    assign pq0 = pq0_q; assign pq1 = pq1_q; assign sq = sq_q;
`else
    assign pq0 = rq0; assign pq1 = rq1; assign sq = rq2;
`endif
    dsfd_pq_lx u_lane (.ck(ck_lane), .rst(rst), .f_bus(f_bus), .f_fault(f_iss[92]), .xws(xws), .xes(xes),
        .xw(xw), .xe(xe), .f_fault_c(f_fault_c)
`ifdef DSFD_PQ_DIAG_BF_X2
        ,.x2w(x2w), .x2e(x2e), .x2ws(x2ws), .x2es(x2es)
`endif
    );
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// dsfd_pq_lx: x lane leaf.  f_bus (native order, msb first) = {cfg, ph 10, np 3, go, gobf, tag 2, qv, p 8, qb 3, sv 2,
// q0 256, e0 10, q1 256, e1 10, qp 3, bfp 3, bv, bfb 3, bsv 4, u 32, d 1024} -> the die lane word (tools/dsrom_s81_fulldie.py
// X0B / X1B / CCB, dsfd_cfifo split, q element pins):
//   x0 = {xs_v = qv, xs_sv = sv, xs_pos = qp, xs_p = p, xs_b = qb, xs_e0 = e0, xs_q0 = q0}   (283, lsb q0)
//   x1 = {xs_e1 = e1, xs_q1 = q1}                                                         (266)
//   cc = {cfg_np = np, cfg_ph = ph (the field's sequencers decode PHW 10), cfg_go = cfg, go}   (15)
//   word = {cc, x1, x0, v}, v = qv | go | cfg (the cfifo qualifies xs_v / go / cfg_go by the word valid)
// One registered copy per start block (W / E: each its own pin group), +1 cycle on every lane field.  The start block's
// status {0, w_live, w_rdy} is captured at the pin; a word presented while its block was not ready (or not live) is a
// sticky lane overrun, ORed with the issuer's f_fault into the core's f_fault (registered).
// ---------------------------------------------------------------------------------------------------------------------
module dsfd_pq_lx (
    input  wire          ck,
    input  wire          rst,
    input  wire [1633:0] f_bus,
    input  wire          f_fault,
    input  wire [2:0]    xws, xes,
`ifdef DSFD_PQ_STATIC_X2
    output reg [1100:0] xw, xe,
`else
    output reg  [564:0]  xw, xe,
`endif
    output reg           f_fault_c
`ifdef DSFD_PQ_DIAG_BF_X2
    ,output reg [536:0] x2w, x2e
    ,input wire [2:0] x2ws, x2es
`endif
);
    wire        cfg = f_bus[1633];
    wire [9:0]  ph  = f_bus[1632:1623];
    wire [2:0]  np  = f_bus[1622:1620];
    wire        go  = f_bus[1619];
    wire        qv  = f_bus[1615];
    wire [7:0]  p   = f_bus[1614:1607];
    wire [2:0]  qb  = f_bus[1606:1604];
    wire [1:0]  sv  = f_bus[1603:1602];
    wire [255:0] q0 = f_bus[1601:1346];
    wire [9:0]  e0  = f_bus[1345:1336];
    wire [255:0] q1 = f_bus[1335:1080];
    wire [9:0]  e1  = f_bus[1079:1070];
    wire [2:0]  qp  = f_bus[1069:1067];
`ifdef DSFD_PQ_LX_MUT_SWAP
    wire [282:0] x0 = {qv, sv, qp, p, qb, e0, q0[254:0], q0[255]};
`else
    wire [282:0] x0 = {qv, sv, qp, p, qb, e0, q0};
`endif
    wire [265:0] x1 = {e1, q1};
    wire [14:0]  cc = {np, ph, cfg, go};
`ifdef DSFD_PQ_HAS_BF_X2
    // Authoritative die map: physical/s81_die_pins/v20/bf_x2_lane.json.
    wire [1067:0] xb = {f_bus[1023:0], f_bus[1055:1024], f_bus[1059:1056],
                       f_bus[1062:1060], f_bus[1063], f_bus[1066:1064], f_bus[1618]};
    wire bv = f_bus[1063] | f_bus[1618];
    wire collision = (f_bus[1063] && (qv || go || cfg)) || (f_bus[1618] && qv);
    wire [564:0] w = bv ? {cc, xb[1067:802], 17'd0, xb[801:536], 1'b1} : {cc, x1, x0, qv | go | cfg};
`ifdef DSFD_PQ_X2_MUT_SWAP
    wire [536:0] w2 = bv ? {1'b1, xb[535:2], xb[0], xb[1]} : 537'd0;
`else
    wire [536:0] w2 = bv ? {1'b1, xb[535:0]} : 537'd0;
`endif
`ifndef DSFD_PQ_STATIC_X2
    reg [2:0] s2w_q, s2e_q;
    always @(posedge ck) begin x2w <= w2; x2e <= w2; s2w_q <= x2ws; s2e_q <= x2es; end
`endif
`else
    wire [564:0] w = {cc, x1, x0, qv | go | cfg};
`endif
`ifdef DSFD_PQ_STATIC_X2
    // One registered 1,101-bit transport, consumed on fixed compiler slots.
    // Valid is bit 0; legacy payload is [564:1]; BF extension is [1100:565].
    // No lane-ready signal participates in data, validity, fault or progress.
    // w2[536] is redundant with w[0] for BF words and is deliberately omitted.
    wire [1100:0] static_word = {w2[535:0], w};
    always @(posedge ck) begin xw <= static_word; xe <= static_word; end
    reg collision_fault;
    always @(posedge ck or negedge rst)
        if (!rst) begin collision_fault <= 1'b0; f_fault_c <= 1'b0; end
        else begin
            if (collision) collision_fault <= 1'b1;
            f_fault_c <= f_fault | collision | collision_fault;
        end
`else
    reg  [2:0]   sw_q, se_q;
    reg          ovf;
    reg [1:0]    rs_q;
    always @(posedge ck or negedge rst) if (!rst) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    always @(posedge ck) begin xw <= w; xe <= w; sw_q <= xws; se_q <= xes; end
    // xw[0] / xe[0] (the word valid) was presented last cycle; the block's w_rdy of that cycle is sw_q[0] now
    always @(posedge ck or negedge rs_q[1])
        if (!rs_q[1]) begin ovf <= 1'b0; f_fault_c <= 1'b0; end
        else begin
            if ((xw[0] && !(sw_q[0] && sw_q[1])) || (xe[0] && !(se_q[0] && se_q[1]))) ovf <= 1'b1;
`ifdef DSFD_PQ_DIAG_BF_X2
            if (collision || (x2w[536] && !(s2w_q[0] && s2w_q[1])) ||
                (x2e[536] && !(s2e_q[0] && s2e_q[1]))) ovf <= 1'b1;
`endif
            f_fault_c <= f_fault | ovf;
        end
`endif // legacy ready/overrun diagnostic transport
endmodule

`ifdef DSFD_PQ_HAS_BF_X2
`undef DSFD_PQ_HAS_BF_X2
`endif

`ifdef DSFD_PQ_DIAG_BF_X2
`undef DSFD_PQ_DIAG_BF_X2
`endif
