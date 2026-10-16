`timescale 1ns/1ps
// OT_QFD_VM_NOX (2026-10-14, owner 08:20 PT: distributed x slices, el1014-qwen-dvm-build.log): the TRIMMED central VM.
// The x read is REMOVED from the port list (me_en_t, x_dv / x_dc / x_dcs / x_dsp, x_q, x_rdy, x_fault, x_hazard) and
// the region tile is ot_qfd_vm_region_nx (rtl/qwen_sys/vm_nox_20261014: no x FIFOs, no xv / pop / me_in / xo / ovf).
// Inside, the x descriptor is the constant "no tuple" (an internal wire, not a port), so the x schedule, rotation,
// planes and line logic never issue and synthesis removes them; banks, SU reads / writes, row reads, skid writes, the
// merge of the ME result links and me_en (maxima writes, row-read admission) are unchanged edge for edge.
`ifdef OT_QFD_VM_NOX
`ifndef OT_QFD_VM_TILE_MOD
`define OT_QFD_VM_TILE_MOD ot_qfd_vm_region_nx
`endif
`endif
`ifndef OT_QFD_VM_TILE_MOD
`define OT_QFD_VM_TILE_MOD ot_qfd_vm_grp
`endif
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_sp_vector_memory_bv (qwen-vm-me 2026-10-08): the banked vector memory of qwen-rtl-finish
// (ot_qfd_sp_vector_memory: 64 row banks, the parallel ME x service) completed with the ports the token bench's
// behavioural VM has and the banked one lacked:
//
//   SU lane reads   the split stream unit's 3 x SW scalar lanes (va / vb / vc).  Served by DEDICATED BANKS: NSU = 3
//                   replica copies of the row-banked store, one per operand, so the ME x beats (copy 0) and the three
//                   SU operands never compete for a macro read port.  A replica is NRBS = 16 row banks of two
//                   ot_sram_1r1w_1024x256 macros (row r in bank r mod 16, 695 of 1,024 lines used): 32 macros a copy
//                   against copy 0's 128 ot_sram_1r1w_256x256 (the x beats need 64 banks), 2.4x denser.  The SU sends each operand as a descriptor
//                   {re0, re1, a0, a1} (lane 0 / lane 1 strobes and addresses: every lane reads a0 + l * (a1 - a0),
//                   ot_hdc_vstream_lane), stride a1 - a0 in {0, 1} (the Qwen program's VM operand strides; else
//                   w_fault).  A vector of SW lanes spans <= NWR = (SW + 30) / 16 consecutive rows = NWR distinct
//                   banks: conflict-free in its copy.  Answer: all SW lanes, FIXED latency 1 + VL edges after the
//                   strobe (VL = 7; the base answers at 1): the SU master runs its lanes at ot_hdc_vstream_lane
//                   ML = max(VL, its constant-ROM ML) and delays this answer by ML - VL.
//   SU lane writes  {mask[SW], a0, a1, data}: <= NWR rows (stride 1) or one element (stride 0: the highest masked lane
//                   wins, as the base's lane-ordered commit).
//   reducer write   one element (skid source), the sequencer's row write w_* (skid source), the tree top's per-slot
//                   maxima row mx_* (engine-edge sampled, skid source).
//   ME results      NB = 6 band serializer links (ot_qfd_res_ser) into the 6:1 merge (ot_qfd_res_merge, inside), one
//                   row a cycle onto the bank-write arbiter; land_cnt counts landed bursts for the tree top.
// Writes are BROADCAST to every copy at the same edge (the copies stay identical).  Uniform latency (the exactness
// argument): every read and every write presented at edge t reaches the macros at edge t + 4 (SU reads: descriptor
// register, broadcast register, per-bank address register beside the macro; writes: descriptor register, row
// formation register, per-bank write register beside the macro), and a 1R1W macro reads the old word when it is
// written in the same edge, so an SU read sees exactly the writes presented before it, as the base.  Per bank, the SU
// lane rows have priority (fixed timing, distinct banks; banks counted mod NRBS, which divides NRB, so a grant set
// is conflict-free in every copy); the three skid sources (in the base's commit order mx, rd,
// seq) take a free bank, else wait in a SQD-row queue; the merge's row takes what is left.  An entry that misses its
// nominal edge is LATE: a read of its row (any copy) or another write onto its row while it is late is w_hazard (the
// contract, as the x path's: programs never touch such a row within the few edges of a bank conflict); a queue
// overflow is w_fault.  The x path (copy 0) is ot_qfd_sp_vector_memory's, its hazard check now over every landing row.
// SKID CAPACITY RULE (2026-10-13, after SEED 9 of tb_qfd_vm_bv_ports lost a sequencer row: three row writes on three
// consecutive edges, the first denied twice by SU lane rows on its bank, against a 2-deep head-of-line queue).  The
// skid ports carry no ready and no spacing rule (one row an edge is legal on each), and a bank takes one row an edge,
// so the memory states what it absorbs and the queue is built to absorb exactly that:
//   * WORK-CONSERVING: every waiting row (not only the oldest of its source) is written on the first edge on which
//     its bank (mod NRBS) is taken neither by an SU lane row nor by a waiting row that goes first (order mx, rd, seq;
//     within a source the older row).  Rows of one source on one bank therefore keep their order; a row is never held
//     behind a row for ANOTHER bank.
//   * hence the rows of a source waiting at an edge are a function of the PRESENTED traffic only (a per-bank server
//     of one row an edge behind the SU lane rows), and the rule is: at most SQD rows of one source wait at once.
//     Sizing: a row presented every edge and denied for D consecutive edges needs D + 1 entries; SQD = 4 covers the
//     longest hold of one bank by a stride-<= 1 lane stream (ceil(16 / SW) + 1 edges: 3 at SW 8, 2 at SW 64) at the
//     full rate of one row an edge.  Traffic beyond the rule is refused loudly: the row is dropped and w_fault rises
//     at the next edge (fail-stop, never a silent loss).
// The bench carries the rule as an independent model (tb_qfd_vm_bv_ports `wmodel`) and requires the memory to raise
// w_fault exactly when the model overflows.  MUT = 14: the queues hold 2 rows (the pre-fix capacity; must FAIL).
// ME result rows reach the memory at a variable time; the tree top counts LANDED bursts, so consumers that wait on
// its progress / idle (the base's contract for ME outputs) see them.
// me_ok: AND of the band serializers' rok (to the die's me_mem_ok), registered.
// MUT = 1: the SU read lane select takes the element one lane off (bench must FAIL).  MUT = 2: the x shift is off
// by one lane (ot_qfd_sp_vector_memory's mutant).
// ---------------------------------------------------------------------------------------------------------------------
// SU replica bank: NRBS-banked rows (512 b) in two ot_sram_1r1w_1024x256 macros (USE_MACRO) or a behavioural model
// with the same one-edge registered read.
module ot_qfd_vm_rowbank_s #(
    parameter integer DEPTH = 1024,
    parameter integer LAW = 10,
    parameter integer USE_MACRO = 0
) (
    input  wire          clk,
    input  wire          re,
    input  wire [LAW-1:0] raddr,
    output wire [511:0]  q,
    input  wire          we,
    input  wire [LAW-1:0] waddr,
    input  wire [15:0]   wmask,
    input  wire [511:0]  wdata
);
    wire [511:0] bm;
    genvar e;
    generate for (e = 0; e < 16; e = e + 1) begin : g_m
        assign bm[32*e +: 32] = {32{wmask[e]}};
    end endgenerate
    generate if (USE_MACRO != 0) begin : g_mac
        wire [9:0] ra = raddr, wa = waddr;
        ot_sram_1r1w_1024x256_m2_r2c2 u_lo (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(q[255:0]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wdata[255:0]), .w_mask_in(bm[255:0]),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
        ot_sram_1r1w_1024x256_m2_r2c2 u_hi (.clk(clk), .r_ce_in(re), .r_addr_in(ra), .rd_out(q[511:256]),
            .w_ce_in(we), .w_addr_in(wa), .wd_in(wdata[511:256]), .w_mask_in(bm[511:256]),
            .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end else begin : g_beh
        reg [511:0] mem [0:DEPTH-1];
        reg [511:0] qr;
        integer i;
        initial for (i = 0; i < DEPTH; i = i + 1) mem[i] = 512'd0;
        always @(posedge clk) begin
            if (re) qr <= mem[raddr];
            if (we) mem[waddr] <= (mem[waddr] & ~bm) | (wdata & bm);
        end
        assign q = qr;
    end endgenerate
endmodule


module ot_qfd_sp_vector_memory_bv #(
    parameter integer USE_OBSERVER_CLOCKS = 0,
    parameter integer STATIC_SCHEDULE = 0,
    parameter integer USE_LEAF_CLOCKS = 0,
    parameter integer ELEMS = 177808,
    parameter integer NRB = 64,
    parameter integer AW = 24,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer XVM = 14,
    parameter integer BMAX = 8,
    parameter integer ND = 14,
    parameter [ND*8-1:0] DSET = {8'd96, 8'd64, 8'd48, 8'd32, 8'd24, 8'd16, 8'd12, 8'd8, 8'd6, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0},
    parameter integer SW = 64,
    parameter integer NSU = 3,
    parameter integer NB = 6,
    parameter integer CRB = 4,
    parameter integer SQD = 4,                         // skid rows a source may have waiting (capacity rule above)
    parameter integer NRBS = 16,                       // banks of each SU replica copy (rows r mod NRBS)
    parameter integer USE_MACRO = 0,
    parameter integer MUT = 0,
    // XQT = 1 (fe-push-qwen-1010, 2026-10-10; 0 = unchanged): the x-descriptor beat count without a divider.  Every
    // bv route stopped at floorplan with -2,429 ps on x_dsp -> span_n = ((1 << x_dsp) - 1) * x_dcs -> bq = span_n / BEAT
    // (a 37-bit divide by the constant 1,008) -> h_b[0].  The span is a shift-subtract ((x_dcs << x_dsp) - x_dcs, equal
    // mod 2^37), and the beat count is a table over the legal descriptor set (x_dcs in DSET via the din one-hot, x_dsp
    // in [SMIN, SMAX]) evaluated at elaboration.  Same edges, 0 cycles; identical h_b / x_fault for every legal
    // descriptor; an illegal descriptor raises x_fault exactly as before (its h_b is then 0 instead of the divider's
    // value: the faulted tuple's beats are unspecified).  XQT = 2: bench negative control (DSET entry 1's count + 1).
    parameter integer XQT = 0,
    // el1011-q-sp 2026-10-11 (main decision: near-square slot, x rate unchanged, me_en one edge early + regional
    // replicas).  MEE = 1: me_en_e is me_en one edge early; every me_en use is a registered regional replica (control,
    // 8 x-stage regions, the tiles), so no port drives the ~160k engine-enabled flops.  VMT = 1 (requires NRB % 8 == 0,
    // NRBS % (NRB / 8) == 0, 1 <= RO <= RV + 1): the banks are NRB / 8 hardened tiles ot_qfd_vm_grp behind RV clock relays
    // (in) and RO relays (out); x latency + XS = RV + RO + 7 engine edges (the x consumer's XVM grows by XS), SU answer
    // latency + SX = RV + RO + 5 edges (the SU master's VL = 7 + SX), row read + RV + RO + 8 edges (r_qv-tagged)
    // (r5: + TLX 5 / TLS 4 / TLR 6 from the tile's in-tile wire relays).
    parameter integer MEE = 0,
    parameter integer VMT = 0,
    parameter integer RV = 1,
    parameter integer RO = 2,
    // qwen-tp8-vm 2026-10-13 (0 = unchanged): BIT-PLANE x transport (requires VMT = 1, XPR >= RO).  The tiles' x words
    // take XPR me-enabled relay leaves (ot_qfd_vm_xrelay_t), then 32 plane leaves (ot_qfd_vm_xplane_t: pin flop, rot1,
    // rot2, bv for one bit position of every element) replace the parent's rot1 / rot2 / bv.  x latency
    // + XPR + 1 - RO engine edges (the x consumer's XVM grows by it); pop, NPP, SU and row paths unchanged.
    // MUT = 3 / 4 / 5: plane 5's fine rotation / element shift / range count wrong; MUT = 6: a relay free-runs;
    // MUT = 7: planes 0 and 1 swapped at the leaves' outputs (all must FAIL).
    parameter integer XPR = 0,
    // qwen-tp8-vm-rtl 2026-10-13 (all 0 = unchanged; need XPR != 0 and VMT = 1).  Registered trees and leaf owners
    // around the bit plane (ot_qfd_vm_xtree.sv), so that NO x-transport logic and no one-edge broadcast stays here:
    //   XTK  levels of the two CONTROL trees (ot_qfd_vm_fantree, EN 1): plane control {beat address, in-range count}
    //        and the line / x_q control.  Each is tapped XTK engine edges early in the seam queue / the s and h
    //        pipelines, so the leaves see it on the original edge: latency + 0.
    //   XMK  levels of the me tree (EN 0, MEE = 1): me_en_t is me_en (XMK + 1) edges early; the tree's last level is
    //        the me_e of every relay / plane / region / fan / line / face leaf, <= XMF sinks per node.
    //   XLO  1: line and x_q are owned by leaves: 32 x ot_qfd_vm_xcol_t (plane + line of one bit position in ONE
    //        leaf, PLAN 2026-10-13), XQR x_q relay stages (ot_qfd_vm_xrelay_t)
    //        and ot_qfd_vm_xqface_t at the consumer face.  x latency + XQR + 2 engine edges (the x consumer's XVM
    //        grows by it; the schedule here runs against XVM - XQR - 2).
    // MUT = 8: a plane-control tree node is transparent; 9: a me-tree node; 10: line leaf 3 picks a wrong source;
    // 11: face 0 free-runs; 12: a line-control tree node is transparent; 13: one x_q relay free-runs (all must FAIL).
    parameter integer XTK = 0,
    parameter integer XMK = 0,
    parameter integer XMF = 16,
    parameter integer XLO = 0,
    parameter integer XQR = 0,
    // Q-VMWB 2026-10-15 (0 = unchanged): PAR_RB = 1 (requires STATIC_SCHEDULE) lands every ME result lane rb_*[j] on
    // its own bank in the same edge (up to NB rows an edge) instead of the one-row OR merge.  The compiler calendar
    // (qfd_res_train_par: bands lag by one burst) puts concurrent lane rows on distinct banks mod NRBS; a same-bank
    // pair (lane/lane, lane/SU row, lane/skid row) is a sticky static_conflict fault, never arbitrated.  Each bank
    // write register selects the matching lane by an AND-OR over the lanes (rows distinct mod NRBS); same write
    // stages as the merge row (rb pins -> bank write register -> macro), 0 added edges.  land_cnt counts the lanes'
    // `end` beats.  PMUT (bench negative control): 1 = lane 1 takes lane 2's data.
    parameter integer PAR_RB = 0,
    parameter integer PMUT = 0,
    parameter integer READ_CONTROL_LEAVES = 0,
    parameter integer RETURN_LEAVES = 0, // opt-in: existing E6/E7/E8 registers in 32 standard bit-plane leaves per copy
    parameter integer RETURN_CLOCKS = 0, // 1: independent return_ck pin per leaf; 0: component equivalence on clk
    parameter integer NATIVE_BANKS = 0   // Q-VMWB 2026-10-15: native storage successors in every region (ot_qfd_vm_region_nx)
) (
    input  wire                    clk,
    input wire [NSU*32-1:0] return_ck,
    input wire [NSU-1:0] read_control_ck,
`ifdef OT_QFD_VM_NOX
    input  wire [(NRB/8)*56-1:0]    leaf_ck,
    input wire [NRB-1:0] observer_ck,
    output wire [511:0]             qr_commit_mask,
    output wire [NRB-1:0] write_commit_v,
    output wire [NRB*LAW-1:0] write_commit_line,
    output wire [NRB*16-1:0] write_commit_mask,
    input wire aw_v,
    input wire [AW-5:0] aw_row,
    input wire [511:0] aw_data,
    output wire aw_cr,
