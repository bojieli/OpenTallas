// COUNT-ALIGNED landed (mesochronous) crossing.  MESO-COUNT-1 study (OWNER-approved 10-27), opt-in, default-off:
// opt-in: instantiated only by the count_aligned form of tools/die_plan/clock_landings.py (MESO-INTEG-1, table
// "count_aligned" from count_align_bind.py).  ot_dp_clk_landing / ot_meso_ring are unchanged and stay the default.
//
// Why.  ot_meso_ring places its read pointer at start-up from the MEASURED PHASE (half-period resolution), so the
// whole-cycle latency of a crossing is a function of (phase mod T).  Two chips whose phases differ by exactly T
// measure the same thing but need pointers one apart, so NO phase-measured placement can give a chip-invariant
// latency once a crossing's derated phase spread reaches T (HEAD 950 ps, KV 1091 ps > 833 ps).
//
// Mechanism.  Both sides count cycles from a chip-invariant COUNT ORIGIN (their start/reset release at a design-time
// known cycle a_x, a_y; see results/meso_count_1027/README.md for how the origin is delivered).
//   * Writer (fclk = the sender's forwarded clock): tc is reset by t_rst_n, the sender's start forwarded beside the
//     bus (source-synchronous with fclk).  Sender word n is written into slot n mod DEPTH with lap bit n[AW] and a
//     written-since-start bit; slot n is rewritten by word n + DEPTH.
//   * Reader (clk): rp is reset by rst_n to -K (mod 2*DEPTH) and increments every cycle, so at receiver count m it
//     consumes the slot of sender word m - K.  NO phase sample, NO Gray synchroniser, NO placement decision.
//   * The lag of every word is then L = (K + a_y - a_x) T + d, d = the static receiver-minus-sender clock phase
//     (+ drift).  The word is captured correctly iff (GUARD_LO + 0.5) T <= L <= (GUARD_HI - 0.5) T: the same
//     opposite-edge lap guards as ot_meso_ring (copied, unchanged) watch exactly that window, fail closed (sticky).
//   * Latency is K + RDREG receiver cycles after the sender cycle, for EVERY static phase in the window: chip-to-chip
//     whole-cycle variation is absorbed by the ring depth, window width (GUARD_HI - GUARD_LO - 1) T (3 T at the
//     default DEPTH 4 / guards 0,4), instead of the old one-period placement window.
//
// Ready-timeout (MESO-RECONCILE-1, COORD 21:55): a lag below the window never consumes a valid word, so the guards
// never arm and the crossing stayed !ready with no fault (fail-closed but silent).  TIMEOUT receiver cycles after rst_n
// release without arming raise the sticky fault on the same fault port.  GUARD_HI defaults to DEPTH.
// Ports as ot_dp_clk_landing plus t_rst_n.  Receiver count c = rclk edges since rst_n release (c = 0 at the first edge
// that samples rst_n high).  Right after edge c, q holds sender word c - K (captured at that edge, RDREG); the
// receiver's own boundary flop takes it at c + 1: crossing latency K + 1 counts, for every lag in the window.
// Start-up: a region's count origin (its rst_n release) comes from ot_dp_landing_origin on ONE tree crossing per
// region (start wavefront over a spanning tree of these rings); every other crossing's K is set at bind time.
// Model, conditions on K / DEPTH / guards and loop consistency: results/meso_count_1027/README.md.
// OT_MESO_CA_FV (formal only): fv_recent / fv_now / fv_any make the reads of a slot written within the STA bound
// (recent) or at the sampling instant (now) arbitrary, i.e. metastable / unbounded data, so the proof covers them.
(* keep_hierarchy *)
module ot_dp_clk_landing_ca #(
    parameter integer W        = 1,
    parameter integer DEPTH    = 4,   // power of two >= 4
    parameter integer K        = 2,   // read offset in counts (binder: K' - (a_y - a_x)); any integer
    parameter integer GUARD_LO = 0,
    parameter integer GUARD_HI = DEPTH, // <= DEPTH; MESO-RECONCILE-1: default DEPTH (4 was wrong at DEPTH 8)
    parameter integer ARM      = 2 * DEPTH + 4, // receiver cycles after the first valid word before guards are trusted
    // MESO-RECONCILE-1 ready-timeout: fault if the crossing is not armed TIMEOUT receiver cycles after rst_n release
    // (0 = off).  In the window the first valid word (sender count 0) is consumed at receiver count max(K, 0), seen one
    // count later, armed ARM counts after that: armed by count max(K,0) + ARM + 2.  The default adds 2*DEPTH + 6 counts
    // of slack, so it never fires in the window (proven, fv_ca2 A_ALL); a lag below the window (no valid word is ever
    // consumed: never ready, previously no fault) now raises fault (fv_ca2 A_TMO).
    parameter integer TIMEOUT  = (K > 0 ? K : 0) + ARM + 2 * DEPTH + 8,
    parameter bit CONTROL_STATUS_COPY = 0, // optional private status bank; same cycles
    // STATUS-REG-1 (KV-SLGLAND-2 11-07): 1 = the ring status crossings end at private per-slot flops (see ot_meso_ring_ca).
    // Data q and ready are cycle-identical in the window; a rv/lap fault is seen one clk later; guard faults unchanged.
    // Default 0 = identical logic.
    parameter bit STATUS_REG = 0,
    parameter bit WFALL = 0, // DIE-HEAD-48 ring-write hold: writer on the falling edge of fclk (see wclk)
    parameter bit GUARD_REG = 0, // GUARD-REG-1 (see ot_meso_ring_ca; needs STATUS_REG); default 0 = identical logic
    // CLAND-QREG-1 (COORD 11-11, KV hub_Ei ring readout -> boundary flop TT -159.5): QREG = 1 adds ONE rclk register
    // stage on q (ot_meso_q_ff, kept, no reset: data only) between the ring readout flop and the receiver's boundary
    // flop, so the long ring -> face wire gets its own cycle.  The ring, its window, K and ready/fault are unchanged;
    // q is the same word stream ONE clk later (+1 data cycle, declared by the plan key landing_output_qreg and counted
    // in the crossing's added_cycles).  Default 0 = identical logic.
    parameter bit QREG = 0,
    // CLAND-SLEW-1 (GEN-CLASS-1 11-12): read-select register copies per 64-bit chunk (ot_meso_ring_ca DSREP, as
    // ot_dp_clk_landing_cas); appended for positional compatibility.  Default 1 = identical logic.
    parameter int DSREP = 1
) (
    input  wire         fclk,
    input  wire         t_rst_n,     // sender start, forwarded with fclk (synchronous to fclk)
    input  wire         clk,
    input  wire         rst_n,       // receiver start (count origin), synchronous to clk
    input  wire [W-1:0] d,
    output wire [W-1:0] q,
    output reg          ready,
    output wire         fault
`ifdef OT_MESO_CA_FV
   ,input  wire [DEPTH-1:0] fv_recent, fv_now,
    input  wire [W+3:0]     fv_any
`endif
);
    localparam integer RW = ((W + 63) / 64) * 64;
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(ARM + 1);
    localparam integer TCW = $clog2(TIMEOUT + 2);
    wire rv, lap_ok, glo_ok, ghi_ok;
    wire [RW-1:0] ring_q;
    generate if (QREG) begin : g_qreg
        ot_meso_q_ff #(.W(W)) u_qreg (.clk(clk), .d(ring_q[W-1:0]), .q(q));
    end else begin : g_noqreg
        assign q = ring_q[W-1:0];
    end endgenerate
    // WFALL = 1: the whole writer (slots, count, tags) runs on the opposite fclk edge, so a word launched on the sender's
    // rising edge is held T/2 by structure (FLOW-16 05:48).  Default 0 = no inverter, identical logic.
    wire wclk = WFALL ? ~fclk : fclk;
    reg seen;                       // first valid word consumed
    reg [CW-1:0] arm_cnt;
`ifdef OT_MESO_CA_MUTANT_SR_ARM
    localparam integer ARM_E = ARM;            // MUTANT: rv is one count later, so ready slips one count
`else
    localparam integer ARM_E = STATUS_REG ? ARM - 1 : ARM;   // STATUS-REG-1: rv one count later, armed on the same count
`endif
    wire armed = seen && (arm_cnt == CW'(ARM_E));
    reg fault_state;
    reg [TCW-1:0] tmo_cnt;          // receiver cycles since rst_n release while not armed (saturates at TIMEOUT)
`ifdef OT_MESO_CA_MUTANT_NO_TIMEOUT
    wire tmo = 1'b0;                // MUTANT: ready-timeout disabled
`else
    wire tmo = (TIMEOUT > 0) && !armed && (tmo_cnt == TCW'(TIMEOUT));
`endif
    wire trip = (armed && (!rv || !lap_ok || !glo_ok || !ghi_ok)) || tmo;
    wire fault_next = fault_state || trip;
    ot_dp_landing_fault_port u_fault_port (.clk(clk), .rst_n(rst_n), .d(fault_next), .q(fault));
    always @(posedge clk) begin
        if (!rst_n) begin
            seen <= 0; arm_cnt <= 0; ready <= 0; fault_state <= 0; tmo_cnt <= 0;
        end else begin
            if (!armed && tmo_cnt != TCW'(TIMEOUT)) tmo_cnt <= tmo_cnt + 1'b1;
            if (rv) seen <= 1;
            if (seen && arm_cnt != CW'(ARM_E)) arm_cnt <= arm_cnt + 1'b1;
            ready <= armed && !fault_next;
            fault_state <= fault_next;
        end
    end
    localparam integer KTW = AW + 1 + 3;      // ring count width (LAPX = 3)
    localparam integer KNT = 1 << KTW;
    localparam integer KM  = ((K % KNT) + KNT) % KNT;
    ot_meso_ring_ca #(.W(RW), .DEPTH(DEPTH), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI),
                      .CONTROL_STATUS_COPY(CONTROL_STATUS_COPY), .STATUS_REG(STATUS_REG), .GUARD_REG(GUARD_REG),
                      .DSREP(DSREP)) u_ring (
        .tclk(wclk), .wen_clk(1'b0), .t_rst_n(t_rst_n), .t_d({{(RW-W){1'b0}}, d}), .rclk(clk), .r_rst_n(rst_n), .r_rst_x(1'b1), .k_s(KTW'(KM)),
        .r_d(ring_q), .r_v(rv), .r_lap_ok(lap_ok), .r_glo_ok(glo_ok), .r_ghi_ok(ghi_ok)
`ifdef OT_MESO_CA_FV
       ,.fv_recent(fv_recent), .fv_now(fv_now), .fv_any(fv_any)
`endif
    );
`ifndef SYNTHESIS
    initial begin
        if (W < 1) $fatal(1, "count-aligned landing requires a nonempty bundle");
        if (DEPTH < 4 || (DEPTH & (DEPTH - 1)) != 0) $fatal(1, "DEPTH must be a power of two >= 4");
        if (GUARD_LO < 0 || GUARD_HI > DEPTH || GUARD_HI < GUARD_LO + 2) $fatal(1, "need 0 <= GUARD_LO, GUARD_LO+2 <= GUARD_HI <= DEPTH");
        if (TIMEOUT != 0 && TIMEOUT < (K > 0 ? K : 0) + ARM + 3) $fatal(1, "TIMEOUT below max(K,0) + ARM + 3 would fire in the window");
    end
`endif
endmodule

// MESO-STRAP-1 (OWNER 12.15a COUNT STRAPS, METHODOLOGY 1.8 conditions): ot_dp_clk_landing_ca with K as the strap input
// strap_k instead of a parameter, so all copies of a partition type share one hardened design; DEPTH stays a parameter
// (the type's largest).  strap_k = K mod 2^KW, KW = log2(DEPTH) + 4 (D4 6 bits, D8 7 bits); every value is legal.  Quasi-
// static: no pin register, read only by the reader-pointer reset load, kit SDC set_false_path -from the strap port, TIEHI/
// TIELO per bit at the parent.  Same logic as ot_dp_clk_landing_ca (LEC per used K: tools/die_plan/strap_lec.py); proof
// with strap_k free-but-constant over all 2^KW values: rtl/test/meso/formal_ca/fv_ca2.sv FV_STRAP.
(* keep_hierarchy *)
module ot_dp_clk_landing_cas #(
    parameter integer W        = 1,
    parameter integer DEPTH    = 4,   // power of two >= 4
    parameter integer GUARD_LO = 0,
    parameter integer GUARD_HI = DEPTH, // <= DEPTH; MESO-RECONCILE-1: default DEPTH (4 was wrong at DEPTH 8)
    parameter integer ARM      = 2 * DEPTH + 4, // receiver cycles after the first valid word before guards are trusted
    // MESO-RECONCILE-1 ready-timeout: fault if the crossing is not armed TIMEOUT receiver cycles after rst_n release
    // (0 = off).  In the window the first valid word (sender count 0) is consumed at receiver count max(K, 0), seen one
    // count later, armed ARM counts after that: armed by count max(K,0) + ARM + 2.  The default adds 2*DEPTH + 6 counts
    // of slack, so it never fires in the window (proven, fv_ca2 A_ALL); a lag below the window (no valid word is ever
    // consumed: never ready, previously no fault) now raises fault (fv_ca2 A_TMO).
    // strap form: K is any value of strap_k, so the timeout covers the largest, 2^KW - 1 (D4 91, D8 171 cycles)
    parameter integer TIMEOUT  = (1 << ($clog2(DEPTH) + 4)) - 1 + ARM + 2 * DEPTH + 8,
    parameter bit CONTROL_STATUS_COPY = 0, // appended to preserve positional parameters
    parameter bit WFALL = 0, // as ot_dp_clk_landing_ca
    // WREG-1 (DIE-HEAD-58 TURNB, 11-03): 1 = the writer START t_rst_n is registered at the receiver face (one wclk edge,
    // == landing_writer_start W=1: K_new = K_old + 1 at bind, count_align_bind.strap_ties) and every (slot, 64-bit chunk)
    // write enable is its own register (fanout <= 64 per enable flop) instead of t_rst_n & slot-decode broadcast to W x
    // DEPTH data flops.  Default 0 = identical logic.
    parameter bit WREG = 0,
    // DSREP-1: copies of each read-select one-hot register per 64-bit chunk (ot_meso_dsel SREP); 1 = identical logic
    parameter integer DSREP = 1,
    // FREG-1 (DIE-HEAD-58 ruling 11-03, hd_turn_a t_i): 1 = the bundle d AND the writer start t_rst_n are registered on
    // the RISING fclk at the receiver face (full-period capture of the source-synchronous input), and the (WFALL) writer
    // reads the registered copies over a local T/2 path.  Data and start move one fclk cycle together and the strap ties
    // K + 1 (count_align_bind.strap_ties) to keep the ring window: q is the same word stream ONE clk cycle later (one
    // added data cycle, results/dh58_turnb_1103/wreg_equiv TB_FREG).
    // Default 0 = identical logic.
    parameter bit FREG = 0,
    // STATUS-REG-1 (KV-SLGLAND-2 11-07): 1 = the ring status crossings end at private per-slot flops (see ot_meso_ring_ca).
    // Data q and ready are cycle-identical in the window; a rv/lap fault is seen one clk later; guard faults unchanged.
    // Default 0 = identical logic.
    parameter bit STATUS_REG = 0,
    parameter int WRITE_CHUNK = 64, // appended for positional compatibility; local write-enable fanout bound
    parameter bit WRITE_TAIL = 0, // optional bounded partial final write chunk; same cycles
    parameter int READ_CHUNK = 0, // optional bounded arbitrary-width read chunks; 0 preserves legacy64/divisibility
    // RSTREP-1 (DIE-QC-97, plan clock.landing_ring_fanout_max): RSTREP extra copies of the receiver start rst_n on
    // rst_xn, same D / raw reset / clock as rst_n (the kept ot_dp_landing_relay_rep last reader-START stage), 0 cycles:
    // rst_n keeps the control flops (seen/arm/ready/fault/timeout, ring rp/status/rv/lap), rst_xn[0] the ring one-hot
    // oh, rst_xn[1..RSTREP-1] the read-select chunks in contiguous groups (ot_meso_ring_ca RSTN).  Every copy equals
    // rst_n, so q/ready/fault are identical; only the reset fanout per driver is bounded.  0 = rst_xn unused, identical logic.
    // RSTH-1 (CLAND-RELAY-3, COORD 11-13): RSTREP = 1 + RH x NCH (RH > 1, NCH read chunks, RH | DSREP) gives every chunk
    // RH copies, each on DSREP/RH read-select copies (reader-START copy <= 48 loads); same D, 0 cycles, no K change.
    parameter int RSTREP = 0,
    // GUARD-REG-1 (see ot_meso_ring_ca; needs STATUS_REG): no logic on a half-cycle rclk path; 0 added cycles.
    // Default 0 = identical logic.
    parameter bit GUARD_REG = 0,
    // PLACEREP-1 (DIE-QC-97, plan clock.landing_ring_fanout_max > 0): every read-select chunk gets its own kept copy of the
    // reader placement value RP0 (one rclk flop per chunk, ot_meso_place_rep) instead of all chunks loading one RP0T net
    // (46-55 loads on an 18-chunk ring).  RP0 = 0 - strap_k is quasi-static (strap tied at the parent); the placement value
    // is read only by the align load, which runs inside the held reset, so a copy that follows RP0 one rclk edge later
    // holds the same value at every align edge.  q / ready / fault / data cycles unchanged.  0 = no copies, identical logic.
    parameter bit PLACEREP = 0,
    // CLAND-QREG-1 (COORD 11-11, KV hub_Ei ring readout -> boundary flop TT -159.5): QREG = 1 adds ONE rclk register
    // stage on q (ot_meso_q_ff, kept, no reset: data only) between the ring readout flop and the receiver's boundary
    // flop, so the long ring -> face wire gets its own cycle.  The ring, its window, K and ready/fault are unchanged;
    // q is the same word stream ONE clk later (+1 data cycle, declared by the plan key landing_output_qreg and counted
    // in the crossing's added_cycles).  Default 0 = identical logic.
    parameter bit QREG = 0
) (
    input  wire         fclk,
    input  wire         t_rst_n,     // sender start, forwarded with fclk (synchronous to fclk)
    input  wire         clk,
    input  wire         rst_n,       // receiver start (count origin), synchronous to clk
    input  wire [(RSTREP > 0 ? RSTREP : 1)-1:0] rst_xn,   // RSTREP-1 copies of rst_n (unused when RSTREP = 0)
    input  wire [$clog2(DEPTH)+3:0] strap_k,  // K mod 2^(log2(DEPTH)+4), quasi-static strap (tied at the parent)
    input  wire [W-1:0] d,
    output wire [W-1:0] q,
    output reg          ready,
    output wire         fault
`ifdef OT_MESO_CA_FV
   ,input  wire [DEPTH-1:0] fv_recent, fv_now,
    input  wire [W+3:0]     fv_any
`endif
);
    localparam integer RW = ((W + 63) / 64) * 64;
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = $clog2(ARM + 1);
    localparam integer TCW = $clog2(TIMEOUT + 2);
    wire rv, lap_ok, glo_ok, ghi_ok;
    wire [RW-1:0] ring_q;
    generate if (QREG) begin : g_qreg
        ot_meso_q_ff #(.W(W)) u_qreg (.clk(clk), .d(ring_q[W-1:0]), .q(q));
    end else begin : g_noqreg
        assign q = ring_q[W-1:0];
    end endgenerate
    // WFALL = 1: the whole writer (slots, count, tags) runs on the opposite fclk edge, so a word launched on the sender's
    // rising edge is held T/2 by structure (FLOW-16 05:48).  Default 0 = no inverter, identical logic.
    wire wclk = WFALL ? ~fclk : fclk;
    wire [W-1:0] d_w;
    wire t_rst_w;
    generate if (FREG) begin : g_freg
        wire t_rst_f;
        ot_meso_face_ff #(.W(W + 1)) u_face (.clk(fclk), .d({t_rst_n, d}), .q({t_rst_f, d_w}));