`endif
    input  wire                    rst_n,
    input  wire                    me_en,
    input  wire                    me_en_e,        // MEE: me_en one edge early
`ifndef OT_QFD_VM_NOX
    input  wire                    me_en_t,        // XMK: me_en (XMK + 1) edges early (unused when XMK = 0)
    // x descriptor (tree top)
    input  wire                    x_dv,
    input  wire [AW-1:0]           x_dc,
    input  wire [AW-1:0]           x_dcs,
    input  wire [3:0]              x_dsp,
    output wire [(1<<SMAX)*32-1:0] x_q,
    output wire                    x_rdy,
    output reg                     x_fault,
    output reg                     x_hazard,
`endif
    // SU lane reads (operand o = 0 a, 1 b, 2 c): descriptors, answers 1 + VL edges later
    input  wire [NSU-1:0]          s_re0,
    input  wire [NSU-1:0]          s_re1,
    input  wire [NSU*AW-1:0]       s_a0,
    input  wire [NSU*AW-1:0]       s_a1,
    output wire [NSU*SW*32-1:0]    s_q,
    // SU lane writes
    input  wire [SW-1:0]           sw_mask,
    input  wire [AW-1:0]           sw_a0,
    input  wire [AW-1:0]           sw_a1,
    input  wire [SW*32-1:0]        sw_data,
    // reducer write
    input  wire                    rd_v,
    input  wire [AW-1:0]           rd_addr,
    input  wire [31:0]             rd_data,
    // sequencer row write / read
    input  wire                    w_v,
    input  wire [AW-5:0]           w_row,
    input  wire [15:0]             w_mask,
    input  wire [511:0]            w_data,
    input  wire                    r_v,
    output wire                    r_rdy,
    input  wire [AW-5:0]           r_row,
    output wire                    r_qv,
    output wire [511:0]            r_q,
    // tree top per-slot maxima (engine-clock registers)
    input  wire                    mx_we,
    input  wire [AW-1:0]           mx_addr,
    input  wire [15:0]             mx_mask,
    input  wire [511:0]            mx_data,
    // ME result links (band serializers)
    input  wire [NB-1:0]           rb_v,
    input  wire [NB-1:0]           rb_end,
    input  wire [NB-1:0]           rb_nul,
    input  wire [NB*(AW-4)-1:0]    rb_row,
    input  wire [NB*16-1:0]        rb_mask,
    input  wire [NB*512-1:0]       rb_data,
    output wire [NB-1:0]           rb_cr,
    input  wire [NB-1:0]           rb_ok,
    output reg                     me_ok,
    output wire [15:0]             land_cnt,
    output reg                     w_fault,
    output reg                     w_hazard
);
`ifdef OT_QFD_VM_NOX
    // no x read: the descriptor is the constant "no tuple"; x_q / x_rdy / x_fault / x_hazard have no consumer
    wire                    me_en_t = 1'b0;
    wire                    x_dv = 1'b0;
    wire [AW-1:0]           x_dc = {AW{1'b0}};
    wire [AW-1:0]           x_dcs = {AW{1'b0}};
    wire [3:0]              x_dsp = 4'd0;
    wire [(1<<SMAX)*32-1:0] x_q;
    wire                    x_rdy;
    reg                     x_fault, x_hazard;
`ifndef SYNTHESIS
    initial if (XPR != 0 || XTK != 0 || XMK != 0 || XLO != 0 || VMT == 0)
        $fatal(1, "ot_qfd_sp_vector_memory_bv OT_QFD_VM_NOX: needs VMT 1 and XPR / XTK / XMK / XLO 0");
`endif
`endif
    localparam integer RW = AW - 4;
    localparam integer NX = 1 << SMAX;
    localparam integer LNRB = $clog2(NRB);
    localparam integer ROWS = (ELEMS + 15) / 16;
    localparam integer DEPTH = (ROWS + NRB - 1) / NRB;
    localparam integer LAW = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer BEAT = (NRB - 1) * 16;
    localparam integer LB = $clog2(BMAX) + 1;
    localparam integer HL = XVM + 2;
    localparam integer XBP = (VMT != 0 && XPR != 0) ? 1 : 0;                  // bit-plane transport built
    localparam integer XOWN = (XBP != 0 && XLO != 0) ? 1 : 0;                 // line / x_q owned by leaves
    localparam integer XO = (XOWN != 0) ? XQR + 2 : 0;                        // their added x edges
    localparam integer XVMI = XVM - XO;                                       // the schedule's x latency
    // XS: the tile FIFO is pushed 4 clocks after the beat's issue edge (relays RV, pin flop, macro, capture); the pop
    // must land at least one edge later (a same-edge pop of an empty FIFO reads the entry being written: gate 18:3x
    // DBG OVF push=1 pop=1 cnt=0), so the pop source is one stage later than the push and x gains RV + RO + 2 edges.
    // TNI / TNX / TNS: the tile's in-tile wire relays (ot_qfd_vm_grp NRI / NRX / NRS, r5); TLX / TLR / TLS the latency
    // they add to the x, row-read and SU paths.
    localparam integer TNI = 2, TNX = 2, TNS = 1;
    localparam integer TLX = (VMT != 0) ? 1 + TNI + TNX : 0;
    localparam integer TLR = (VMT != 0) ? 2 + TNI + TNX : 0;
    localparam integer TLS = (VMT != 0) ? 1 + TNI + TNS : 0;
    localparam integer XA = (VMT != 0 && XPR != 0) ? XPR + 1 - RO : 0;   // bit-plane transport: added x edges
    localparam integer XRN = (VMT != 0 && XPR != 0) ? XPR : RO;          // x relays after the tile's xo register
    localparam integer XS = (VMT != 0) ? RV + RO + 2 + TLX + XA : 0;  // extra engine edges, x path (rot1 at issue + 4 + XS)
    localparam integer SX = (VMT != 0) ? RV + RO + 1 + TLS : 0;  // extra edges, SU answers
    localparam integer RL = (VMT != 0) ? RV + RO + 5 + TLR : 3;  // row read: r_qr at r_v + 2 (+ RV + RO + 2 + TLR)
    localparam integer NPP = RV + 6 + TLX;                       // tile x FIFO: beats in flight between push and pop
    // r6: the tile distributes pop through one more engine-edge stage (pin flop per bank -> per-slice replica), so the
    // pop source is one x stage earlier (TPP) and lands on the same edge as before; XS / NPP unchanged.
    localparam integer TPP = (VMT != 0) ? 1 : 0;
    localparam integer XPOP = 4 + RV - RO + TLX - TPP;           // the x stage whose valid becomes the tiles' pop
    localparam integer NG = (NRB >= 8) ? NRB / 8 : 1;
    localparam integer NSB = NRBS / NG;
    localparam integer NWR = (SW + 30) / 16;           // rows an SU vector can span
    localparam integer NWE = NWR * 16;
    localparam integer LSW = (SW > 1) ? $clog2(SW) : 1;
    localparam integer NP = NWR + 7;                   // coarse-rotate positions
`ifdef OT_QFD_VM_NOX
    localparam integer NK = 4;
`else
    localparam integer NK = 3;                         // skid sources: 0 mx, 1 rd, 2 seq (base commit order)
`endif
    localparam integer LNRBS = $clog2(NRBS);
    localparam integer DEPTHS = (ROWS + NRBS - 1) / NRBS;
    localparam integer LAWS = (DEPTHS > 1) ? $clog2(DEPTHS) : 1;
    localparam integer NPS = (NWR + 7 < NRBS) ? NWR + 7 : NRBS;   // coarse-rotate positions of an SU copy
    localparam integer NQ = NK * SQD;                  // skid entries, in grant order (source major, oldest first)
    localparam integer LSQ = $clog2(SQD + 1);
    localparam integer QCAP = (MUT == 14) ? 2 : SQD;   // MUT 14: the pre-fix capacity
    localparam integer NL = 2 * NQ;                    // late rows checked per cycle (queue entries + late grants)
    integer i, a, di, k, b;
    genvar g, gc, c, dd;

    // ---- me_en: the port (MEE 0) or registered replicas of me_en_e (MEE 1): control + 8 x-stage regions ----
    wire       me_c;
    wire [7:0] me_x;
    genvar mr;
    generate if (MEE != 0) begin : g_mee
        (* keep *) reg me_cr;
        always @(posedge clk) me_cr <= me_en_e;
        assign me_c = me_cr;
        for (mr = 0; mr < 8; mr = mr + 1) begin : g_r
            (* keep *) reg me_xr;
            always @(posedge clk) me_xr <= me_en_e;
            assign me_x[mr] = me_xr;
        end
    end else begin : g_mep
        assign me_c = me_en;
        assign me_x = {8{me_en}};
    end endgenerate
    // ---- me_e of every x-transport LEAF (qwen-tp8-vm-rtl 2026-10-13).  Consumers in physical order: per region the
    //      tile and its 8 x XRN x relays; the 32 planes and their control tree; the 32 line leaves, their control tree,
    //      the x_q relays and the faces.  XMK = 0: all take the me_en_e broadcast (as before).  XMK > 0: the last level
    //      of the me tree, <= XMF consumers per node. ----
    localparam integer RWX = (NX >= 512) ? 512 : NX;            // x_q relay leaf width (one plane, RWX elements)
    localparam integer NQS = NX / RWX;
    localparam integer FW = (NX * 32 >= 1024) ? 1024 : NX * 32; // x_q face leaf width (element-major)
    localparam integer NF = (NX * 32) / FW;
    localparam integer MCG = 1 + 8 * XRN;
    localparam integer MB_P = ((NRB >= 8) ? NRB / 8 : 1) * MCG;
    localparam integer MB_PC = MB_P + 32;
    localparam integer MB_L = MB_PC + XTK * 8;
    localparam integer MB_LC = MB_L;                            // PLAN 2026-10-13: the line leaf is inside the plane leaf (ot_qfd_vm_xcol_t): one me pin
    localparam integer MB_QR = MB_LC + XTK * 8 * XOWN;
    localparam integer MB_F = MB_QR + 32 * NQS * XQR * XOWN;
    localparam integer NMC = MB_F + NF * XOWN;
    wire [NMC-1:0] me_lf;
    generate if (XBP != 0 && XMK != 0 && MEE != 0) begin : g_met
        localparam integer NML = (NMC + XMF - 1) / XMF;
        wire [NML-1:0] mq;
        ot_qfd_vm_fantree #(.W(1), .K(XMK), .NLAST(NML), .FO(XMF), .NS(NML), .EN(0),
            .MUTL((MUT == 9) ? XMK - 1 : -1), .MUTI(0)) u_met (.clk(clk), .me_e({(XMK*NML){1'b0}}), .d(me_en_t), .q(mq));
        genvar mc;
        for (mc = 0; mc < NMC; mc = mc + 1) begin : g_c
            assign me_lf[mc] = mq[(mc * NML) / NMC];
        end
    end else begin : g_mef
        assign me_lf = {NMC{(MEE != 0) ? me_en_e : me_en}};
    end endgenerate
`ifdef OT_QFD_VM_NOX
    wire [(NRB/8)*512-1:0] qr_masks;
    reg [511:0] qcm_or;
    integer qci;
    always @* begin qcm_or = 512'd0; for (qci=0;qci<NRB/8;qci=qci+1) qcm_or=qcm_or|qr_masks[512*qci +:512]; end
    assign qr_commit_mask = qcm_or;
`endif
    // =================================================================================================================
    // x path (copy 0), as ot_qfd_sp_vector_memory
    // =================================================================================================================
    reg  [HL-1:0] h_new;
    reg  [AW-1:0] h_dc [0:HL-1];
    reg  [AW-1:0] h_d  [0:HL-1];
    reg  [3:0]    h_sp [0:HL-1];
    reg  [LB-1:0] h_b  [0:HL-1];
    reg  [AW+12:0] h_span [0:HL-1];
    reg           p_v;
    reg  [AW-1:0] p_dc, p_d;
    reg  [3:0]    p_sp;
    wire           same = p_v && x_dv && p_dc == x_dc && p_d == x_dcs && p_sp == x_dsp;
    wire           nt = x_dv && !same;
    reg  [ND-1:0]  din;
    always @(*) for (di = 0; di < ND; di = di + 1) din[di] = (x_dcs == DSET[di*8 +: 8]);
    wire [AW+12:0] span_n;
    wire [LB-1:0]  bq_lo;                                // bq[LB-1:0]
    wire           bq_ge;                                // bq >= BMAX
    generate if (XQT != 0) begin : g_xqt
        function automatic [63:0] xq_beats(input integer d, input integer sp);
            xq_beats = (((64'd1 << sp) - 64'd1) * d) / BEAT;
        endfunction
        wire [AW+12:0] dcs_w = {{13{1'b0}}, x_dcs};
        assign span_n = (dcs_w << x_dsp) - dcs_w;
        reg [LB-1:0] t_lo;
        reg          t_ge;
        integer td, ts;
        always @(*) begin
            t_lo = 0; t_ge = 1'b0;
            for (td = 0; td < ND; td = td + 1)
                for (ts = SMIN; ts <= SMAX; ts = ts + 1)
                    if (din[td] && x_dsp == ts) begin
                        t_lo = t_lo | (xq_beats(DSET[td*8 +: 8], ts) + ((XQT == 2 && td == 1) ? 64'd1 : 64'd0));
                        t_ge = t_ge | (xq_beats(DSET[td*8 +: 8], ts) >= BMAX);
                    end
        end
        assign bq_lo = t_lo;
        assign bq_ge = t_ge;
    end else begin : g_xdiv
        assign span_n = (({{13{1'b0}}, {AW{1'b0}}} | ((1 << x_dsp) - 1)) * x_dcs);
        wire [AW+12:0] bq = span_n / BEAT;
        assign bq_lo = bq[LB-1:0];
        assign bq_ge = (bq >= BMAX);
    end endgenerate
    reg            bi_v;
    reg  [LB-1:0]  bi_j;
    reg  [AW-1:0]  bi_dc, bi_d;
    reg  [3:0]     bi_sp;
    reg  [1:0]     bi_n;
    reg  [AW+12:0] bi_end;                               // the tuple's last element
    always @(*) begin
        bi_v = 1'b0; bi_j = 0; bi_dc = 0; bi_d = 0; bi_sp = 0; bi_n = 0; bi_end = 0;
        for (a = 0; a < HL; a = a + 1)
            if (h_new[a] && a + h_b[a] >= XVMI - 7 - XS && a <= XVMI - 8 - XS) begin
                bi_v = 1'b1; bi_j = a + h_b[a] - (XVMI - 7 - XS); bi_dc = h_dc[a]; bi_d = h_d[a]; bi_sp = h_sp[a];
                bi_end = h_dc[a] + h_span[a];
                bi_n = bi_n + 1'b1;
            end
    end
    reg [LB+1:0] xcnt;
    assign x_rdy = (xcnt == BMAX);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) xcnt <= BMAX;
        else if (me_c) xcnt <= nt ? 0 : (xcnt == BMAX) ? xcnt : xcnt + 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            h_new <= 0; p_v <= 1'b0; x_fault <= 1'b0;
        end else if (me_c) begin
            h_new <= {h_new[HL-2:0], nt};
            p_v <= x_dv; p_dc <= x_dc; p_d <= x_dcs; p_sp <= x_dsp;
            if (nt && (bq_ge || !(|din) || x_dsp > SMAX || x_dsp < SMIN)) x_fault <= 1'b1;
            if (bi_n > 1) x_fault <= 1'b1;
        end
    end
    always @(posedge clk) if (me_c) begin
        for (a = HL - 1; a > 0; a = a - 1) begin
            h_dc[a] <= h_dc[a-1]; h_d[a] <= h_d[a-1]; h_sp[a] <= h_sp[a-1]; h_b[a] <= h_b[a-1]; h_span[a] <= h_span[a-1];
        end
        h_dc[0] <= x_dc; h_d[0] <= x_dcs; h_sp[0] <= x_dsp; h_b[0] <= bq_lo + 1'b1; h_span[0] <= span_n;
    end
    wire [AW-1:0] ba = bi_dc + bi_j * BEAT;
    wire [AW-5:0] br0 = ba[AW-1:4];
    // only the banks of the rows the beat needs read (ba .. min(ba + BEAT - 1, the tuple's end)): a beat never touches
    // a row outside its tuple's span (the late-write hazard check is then exact for the x path too)
    wire [AW+12:0] bl_e = (ba + BEAT - 1 < bi_end) ? ba + BEAT - 1 : bi_end;
    wire [AW+8:0]  bnr = bl_e[AW+12:4] - br0 + 1'b1;      // rows the beat reads (<= NRB)
    reg  [NRB-1:0] b_re;
    reg  [NRB*LAW-1:0] b_ra;
    assign r_rdy = !(me_c && bi_v);
    generate for (g = 0; g < NRB; g = g + 1) begin : g_s0
        wire [AW-5:0] rowb = br0 + ((g - br0) & (NRB - 1));
        always @(posedge clk) begin
            b_re[g] <= (me_c && bi_v && (((g - br0) & (NRB - 1)) < bnr)) || (r_v && r_rdy && (r_row[LNRB-1:0] == g));
            b_ra[g*LAW +: LAW] <= (me_c && bi_v) ? rowb[LNRB +: LAW] : r_row[LNRB +: LAW];
        end
    end endgenerate
    reg  s1_bv, s2_bv, s3_bv, s4_bv, s5_bv, s6_bv;
    reg  [1:0] bpp, s1_pp, s2_pp, s3_pp;
    reg  [LB-1:0] s1_j, s2_j, s3_j, s4_j, s5_j, s6_j;
    reg  [AW-1:0] s1_a, s2_a, s3_a, s4_a, s5_a;
    reg  [ND-1:0] s1_d, s2_d, s3_d, s4_d, s5_d, s6_d;
    reg  [3:0]    s1_sp, s2_sp, s3_sp, s4_sp, s5_sp, s6_sp;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin s1_bv <= 0; s2_bv <= 0; s3_bv <= 0; s4_bv <= 0; s5_bv <= 0; s6_bv <= 0; bpp <= 2'd0; end
        else if (me_c) begin
            s1_bv <= bi_v; s2_bv <= s1_bv; s3_bv <= xs_bv; s4_bv <= s3_bv; s5_bv <= s4_bv; s6_bv <= s5_bv;
            if (bi_v) bpp <= (bpp == 2'd2) ? 2'd0 : bpp + 2'd1;
        end
    end
    // ---- VMT: XS engine edges between s2 and s3 (the tile seam: relays in, FIFO, relays out) ----
    wire            xs_bv;
    wire [LB-1:0]   xs_j;
    wire [AW-1:0]   xs_a;
    wire [ND-1:0]   xs_d;
    wire [3:0]      xs_sp;
    wire            x_pop;                                  // the tiles' FIFO pop source (stage XPOP's valid)
    generate if (XS == 0) begin : g_nxs
        assign xs_bv = s2_bv; assign xs_j = s2_j; assign xs_a = s2_a; assign xs_d = s2_d; assign xs_sp = s2_sp;
        assign x_pop = 1'b0;
    end else begin : g_xs
        localparam integer QW = LB + AW + ND + 4;
        reg [XS-1:0]    qb;
        reg [XS*QW-1:0] qd;
        always @(posedge clk or negedge rst_n) if (!rst_n) qb <= 0; else if (me_c) qb <= {qb, s2_bv};
        always @(posedge clk) if (me_c) qd <= {qd, s2_j, s2_a, s2_d, s2_sp};
        assign xs_bv = qb[XS-1];
        assign {xs_j, xs_a, xs_d, xs_sp} = qd[(XS-1)*QW +: QW];
        if (XPOP == 1) begin : g_p1
            assign x_pop = s1_bv;
        end else if (XPOP == 2) begin : g_p2
            assign x_pop = s2_bv;
        end else begin : g_pq
            assign x_pop = qb[XPOP-3];
        end
    end endgenerate
    reg [ND-1:0] bdin;
    always @(*) for (di = 0; di < ND; di = di + 1) bdin[di] = (bi_d == DSET[di*8 +: 8]);
    always @(posedge clk) if (me_c) begin
        s1_j <= bi_j; s1_a <= ba; s1_d <= bdin; s1_sp <= bi_sp; s1_pp <= bpp; s2_pp <= s1_pp; s3_pp <= s2_pp;
        s6_j <= s5_j; s6_d <= s5_d; s6_sp <= s5_sp;
        s2_j <= s1_j; s2_a <= s1_a; s2_d <= s1_d; s2_sp <= s1_sp;
        s3_j <= xs_j; s3_a <= xs_a; s3_d <= xs_d; s3_sp <= xs_sp;
        s4_j <= s3_j; s4_a <= s3_a; s4_d <= s3_d; s4_sp <= s3_sp;
        s5_j <= s4_j; s5_a <= s4_a; s5_d <= s4_d; s5_sp <= s4_sp;
    end

    // =================================================================================================================
    // write side: SU lane rows (formation), skid queues, the result merge, the per-bank write registers
    // =================================================================================================================
    // ---- E1: input registers ----
    reg  [SW-1:0]    e1_m;
    reg  [AW-1:0]    e1_a0, e1_a1;
    reg  [SW*32-1:0] e1_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) e1_m <= 0; else e1_m <= sw_mask;
    always @(posedge clk) begin e1_a0 <= sw_a0; e1_a1 <= sw_a1; e1_d <= sw_data; end
    // skid sources: input registers (mx sampled on engine edges: the tree top's mx is an engine-clock register)
    reg  [NK-1:0]  k1_v;
    reg  [RW-1:0]  k1_row [0:NK-1];
    reg  [15:0]    k1_mask [0:NK-1];
    reg  [511:0]   k1_data [0:NK-1];
    always @(posedge clk or negedge rst_n) if (!rst_n) k1_v <= 0; else k1_v <= {
`ifdef OT_QFD_VM_NOX
        aw_v,
`endif
        w_v, rd_v, me_c && mx_we};
    always @(posedge clk) begin
        if (me_c) begin k1_row[0] <= mx_addr[RW-1:0]; k1_mask[0] <= mx_mask; k1_data[0] <= mx_data; end
        k1_row[1] <= rd_addr[AW-1:4]; k1_mask[1] <= 16'd1 << rd_addr[3:0]; k1_data[1] <= {16{rd_data}};
`ifdef OT_QFD_VM_NOX
        k1_row[3] <= aw_row; k1_mask[3] <= 16'hffff; k1_data[3] <= aw_data;
`endif
        k1_row[2] <= w_row; k1_mask[2] <= w_mask; k1_data[2] <= w_data;
    end
    // ---- E2: SU rows formed (window of NWR rows from row r0), ELEMS-bounded ----
    wire [AW-1:0] e1_si = e1_a1 - e1_a0;
    reg  [LSW-1:0] hi_l;
    always @(*) begin hi_l = 0; for (i = 0; i < SW; i = i + 1) if (e1_m[i]) hi_l = i; end
    reg            f_v;
    reg  [RW-1:0]  f_r0;
    reg  [NWE-1:0] f_m;
    reg  [NWE*32-1:0] f_d;
    reg            f_bad;
    wire [3:0]     e1_off = e1_a0[3:0];
    wire           e1_s0 = !e1_m[1] || (e1_si == 0);
    generate for (g = 0; g < NWE; g = g + 1) begin : g_form
        reg        mm;
        reg [31:0] md;
        integer ll;
        always @(*) begin
            mm = 1'b0; md = 32'd0; ll = g - e1_off;
            if (e1_s0) begin
                if (g == e1_off) begin mm = |e1_m; md = e1_d[hi_l*32 +: 32]; end
            end else begin
                if (ll >= 0 && ll < SW) begin mm = e1_m[ll]; md = e1_d[ll*32 +: 32]; end
            end
            if ({e1_a0[AW-1:4], 4'h0} + g >= ELEMS) mm = 1'b0;
        end
        always @(posedge clk) begin f_m[g] <= mm; f_d[g*32 +: 32] <= md; end
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin f_v <= 1'b0; f_bad <= 1'b0; end
        else begin f_v <= |e1_m; f_bad <= (|e1_m) && e1_m[1] && e1_si > 1; end
    end
    always @(posedge clk) f_r0 <= e1_a0[AW-1:4];
    // ---- skid queues (pushed at E2), ELEMS-bounded masks ----
    reg  [RW-1:0]  q_row  [0:NK*SQD-1];
    reg  [15:0]    q_mask [0:NK*SQD-1];
    reg  [511:0]   q_data [0:NK*SQD-1];
    reg  [SQD-1:0] q_v    [0:NK-1];
    reg  [SQD-1:0] q_late [0:NK-1];
    reg  [15:0]    k1_mb  [0:NK-1];
    always @(*) for (k = 0; k < NK; k = k + 1)
        for (i = 0; i < 16; i = i + 1) k1_mb[k][i] = k1_mask[k][i] && ({k1_row[k], 4'h0} + i < ELEMS);
    // every entry is a grant candidate (work-conserving queue); flat index e = source * SQD + age rank (0 oldest)
    reg  [NQ-1:0] qvf;
    always @(*) for (k = 0; k < NK; k = k + 1) for (i = 0; i < SQD; i = i + 1) qvf[k*SQD + i] = q_v[k][i];
    // ---- merge ----
    wire           m_v, m_nowr, m_land;
    wire [RW-1:0]  m_row;
    wire [15:0]    m_mask;
    wire [511:0]   m_data;
    wire           m_take;
    wire           m_busy, m_fault;
    reg  [15:0]    m_mb;
    always @(*) for (i = 0; i < 16; i = i + 1) m_mb[i] = m_mask[i] && ({m_row, 4'h0} + i < ELEMS);
    generate if(STATIC_SCHEDULE!=0)begin : g_static_merge
        reg [RW-1:0] row;reg [15:0] mask;reg [511:0] data;
        reg nv,nul,en;integer j,n;
        reg [15:0] landed;
        reg bad;
        always @* begin
            row=0;mask=0;data=0;nv=0;nul=0;en=0;n=0;
            for(j=0;j<NB;j=j+1)if(rb_v[j])begin
                n=n+1;nv=1;row=row|rb_row[RW*j+:RW];mask=mask|rb_mask[16*j+:16];
                data=data|rb_data[512*j+:512];nul=nul|rb_nul[j];en=en|rb_end[j];
            end
        end
        integer nend;
        always @* begin nend=0; for(j=0;j<NB;j=j+1) if(rb_v[j] && rb_end[j]) nend=nend+1; end
        assign m_v=(PAR_RB!=0) ? 1'b0 : nv;assign m_nowr=nul;assign m_land=en;
        assign m_row=row;assign m_mask=mask;assign m_data=data;
        assign m_busy=nv;assign m_fault=bad;assign land_cnt=landed;
        assign rb_cr=0; // Historical parent-only output; absent from the static native die interface.
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin landed<=0;bad<=0;end
            else begin
                if(PAR_RB==0 && (n>1 || (nv && !m_take)))bad<=1;
                if(PAR_RB!=0) landed<=landed+16'(nend);
                else if(nv && en)landed<=landed+1'b1;
            end
        initial if(PAR_RB!=0 && NB>8) $fatal(1,"PAR_RB lanes > 8");
    end else begin : g_legacy_merge
        initial if(PAR_RB!=0) $fatal(1,"PAR_RB requires STATIC_SCHEDULE");
    ot_qfd_res_merge #(.NB(NB), .W(16), .RW(RW), .CRB(CRB)) u_merge (.clk(clk), .rst_n(rst_n),
        .b_v(rb_v), .b_end(rb_end), .b_nul(rb_nul), .b_row(rb_row), .b_mask(rb_mask), .b_data(rb_data), .b_cr(rb_cr),
        .m_v(m_v), .m_nowr(m_nowr), .m_land(m_land), .m_row(m_row), .m_mask(m_mask), .m_data(m_data),
        .m_take(m_take), .land_cnt(land_cnt), .busy(m_busy), .fault(m_fault));
    end endgenerate
    // ---- PAR_RB result lanes (each lane is its own bank write source; unused when PAR_RB = 0) ----
    reg  [NB-1:0]     pl_w;                             // lane j writes a row this edge
    reg  [NB*RW-1:0]  pl_row;
    reg  [NB*16-1:0]  pl_mb;
    reg  [NB*512-1:0] pl_data;
    always @(*) begin
        for (i = 0; i < NB; i = i + 1) begin
            pl_w[i] = (PAR_RB != 0) && rb_v[i] && !rb_nul[i];
            pl_row[RW*i +: RW] = rb_row[RW*i +: RW];
            pl_data[512*i +: 512] = (PMUT == 1 && i == 1 && NB > 2) ? rb_data[512*2 +: 512] : rb_data[512*i +: 512];
            for (k = 0; k < 16; k = k + 1)
                pl_mb[16*i + k] = rb_mask[16*i + k] && ({rb_row[RW*i +: RW], 4'h0} + k < ELEMS);
        end
    end
    // ---- E2 -> E3: per-bank arbitration ----
    reg  [NRB-1:0] su_hit;
    reg  [NRB*3-1:0] su_k;
    always @(*) begin
        for (b = 0; b < NRB; b = b + 1) begin : su_b
            reg [LNRB-1:0] kk;
            kk = b[LNRB-1:0] - f_r0[LNRB-1:0];
            su_k[b*3 +: 3] = kk[2:0];
            su_hit[b] = f_v && (kk < NWR) && (|f_m[kk*16 +: 16]);
        end
    end
    // grants in the SU copies' bank space (NRBS | NRB: a set of rows distinct mod NRBS is distinct mod NRB)
    reg  [NRBS-1:0] su_hs;
    always @(*) begin
        for (b = 0; b < NRBS; b = b + 1) begin : su_bs
            reg [LNRBS-1:0] kk;
            kk = b[LNRBS-1:0] - f_r0[LNRBS-1:0];
            su_hs[b] = f_v && (kk < NWR) && (|f_m[kk*16 +: 16]);
        end
    end
    // An entry is granted when its bank is taken neither by an SU lane row nor by an entry that goes first (any
    // valid earlier entry on the bank: it is either granted or denied by the SU row, the bank is taken either way).
    // Pairwise bank compares, no priority chain through the bank set.
    reg  [NQ-1:0]  ge;                                  // skid entry grants
    reg            gm;
    integer e, e2;
    always @(*) begin : arb
        reg bl;
        for (e = 0; e < NQ; e = e + 1) begin
            bl = su_hs[q_row[e][LNRBS-1:0]];
            for (e2 = 0; e2 < e; e2 = e2 + 1)
                if (qvf[e2] && q_row[e2][LNRBS-1:0] == q_row[e][LNRBS-1:0]) bl = 1'b1;
            ge[e] = qvf[e] && !bl;
        end
        bl = su_hs[m_row[LNRBS-1:0]];
        for (e = 0; e < NQ; e = e + 1) if (qvf[e] && q_row[e][LNRBS-1:0] == m_row[LNRBS-1:0]) bl = 1'b1;
        gm = m_v && !m_nowr && !bl;
        if(STATIC_SCHEDULE!=0)begin ge=qvf;gm=m_v && !m_nowr;end
    end
`ifdef OT_QFD_VM_NOX
    // Return every attention-row credit exactly once after its skid entry is granted. The arbiter may grant
    // several rows in one cycle; serialise the count into pulses rather than losing simultaneous credits.
    generate if(STATIC_SCHEDULE!=0)begin : g_no_credit
        assign aw_cr=1'b0;
    end else begin : g_aw_credit
    reg [7:0] aw_return;
    integer aw_taken, aq;
    always @* begin aw_taken=0; for(aq=3*SQD;aq<4*SQD;aq=aq+1) if(ge[aq]) aw_taken=aw_taken+1; end
    assign aw_cr = (aw_return != 0) || (aw_taken != 0);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) aw_return<=0; else aw_return<=aw_return+aw_taken-aw_cr;
    end endgenerate
`endif
    assign m_take = m_v && (m_nowr || gm);
    // per-bank write registers (beside the bank; written into every copy's macro the next edge)
    reg  [NRB-1:0]      bw_we;
    reg  [NRB*LAW-1:0]  bw_line;
    reg  [NRB*16-1:0]   bw_mask;
    reg  [NRB*512-1:0]  bw_data;
    reg  [NRB*3-1:0]    bw_src;
    generate for (g = 0; g < NRB; g = g + 1) begin : g_bw
        wire [2:0] kk = su_k[g*3 +: 3];
        wire [RW-1:0] srow = f_r0 + kk;
        reg  [2:0] src;          // 0 none, 1 su, 2 mx, 3 rd, 4 seq, 5 merge
        // the one granted skid entry of this bank (grants are distinct mod NRBS, so distinct mod NRB): AND-OR select
        reg  [2:0]    es;
        reg  [RW-1:0] er;
        reg  [15:0]   em;
        reg  [511:0]  ed;
        // PAR_RB: the lane row of this bank (lanes are distinct mod NRBS, so at most one matches): AND-OR select
        reg  [NB-1:0] lh;
        reg  [RW-1:0] lr;
        reg  [15:0]   lm;
        reg  [511:0]  ld;
        integer li;
        always @(*) begin
            lh = 0; lr = m_row; lm = m_mb; ld = m_data;
            if (PAR_RB != 0) begin
                lr = 0; lm = 0; ld = 0;
                for (li = 0; li < NB; li = li + 1) if (pl_w[li] && pl_row[RW*li +: LNRB] == g) begin
                    lh[li] = 1'b1; lr = lr | pl_row[RW*li +: RW]; lm = lm | pl_mb[16*li +: 16]; ld = ld | pl_data[512*li +: 512];
                end
            end
        end
        integer ee;
        always @(*) begin
            es = 3'd0; er = {RW{1'b0}}; em = 16'd0; ed = 512'd0;
            for (ee = 0; ee < NQ; ee = ee + 1)
                if (ge[ee] && q_row[ee][LNRB-1:0] == g) begin
                    es = es | ((ee / SQD == 3) ? 6 : ee / SQD + 2); er = er | q_row[ee]; em = em | q_mask[ee]; ed = ed | q_data[ee];
                end
            src = 3'd0;
            if (su_hit[g]) src = 3'd1;
            else if (es != 3'd0) src = es;
            else if (gm && m_row[LNRB-1:0] == g) src = 3'd5;
            else if (|lh) src = 3'd5;
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) bw_we[g] <= 1'b0; else bw_we[g] <= (src != 0);
        always @(posedge clk) begin
            bw_src[g*3 +: 3] <= src;
            case (src)
                3'd1: begin bw_line[g*LAW +: LAW] <= srow[LNRB +: LAW]; bw_mask[g*16 +: 16] <= f_m[kk*16 +: 16];
                            bw_data[g*512 +: 512] <= f_d[kk*512 +: 512]; end
                3'd2, 3'd3, 3'd4, 3'd6: begin bw_line[g*LAW +: LAW] <= er[LNRB +: LAW]; bw_mask[g*16 +: 16] <= em;
                            bw_data[g*512 +: 512] <= ed; end
                default: begin bw_line[g*LAW +: LAW] <= lr[LNRB +: LAW]; bw_mask[g*16 +: 16] <= lm;
                            bw_data[g*512 +: 512] <= ld; end
            endcase
        end
    end endgenerate
    // per-bank write registers of the SU replica copies (NRBS banks, beside them)
    reg  [NRBS-1:0]      ws_we;
    reg  [NRBS*LAWS-1:0] ws_line;
    reg  [NRBS*16-1:0]   ws_mask;
    reg  [NRBS*512-1:0]  ws_data;
    generate for (g = 0; g < NRBS; g = g + 1) begin : g_ws
        wire [LNRBS-1:0] kk = g[LNRBS-1:0] - f_r0[LNRBS-1:0];
        wire [RW-1:0] srow = f_r0 + kk;
        reg  [2:0] src;
        reg           es;
        reg  [RW-1:0] er;
        reg  [15:0]   em;
        reg  [511:0]  ed;
        reg  [NB-1:0] lh;
        reg  [RW-1:0] lr;
        reg  [15:0]   lm;
        reg  [511:0]  ld;
        integer li;
        always @(*) begin
            lh = 0; lr = m_row; lm = m_mb; ld = m_data;
            if (PAR_RB != 0) begin
                lr = 0; lm = 0; ld = 0;
                for (li = 0; li < NB; li = li + 1) if (pl_w[li] && pl_row[RW*li +: LNRBS] == g) begin
                    lh[li] = 1'b1; lr = lr | pl_row[RW*li +: RW]; lm = lm | pl_mb[16*li +: 16]; ld = ld | pl_data[512*li +: 512];
                end
            end
        end
        integer ee;
        always @(*) begin
            es = 1'b0; er = {RW{1'b0}}; em = 16'd0; ed = 512'd0;
            for (ee = 0; ee < NQ; ee = ee + 1)
                if (ge[ee] && q_row[ee][LNRBS-1:0] == g) begin
                    es = 1'b1; er = er | q_row[ee]; em = em | q_mask[ee]; ed = ed | q_data[ee];
                end
            src = 3'd0;
            if (su_hs[g]) src = 3'd1;
            else if (es) src = 3'd2;
            else if (gm && m_row[LNRBS-1:0] == g) src = 3'd5;
            else if (|lh) src = 3'd5;
        end
        always @(posedge clk or negedge rst_n) if (!rst_n) ws_we[g] <= 1'b0; else ws_we[g] <= (src != 0);
        always @(posedge clk) begin
            case (src)
                3'd1: begin ws_line[g*LAWS +: LAWS] <= srow[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= f_m[kk*16 +: 16];
                            ws_data[g*512 +: 512] <= f_d[kk*512 +: 512]; end
                3'd2: begin ws_line[g*LAWS +: LAWS] <= er[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= em;
                            ws_data[g*512 +: 512] <= ed; end
                default: begin ws_line[g*LAWS +: LAWS] <= lr[LNRBS +: LAWS]; ws_mask[g*16 +: 16] <= lm;
                            ws_data[g*512 +: 512] <= ld; end
            endcase
        end
    end endgenerate
    // skid queue state: granted entries leave (any of them), the survivors close up in age order and are late, the
    // E1 register is pushed behind them; a push onto QCAP survivors is the overflow.  Late grants for one cycle.
    reg  [NQ-1:0]     cs_v, cs_new;                    // next state of slot j: valid / the pushed row
    reg  [NQ*LSQ-1:0] cs_src;                          // else the survivor that moves into it
    reg  [NK-1:0]     cs_ovf;
    always @(*) begin : compact
        integer n;
        cs_v = 0; cs_new = 0; cs_src = 0; cs_ovf = 0;
        for (k = 0; k < NK; k = k + 1) begin
            n = 0;
            for (i = 0; i < SQD; i = i + 1)
                if (q_v[k][i] && !ge[k*SQD + i]) begin
                    cs_v[k*SQD + n] = 1'b1; cs_src[(k*SQD + n)*LSQ +: LSQ] = i; n = n + 1;
                end
            if (k1_v[k]) begin
                if (n < QCAP) begin cs_v[k*SQD + n] = 1'b1; cs_new[k*SQD + n] = 1'b1; end
                else cs_ovf[k] = 1'b1;
            end
        end
    end
    reg  [NQ-1:0] lg_v;
    reg  [RW-1:0] lg_row [0:NQ-1];
    reg           q_ovf;
    generate if(STATIC_SCHEDULE!=0)begin : g_static_writes
        // Exactly one fixed pipeline register per source. No occupancy state,compaction,credit or held request.
        integer k,i;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin
                for(k=0;k<NK;k=k+1)begin q_v[k]<=0;q_late[k]<=0;end
                lg_v<=0;q_ovf<=0;
            end else begin
                lg_v<=0;q_ovf<=0;
                for(k=0;k<NK;k=k+1)begin q_v[k]<={{(SQD-1){1'b0}},k1_v[k]};q_late[k]<=0;end
            end
        always @(posedge clk)
            for(k=0;k<NK;k=k+1)begin
                q_row[k*SQD]<=k1_row[k];q_mask[k*SQD]<=k1_mb[k];q_data[k*SQD]<=k1_data[k];
                for(i=1;i<SQD;i=i+1)begin q_row[k*SQD+i]<=0;q_mask[k*SQD+i]<=0;q_data[k*SQD+i]<=0;end
            end
    end else begin : g_legacy_writes
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (k = 0; k < NK; k = k + 1) begin q_v[k] <= 0; q_late[k] <= 0; end
            lg_v <= 0; q_ovf <= 1'b0;
        end else begin
            q_ovf <= |cs_ovf;
            for (k = 0; k < NK; k = k + 1) begin
                q_v[k] <= cs_v[k*SQD +: SQD]; q_late[k] <= cs_v[k*SQD +: SQD] & ~cs_new[k*SQD +: SQD];
                for (i = 0; i < SQD; i = i + 1) lg_v[k*SQD + i] <= ge[k*SQD + i] && q_late[k][i];
            end
        end
    end
    always @(posedge clk) begin
        for (k = 0; k < NK; k = k + 1)
            for (i = 0; i < SQD; i = i + 1) begin
                lg_row[k*SQD + i] <= q_row[k*SQD + i];
                if (cs_new[k*SQD + i]) begin
                    q_row[k*SQD + i] <= k1_row[k]; q_mask[k*SQD + i] <= k1_mb[k]; q_data[k*SQD + i] <= k1_data[k];
                end else if (cs_v[k*SQD + i]) begin
                    q_row[k*SQD + i]  <= q_row[k*SQD + cs_src[(k*SQD + i)*LSQ +: LSQ]];
                    q_mask[k*SQD + i] <= q_mask[k*SQD + cs_src[(k*SQD + i)*LSQ +: LSQ]];
                    q_data[k*SQD + i] <= q_data[k*SQD + cs_src[(k*SQD + i)*LSQ +: LSQ]];
                end
            end
    end
    end endgenerate
    // late rows (queue entries with late set + late grants now in the bank write registers)
    reg  [NL-1:0]  lt_v;
    reg  [NL*RW-1:0] lt_row;
    always @(*) begin
        for (k = 0; k < NK; k = k + 1)
            for (i = 0; i < SQD; i = i + 1) begin
                lt_v[k*SQD + i] = q_v[k][i] && q_late[k][i];
                lt_row[(k*SQD + i)*RW +: RW] = q_row[k*SQD + i];
                lt_v[NQ + k*SQD + i] = lg_v[k*SQD + i];
                lt_row[(NQ + k*SQD + i)*RW +: RW] = lg_row[k*SQD + i];
            end
    end

    // =================================================================================================================
    // banks: copy 0 (x path + row read), copies 1..NSU (SU operand reads); one shared write register per bank
    // =================================================================================================================
    reg [RL-1:0] rr_v;
    reg [LNRB-1:0] rr_b0, rr_b1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rr_v <= 0;
        else rr_v <= {rr_v[RL-2:0], r_v && r_rdy};
    end
    always @(posedge clk) begin rr_b0 <= r_row[LNRB-1:0]; rr_b1 <= rr_b0; end
    reg  m1;
    always @(posedge clk) m1 <= me_c && bi_v;
    assign r_qv = rr_v[RL-1];
    wire [NRB*512-1:0]        capx;     // the x beat's words at the rot1 edge
    wire [NSU-1:0]            su_v3;    // per SU copy: d3_v (aligned with its bank read registers)
    wire [NSU*NRBS-1:0]       su_re;
    wire [NSU*NRBS*LAWS-1:0]  su_ra;
    wire [NSU*NRBS*512-1:0]   su_cap;   // per SU copy: the captured banks (the base's scap), read at d(5 + SX)
    wire                      t_ovf;
    generate if (VMT == 0) begin : g_flat
        wire [NRB*512-1:0] bq_w;
        reg  [NRB*512-1:0] cap0, cap1, cap2;
        reg  m2;
        reg  [1:0] m1_pp, m2_pp;
        for (g = 0; g < NRB; g = g + 1) begin : g_bank
            ot_qfd_vm_rowbank #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_b (.clk(clk),
                .re(b_re[g]), .raddr(b_ra[g*LAW +: LAW]), .q(bq_w[g*512 +: 512]),
                .we(bw_we[g]), .waddr(bw_line[g*LAW +: LAW]), .wmask(bw_mask[g*16 +: 16]), .wdata(bw_data[g*512 +: 512]));
        end
        reg [511:0] r_qr;
        always @(posedge clk) begin
            m1_pp <= bpp; m2 <= m1; m2_pp <= m1_pp;
            if (m2 && m2_pp == 2'd0) cap0 <= bq_w;
            if (m2 && m2_pp == 2'd1) cap1 <= bq_w;
            if (m2 && m2_pp == 2'd2) cap2 <= bq_w;
            if (rr_v[1]) r_qr <= bq_w[rr_b1*512 +: 512];
        end
        assign capx = (s3_pp == 2'd0) ? cap0 : (s3_pp == 2'd1) ? cap1 : cap2;
        assign r_q = r_qr;
        assign t_ovf = 1'b0;
        for (gc = 0; gc < NSU; gc = gc + 1) begin : g_sb
            wire [NRBS*512-1:0] sq_w;
            reg  [NRBS*512-1:0] scap;
            reg                 v4;
            for (g = 0; g < NRBS; g = g + 1) begin : g_bank
                ot_qfd_vm_rowbank_s #(.DEPTH(DEPTHS), .LAW(LAWS), .USE_MACRO(USE_MACRO)) u_b (.clk(clk),
                    .re(su_re[gc*NRBS + g]), .raddr(su_ra[(gc*NRBS + g)*LAWS +: LAWS]), .q(sq_w[g*512 +: 512]),
                    .we(ws_we[g]), .waddr(ws_line[g*LAWS +: LAWS]), .wmask(ws_mask[g*16 +: 16]), .wdata(ws_data[g*512 +: 512]));
            end
            always @(posedge clk) v4 <= su_v3[gc];
            always @(posedge clk) if (v4) scap <= sq_w;
            assign su_cap[gc*NRBS*512 +: NRBS*512] = scap;
        end
    end else begin : g_tile
        //: NG hardened bank-group tiles.  In: the bank read / write registers, x / row / SU capture tags through RV clock
        //: relays (the tile adds its pin flop); the x FIFO pop through RO - 1 engine-edge relays (+ the tile's pin flop).
        //: Out: x words through RO engine-edge relays (me_x replica of the tile's region), row / SU words through RO
        //: clock relays.
        wire [NG*512-1:0] ro_all;
        wire [NG-1:0]     ovf_all;
        genvar kq;
        for (g = 0; g < NG; g = g + 1) begin : g_t
            wire [NSU*NSB-1:0]      t_sre;
            wire [NSU*NSB*LAWS-1:0] t_sra;
            for (gc = 0; gc < NSU; gc = gc + 1) begin : g_sm
                assign t_sre[gc*NSB +: NSB] = su_re[gc*NRBS + g*NSB +: NSB];
                assign t_sra[gc*NSB*LAWS +: NSB*LAWS] = su_ra[(gc*NRBS + g*NSB)*LAWS +: NSB*LAWS];
            end
            wire [7:0] d_re, d_we; wire d_xv, d_rq; wire [NSU*NSB-1:0] d_sre; wire [NSU-1:0] d_sv; wire [NSB-1:0] d_swe;
            ot_hdc_delay #(.W(8 + 8 + 2 + NSU*NSB + NSU + NSB), .D(RV), .RESET(1)) u_iv (.clk(clk), .rst_n(rst_n),
                .d({b_re[g*8 +: 8], bw_we[g*8 +: 8], m1, rr_v[0], t_sre, su_v3, ws_we[g*NSB +: NSB]}),
                .q({d_re, d_we, d_xv, d_rq, d_sre, d_sv, d_swe}));
            wire [8*LAW-1:0] d_ra, d_wl; wire [8*16-1:0] d_wm; wire [8*512-1:0] d_wd; wire [2:0] d_rqb;
            wire [NSU*NSB*LAWS-1:0] d_sra; wire [NSB*LAWS-1:0] d_swl; wire [NSB*16-1:0] d_swm; wire [NSB*512-1:0] d_swd;
            ot_hdc_delay #(.W(16*LAW + 8*16 + 8*512 + 3 + NSU*NSB*LAWS + NSB*LAWS + NSB*16 + NSB*512), .D(RV)) u_id (
                .clk(clk), .rst_n(rst_n),
                .d({b_ra[g*8*LAW +: 8*LAW], bw_line[g*8*LAW +: 8*LAW], bw_mask[g*8*16 +: 8*16], bw_data[g*8*512 +: 8*512],
                    rr_b0[2:0], t_sra, ws_line[g*NSB*LAWS +: NSB*LAWS], ws_mask[g*NSB*16 +: NSB*16],
                    ws_data[g*NSB*512 +: NSB*512]}),
                .q({d_ra, d_wl, d_wm, d_wd, d_rqb, d_sra, d_swl, d_swm, d_swd}));
            wire mxg = me_x[g % 8];
            wire [RO-1:0] pw;                     // pop: pw[0] = source, pw[k] = engine-edge relay k
            assign pw[0] = x_pop;
            for (kq = 1; kq < RO; kq = kq + 1) begin : g_pr
                reg r;
                always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else if (mxg) r <= pw[kq-1];
                assign pw[kq] = r;
            end
            wire [8*512-1:0] xo; wire [511:0] ro_t; wire [NSU*NSB*512-1:0] so_t; wire ovf_t;
`ifdef OT_QFD_VM_NOX
            `OT_QFD_VM_TILE_MOD #(.NBK(8), .NSB(NSB), .NSU(NSU), .DEPTH(DEPTH), .LAW(LAW), .DEPTHS(DEPTHS), .LAWS(LAWS),
                .USE_OBSERVER_CLOCKS(USE_OBSERVER_CLOCKS), .BANK_BASE(8*g), .TOTAL_BANKS(NRB), .USE_MACRO(USE_MACRO), .USE_LEAF_CLOCKS(USE_LEAF_CLOCKS), .NRI(TNI), .NRX(TNX), .NRS(TNS), .NATIVE_BANKS(NATIVE_BANKS)) u_t (
                .clk(clk), .rst_n(rst_n), .leaf_ck(leaf_ck[56*g +: 56]), .observer_ck(observer_ck[8*g+:8]),
                .re(d_re), .ra(d_ra), .we(d_we), .wl(d_wl), .wm(d_wm), .wd(d_wd), .rq(d_rq), .rqb(d_rqb),
                .sre(d_sre), .sra(d_sra), .sv(d_sv), .swe(d_swe), .swl(d_swl), .swm(d_swm), .swd(d_swd),
                .qr_commit_mask(qr_masks[512*g +: 512]),
                .write_commit_v(write_commit_v[8*g+:8]),
                .write_commit_line(write_commit_line[8*LAW*g+:8*LAW]),
                .write_commit_mask(write_commit_mask[128*g+:128]), .ro(ro_t), .so(so_t));
            assign xo = {8*512{1'b0}};
            assign ovf_t = 1'b0;
`else
            `OT_QFD_VM_TILE_MOD #(.NBK(8), .NSB(NSB), .NSU(NSU), .DEPTH(DEPTH), .LAW(LAW), .DEPTHS(DEPTHS), .LAWS(LAWS),
                .USE_MACRO(USE_MACRO), .NPP(NPP), .MEREG((MEE != 0) ? 1 : 0), .NRI(TNI), .NRX(TNX), .NRS(TNS)) u_t (
                .clk(clk), .rst_n(rst_n), .me_in(me_lf[g*MCG]),
                .re(d_re), .ra(d_ra), .we(d_we), .wl(d_wl), .wm(d_wm), .wd(d_wd), .xv(d_xv), .rq(d_rq), .rqb(d_rqb),
                .sre(d_sre), .sra(d_sra), .sv(d_sv), .swe(d_swe), .swl(d_swl), .swm(d_swm), .swd(d_swd),
                .pop(pw[RO-1]), .xo(xo), .ro(ro_t), .so(so_t), .ovf(ovf_t));
`endif
            wire [(XRN+1)*8*512-1:0] xw;         // x words: tile register, then XRN engine-edge relays
            assign xw[0 +: 8*512] = xo;
            if (XPR == 0) begin : g_xsoft
                for (kq = 1; kq <= RO; kq = kq + 1) begin : g_xr
                    reg [8*512-1:0] r;
                    always @(posedge clk) if (mxg) r <= xw[(kq-1)*8*512 +: 8*512];
                    assign xw[kq*8*512 +: 8*512] = r;
                end
            end else begin : g_xleaf            // one 512-b relay leaf per bank per stage, own me replica
                genvar kb;
                for (kq = 1; kq <= XRN; kq = kq + 1) begin : g_xr
                    for (kb = 0; kb < 8; kb = kb + 1) begin : g_b
                        ot_qfd_vm_xrelay_t #(.W(512), .MEREG((MEE != 0) ? 1 : 0),
                            .MUT((MUT == 6 && g == 0 && kb == 3 && kq == XRN) ? 1 : 0)) u_r (.clk(clk),
                            .me_e(me_lf[g*MCG + 1 + (kq-1)*8 + kb]),
                            .d(xw[((kq-1)*8 + kb)*512 +: 512]), .q(xw[(kq*8 + kb)*512 +: 512]));
                    end
                end
            end
            assign capx[g*8*512 +: 8*512] = xw[XRN*8*512 +: 8*512];
            wire [511:0] ro_r;
            ot_hdc_delay #(.W(512), .D(RO)) u_rr (.clk(clk), .rst_n(rst_n), .d(ro_t), .q(ro_r));
            assign ro_all[g*512 +: 512] = ro_r;
            wire [NSU*NSB*512-1:0] so_r;
            ot_hdc_delay #(.W(NSU*NSB*512), .D(RO)) u_sr (.clk(clk), .rst_n(rst_n), .d(so_t), .q(so_r));
            for (gc = 0; gc < NSU; gc = gc + 1) begin : g_sc
                assign su_cap[(gc*NRBS + g*NSB)*512 +: NSB*512] = so_r[gc*NSB*512 +: NSB*512];
            end
            assign ovf_all[g] = ovf_t;
        end
        wire [LNRB-1:0] rbq;
        ot_hdc_delay #(.W(LNRB), .D(RV + RO + 3 + TLR)) u_rb (.clk(clk), .rst_n(rst_n), .d(rr_b0), .q(rbq));
        reg [511:0] r_qr;
        always @(posedge clk) if (rr_v[RV + RO + 3 + TLR]) r_qr <= ro_all[(rbq >> 3)*512 +: 512];
        assign r_q = r_qr;
        assign t_ovf = |ovf_all;
    end endgenerate
    reg [NRB*512-1:0] rot1, rot2;
    reg [BEAT*32-1:0] bv;
    wire [BEAT*32-1:0] bvs;
    wire [32*BEAT-1:0] pq_all;                             // the planes' q, plane-major (bit plane only)
    generate if (XPR == 0 || VMT == 0) begin : g_rsoft
        wire [LNRB-1:0] rot = s3_a[4 +: LNRB];
        always @(posedge clk) begin
            for (i = 0; i < NRB; i = i + 1) if (me_x[(i * 8) / NRB])
                rot1[i*512 +: 512] <= capx[((i + (rot & ~((NRB >= 8) ? 7 : 0))) % NRB)*512 +: 512];
        end
        wire [LNRB-1:0] rotf = s4_a[4 +: LNRB] & ((NRB >= 8) ? 7 : {LNRB{1'b1}});
        always @(posedge clk) begin
            for (i = 0; i < NRB; i = i + 1) if (me_x[(i * 8) / NRB]) rot2[i*512 +: 512] <= rot1[((i + ((NRB >= 8) ? rotf : 0)) % NRB)*512 +: 512];
        end
        wire [3:0] sh = s5_a[3:0] + ((MUT == 2) ? 4'd1 : 4'd0);
        always @(posedge clk) begin
            for (i = 0; i < BEAT; i = i + 1) if (me_x[(i * 8) / BEAT])
                bv[i*32 +: 32] <= ((s5_a + i) < ELEMS) ? rot2[(i + sh)*32 +: 32] : 32'd0;
        end
        assign bvs = bv;
    end else begin : g_plane
        //: 32 plane leaves.  Control at the leaves' pins one engine edge before s3: the beat address (seam-queue
        //: entry XS-1) and nvx, the count of in-range elements of that beat.  XTK = 0: both are broadcast in one edge.
        //: XTK > 0: the same word of the entry XTK places earlier goes through XTK engine-enabled fan levels (1 -> 2
        //: -> 8 nodes -> 4 planes at XTK 3), so the planes see it on the same edge.
        localparam integer NVW = $clog2(BEAT + 1);
        localparam integer QWP = LB + AW + ND + 4;
        localparam integer PCW = LNRB + 4 + NVW;
        wire [AW-1:0] a_pre = g_xs.qd[(XS-2-XTK)*QWP + ND + 4 +: AW];
        wire [AW-1:0] a_tap = g_xs.qd[(XS-1-XTK)*QWP + ND + 4 +: AW];
        reg  [NVW-1:0] nvx;
        always @(posedge clk) if (me_c)
            nvx <= (a_pre >= ELEMS) ? {NVW{1'b0}} : ((ELEMS - a_pre) >= BEAT) ? BEAT[NVW-1:0] : NVW'(ELEMS - a_pre);
        wire [32*PCW-1:0] pcq;
        if (XTK == 0) begin : g_cb
            assign pcq = {32{a_tap[LNRB+3:0], nvx}};
        end else begin : g_ct
            ot_qfd_vm_fantree #(.W(PCW), .K(XTK), .NLAST(8), .FO(4), .NS(32), .EN(1), .MEREG((MEE != 0) ? 1 : 0),
                .MUTL((MUT == 8) ? XTK - 1 : -1), .MUTI(1)) u_ct (.clk(clk), .me_e(me_lf[MB_PC +: XTK*8]),
                .d({a_tap[LNRB+3:0], nvx}), .q(pcq));
        end
        genvar pl, pb;
        for (pl = 0; pl < 32; pl = pl + 1) begin : g_p
            wire [NRB*16-1:0] pd;
            wire [BEAT-1:0]   pq;
            for (pb = 0; pb < NRB*16; pb = pb + 1) begin : g_i
                assign pd[pb] = capx[pb*32 + pl];
            end
            if (XOWN == 0) begin : g_pl        // XOWN: the plane is inside ot_qfd_vm_xcol_t (g_xown), which takes pd and pcq
                ot_qfd_vm_xplane_t #(.NRB(NRB), .MEREG((MEE != 0) ? 1 : 0),
                    .MUT((pl == 5 && MUT >= 3 && MUT <= 5) ? MUT - 2 : 0)) u_p (.clk(clk),
                    .me_e(me_lf[MB_P + pl]), .d(pd), .c_a(pcq[pl*PCW + NVW +: LNRB+4]), .c_nv(pcq[pl*PCW +: NVW]), .q(pq));
                assign pq_all[((MUT == 7 && pl < 2) ? 1 - pl : pl)*BEAT +: BEAT] = pq;
            end
            for (pb = 0; pb < BEAT; pb = pb + 1) begin : g_o
                assign bvs[pb*32 + pl] = pq_all[pl*BEAT + pb];
            end
        end
    end endgenerate
    wire       co_v = h_new[XVMI-1];
    wire [3:0] co_sp = h_sp[XVMI-1];
    generate if (XOWN == 0) begin : g_lflat
        reg [NX*32-1:0] line;
        reg [NX*32-1:0] x_q_r;
        for (c = 0; c < NX; c = c + 1) begin : g_ent
            wire [ND-1:0] hit;
            wire [ND*32-1:0] src;
            for (dd = 0; dd < ND; dd = dd + 1) begin : g_d
                localparam integer DV = DSET[dd*8 +: 8];
                localparam integer JJ = (c * DV) / BEAT;
                localparam integer MM = (c * DV) % BEAT;
                if (JJ < BMAX) begin : g_ok
                    assign hit[dd] = s6_d[dd] && (s6_j == JJ);
                    assign src[dd*32 +: 32] = bvs[MM*32 +: 32];
                end else begin : g_no
                    assign hit[dd] = 1'b0;
                    assign src[dd*32 +: 32] = 32'd0;
                end
            end
            reg [31:0] pick;
            integer kk;
            always @(*) begin
                pick = 32'd0;
                for (kk = 0; kk < ND; kk = kk + 1) if (hit[kk]) pick = src[kk*32 +: 32];
            end
            always @(posedge clk) if (me_x[(c * 8) / NX] && s6_bv && (|hit) && c < (1 << s6_sp)) line[c*32 +: 32] <= pick;
        end
        always @(posedge clk) if (co_v) begin
            for (i = 0; i < NX; i = i + 1) if (me_x[(i * 8) / NX]) x_q_r[i*32 +: 32] <= line[(i & ((1 << co_sp) - 1))*32 +: 32];
        end
        assign x_q = x_q_r;
    end else begin : g_xown
        //: line / x_q in LEAVES ONLY (no flop and no logic here).  32 x ot_qfd_vm_xline_t, one per bit position: its
        //: control {s6 line write, co capture} comes through an engine-enabled fan tree tapped XTK stages early (s
        //: pipeline, below it the seam queue; h pipeline for co), its q is the flat x_q plane one engine edge late.
        //: Then XQR relay stages (RWX-b ot_qfd_vm_xrelay_t, plane-major) and the element-major face leaves.
        localparam integer QWL = LB + AW + ND + 4;
        localparam integer LCW = 1 + ND + LB + 4 + 1 + 4;
        localparam integer SWW = 1 + ND + LB + 4;
        localparam integer XNVW = $clog2(BEAT + 1);
        localparam integer XPCW = LNRB + 4 + XNVW;
        // PLAN 2026-10-13: the placed control chain along the column row needs XTK 7 (13 stations, root at the centre), one
        // more than the 7-entry word pipeline allowed: the seam-queue part now has QE = max(3, XTK - 3) entries (same taps
        // for XTK <= 6; the seam queue holds XS >= XTK + 2 entries whenever the bit plane is on).
        localparam integer QE = (XTK > 6) ? XTK - 3 : 3;
        wire [(QE+4)*SWW-1:0] stg;                             // the line-write word at stage n (QE + 3 = s6 ... QE = s3)
        assign stg[(QE+3)*SWW +: SWW] = {s6_bv, s6_d, s6_j, s6_sp};
        assign stg[(QE+2)*SWW +: SWW] = {s5_bv, s5_d, s5_j, s5_sp};
        assign stg[(QE+1)*SWW +: SWW] = {s4_bv, s4_d, s4_j, s4_sp};
        assign stg[QE*SWW +: SWW] = {s3_bv, s3_d, s3_j, s3_sp};
        genvar sq;
        for (sq = 0; sq < QE; sq = sq + 1) begin : g_sq         // stage QE - 1 = seam-queue entry XS-1, ... 0 = XS-QE
            assign stg[sq*SWW +: SWW] = {g_xs.qb[XS-QE+sq], g_xs.qd[(XS-QE+sq)*QWL + 4 +: ND],
                                         g_xs.qd[(XS-QE+sq)*QWL + ND + 4 + AW +: LB], g_xs.qd[(XS-QE+sq)*QWL +: 4]};
        end
        wire [LCW-1:0] lc_d = {stg[(QE+3-XTK)*SWW +: SWW], h_new[XVMI-1-XTK], h_sp[XVMI-1-XTK]};
        wire [32*LCW-1:0] lcq;
        if (XTK == 0) begin : g_cb
            assign lcq = {32{lc_d}};
        end else begin : g_ct
            ot_qfd_vm_fantree #(.W(LCW), .K(XTK), .NLAST(8), .FO(4), .NS(32), .EN(1), .MEREG((MEE != 0) ? 1 : 0),
                .MUTL((MUT == 12) ? XTK - 1 : -1), .MUTI(2)) u_ct (.clk(clk), .me_e(me_lf[MB_LC +: XTK*8]),
                .d(lc_d), .q(lcq));
        end
        wire [(XQR+1)*32*NX-1:0] xr;                           // plane-major x_q: line leaf q, then XQR relay stages
        genvar lp, lk, ls, lf, lb;
        for (lp = 0; lp < 32; lp = lp + 1) begin : g_l
            wire [LCW-1:0] w = lcq[lp*LCW +: LCW];
            // PLAN 2026-10-13: plane + line of one bit position are ONE leaf (ot_qfd_vm_xcol_t); MUT 7 swaps the data
            // of planes 0 and 1 at the leaves' inputs (the bv plane is no longer a net of this module)
            localparam integer PSRC = (MUT == 7 && lp < 2) ? 1 - lp : lp;
            wire [NRB*16-1:0] cd;
            for (lb = 0; lb < NRB*16; lb = lb + 1) begin : g_i
                assign cd[lb] = capx[lb*32 + PSRC];
            end
            ot_qfd_vm_xcol_t #(.NRB(NRB), .SMIN(SMIN), .SMAX(SMAX), .BMAX(BMAX), .ND(ND), .DSET(DSET),
                .MEREG((MEE != 0) ? 1 : 0), .PMUT((lp == 5 && MUT >= 3 && MUT <= 5) ? MUT - 2 : 0),
                .LMUT((MUT == 10 && lp == 3) ? 1 : 0)) u_l (.clk(clk), .me_e(me_lf[MB_P + lp]),
                .d_lo(cd[NRB*8-1:0]), .d_hi(cd[NRB*16-1:NRB*8]),
                .c_a(g_plane.pcq[lp*XPCW + XNVW +: LNRB+4]), .c_nv(g_plane.pcq[lp*XPCW +: XNVW]),
                .c_v(w[LCW-1]), .c_d(w[LB + 9 +: ND]), .c_j(w[9 +: LB]), .c_sp(w[8:5]),
                .o_v(w[4]), .o_sp(w[3:0]), .q_lo(xr[lp*NX +: NX/2]), .q_hi(xr[lp*NX + NX/2 +: NX/2]));
        end
        for (lk = 1; lk <= XQR; lk = lk + 1) begin : g_r
            for (lp = 0; lp < 32; lp = lp + 1) begin : g_p
                for (ls = 0; ls < NQS; ls = ls + 1) begin : g_s
                    ot_qfd_vm_xrelay_t #(.W(RWX), .MEREG((MEE != 0) ? 1 : 0),
                        .MUT((MUT == 13 && lk == XQR && lp == 7 && ls == 0) ? 1 : 0)) u_r (.clk(clk),
                        .me_e(me_lf[MB_QR + ((lk-1)*32 + lp)*NQS + ls]),
                        .d(xr[((lk-1)*32 + lp)*NX + ls*RWX +: RWX]), .q(xr[(lk*32 + lp)*NX + ls*RWX +: RWX]));
                end
            end
        end
        for (lf = 0; lf < NF; lf = lf + 1) begin : g_f
            wire [FW-1:0] fd;
            for (lb = 0; lb < FW; lb = lb + 1) begin : g_b
                assign fd[lb] = xr[(XQR*32 + ((lf*FW + lb) % 32))*NX + (lf*FW + lb) / 32];
            end
            ot_qfd_vm_xqface_t #(.W(FW), .MEREG((MEE != 0) ? 1 : 0), .MUT((MUT == 11 && lf == 0) ? 1 : 0)) u_f (
                .clk(clk), .me_e(me_lf[MB_F + lf]), .d(fd), .q(x_q[lf*FW +: FW]));
        end
    end endgenerate

    // ---- SU operand copies ----
    wire [NSU-1:0] su_hz;
    generate for (gc = 0; gc < NSU; gc = gc + 1) begin : g_cp
        wire [NRBS-1:0] sb_re;
        wire [NRBS*LAWS-1:0] sb_ra;
        wire d2_bad,d3_v,d5_v,d6_v,d7_v,d7_si;
        wire [AW-1:0] d5_a0,d6_a0,d7_a0;
        if (READ_CONTROL_LEAVES != 0) begin : g_read_control_leaf
            ot_qfd_vm_su_read_control #(.AW(AW),.SW(SW),.NRBS(NRBS),.LAWS(LAWS),.SX(SX)) u_control (
                .ck((RETURN_CLOCKS != 0) ? read_control_ck[gc] : clk),.rst_n(rst_n),
                .re0(s_re0[gc]),.re1(s_re1[gc]),.a0(s_a0[gc*AW+:AW]),.a1(s_a1[gc*AW+:AW]),
                .sb_re(sb_re),.sb_ra(sb_ra),.d2_bad(d2_bad),
                .ov3(d3_v),.ov5(d5_v),.ov6(d6_v),.ov7(d7_v),.osi7(d7_si),
                .oa5(d5_a0),.oa6(d6_a0),.oa7(d7_a0));
        end else begin : g_read_control_flat
        // E1: descriptor registers; E2: broadcast registers (window rows, offset, stride)
        reg           d1_v, d1_r1;
        reg  [AW-1:0] d1_a0, d1_a1;
        reg           d2_v, d2_si;
        reg  [AW-1:0] d2_a0;
        reg  [3:0]    d2_nr;
        reg           d2_bad_flat;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin d1_v <= 1'b0; d2_v <= 1'b0; d2_bad_flat <= 1'b0; end
            else begin
                d1_v <= s_re0[gc]; d2_v <= d1_v;
                d2_bad_flat <= d1_v && d1_r1 && (d1_a1 - d1_a0) > 1;
            end
        end
        wire si1 = d1_r1 && (d1_a1 - d1_a0) == 1;
        always @(posedge clk) begin
            d1_r1 <= s_re1[gc]; d1_a0 <= s_a0[gc*AW +: AW]; d1_a1 <= s_a1[gc*AW +: AW];
            d2_a0 <= d1_a0; d2_si <= si1;
            d2_nr <= si1 ? ((d1_a0[3:0] + SW - 1) >> 4) + 1 : 4'd1;
        end
        // E3: per-bank read registers (beside the macros)
        reg  [NRBS-1:0]      sb_re_flat;
        reg  [NRBS*LAWS-1:0] sb_ra_flat;
        wire [RW-1:0]        d2_r0 = d2_a0[AW-1:4];
        for (g = 0; g < NRBS; g = g + 1) begin : g_ra
            wire [LNRBS-1:0] kk = g[LNRBS-1:0] - d2_r0[LNRBS-1:0];
            wire [RW-1:0]    rr = d2_r0 + kk;
            always @(posedge clk) begin
                sb_re_flat[g] <= d2_v && (kk < d2_nr);
                sb_ra_flat[g*LAWS +: LAWS] <= rr[LNRBS +: LAWS];
            end
        end
        //: d3 .. d(7 + SX): VMT adds SX edges between the bank read registers and the coarse rotate (the tile seam)
        localparam integer DN = 5 + SX;                     // stages d3 .. d(7 + SX)
        reg  [DN-1:0]    dvv, dsv;
        reg  [DN*AW-1:0] dav;
        always @(posedge clk) begin
            dvv <= {dvv, d2_v}; dsv <= {dsv, d2_si}; dav <= {dav, d2_a0};
        end
        wire          d3_v_flat  = dvv[0];
        wire          d5_v_flat  = dvv[2 + SX], d6_v_flat = dvv[3 + SX], d7_v_flat = dvv[4 + SX];
        wire [AW-1:0] d5_a0_flat = dav[(2 + SX)*AW +: AW], d6_a0_flat = dav[(3 + SX)*AW +: AW], d7_a0_flat = dav[(4 + SX)*AW +: AW];
        wire          d7_si_flat = dsv[4 + SX];
            assign sb_re=sb_re_flat;
            assign sb_ra=sb_ra_flat;
            assign d2_bad=d2_bad_flat;
            assign d3_v=d3_v_flat;
            assign d5_v=d5_v_flat;
            assign d6_v=d6_v_flat;
            assign d7_v=d7_v_flat;
            assign d7_si=d7_si_flat;
            assign d5_a0=d5_a0_flat;
            assign d6_a0=d6_a0_flat;
            assign d7_a0=d7_a0_flat;
        end
        assign su_re[gc*NRBS+:NRBS]=sb_re;
        assign su_ra[gc*NRBS*LAWS+:NRBS*LAWS]=sb_ra;
        assign su_v3[gc]=d3_v;
        wire [NRBS*512-1:0] scap = su_cap[gc*NRBS*512 +: NRBS*512];
        if (RETURN_LEAVES != 0) begin : g_return_leaves
            for (genvar plane = 0; plane < 32; plane = plane + 1) begin : g_plane
                wire [NRBS*16-1:0] pd;
                wire [SW-1:0] pq;
                for (genvar elem = 0; elem < NRBS*16; elem = elem + 1) begin : g_unpack
                    assign pd[elem] = scap[elem*32 + plane];
                end
                ot_qfd_vm_su_return_plane #(.ELEMS(ELEMS), .AW(AW), .SW(SW), .NRBS(NRBS), .MUT(MUT)) u_plane (
                    .ck((RETURN_CLOCKS != 0) ? return_ck[gc*32+plane] : clk),
                    .v5(d5_v), .v6(d6_v), .v7(d7_v), .a5(d5_a0), .a6(d6_a0), .a7(d7_a0),
                    .stride1(d7_si), .d(pd), .q(pq));
                for (genvar lane = 0; lane < SW; lane = lane + 1) begin : g_pack
                    assign s_q[(gc*SW+lane)*32+plane] = pq[lane];
                end
            end
        end else begin : g_return_flat
        // E6: coarse rotate (by the window's first bank, rounded down to 8), E7: fine (by its low 3 bits)
        reg  [NPS*512-1:0] pos;
        reg  [NWR*512-1:0] win;
        wire [LNRBS-1:0] r5 = d5_a0[4 +: LNRBS];
        wire [LNRBS-1:0] r6 = d6_a0[4 +: LNRBS];
        always @(posedge clk) if (d5_v)
            for (i = 0; i < NPS; i = i + 1) pos[i*512 +: 512] <= scap[((i + (r5 & ~7)) % NRBS)*512 +: 512];
        always @(posedge clk) if (d6_v)
            for (i = 0; i < NWR; i = i + 1) win[i*512 +: 512] <= pos[(i + (r6 & 7))*512 +: 512];
        // E8: lane select (stride 1: element off + l; stride 0: element off), ELEMS-bounded
        reg  [SW*32-1:0] q8;
        wire [3:0] off7 = d7_a0[3:0] + ((MUT == 1) ? 4'd1 : 4'd0);
        always @(posedge clk) if (d7_v)
            for (i = 0; i < SW; i = i + 1)
                q8[i*32 +: 32] <= ((d7_a0 + (d7_si ? i : 0)) < ELEMS) ? win[(off7 + (d7_si ? i : 0))*32 +: 32] : 32'd0;
        assign s_q[gc*SW*32 +: SW*32] = q8;
        end
        // hazard: this copy reads (macro edge next) a row with a late write pending
        reg hz;
        always @(*) begin
            hz = 1'b0;
            for (k = 0; k < NL; k = k + 1)
                if (lt_v[k] && sb_re[lt_row[k*RW +: LNRBS]] && sb_ra[lt_row[k*RW +: LNRBS]*LAWS +: LAWS] == lt_row[k*RW + LNRBS +: LAWS])
                    hz = 1'b1;
        end
        assign su_hz[gc] = hz || d2_bad;
    end endgenerate

    // ---- hazards / faults ----
    reg hz0;
    always @(*) begin
        hz0 = 1'b0;
        for (k = 0; k < NL; k = k + 1)
            if (lt_v[k] && b_re[lt_row[k*RW +: LNRB]] && b_ra[lt_row[k*RW +: LNRB]*LAW +: LAW] == lt_row[k*RW + LNRB +: LAW])
                hz0 = 1'b1;
    end
    // WAW: a bank write registered now onto the row of an entry still late in a queue
    reg waw;
    always @(*) begin
        waw = 1'b0;
        for (k = 0; k < NK; k = k + 1)
            for (i = 0; i < SQD; i = i + 1)
                if (q_v[k][i] && q_late[k][i] && bw_we[q_row[k*SQD + i][LNRB-1:0]] &&
                    bw_src[q_row[k*SQD + i][LNRB-1:0]*3 +: 3] != ((k == 3) ? 6 : k + 2) &&
                    bw_line[q_row[k*SQD + i][LNRB-1:0]*LAW +: LAW] == q_row[k*SQD + i][LNRB +: LAW]) waw = 1'b1;
    end
    // x hazard: a landing row (registered rows of this edge's bank writes) on the span of a pending x tuple
    reg            lr_su, lr_m;
    reg  [RW-1:0]  lr_r0, lr_mr;
    reg  [NQ-1:0]  lr_k;
    reg  [RW-1:0]  lr_kr [0:NQ-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin lr_su <= 1'b0; lr_m <= 1'b0; lr_k <= 0; end
        else begin lr_su <= |su_hit; lr_m <= gm; lr_k <= ge; end
    end
    always @(posedge clk) begin
        lr_r0 <= f_r0; lr_mr <= m_row;
        for (k = 0; k < NQ; k = k + 1) lr_kr[k] <= q_row[k];
    end
    function automatic hits(input [RW-1:0] lo, input [RW-1:0] hi, input [AW-1:0] dc, input [AW+12:0] sp);
        hits = ({lo, 4'h0} <= dc + sp) && ({hi, 4'hf} >= dc);
    endfunction
    reg hzx;
    always @(*) begin
        hzx = 1'b0;
        for (a = 0; a <= XVM; a = a + 1) if (h_new[a]) begin
            if (lr_su && hits(lr_r0, lr_r0 + NWR - 1, h_dc[a], h_span[a])) hzx = 1'b1;
            if (lr_m && hits(lr_mr, lr_mr, h_dc[a], h_span[a])) hzx = 1'b1;
            for (k = 0; k < NQ; k = k + 1) if (lr_k[k] && hits(lr_kr[k], lr_kr[k], h_dc[a], h_span[a])) hzx = 1'b1;
        end
        if (nt) begin
            if (lr_su && hits(lr_r0, lr_r0 + NWR - 1, x_dc, span_n)) hzx = 1'b1;
            if (lr_m && hits(lr_mr, lr_mr, x_dc, span_n)) hzx = 1'b1;
            for (k = 0; k < NQ; k = k + 1) if (lr_k[k] && hits(lr_kr[k], lr_kr[k], x_dc, span_n)) hzx = 1'b1;
        end
    end
    reg static_conflict;
    integer se,sf;
    always @* begin
        static_conflict=0;
        if(STATIC_SCHEDULE!=0)begin
            for(se=0;se<NQ;se=se+1)if(qvf[se])begin
                if(su_hs[q_row[se][LNRBS-1:0]])static_conflict=1;
                if(m_v && !m_nowr && m_row[LNRBS-1:0]==q_row[se][LNRBS-1:0])static_conflict=1;
                for(sf=0;sf<se;sf=sf+1)
                    if(qvf[sf] && q_row[sf][LNRBS-1:0]==q_row[se][LNRBS-1:0])static_conflict=1;
            end
            if(m_v && !m_nowr && su_hs[m_row[LNRBS-1:0]])static_conflict=1;
            for(se=0;se<NB;se=se+1)if(pl_w[se])begin
                if(su_hs[pl_row[RW*se +: LNRBS]])static_conflict=1;
                for(sf=0;sf<NQ;sf=sf+1)if(qvf[sf] && q_row[sf][LNRBS-1:0]==pl_row[RW*se +: LNRBS])static_conflict=1;
                for(sf=0;sf<se;sf=sf+1)if(pl_w[sf] && pl_row[RW*sf +: LNRBS]==pl_row[RW*se +: LNRBS])static_conflict=1;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin x_hazard <= 1'b0; w_hazard <= 1'b0; w_fault <= 1'b0; me_ok <= 1'b0; end
        else begin
            if (hzx) x_hazard <= 1'b1;
            if (hz0 || (|su_hz) || waw) w_hazard <= 1'b1;
            if (q_ovf || f_bad || m_fault || t_ovf || static_conflict) w_fault <= 1'b1;
            me_ok <= (STATIC_SCHEDULE!=0) ? !(q_ovf || f_bad || m_fault || t_ovf || static_conflict) : &rb_ok;
        end
    end
endmodule



// ---------------------------------------------------------------------------------------------------------------------
// el1011-q-sp 2026-10-12 r6 (qfd_vm_grp_b-4f52a5999 EARLY_FAIL_SETUP -655 ps / 6,588 ep; grp_a PREROUTE -1,270): the
// flat tile had ONE TritonCTS tree over 96,573 flops + 28 macros on 993.6 x 648 um (insertion ~1.06 ns, 390 ps of it
// pin-to-root wire), pop fanned from the pin to 128 slice replicas across the 648-um face, and one reset flop drove 3,690
// async flops.  r6 splits the macro side into hard leaf children (registered boundaries, own local clock tree):
//   ot_qfd_vm_bank_t  one copy-0 row bank: pin flops -> 2 macros -> capture beside the macros -> registered q
//   ot_qfd_vm_su_t    one SU copy (NSB row banks): pin flops -> 2*NSB macros -> capture -> registered q
// Each child = one input relay + macro + capture + one output relay of r5, so every path keeps the r5 latency
// (the grp carries NRI - 1 / NRX - 1 / NRS - 1 relays around them).  Defaults = TP4 production; TP8 sets params.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_bank_t #(
    parameter integer DEPTH = 174,
    parameter integer LAW = 8,
    parameter integer USE_MACRO = 1
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            re,
    input  wire [LAW-1:0]  ra,
    input  wire            we,
    input  wire [LAW-1:0]  wl,
    input  wire [15:0]     wm,
    input  wire [511:0]    wd,
    output reg  [511:0]    q
);
    reg rr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rr <= 1'b0; else rr <= 1'b1;
    reg p_re, p_we;
    always @(posedge clk or negedge rr) if (!rr) begin p_re <= 1'b0; p_we <= 1'b0; end else begin p_re <= re; p_we <= we; end
    reg [LAW-1:0] p_ra, p_wl;
    reg [15:0]    p_wm;
    reg [511:0]   p_wd;
    always @(posedge clk) begin p_ra <= ra; p_wl <= wl; p_wm <= wm; p_wd <= wd; end
    wire [511:0] bq;
    ot_qfd_vm_rowbank #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_b (.clk(clk),
        .re(p_re), .raddr(p_ra), .q(bq), .we(p_we), .waddr(p_wl), .wmask(p_wm), .wdata(p_wd));
    reg [511:0] cq;                       // capture beside the macros: no logic, no reset, no enable
    always @(posedge clk) begin cq <= bq; q <= cq; end
endmodule

module ot_qfd_vm_su_t #(
    parameter integer NSB = 1,
    parameter integer DEPTHS = 695,
    parameter integer LAWS = 10,
    parameter integer USE_MACRO = 1
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire [NSB-1:0]        sre,
    input  wire [NSB*LAWS-1:0]   sra,
    input  wire [NSB-1:0]        swe,
    input  wire [NSB*LAWS-1:0]   swl,
    input  wire [NSB*16-1:0]     swm,
    input  wire [NSB*512-1:0]    swd,
    output reg  [NSB*512-1:0]    q
);
    reg rr;
    always @(posedge clk or negedge rst_n) if (!rst_n) rr <= 1'b0; else rr <= 1'b1;
    reg [NSB-1:0] p_sre, p_swe;
    always @(posedge clk or negedge rr) if (!rr) begin p_sre <= 0; p_swe <= 0; end else begin p_sre <= sre; p_swe <= swe; end
    reg [NSB*LAWS-1:0] p_sra, p_swl;
    reg [NSB*16-1:0]   p_swm;
    reg [NSB*512-1:0]  p_swd;
    always @(posedge clk) begin p_sra <= sra; p_swl <= swl; p_swm <= swm; p_swd <= swd; end
    wire [NSB*512-1:0] sq;
    genvar j;
    generate for (j = 0; j < NSB; j = j + 1) begin : g_s
        ot_qfd_vm_rowbank_s #(.DEPTH(DEPTHS), .LAW(LAWS), .USE_MACRO(USE_MACRO)) u_s (.clk(clk),
            .re(p_sre[j]), .raddr(p_sra[j*LAWS +: LAWS]), .q(sq[j*512 +: 512]),
            .we(p_swe[j]), .waddr(p_swl[j*LAWS +: LAWS]), .wmask(p_swm[j*16 +: 16]), .wdata(p_swd[j*512 +: 512]));
    end endgenerate
    reg [NSB*512-1:0] cq;
    always @(posedge clk) begin cq <= sq; q <= cq; end
endmodule
// ---------------------------------------------------------------------------------------------------------------------
// el1011-q-sp 2026-10-11 (owner textbook audit; main decision: near-square VM slot, x rate unchanged, me_en one edge
// early with regional replicas): ot_qfd_vm_grp, the HARDENED BANK-GROUP TILE of ot_qfd_sp_vector_memory_bv VMT = 1.
// One tile = NBK = 8 copy-0 row banks (16 x ot_sram_1r1w_256x256) + NSB row banks of each of the NSU SU replica copies
// (NSU x NSB x 2 ot_sram_1r1w_1024x256), with its own clock tree, reset relay and me_en replica.  Every input is a pin
// flop; every output is a register.  The parent's bank read / write registers reach these pins through RV clock relays,
// so every macro access (x beat, row read, SU read, every write) is shifted by the same RV + 1 edges (the ordering
// argument of the base -- a read sees exactly the writes presented before it -- is unchanged).
//   x beats   captured on the clock (xv, as the base's m2) into an NPP-deep FIFO; popped on engine edges (pop, me_en
//             domain) into xo -- the base's 3 rotating capture buffers + capx select, made a FIFO so that consumption may
//             trail capture by the seam's engine edges (stalls included: NPP >= 4 + RV + 1 covers every beat in flight).
//   row read  ro <= the requested bank (rqb) two edges after the pin, as the base's r_qr.
//   SU reads  so <= the copy's NSB banks two edges after the pin (sv), as the base's scap.
// ovf: FIFO overflow / pop of an empty FIFO (never in a legal schedule; reaches w_fault).
// el1011-q-sp 2026-10-11 r5 (qfd_vm_grp_{a,b}-5839e0912 PREROUTE_MARGIN -924.9 / -1,068.2 ps: the worst paths were 4-5
// logic cells + 27-29 repeaters, i.e. ~1.5 ns of WIRE from the W macro columns to the E pin face in one cycle, class 4):
// every macro input crosses the tile in NRI relays, every macro output is captured beside the macro and relayed NRX / NRS
// stages to the E region, where the x FIFO (per-slice replicas) and the row-read rungs (two one-hot 4:1 rungs + 2:1,
// registered) sit next to the pins.  Latency vs r4: x + (1 + NRI + NRX), row + (2 + NRI + NRX), SU + (1 + NRI + NRS);
// the parent carries them as TLX / TLR / TLS (x FIFO NPP + TLX, pop source TLX engine edges later).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_grp #(
    parameter integer NBK = 8,
    parameter integer NSB = 2,
    parameter integer NSU = 3,
    parameter integer DEPTH = 1024,
    parameter integer LAW = 10,
    parameter integer DEPTHS = 1024,
    parameter integer LAWS = 10,
    parameter integer USE_MACRO = 0,
    parameter integer NPP = 12,          // production RV 1: RV + 6 + TLX (TLX = 1 + NRI + NRX = 5)
    parameter integer MEREG = 1,         // 1: me_in is me_en one edge early (registered here: the tile's replica)
    parameter integer NRI = 2,           // clock relays pin flop -> macro inputs (every read / write port, uniform)
    parameter integer NRX = 2,           // clock relays copy-0 capture -> E region (x FIFO + row-read rungs)
    parameter integer NRS = 1,           // clock relays SU capture -> E region (so)
    parameter integer FSW = 32           // x FIFO slice width: each FSW-bit slice owns kept one-hot wp/rp + push/pop replicas
                                         // (128 -> 32 after e39fac4f9: pp_k -> 128 xo enables across the pin face was -1,068.9 ps)
) (
    input  wire                      clk,
    input  wire                      rst_n,
    input  wire                      me_in,
    input  wire [NBK-1:0]            re,
    input  wire [NBK*LAW-1:0]        ra,
    input  wire [NBK-1:0]            we,
    input  wire [NBK*LAW-1:0]        wl,
    input  wire [NBK*16-1:0]         wm,
    input  wire [NBK*512-1:0]        wd,
    input  wire                      xv,
    input  wire                      rq,
    input  wire [2:0]                rqb,
    input  wire [NSU*NSB-1:0]        sre,
    input  wire [NSU*NSB*LAWS-1:0]   sra,
    input  wire [NSU-1:0]            sv,
    input  wire [NSB-1:0]            swe,
    input  wire [NSB*LAWS-1:0]       swl,
    input  wire [NSB*16-1:0]         swm,
    input  wire [NSB*512-1:0]        swd,
    input  wire                      pop,
    output reg  [NBK*512-1:0]        xo,
    output reg  [511:0]              ro,
    output reg  [NSU*NSB*512-1:0]    so,
    output reg                       ovf
);
    localparam integer LP = (NPP > 1) ? $clog2(NPP) : 1;
    genvar g, c, j;
    // ---- reset relay, me_en replica ----
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    // r6: per-bank reset relays (one flop drove 3,690 async flops: recovery -254 ps) and per-bank pop pin flops
    //     (pop -> 128 slice replicas across the face was -745 ps): pop gains one engine edge (parent TPP).
    wire [NBK-1:0] rtg, pgw;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_rg
        (* keep = "true", dont_touch = "true" *) reg r;
        (* keep = "true", dont_touch = "true" *) reg mg;
        (* keep = "true", dont_touch = "true" *) reg pg;
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rt;
        always @(posedge clk) mg <= me_in;
        always @(posedge clk or negedge rt) if (!rt) pg <= 1'b0; else if ((MEREG != 0) ? mg : me_in) pg <= pop;
        assign rtg[g] = r;
        assign pgw[g] = pg;
    end endgenerate
    wire me_t;
    generate if (MEREG != 0) begin : g_mer
        reg mr;
        always @(posedge clk) mr <= me_in;
        assign me_t = mr;
    end else begin : g_mew
        assign me_t = me_in;
    end endgenerate
    // ---- pin flops ----
    reg [NBK-1:0] p_re, p_we;
    reg           p_xv, p_rq, p_pop;
    reg [NSU*NSB-1:0] p_sre;
    reg [NSU-1:0] p_sv;
    reg [NSB-1:0] p_swe;
    always @(posedge clk or negedge rt)
        if (!rt) begin p_re <= 0; p_we <= 0; p_xv <= 1'b0; p_rq <= 1'b0; p_sre <= 0; p_sv <= 0; p_swe <= 0; end
        else begin p_re <= re; p_we <= we; p_xv <= xv; p_rq <= rq; p_sre <= sre; p_sv <= sv; p_swe <= swe; end
    reg p_pop2;                           // central copy of the per-bank pop stage (occupancy / ovf)
    always @(posedge clk or negedge rt) if (!rt) begin p_pop <= 1'b0; p_pop2 <= 1'b0; end
        else if (me_t) begin p_pop <= pop; p_pop2 <= p_pop; end
    reg [NBK*LAW-1:0] p_ra, p_wl;
    reg [NBK*16-1:0]  p_wm;
    reg [NBK*512-1:0] p_wd;
    reg [2:0]         p_rqb;
    reg [NSU*NSB*LAWS-1:0] p_sra;
    reg [NSB*LAWS-1:0] p_swl;
    reg [NSB*16-1:0]   p_swm;
    reg [NSB*512-1:0]  p_swd;
    always @(posedge clk) begin
        p_ra <= ra; p_wl <= wl; p_wm <= wm; p_wd <= wd; p_rqb <= rqb;
        p_sra <= sra; p_swl <= swl; p_swm <= swm; p_swd <= swd;
    end
    // ---- macro-side input relays: every macro input crosses the tile from the E-face pin flops in NRI clock stages
    //      (the far copy-0 column sits ~750 um from the pins; <= ~500 um of wire per stage).  Uniform delay on every
    //      read / write port keeps the base ordering argument (a read sees exactly the writes presented before it). ----
    wire [NBK-1:0]          m_re, m_we;
    wire [NSU*NSB-1:0]      m_sre;
    wire [NSB-1:0]          m_swe;
    wire [NBK*LAW-1:0]      m_ra, m_wl;
    wire [NBK*16-1:0]       m_wm;
    wire [NBK*512-1:0]      m_wd;
    wire [NSU*NSB*LAWS-1:0] m_sra;
    wire [NSB*LAWS-1:0]     m_swl;
    wire [NSB*16-1:0]       m_swm;
    wire [NSB*512-1:0]      m_swd;
    ot_hdc_delay #(.W(2*NBK + NSU*NSB + NSB), .D(NRI - 1), .RESET(1)) u_ic (.clk(clk), .rst_n(rt),
        .d({p_re, p_we, p_sre, p_swe}), .q({m_re, m_we, m_sre, m_swe}));
    ot_hdc_delay #(.W(2*NBK*LAW + NBK*16 + NBK*512 + NSU*NSB*LAWS + NSB*LAWS + NSB*16 + NSB*512), .D(NRI - 1)) u_id (
        .clk(clk), .rst_n(rt), .d({p_ra, p_wl, p_wm, p_wd, p_sra, p_swl, p_swm, p_swd}),
        .q({m_ra, m_wl, m_wm, m_wd, m_sra, m_swl, m_swm, m_swd}));
    // ---- copy-0 banks ----
    //      r6: hard leaf children (pin flop + macros + capture + registered q = 1 input + 1 + 1 + 1 output relay of r5)
    wire [NBK*512-1:0] bq;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_b
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_bank_t #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_bt (.clk(clk), .rst_n(rtg[g]),
`else   // hardened cluster: the leaf view is built with the TP4 defaults (DEPTH 174 / LAW 8); no parameters on a hard child
        ot_qfd_vm_bank_t u_bt (.clk(clk), .rst_n(rtg[g]),
`endif
            .re(m_re[g]), .ra(m_ra[g*LAW +: LAW]), .q(bq[g*512 +: 512]),
            .we(m_we[g]), .wl(m_wl[g*LAW +: LAW]), .wm(m_wm[g*16 +: 16]), .wd(m_wd[g*512 +: 512]));
    end endgenerate
    // ---- SU copy banks ----
    wire [NSU*NSB*512-1:0] sq;
    //      r6b: one hard child per SU row bank (NSB = 1: pin flops -> 2 x 1024x256 -> capture -> registered q), NSU x NSB
    //      per grp -- the NSB = 2 child (4 macros, 3,149 flops) gated at TT clock insertion 312-451 ps vs 188-268 for the
    //      2-macro bank_t.  Same per-row-bank pipeline, so latency and behaviour are unchanged.
    generate for (c = 0; c < NSU; c = c + 1) begin : g_c
      for (j = 0; j < NSB; j = j + 1) begin : g_j
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_su_t #(.NSB(1), .DEPTHS(DEPTHS), .LAWS(LAWS), .USE_MACRO(USE_MACRO)) u_st (.clk(clk),
`else   // hardened cluster: leaf view built with the TP4 defaults (NSB 1 / DEPTHS 695 / LAWS 10)
        ot_qfd_vm_su_t u_st (.clk(clk),
`endif
            .rst_n(rtg[(c*NSB + j) % NBK]), .sre(m_sre[c*NSB + j]), .sra(m_sra[(c*NSB + j)*LAWS +: LAWS]),
            .swe(m_swe[j]), .swl(m_swl[j*LAWS +: LAWS]), .swm(m_swm[j*16 +: 16]), .swd(m_swd[j*512 +: 512]),
            .q(sq[(c*NSB + j)*512 +: 512]));
      end
    end endgenerate
    // ---- output data path: capture register beside every macro (no logic before it), then NRX (copy-0) / NRS (SU)
    //      clock relays toward the E face.  Datapath registers carry no reset and no enable. ----
    wire [NBK*512-1:0]     bx;          // copy-0 words at the E region: bq + 1 + NRX edges
    wire [NSU*NSB*512-1:0] sx;          // SU words at the E region:     sq + 1 + NRS edges
    ot_hdc_delay #(.W(NBK*512), .D(NRX - 1)) u_bx (.clk(clk), .rst_n(rt), .d(bq), .q(bx));
    ot_hdc_delay #(.W(NSU*NSB*512), .D(NRS - 1)) u_sx (.clk(clk), .rst_n(rt), .d(sq), .q(sx));
    // ---- tags (pin flop -> central control chain -> per-region kept replicas -> per-slice kept replicas) ----
    //   x push:  p_xv + 2 + NRI + NRX edges (aligned with bx)   = central (NRI + NRX) + xg (bank) + xv_k (slice)
    //   row:     one-hot select of p_rqb, p_rqb[2], p_rq   + 2 + NRI + NRX = decode + central (NRI + NRX) + slice
    //   SU:      p_sv + 2 + NRI + NRS edges (aligned with sx) = central (NRI + NRS) + sg (copy) + sv_k (slice)
    wire          xvc;
    ot_hdc_delay #(.W(1), .D(NRI + NRX), .RESET(1)) u_xc (.clk(clk), .rst_n(rt), .d(p_xv), .q(xvc));
    wire          xpush;                // central push (FIFO occupancy / ovf), aligned with every xv_k
    ot_hdc_delay #(.W(1), .D(2 + NRI + NRX), .RESET(1)) u_xp (.clk(clk), .rst_n(rt), .d(p_xv), .q(xpush));
    reg  [5:0]    rdq;                  // decoded row tag: {rq, rqb[2], onehot(rqb[1:0])}
    always @(posedge clk or negedge rt)
        if (!rt) rdq <= 6'd0;
        else rdq <= {p_rq, p_rqb[2], (p_rqb[1:0] == 2'd3), (p_rqb[1:0] == 2'd2), (p_rqb[1:0] == 2'd1), (p_rqb[1:0] == 2'd0)};
    wire [5:0]    rdc;
    ot_hdc_delay #(.W(6), .D(NRI + NRX), .RESET(1)) u_rc (.clk(clk), .rst_n(rt), .d(rdq), .q(rdc));
    wire [NSU-1:0] svc;
    ot_hdc_delay #(.W(NSU), .D(NRI + NRS), .RESET(1)) u_sc (.clk(clk), .rst_n(rt), .d(p_sv), .q(svc));
    // ---- row read: registered 8:1 as two 4:1 rungs (one-hot select, one AND-OR level) + a 2:1 rung into ro ----
    localparam integer RSL = 512 / FSW;
    genvar k, e;
    generate for (k = 0; k < RSL; k = k + 1) begin : g_rs
        (* keep = "true", dont_touch = "true" *) reg [5:0] rs1;   // select replica, rung 1
        (* keep = "true", dont_touch = "true" *) reg [1:0] rs2;   // {en, half} replica, rung 2
        reg [2*FSW-1:0] t1, t1n;
        always @(posedge clk or negedge rtg[k % NBK]) if (!rtg[k % NBK]) begin rs1 <= 6'd0; rs2 <= 2'd0; end
            else begin rs1 <= rdc; rs2 <= rs1[5:4]; end
        integer h, i;
        always @* begin
            t1n = {(2*FSW){1'b0}};
            for (h = 0; h < 2; h = h + 1)
                for (i = 0; i < 4; i = i + 1)
                    t1n[h*FSW +: FSW] = t1n[h*FSW +: FSW] | (bx[(4*h + i)*512 + k*FSW +: FSW] & {FSW{rs1[i]}});
        end
        always @(posedge clk) t1 <= t1n;
        always @(posedge clk) if (rs2[1]) ro[k*FSW +: FSW] <= rs2[0] ? t1[FSW +: FSW] : t1[0 +: FSW];
    end endgenerate
    // ---- SU answers: per-copy region replica, per-slice enable replica ----
    localparam integer SSL = (NSB * 512) / FSW;
    generate for (c = 0; c < NSU; c = c + 1) begin : g_sc
        (* keep = "true", dont_touch = "true" *) reg sg;
        always @(posedge clk or negedge rtg[c % NBK]) if (!rtg[c % NBK]) sg <= 1'b0; else sg <= svc[c];
        for (k = 0; k < SSL; k = k + 1) begin : g_k
            (* keep = "true", dont_touch = "true" *) reg sv_k;
            always @(posedge clk or negedge rtg[c % NBK]) if (!rtg[c % NBK]) sv_k <= 1'b0; else sv_k <= sg;
            always @(posedge clk) if (sv_k) so[c*NSB*512 + k*FSW +: FSW] <= sx[c*NSB*512 + k*FSW +: FSW];
        end
    end endgenerate
    // ---- x beat FIFO in the E region: push on the clock (aligned with bx), pop on engine edges ----
    // Every FSW-bit slice owns kept one-hot wp / rp and its own push / pop / me replicas (a select drives FSW x NPP
    // flops, the read is one AND-OR level, no pointer net crosses the tile); push comes from a per-bank region replica.
    localparam integer NSL = (NBK * 512) / FSW;
    localparam integer SPB = 512 / FSW;
    reg [LP:0]   cnt;
    wire popn = me_t && p_pop2;
    always @(posedge clk or negedge rt) begin
        if (!rt) begin cnt <= 0; ovf <= 1'b0; end
        else begin
            cnt <= cnt + (xpush ? 1'b1 : 1'b0) - (popn ? 1'b1 : 1'b0);
            if ((xpush && !popn && cnt == NPP) || (popn && cnt == 0)) ovf <= 1'b1;
        end
    end
    wire [NBK-1:0] xg;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_xg
        (* keep = "true", dont_touch = "true" *) reg r;
        always @(posedge clk or negedge rtg[g]) if (!rtg[g]) r <= 1'b0; else r <= xvc;
        assign xg[g] = r;
    end endgenerate
    generate for (k = 0; k < NSL; k = k + 1) begin : g_fs
        (* keep = "true", dont_touch = "true" *) reg mr_k;       // me_t replica
        (* keep = "true", dont_touch = "true" *) reg pp_k;       // pop pin-flop replica
        (* keep = "true", dont_touch = "true" *) reg xv_k;       // push replica
        (* keep = "true", dont_touch = "true" *) reg [NPP-1:0] wpo, rpo;
        wire me_k = (MEREG != 0) ? mr_k : me_in;
        wire pop_k = me_k && pp_k;
        always @(posedge clk) mr_k <= me_in;
        always @(posedge clk or negedge rtg[k / SPB])
            if (!rtg[k / SPB]) begin pp_k <= 1'b0; xv_k <= 1'b0; wpo <= {{(NPP-1){1'b0}}, 1'b1}; rpo <= {{(NPP-1){1'b0}}, 1'b1}; end
            else begin
                if (me_k) pp_k <= pgw[k / SPB];
                xv_k <= xg[k / SPB];
                if (xv_k) wpo <= (NPP > 1) ? {wpo[NPP-2:0], wpo[NPP-1]} : wpo;
                if (pop_k) rpo <= (NPP > 1) ? {rpo[NPP-2:0], rpo[NPP-1]} : rpo;
            end
        reg [FSW-1:0] fe [0:NPP-1];
        for (e = 0; e < NPP; e = e + 1) begin : g_fe
            always @(posedge clk) if (xv_k && wpo[e]) fe[e] <= bx[k*FSW +: FSW];
        end
        reg [FSW-1:0] rd;
        integer i;
        always @* begin
            rd = {FSW{1'b0}};
            for (i = 0; i < NPP; i = i + 1) rd = rd | (fe[i] & {FSW{rpo[i]}});
        end
        always @(posedge clk) if (pop_k) xo[k*FSW +: FSW] <= rd;
    end endgenerate
endmodule

// Standard return leaf. The old E6/E7/E8 registers are moved, with zero added edges.
// Existing first/last registers own data pins; physical opt-out must cite this RTL
// and verify native launch/capture after CTS, rather than add hidden wrapper stages.
module ot_qfd_vm_su_return_plane #(
    parameter integer ELEMS=177808, AW=24, SW=64, NRBS=16, MUT=0
)(
    input wire ck, v5, v6, v7,
    input wire [AW-1:0] a5, a6, a7,
    input wire stride1,
    input wire [NRBS*16-1:0] d,
    output reg [SW-1:0] q
);
    localparam integer NWR=(SW+30)/16;
    localparam integer NPS=(NWR+7<NRBS)?NWR+7:NRBS;
    localparam integer LNRBS=$clog2(NRBS);
    reg [NPS*16-1:0] pos;
    reg [NWR*16-1:0] win;
    wire [LNRBS-1:0] r5=a5[4+:LNRBS], r6=a6[4+:LNRBS];
    wire [3:0] off7=a7[3:0]+((MUT==1)?4'd1:4'd0);
    integer row,lane;
    always @(posedge ck) begin
        if(v5) for(row=0;row<NPS;row=row+1)
            pos[row*16+:16] <= d[((row+(r5 & ~7))%NRBS)*16+:16];
        if(v6) for(row=0;row<NWR;row=row+1)
            win[row*16+:16] <= pos[(row+(r6 & 7))*16+:16];
        if(v7) for(lane=0;lane<SW;lane=lane+1)
            q[lane] <= ((a7+(stride1?lane:0))<ELEMS) ? win[off7+(stride1?lane:0)] : 1'b0;
    end
endmodule

// Owns the original E1/E2/E3 descriptor/read controls and fixed-age valid/address pipeline.
// Every functional input and output terminates in an existing register; no added edges.
module ot_qfd_vm_su_read_control #(
    parameter integer AW=24,SW=64,NRBS=16,LAWS=10,SX=8
)(
    input wire ck,rst_n,re0,re1,
    input wire [AW-1:0] a0,a1,
    output reg [NRBS-1:0] sb_re,
    output reg [NRBS*LAWS-1:0] sb_ra,
    output reg d2_bad,
    output wire ov3,ov5,ov6,ov7,osi7,
    output wire [AW-1:0] oa5,oa6,oa7
);
    localparam integer RW=AW-4,LNRBS=$clog2(NRBS);
        // E1: descriptor registers; E2: broadcast registers (window rows, offset, stride)
        reg           d1_v, d1_r1;
        reg  [AW-1:0] d1_a0, d1_a1;
        reg           d2_v, d2_si;
        reg  [AW-1:0] d2_a0;
        reg  [3:0]    d2_nr;
        
        always @(posedge ck or negedge rst_n) begin
            if (!rst_n) begin d1_v <= 1'b0; d2_v <= 1'b0; d2_bad <= 1'b0; end
            else begin
                d1_v <= re0; d2_v <= d1_v;
                d2_bad <= d1_v && d1_r1 && (d1_a1 - d1_a0) > 1;
            end
        end
        wire si1 = d1_r1 && (d1_a1 - d1_a0) == 1;
        always @(posedge ck) begin
            d1_r1 <= re1; d1_a0 <= a0; d1_a1 <= a1;
            d2_a0 <= d1_a0; d2_si <= si1;
            d2_nr <= si1 ? ((d1_a0[3:0] + SW - 1) >> 4) + 1 : 4'd1;
        end
        // E3: per-bank read registers (beside the macros)
        
        
        wire [RW-1:0]        d2_r0 = d2_a0[AW-1:4];
        for (genvar g = 0; g < NRBS; g = g + 1) begin : g_ra
            wire [LNRBS-1:0] kk = g[LNRBS-1:0] - d2_r0[LNRBS-1:0];
            wire [RW-1:0]    rr = d2_r0 + kk;
            always @(posedge ck) begin
                sb_re[g] <= d2_v && (kk < d2_nr);
                sb_ra[g*LAWS +: LAWS] <= rr[LNRBS +: LAWS];
            end
        end
        //: d3 .. d(7 + SX): VMT adds SX edges between the bank read registers and the coarse rotate (the tile seam)
        localparam integer DN = 5 + SX;                     // stages d3 .. d(7 + SX)
        reg  [DN-1:0]    dvv, dsv;
        reg  [DN*AW-1:0] dav;
        always @(posedge ck) begin
            dvv <= {dvv, d2_v}; dsv <= {dsv, d2_si}; dav <= {dav, d2_a0};
        end
        wire          d3_v  = dvv[0];
        wire          d5_v  = dvv[2 + SX], d6_v = dvv[3 + SX], d7_v = dvv[4 + SX];
        wire [AW-1:0] d5_a0 = dav[(2 + SX)*AW +: AW], d6_a0 = dav[(3 + SX)*AW +: AW], d7_a0 = dav[(4 + SX)*AW +: AW];
        wire          d7_si = dsv[4 + SX];

    assign {ov3,ov5,ov6,ov7,osi7}={d3_v,d5_v,d6_v,d7_v,d7_si};
    assign {oa5,oa6,oa7}={d5_a0,d6_a0,d7_a0};
endmodule