`ifdef OT_MESO_CA_MUTANT_FREG
        assign t_rst_w = t_rst_n;   // MUTANT: data registered at the face, writer start not (one-cycle misalignment)
`else
        assign t_rst_w = t_rst_f;
`endif
    end else begin : g_nofreg
        assign d_w = d;
        assign t_rst_w = t_rst_n;
    end endgenerate
    reg seen;                       // first valid word consumed
    reg [CW-1:0] arm_cnt;
`ifdef OT_MESO_CA_MUTANT_SR_ARM
    localparam integer ARM_E = ARM;            // MUTANT: rv is one count later, so ready slips one count
`else
    localparam integer ARM_E = STATUS_REG ? ARM - 1 : ARM;   // STATUS-REG-1: rv one count later, armed on the same count
`endif
    wire armed = seen && (arm_cnt == CW'(ARM_E));
    reg fault_state;
    reg [TCW-1:0] tmo_cnt;          // receiver cycles since rst_n release while not armed (saturates at TIMEOUT)
`ifdef OT_MESO_CA_MUTANT_NO_TIMEOUT
    wire tmo = 1'b0;                // MUTANT: ready-timeout disabled
`else
    wire tmo = (TIMEOUT > 0) && !armed && (tmo_cnt == TCW'(TIMEOUT));
`endif
    wire trip = (armed && (!rv || !lap_ok || !glo_ok || !ghi_ok)) || tmo;
    wire fault_next = fault_state || trip;
    ot_dp_landing_fault_port u_fault_port (.clk(clk), .rst_n(rst_n), .d(fault_next), .q(fault));
    always @(posedge clk) begin
        if (!rst_n) begin
            seen <= 0; arm_cnt <= 0; ready <= 0; fault_state <= 0; tmo_cnt <= 0;
        end else begin
            if (!armed && tmo_cnt != TCW'(TIMEOUT)) tmo_cnt <= tmo_cnt + 1'b1;
            if (rv) seen <= 1;
            if (seen && arm_cnt != CW'(ARM_E)) arm_cnt <= arm_cnt + 1'b1;
            ready <= armed && !fault_next;
            fault_state <= fault_next;
        end
    end
    localparam integer RXW = RSTREP > 0 ? RSTREP : 1;
`ifdef OT_MESO_CA_MUTANT_RSTREP
    wire [RXW-1:0] rst_x = RSTREP > 0 ? {rst_xn[RXW-1:1], rst_n & ~rst_xn[0]} : {RXW{1'b1}};  // MUTANT: oh copy wrong
`else
    wire [RXW-1:0] rst_x = RSTREP > 0 ? rst_xn : {RXW{1'b1}};
`endif
    ot_meso_ring_ca #(.W(RW), .DEPTH(DEPTH), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI),
                      .CONTROL_STATUS_COPY(CONTROL_STATUS_COPY), .WREG(WREG), .WEN_NEG(WFALL), .DSREP(DSREP), .WRITE_CHUNK(WRITE_CHUNK), .STATUS_REG(STATUS_REG), .WRITE_TAIL(WRITE_TAIL), .READ_CHUNK(READ_CHUNK), .WLIVE(W), .RSTN(RSTREP), .GUARD_REG(GUARD_REG), .PLACEREP(PLACEREP)) u_ring (
        .tclk(wclk), .wen_clk(WFALL ? fclk : wclk), .t_rst_n(t_rst_w), .t_d({{(RW-W){1'b0}}, d_w}), .rclk(clk), .r_rst_n(rst_n), .r_rst_x(rst_x), .k_s(strap_k),
        .r_d(ring_q), .r_v(rv), .r_lap_ok(lap_ok), .r_glo_ok(glo_ok), .r_ghi_ok(ghi_ok)
`ifdef OT_MESO_CA_FV
       ,.fv_recent(fv_recent), .fv_now(fv_now), .fv_any(fv_any)
`endif
    );
`ifndef SYNTHESIS
    initial begin
        if (W < 1) $fatal(1, "count-aligned landing requires a nonempty bundle");
        if (DEPTH < 4 || (DEPTH & (DEPTH - 1)) != 0) $fatal(1, "DEPTH must be a power of two >= 4");
        if (GUARD_LO < 0 || GUARD_HI > DEPTH || GUARD_HI < GUARD_LO + 2) $fatal(1, "need 0 <= GUARD_LO, GUARD_LO+2 <= GUARD_HI <= DEPTH");
        if (TIMEOUT != 0 && TIMEOUT < (1 << ($clog2(DEPTH) + 4)) - 1 + ARM + 3) $fatal(1, "strap TIMEOUT below 2^KW - 1 + ARM + 3 would fire in the window");
    end
`endif
endmodule

// One direction: DEPTH-slot ring, writer slot = sender count, reader slot = receiver count - K.
// MESO-STRAP-1 (OWNER 12.15a): the read offset is the INPUT k_s (K mod 2^TW, TW = log2(DEPTH)+1+LAPX), so one hardened
// type serves every K: ot_dp_clk_landing_ca drives it with the constant K (identical logic after constant propagation),
// ot_dp_clk_landing_cas with its strap_k pin.  k_s is quasi-static (tied at the parent, sampled only by the reset load of
// rp/oh/dsel), never registered; every value is legal (the ring only uses K mod 2^TW).
module ot_meso_ring_ca #(
    parameter int W        = 64,
    parameter int DEPTH    = 4,
    parameter int GUARD_LO = 0,
    parameter int GUARD_HI = 4,
    parameter int LAPX     = 3,     // extra lap-tag bits per slot: a consumed word from the wrong lap is caught for
                                    // origin errors up to 2^(AW+1+LAPX) counts (the 1-bit lap aliases every 2*DEPTH)
    parameter bit CONTROL_STATUS_COPY = 0,
    parameter bit WREG = 0,         // WREG-1: registered writer start + registered per-(slot, chunk) write enables
    parameter bit WEN_NEG = 0,      // WREG with WFALL: write-enable flops on the falling edge of wen_clk (raw fclk)
    parameter int DSREP = 1,        // DSREP-1: read-select register copies per chunk (ot_meso_dsel SREP)
    // STATUS-REG-1: every status read of the write domain ends at a private rclk flop per slot, with nothing but the slot
    // flop before it; the select/compare then sits between rclk flops (a full period), not on the fclk -> clk crossing
    // (io_ft_v1, io_cor_v1: written/lap_q -> lap_ok 480 ps TT vs 416.5 max_delay). The flops sample at the edge the old
    // r_v_q / r_lap_q sampled, so r_v and r_lap_ok are the old values exactly one rclk later. An unselected slot may be
    // mid-write and go metastable; its select is 0 at the next edge, as an unselected slot's value was masked before.
    // The guards sample the same falling edge into per-slot flops, select at the next rising edge: glo1/ghi1 values and
    // cycles unchanged; oh -> guard becomes a full period instead of T/2. Data path untouched.
    parameter bit STATUS_REG = 0,
    parameter int WRITE_CHUNK = 64, // appended for positional compatibility; local write-enable fanout bound
    parameter bit WRITE_TAIL = 0, // optional bounded partial final write chunk; same cycles
    parameter int READ_CHUNK = 0, // optional bounded arbitrary-width read chunks; 0 preserves legacy64/divisibility
    // WLIVE-1 (DIE-QC-97): live bits of t_d (the cas bundle W before 64-bit padding); a write chunk wholly above it
    // writes only constant padding, so its write-enable flop takes D = 0 (the start has no unproven sink).  Default W: every chunk.
    parameter int WLIVE = W,
    // RSTREP-1: copies of r_rst_n on r_rst_x (0 = unused): r_rst_x[0] resets oh, r_rst_x[1..RSTN-1] the read-select
    // chunks in contiguous groups (chunk c -> 1 + c*(RSTN-1)/NCH); r_rst_n keeps rp and the status/rv/lap flops.
    // RSTH-1 (CLAND-RELAY-3): RSTN - 1 = RH x NCH (RH > 1, RH | DSREP) gives each chunk RH copies
    // r_rst_x[1 + c*RH + h], copy h driving read-select copies [h*DSREP/RH, (h+1)*DSREP/RH) (ot_meso_dsel NR)
    parameter int RSTN = 0,
    // GUARD-REG-1 (CLAND-RING-NEGEDGE, COORD 11-11 09:47; needs STATUS_REG): no logic on any half-cycle rclk path.
    // STATUS_REG still selects/compares the falling-edge guard sample (w_n/lap_n, negedge) into glo1/ghi1 (posedge):
    // a T/2 path through the oh select and the 2*DEPTH OR (kv3_io_cor_v1 legacy form: oh[3] -> ghi0 -152 ps TT).
    // GUARD_REG = 1: the falling-edge sample is UNCHANGED (same instant, so the (GUARD + 0.5) T window is unchanged); it
    // is re-registered on the next rising edge (w_p/lap_p, a zero-logic T/2 hop, as glo0 -> glo1 was), the select uses
    // a private copy oh_q of that edge's oh, and the compare lands in glo2/ghi2 a full period later.  glo1/ghi1 drop
    // out, so glo2/ghi2/glo3/ghi3 and r_glo_ok/r_ghi_ok are cycle-identical to STATUS_REG 0 and 1 (0 added cycles;
    // bench rtl/test/meso/guard_reg).  Default 0 = identical logic.
    parameter bit GUARD_REG = 0,
    // PLACEREP-1: per-chunk kept copy of the placement value RP0 (needs more than one read chunk); see ot_dp_clk_landing_cas
    parameter bit PLACEREP = 0
) (
    input  logic         tclk,
    input  logic         wen_clk,    // WREG write-enable clock: tclk, or the raw fclk with WEN_NEG; unused when !WREG
    input  logic         t_rst_n,
    input  logic [W-1:0] t_d,
    input  logic         rclk,
    input  logic         r_rst_n,
    input  logic [(RSTN > 0 ? RSTN : 1)-1:0] r_rst_x,   // RSTREP-1 copies of r_rst_n (unused when RSTN = 0)
    input  logic [$clog2(DEPTH)+LAPX:0] k_s,   // read offset K mod 2^TW (constant / strap)
    output logic [W-1:0] r_d,        // RDREG: word captured at the consuming edge, presented one period later
    output logic         r_v,        // consumed slot written since the sender start, in the expected lap
    output logic         r_lap_ok,
    output logic         r_glo_ok,
    output logic         r_ghi_ok
`ifdef OT_MESO_CA_FV
   ,input  logic [DEPTH-1:0] fv_recent, fv_now,
    input  logic [W+3:0]     fv_any
`endif
);
    localparam int AW = $clog2(DEPTH);
    localparam int PW = AW + 1;
    localparam int NS = 2 * DEPTH;
    localparam int TW = PW + LAPX;                       // count bits kept: {ext tag, lap, slot}
    localparam int NT = 1 << TW;
    // reader reset value: count of sender word (0 - K) modulo 2^TW
`ifdef OT_MESO_CA_MUTANT_K
    wire [TW-1:0] RP0T = TW'(0) - k_s + TW'(1);   // MUTANT: one count late
`else
    wire [TW-1:0] RP0T = TW'(0) - k_s;
`endif
    wire [PW-1:0] RP0 = RP0T[PW-1:0];

    // ---------------- transmit (tclk): slot = sender count ----------------
    logic [TW-1:0] tc;
    // The CA crossing is the declared flop ring, including widths above the RAM guard.
    (* mem2reg *) logic [W-1:0]  s_d   [DEPTH];
    logic [DEPTH-1:0] s_w, s_lap;
    // WREG-1: t_go = the writer start every slot/count/tag flop uses.  WREG 0: t_go = t_rst_n (identical logic).
    // WREG 1: t_go = t_rst_n one wclk edge late (fs_q), and wen[i, c] = t_go && tc[slot] == i is precomputed one edge
    // early from the port (fs_q ? tc + 1 : 0 is tc at the next edge), one kept flop per (slot, 64-bit chunk).
    // Exactly the WREG 0 ring fed by t_rst_n through one flop (proof: results/dh58_turnb_1103/wreg_equiv).
    localparam int WNC = (WRITE_TAIL && WRITE_CHUNK > 0) ? (W + WRITE_CHUNK - 1) / WRITE_CHUNK : ((WRITE_CHUNK > 0 && W % WRITE_CHUNK == 0) ? W / WRITE_CHUNK : 1);
    localparam int WWC = (WRITE_TAIL && WRITE_CHUNK > 0) ? WRITE_CHUNK : W / WNC;
    wire t_go;
    wire [DEPTH*WNC-1:0] wen;
    if (WREG) begin : g_wreg
        logic fs_q;
        always_ff @(posedge tclk) fs_q <= t_rst_n;
        wire [AW-1:0] slot_nx = fs_q ? tc[AW-1:0] + 1'b1 : '0;
        for (genvar i = 0; i < DEPTH; i++) begin : sl
            for (genvar c = 0; c < WNC; c++) begin : ch
                // WLIVE-1: a padding-only chunk's enable flop keeps its name/site but takes D = 0 (no start load)
                localparam bit LIVE = (c * WWC) < WLIVE;
                wire wen_d = LIVE ? (t_rst_n && (slot_nx == AW'(i))) : 1'b0;
                (* keep = "true" *) ot_meso_wen_ff #(.NEG(WEN_NEG)) u_wen (.clk(wen_clk), .d(wen_d), .q(wen[i * WNC + c]));
            end
        end
        assign t_go = fs_q;
    end else begin : g_wreg_off
        assign t_go = t_rst_n;
        assign wen = '0;
    end
    always_ff @(posedge tclk) begin
`ifdef OT_MESO_CA_MUTANT_FREERUN
        tc <= tc + 1'b1;                                // MUTANT: old free-running writer (no count origin)
        if (!CONTROL_STATUS_COPY) begin
            if (!t_go) s_w <= '0; else s_w[tc[AW-1:0]] <= 1'b1;
        end
`else
        if (!t_go) begin tc <= '0; if (!CONTROL_STATUS_COPY) s_w <= '0; end
        else begin tc <= tc + 1'b1; if (!CONTROL_STATUS_COPY) s_w[tc[AW-1:0]] <= 1'b1; end
`endif
        if (t_go) begin
            if (!CONTROL_STATUS_COPY) s_lap[tc[AW-1:0]] <= tc[AW];
            if (!WREG) s_d[tc[AW-1:0]] <= t_d;
        end
    end
    // Static, disjoint vector slices preserve the declared data flops and
    // avoid an out-of-range final slice when a word has a constant/status tail.
    if (WREG) begin : g_write_chunks
        for (genvar wi = 0; wi < DEPTH; wi++) begin : sl
            for (genvar wc = 0; wc < WNC; wc++) begin : ch
                localparam int CW = W - wc * WWC < WWC ? W - wc * WWC : WWC;
                always_ff @(posedge tclk)
`ifdef OT_MESO_CA_MUTANT_WREG
                    if (wen[wi * WNC + wc] && !(wi == 0 && wc == 0))
`else
                    if (wen[wi * WNC + wc])
`endif
                        s_d[wi][wc * WWC +: CW] <= t_d[wc * WWC +: CW];
            end
        end
    end

    // Private valid/lap status drivers separate their control decode from the
    // falling-edge guard bank. Same D/clock/reset as the original slot flags;
    // no extra crossing or data cycle. Off by default pending physical proof.
    wire [DEPTH-1:0] ctl_w, ctl_lap;
    if (CONTROL_STATUS_COPY) begin : g_control_status_copy
        // Both native banks expose directly kept register outputs. A kept
        // alias through a frontend connection is insufficient for the canonical
        // hook's one-cell driver selection; it allowed the lap banks to merge.
        ot_meso_ca_status_copy #(.DEPTH(DEPTH)) u_guard_status (
            .tclk(tclk), .t_rst_n(t_go), .slot(tc[AW-1:0]),
            .lap(tc[AW]), .written(s_w), .lap_q(s_lap)
        );
        ot_meso_ca_status_copy #(.DEPTH(DEPTH)) u_status (
            .tclk(tclk), .t_rst_n(t_go), .slot(tc[AW-1:0]),
            .lap(tc[AW]), .written(ctl_w), .lap_q(ctl_lap)
        );
    end else begin : g_control_status_original
        assign ctl_w = s_w;
        assign ctl_lap = s_lap;
    end

    // ---------------- receive (rclk): rp = receiver count - K ----------------
    logic [TW-1:0] rp;
    logic [NS-1:0] oh;
    wire r_rst_oh = RSTN > 0 ? r_rst_x[0] : r_rst_n;   // RSTREP-1: equal copy of r_rst_n
    always_ff @(posedge rclk) begin
        if (!r_rst_n) rp <= RP0T;
        else rp <= rp + 1'b1;
    end
    always_ff @(posedge rclk) begin
        if (!r_rst_oh) oh <= NS'(1) << RP0;
        else oh <= {oh[NS-2:0], oh[NS-1]};
    end
    function automatic logic [NS-1:0] rot(input logic [NS-1:0] x, input int k);
        for (int j = 0; j < NS; j++) rot[j] = x[(j - k + 2 * NS) % NS];
    endfunction
    // Status as read by the select: the crossing itself, or (STATUS_REG) its per-slot rclk capture one edge old, read
    // with the select and reset of that same edge. oh rotates every active edge, so rot(oh, -1) is last edge's oh, and
    // with r_rst_n low the st_rst term masks the result.
    wire [DEPTH-1:0] st_w, st_lap;
    wire [NS-1:0] st_oh;
    wire st_rst;
    if (STATUS_REG) begin : g_status_reg
        logic [DEPTH-1:0] w_q, lap_q;
        logic rst_q;
        always_ff @(posedge rclk) begin w_q <= ctl_w; lap_q <= ctl_lap; rst_q <= r_rst_n; end
        assign st_w = w_q; assign st_lap = lap_q; assign st_rst = rst_q;
`ifdef OT_MESO_CA_MUTANT_SR_OH
        assign st_oh = oh;                  // MUTANT: selects the next slot from last edge's capture
`else
        assign st_oh = rot(oh, -1);
`endif
    end else begin : g_status_direct
        assign st_w = ctl_w; assign st_lap = ctl_lap; assign st_rst = r_rst_n; assign st_oh = oh;
    end
    wire [NS-1:0] pos_v   = {st_w & st_lap, st_w & ~st_lap};
    wire [NS-1:0] pos_lap = {st_lap, ~st_lap} | {~st_w, ~st_w};   // not yet written since start: no lap verdict
    // data: per-64-bit chunk registered one-hot select (ot_meso_dsel, REG=1), placed at reset, rotating every cycle
    localparam int NCH = READ_CHUNK > 0 ? (W + READ_CHUNK - 1) / READ_CHUNK : ((W % 64 == 0) ? W / 64 : 1);
    localparam int RSTEP = READ_CHUNK > 0 ? READ_CHUNK : W / NCH;
    // RSTH-1 (CLAND-RELAY-3): reset copies per read chunk.  RSTN - 1 <= NCH (every legacy / fanout-max form) -> 1, the
    // contiguous chunk-group mapping below, identical logic; RSTN - 1 = RH x NCH with RH > 1 -> RH copies per chunk.
    localparam int RH = (RSTN > 1 && RSTN - 1 > NCH) ? (RSTN - 1) / NCH : 1;
    if (RH > 1 && (RH * NCH != RSTN - 1 || DSREP % RH != 0)) begin : g_bad_rh
        $error("ot_meso_ring_ca: RSTN - 1 > NCH needs RSTN - 1 = RH x NCH with RH dividing DSREP");
    end
    logic [W-1:0] rd_q;
    for (genvar c = 0; c < NCH; c++) begin : dch
        localparam int WCH = W - c * RSTEP < RSTEP ? W - c * RSTEP : RSTEP;
        logic [DEPTH*WCH-1:0] sd_c;
        for (genvar i = 0; i < DEPTH; i++) begin : sl
            assign sd_c[i*WCH +: WCH] = s_d[i][c*RSTEP +: WCH];
        end
        // RSTREP-1: this chunk's equal copy of r_rst_n (contiguous chunk groups over r_rst_x[1..RSTN-1])
        wire r_rst_c = RSTN > 1 ? r_rst_x[(RSTN > 1 ? 1 + (c * (RSTN - 1)) / NCH : 0)] : r_rst_n;
        // RSTH-1: with RSTN - 1 = RH x NCH (RH > 1) the chunk takes RH copies r_rst_x[1 + c*RH + h], each driving
        // DSREP/RH of the chunk's read-select copies (ot_meso_dsel NR); RH = 1 keeps r_rst_c (identical logic)
        wire [RH-1:0] r_rst_cv;
        if (RH > 1) begin : g_rh
            for (genvar h = 0; h < RH; h++) begin : hx
                assign r_rst_cv[h] = r_rst_x[1 + c * RH + h];
            end
        end else begin : g_rh1
            assign r_rst_cv = r_rst_c;
        end
        // PLACEREP-1: this chunk's own copy of the placement value (see parameter PLACEREP)
        logic [AW-1:0] pl_c;
        if (PLACEREP && NCH > 1) begin : g_pl
            ot_meso_place_rep #(.N(AW)) u_pl (.clk(rclk), .d(RP0[AW-1:0]), .q(pl_c));
        end else begin : g_pl0
            assign pl_c = RP0[AW-1:0];
        end
        ot_meso_dsel #(.W(WCH), .DEPTH(DEPTH), .REG(1), .SPLIT(0), .SREP(DSREP), .NR(RH)) u_dsel (.clk(rclk),
            .align(~r_rst_cv), .on(r_rst_cv), .place(pl_c), .sd(sd_c), .y(rd_q[c*RSTEP +: WCH]));
    end
    logic r_v_c, r_lap_c, r_lap1_c;
    ot_meso_ohor #(.N(NS)) u_v   (.sel(st_oh), .x(pos_v),   .y(r_v_c));
    ot_meso_ohor #(.N(NS)) u_lap (.sel(st_oh), .x(pos_lap), .y(r_lap1_c));
    if (LAPX > 0) begin : g_tag
        // extended lap tag of every slot (written with the word); the consumed slot's tag must equal rp's upper bits
        (* mem2reg *) logic [LAPX-1:0] s_tag [DEPTH];
        always_ff @(posedge tclk) if (t_go) s_tag[tc[AW-1:0]] <= tc[TW-1:PW];
        wire [LAPX-1:0] st_tag [DEPTH];
        wire [LAPX-1:0] st_rp;
        if (STATUS_REG) begin : g_status_tag
            (* mem2reg *) logic [LAPX-1:0] tag_q [DEPTH];
            logic [LAPX-1:0] rp_q;
            always_ff @(posedge rclk) begin
                for (int i = 0; i < DEPTH; i++) tag_q[i] <= s_tag[i];
`ifdef OT_MESO_CA_MUTANT_SR_TAG
                rp_q <= rp[TW-1:PW] + 1'b1;     // MUTANT: compares the tag against the wrong count
`else
                rp_q <= rp[TW-1:PW];
`endif
            end
            for (genvar i = 0; i < DEPTH; i++) begin : g_t
                assign st_tag[i] = tag_q[i];
            end
            assign st_rp = rp_q;
        end else begin : g_direct_tag
            for (genvar i = 0; i < DEPTH; i++) begin : g_t
                assign st_tag[i] = s_tag[i];
            end
            assign st_rp = rp[TW-1:PW];
        end
        logic [LAPX-1:0] tag_c; logic w_c;
        always_comb begin
            tag_c = '0; w_c = 1'b0;
            for (int i = 0; i < DEPTH; i++) if (st_oh[i] || st_oh[i + DEPTH]) begin tag_c = tag_c | st_tag[i]; w_c = w_c | st_w[i]; end
        end
`ifdef OT_MESO_CA_MUTANT_NO_TAG
        assign r_lap_c = r_lap1_c;                                       // MUTANT: extended tag ignored
`else
`ifdef OT_MESO_CA_SLOT_LAP
        // Opt-in short crossing control: compare each slot tag locally, before
        // selecting it. rp/oh reset and rotate together, hence oh is one-hot
        // on every active read edge. No new registers or interface cycles.
        wire [NS-1:0] slot_lap_ok;
        for (genvar li = 0; li < DEPTH; li++) begin : g_slot_lap
            wire tag_ok = st_tag[li] == st_rp;
`ifdef OT_MESO_CA_MUTANT_SLOT_LAP
            wire unwritten = 1'b0; // mutant: absent slot must have no lap verdict
`else
            wire unwritten = !st_w[li];
`endif
            assign slot_lap_ok[li] = unwritten || (!st_lap[li] && tag_ok);
            assign slot_lap_ok[li+DEPTH] = unwritten || (st_lap[li] && tag_ok);
        end
        assign r_lap_c = |(st_oh & slot_lap_ok);
`else
        assign r_lap_c = r_lap1_c && (!w_c || tag_c == st_rp);
`endif
`endif
    end else begin : g_notag
        assign r_lap_c = r_lap1_c;
    end
    logic r_v_q, r_lap_q;
`ifdef OT_MESO_CA_FV
    if (STATUS_REG) begin : g_fv_status_reg_unmodeled
        $error("OT_MESO_CA_FV does not model STATUS_REG; prove it with rtl/test/meso/status_reg");
    end
    // the slot consumed at this edge; if it was written within the STA bound the captured word/flags are arbitrary
    logic [AW-1:0] fv_rs; always_comb begin fv_rs = '0; for (int j = 0; j < NS; j++) if (oh[j]) fv_rs = AW'(j % DEPTH); end
    wire fv_dx = fv_recent[fv_rs];
    logic fv_dx_q; logic [W-1:0] fv_any_q;
    always_ff @(posedge rclk) begin
        r_v_q   <= (fv_dx ? fv_any[0] : r_v_c) && r_rst_n;
        r_lap_q <= (fv_dx ? fv_any[1] : r_lap_c) || !r_rst_n;
    end
    assign r_d = fv_dx_q ? fv_any_q : rd_q;
    always_ff @(posedge rclk) begin fv_dx_q <= fv_dx; fv_any_q <= W'(fv_any >> 4); end
`else
    always_ff @(posedge rclk) begin
        r_v_q   <= r_v_c && st_rst;
        r_lap_q <= r_lap_c || !st_rst;
    end
    assign r_d = rd_q;
`endif
    assign r_v = r_v_q; assign r_lap_ok = r_lap_q;

    // guards (as ot_meso_ring): falling read edge, then 3 rising flops
    wire [NS-1:0] g_oh;              // guard select: oh, or (GUARD_REG) its private copy one edge old
    wire [NS-1:0] oh_lo = rot(g_oh, GUARD_LO);
    wire [NS-1:0] oh_hi = rot(g_oh, GUARD_HI - 1);
    wire [DEPTH-1:0] gs_w, gs_lap;
    if (STATUS_REG) begin : g_guard_reg
        // same falling edge as glo0/ghi0; oh only changes on the rising edge, so the select below is the select at it
        logic [DEPTH-1:0] w_n, lap_n;
`ifdef OT_MESO_CA_MUTANT_SR_GUARD
        always_ff @(posedge rclk) begin w_n <= s_w; lap_n <= s_lap; end   // MUTANT: guard samples the wrong edge
`else
        always_ff @(negedge rclk) begin w_n <= s_w; lap_n <= s_lap; end
`endif
        if (GUARD_REG) begin : g_gpos
            // GUARD-REG-1: the falling-edge sample, re-registered at the next rising edge with that edge's select
            (* async_reg = "true" *) logic [DEPTH-1:0] w_p, lap_p;
            logic [NS-1:0] oh_q;
            always_ff @(posedge rclk) begin w_p <= w_n; lap_p <= lap_n; oh_q <= oh; end
            assign gs_w = w_p; assign gs_lap = lap_p;
`ifdef OT_MESO_CA_MUTANT_GR_OH
            assign g_oh = oh;               // MUTANT: selects with the next edge's one-hot (one slot late)
`else
            assign g_oh = oh_q;
`endif
        end else begin : g_gneg
            assign gs_w = w_n; assign gs_lap = lap_n; assign g_oh = oh;
        end
    end else begin : g_guard_direct
        assign gs_w = s_w; assign gs_lap = s_lap; assign g_oh = oh;
    end
    wire glo_c = |(oh_lo & {gs_lap, ~gs_lap} & {gs_w, gs_w});   // written since start, in this lap
    wire ghi_c = ~|(oh_hi & {gs_lap, ~gs_lap} & {gs_w, gs_w});  // not yet written in this lap
    (* async_reg = "true" *) logic glo0, ghi0;
    (* async_reg = "true" *) logic glo1, glo2, ghi1, ghi2;
    logic glo3, ghi3;
`ifdef OT_MESO_CA_FV
    logic [AW-1:0] fv_lo_s, fv_hi_s;
    always_comb begin
        fv_lo_s = '0; fv_hi_s = '0;
        for (int j = 0; j < NS; j++) begin if (oh_lo[j]) fv_lo_s = AW'(j % DEPTH); if (oh_hi[j]) fv_hi_s = AW'(j % DEPTH); end
    end
    always_ff @(negedge rclk) begin
        glo0 <= fv_now[fv_lo_s] ? fv_any[2] : glo_c;
        ghi0 <= fv_now[fv_hi_s] ? fv_any[3] : ghi_c;
    end
`else
    always_ff @(negedge rclk) begin
        glo0 <= STATUS_REG ? 1'b0 : glo_c;
        ghi0 <= STATUS_REG ? 1'b0 : ghi_c;
    end
`endif
`ifdef OT_MESO_CA_MUTANT_GR_LATE
    localparam bit GR = 1'b0;               // MUTANT: compare into glo1 as STATUS_REG, i.e. guards one clk late
`else
    localparam bit GR = GUARD_REG;          // GUARD-REG-1: the compare (one edge later) replaces the glo1/ghi1 stage
`endif
    always_ff @(posedge rclk) begin
        glo1 <= STATUS_REG ? glo_c : glo0; glo2 <= GR ? glo_c : glo1; glo3 <= glo2;
        ghi1 <= STATUS_REG ? ghi_c : ghi0; ghi2 <= GR ? ghi_c : ghi1; ghi3 <= ghi2;
    end
`ifndef SYNTHESIS
    initial if (GUARD_REG && !STATUS_REG) $fatal(1, "GUARD_REG needs STATUS_REG");
`endif
`ifdef OT_MESO_CA_MUTANT_NO_GUARD
    assign r_glo_ok = 1'b1;
    assign r_ghi_ok = 1'b1;
`else
    assign r_glo_ok = glo3;
    assign r_ghi_ok = ghi3;
`endif
endmodule

// Count origin of a region from its parent's start, forwarded beside a tree crossing (start wavefront).
// p_start: the parent's start flop, forwarded with fclk (as t_rst_n of the ring); it rises once and stays high.
// The child's start = 3 synchroniser flops (the first optionally on the falling edge, EDGE_FALL, chosen at bind time
// so the sampling boundary lies away from the crossing's derated phase interval) + PAD plain flops.  Whole cycles
// added: PAD + 3 + j, j in {0, 1} set by the static phase; j is chip-invariant when the derated phase interval avoids
// the sampling boundary, otherwise both values occur across chips and the binder widens the lag window of every
// crossing whose tree path includes this edge by one period (tools/die_plan/count_align_plan.py).  The tree crossing
// itself always lands in its window: its lag lies in [c, c + T) by construction.  Cleared only by the raw reset.
(* keep_hierarchy *)
module ot_dp_landing_origin #(
    parameter integer PAD = 0,
    parameter bit EDGE_FALL = 0
) (
    input  wire clk,
    input  wire rst_raw_n,   // raw region reset (power-on / die reset), synchronous to clk
    input  wire p_start,     // parent's forwarded start (asynchronous to clk, monotonic 0 -> 1)
    output wire start        // region count origin: the ring readers' rst_n and the region's own start
);
    (* async_reg = "true" *) reg s0, s1;
    reg s2;
    wire s_in;
    if (EDGE_FALL) begin : g_fall
        (* async_reg = "true" *) reg sf;
        always @(negedge clk) sf <= p_start;
        assign s_in = sf;
    end else begin : g_rise
        assign s_in = p_start;
    end
    always @(posedge clk) begin
        if (!rst_raw_n) begin s0 <= 0; s1 <= 0; s2 <= 0; end
        else begin s0 <= s_in; s1 <= s0; s2 <= s1; end
    end
    if (PAD > 0) begin : g_pad
        reg [PAD-1:0] pd;
        always @(posedge clk) if (!rst_raw_n) pd <= 0; else pd <= PAD'({pd, s2});
        assign start = pd[PAD-1];
    end else begin : g_nopad
        assign start = s2;
    end
endmodule

// MESO-STRAP-1 (OWNER 12.15a): ot_dp_landing_origin with PAD and EDGE_FALL as strap inputs instead of parameters, so the
// copies of a partition type that differ only in their start-tree edge share one hardened design.  strap_pad selects the
// tap of a PADMAX = 2^PADW - 1 flop chain (every value legal), strap_efall the falling-edge first synchroniser.  Both are
// quasi-static (tied TIEHI/TIELO at the parent, no pin register, set_false_path -from in the kit SDC); for a tied value the
// logic equals ot_dp_landing_origin #(.PAD(strap_pad), .EDGE_FALL(strap_efall)) plus unobservable flops (LEC per used
// value: tools/die_plan/strap_lec.py).  The static select muxes sit before the first synchroniser flop (p_start is
// asynchronous; a constant select never glitches) and after the chain (start, timed like the parameter form's last flop).
(* keep_hierarchy *)
module ot_dp_landing_origin_s #(
    parameter integer PADW = 1,
    // Optional retained DATA-state copies for the forwarded START face flops.
    // Their D/clock/reset match the existing stages; latency and sampling stay exact.
    parameter integer FWD_COPY = 0
) (
    input  wire            clk,
    input  wire            rst_raw_n,
    input  wire            p_start,
    input  wire            strap_efall,
    input  wire [PADW-1:0] strap_pad,
    output wire            start,
    // DIE-HEAD-10 FSTART out: D-side of start (start_d(t) == start(t+1) while rst_raw_n is high).  The wrapper's
    // dedicated face flop per forwarded start pin (d = start_d, same clk / raw reset) equals start every cycle:
    // 0 added cycles, proven by results/die_head_1028/die_head_10_fstart/fv_start_o.sh; internal loads keep start
    output wire            start_d
);
    localparam integer PADMAX = (1 << PADW) - 1;
    (* async_reg = "true" *) reg s0, s1, sf;
    reg s2;
    always @(negedge clk) sf <= p_start;
    wire s_in = strap_efall ? sf : p_start;
    always @(posedge clk) begin
        if (!rst_raw_n) begin s0 <= 0; s1 <= 0; s2 <= 0; end
        else begin s0 <= s_in; s1 <= s0; s2 <= s1; end
    end
    reg [PADMAX-1:0] pd;
    always @(posedge clk) if (!rst_raw_n) pd <= 0; else pd <= PADMAX'({pd, s2});
    wire [PADMAX:0] taps = {pd, s2};
    assign start = taps[strap_pad];
    // one tap earlier: taps_e[j] is the D-side of taps[j] (taps_e[0] = s1 -> s2, taps_e[j] = taps[j-1])
    wire [PADMAX:0] taps_e = {taps[PADMAX-1:0], s1};
`ifdef OT_ORIGIN_MUTANT_LATE
    assign start_d = taps[strap_pad];     // MUTANT (fv only): one cycle late
`else
    generate if (FWD_COPY != 0) begin : g_export
        wire [PADMAX-1:0] export_q;
        for (genvar k = 0; k < PADMAX; k = k + 1) begin : g_copy
            wire d;
            if (k == 0) assign d = s1;
            else if (k == 1) assign d = s2;
            else assign d = pd[k-2];
`ifdef OT_ORIGIN_EXPORT_MUTANT_LATE
            wire copy_d;
            if (k == 0) assign copy_d = s2; else assign copy_d = d;
`else
            wire copy_d = d;
`endif
            (* keep = "true" *) ot_dp_origin_export_ff u_copy (
                .clk(clk), .rst_raw_n(rst_raw_n), .d(copy_d), .q(export_q[k]));
        end
        wire [PADMAX:0] export_taps = {export_q, s1};
        assign start_d = export_taps[strap_pad];
    end else begin : g_shared_export
        assign start_d = taps_e[strap_pad];
    end endgenerate
`endif
`ifndef SYNTHESIS
    initial if (PADW < 1 || PADW > 4) $fatal(1, "origin strap PADW must be 1..4");
`endif
endmodule

// Hierarchy retains the distinct physical export copy when its data equation
// equals an internal origin stage. This is a data register, never a clock pad.
(* keep_hierarchy = "yes" *)
module ot_dp_origin_export_ff (
    input wire clk,
    input wire rst_raw_n,
    input wire d,
    output reg q
);
    always @(posedge clk) if (!rst_raw_n) q <= 1'b0; else q <= d;
endmodule

// Root region count origin (MESO-INTEG-1): the start tree's root has no parent start; its origin is a plain counter
// SETTLE cycles after its raw reset release, so it is chip-invariant.  SETTLE must cover the die's raw-reset wavefront
// release spread (every child origin's rst_raw_n must be high before the start wave reaches it); the binder takes it
// from the bind table (root_settle_cycles).  Cleared only by the raw reset; start rises once and stays high.
(* keep_hierarchy *)
module ot_dp_landing_root #(
    parameter integer SETTLE = 64
) (
    input  wire clk,
    input  wire rst_raw_n,
    output reg  start,
    // DIE-HEAD-10 FSTART out: D-side of start (start_d(t) == start(t+1) while rst_raw_n is high), see origin_s
    output wire start_d
);
    localparam integer CW = $clog2(SETTLE + 1);
    reg [CW-1:0] n;
`ifdef OT_ROOT_MUTANT_EARLY
    assign start_d = (n == CW'(SETTLE - 1));   // MUTANT (fv only): one cycle early
`else
    assign start_d = (n == CW'(SETTLE));
`endif
    always @(posedge clk) begin
        if (!rst_raw_n) begin n <= 0; start <= 0; end
        else begin
            if (n != CW'(SETTLE)) n <= n + 1'b1;
            start <= (n == CW'(SETTLE));
        end
    end
`ifndef SYNTHESIS
    initial if (SETTLE < 1) $fatal(1, "root SETTLE must be >= 1");
`endif
endmodule

// Intra-region start relay stage (DIE-KV-3/CAORIGIN, COORD 21:14 ASK 3): a region holding several landed partitions
// has ONE origin (ot_dp_landing_root / ot_dp_landing_origin) in its origin partition; every other landed partition of
// the region takes the origin's start through two of these flops on the region clock (tx in the origin partition ->
// cland_rstart pin -> rx in the relay partition).  It is a plain registered same-clock control path, timed by the die
// STA as an intra-region related pair (not a landed crossing).  count_align_bind.py gives the relay partition the
// count origin N_origin + 2 and shifts the K of its crossings by the same 2 counts.  Cleared by the partition's raw
// reset (synchronous, like ot_dp_landing_root); the raw reset must release before the start wave arrives (root SETTLE).
(* keep_hierarchy *)
module ot_dp_landing_relay (
    input  wire clk,
    input  wire rst_raw_n,
    input  wire d,
    output reg  q
);
    always @(posedge clk) begin
        if (!rst_raw_n) q <= 1'b0;
        else q <= d;
    end
endmodule

// RSTREP-1 (DIE-QC-97): one reader-START stage as 1 + N kept ot_dp_landing_relay copies at the same site, same clk /
// rst_raw_n / d: q is the stage itself (control loads), qx[j] equal copies for the ring's rst_xn (0 cycles; each
// copy's reset fanout is bounded instead of one flop driving every reset load of the ring).
(* keep_hierarchy *)
module ot_dp_landing_relay_rep #(parameter integer N = 1) (
    input  wire         clk,
    input  wire         rst_raw_n,
    input  wire         d,
    output wire         q,
    output wire [N-1:0] qx
);
    (* keep = "true" *) ot_dp_landing_relay u_q (.clk(clk), .rst_raw_n(rst_raw_n), .d(d), .q(q));
    for (genvar j = 0; j < N; j++) begin : g_x
        (* keep = "true" *) ot_dp_landing_relay u_r (.clk(clk), .rst_raw_n(rst_raw_n), .d(d), .q(qx[j]));
    end
endmodule

// FREG-1 receiver face register of ot_dp_clk_landing_cas (rising fclk): kept so synthesis does not retime or merge it
// into the ring and the face-flop placement keeps it at the input pins.
(* keep_hierarchy, keep *)
module ot_meso_face_ff #(parameter integer W = 1) (
    input wire clk,
    input wire [W-1:0] d,
    (* keep *) output reg [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule

// WREG-1 write-enable register of one (slot, 64-bit chunk) of ot_meso_ring_ca: kept so the per-chunk copies (same D)
// are not merged back into one W x DEPTH broadcast.
// NEG = 1 (DIE-QC-70, WFALL ring): the flop captures on the falling edge of clk, the raw fclk.  A kept module cannot
// absorb the wclk inverter as the slot flops do, so posedge ~fclk here left one inverter per ring on the clock path
// and the write enables on another clock net than the slots they enable.
(* keep_hierarchy, keep *)
module ot_meso_wen_ff #(parameter bit NEG = 0) (
    input wire clk, d,
    (* keep *) output reg q
);
    generate if (NEG) begin : g_neg
        always @(negedge clk) q <= d;
    end else begin : g_pos
        always @(posedge clk) q <= d;
    end endgenerate
endmodule

// Dedicated same-state slot status bank. The canonical keep-register hook
// preserves these drivers and the explicitly kept original guard bank.
(* keep_hierarchy, keep *)
module ot_meso_ca_status_copy #(parameter int DEPTH=4) (
    input logic tclk, t_rst_n,
    input logic [$clog2(DEPTH)-1:0] slot,
    input logic lap,
    (* keep *) output logic [DEPTH-1:0] written,
    (* keep *) output logic [DEPTH-1:0] lap_q
);
    always_ff @(posedge tclk) begin
        if (!t_rst_n) written <= '0;
        else written[slot] <= 1'b1;
        if (t_rst_n) lap_q[slot] <= lap;
`ifdef OT_MESO_CA_MUTANT_STATUS_COPY
        written[0] <= 1'b0; // control: omit one slot's written status
`endif
    end
endmodule

// HEAD raw-reset output: preserve the original wavefront state and provide a
// dedicated same-cycle output register. The pin copy samples the SAME D and
// clock; adding a flop after q would add an unpriced reset-release cycle.
(* keep_hierarchy, keep *)
module ot_dp_head_raw_export_pair (
    input wire clk, d,
    (* keep *) output reg q,
    (* keep *) output reg export_q
);
    always @(posedge clk) begin
        q <= d;
`ifdef OT_HEAD_RAW_EXPORT_MUTANT_LATE
        export_q <= q;
`else
        export_q <= d;
`endif
    end
endmodule

// PLACEREP-1 (DIE-QC-97): one chunk's kept copy of the ring placement value; a separate kept module so synthesis does not
// merge the per-chunk flops back into one net.
(* keep_hierarchy, keep *)
module ot_meso_place_rep #(parameter int N = 2) (
    input  logic         clk,
    input  logic [N-1:0] d,
    output logic [N-1:0] q
);
    always_ff @(posedge clk) q <= d;
endmodule
