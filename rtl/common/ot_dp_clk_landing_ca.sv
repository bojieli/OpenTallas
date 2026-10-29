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
    parameter integer TIMEOUT  = (K > 0 ? K : 0) + ARM + 2 * DEPTH + 8
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
    assign q = ring_q[W-1:0];
    reg seen;                       // first valid word consumed
    reg [CW-1:0] arm_cnt;
    wire armed = seen && (arm_cnt == CW'(ARM));
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
            if (seen && arm_cnt != CW'(ARM)) arm_cnt <= arm_cnt + 1'b1;
            ready <= armed && !fault_next;
            fault_state <= fault_next;
        end
    end
    localparam integer KTW = AW + 1 + 3;      // ring count width (LAPX = 3)
    localparam integer KNT = 1 << KTW;
    localparam integer KM  = ((K % KNT) + KNT) % KNT;
    ot_meso_ring_ca #(.W(RW), .DEPTH(DEPTH), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI)) u_ring (
        .tclk(fclk), .t_rst_n(t_rst_n), .t_d({{(RW-W){1'b0}}, d}), .rclk(clk), .r_rst_n(rst_n), .k_s(KTW'(KM)),
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
    parameter integer TIMEOUT  = (1 << ($clog2(DEPTH) + 4)) - 1 + ARM + 2 * DEPTH + 8
) (
    input  wire         fclk,
    input  wire         t_rst_n,     // sender start, forwarded with fclk (synchronous to fclk)
    input  wire         clk,
    input  wire         rst_n,       // receiver start (count origin), synchronous to clk
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
    assign q = ring_q[W-1:0];
    reg seen;                       // first valid word consumed
    reg [CW-1:0] arm_cnt;
    wire armed = seen && (arm_cnt == CW'(ARM));
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
            if (seen && arm_cnt != CW'(ARM)) arm_cnt <= arm_cnt + 1'b1;
            ready <= armed && !fault_next;
            fault_state <= fault_next;
        end
    end
    ot_meso_ring_ca #(.W(RW), .DEPTH(DEPTH), .GUARD_LO(GUARD_LO), .GUARD_HI(GUARD_HI)) u_ring (
        .tclk(fclk), .t_rst_n(t_rst_n), .t_d({{(RW-W){1'b0}}, d}), .rclk(clk), .r_rst_n(rst_n), .k_s(strap_k),
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
    parameter int LAPX     = 3      // extra lap-tag bits per slot: a consumed word from the wrong lap is caught for
                                    // origin errors up to 2^(AW+1+LAPX) counts (the 1-bit lap aliases every 2*DEPTH)
) (
    input  logic         tclk,
    input  logic         t_rst_n,
    input  logic [W-1:0] t_d,
    input  logic         rclk,
    input  logic         r_rst_n,
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
    always_ff @(posedge tclk) begin
`ifdef OT_MESO_CA_MUTANT_FREERUN
        tc <= tc + 1'b1;                                // MUTANT: old free-running writer (no count origin)
        if (!t_rst_n) s_w <= '0; else s_w[tc[AW-1:0]] <= 1'b1;
`else
        if (!t_rst_n) begin tc <= '0; s_w <= '0; end
        else begin tc <= tc + 1'b1; s_w[tc[AW-1:0]] <= 1'b1; end
`endif
        if (t_rst_n) begin s_lap[tc[AW-1:0]] <= tc[AW]; s_d[tc[AW-1:0]] <= t_d; end
    end

    // ---------------- receive (rclk): rp = receiver count - K ----------------
    logic [TW-1:0] rp;
    logic [NS-1:0] oh;
    always_ff @(posedge rclk) begin
        if (!r_rst_n) begin rp <= RP0T; oh <= NS'(1) << RP0; end
        else begin rp <= rp + 1'b1; oh <= {oh[NS-2:0], oh[NS-1]}; end
    end
    wire [NS-1:0] pos_v   = {s_w & s_lap, s_w & ~s_lap};
    wire [NS-1:0] pos_lap = {s_lap, ~s_lap} | {~s_w, ~s_w};   // not yet written since start: no lap verdict
    function automatic logic [NS-1:0] rot(input logic [NS-1:0] x, input int k);
        for (int j = 0; j < NS; j++) rot[j] = x[(j - k + 2 * NS) % NS];
    endfunction
    // data: per-64-bit chunk registered one-hot select (ot_meso_dsel, REG=1), placed at reset, rotating every cycle
    localparam int NCH = (W % 64 == 0) ? W / 64 : 1;
    localparam int WCH = W / NCH;
    logic [W-1:0] rd_q;
    for (genvar c = 0; c < NCH; c++) begin : dch
        logic [DEPTH*WCH-1:0] sd_c;
        for (genvar i = 0; i < DEPTH; i++) begin : sl
            assign sd_c[i*WCH +: WCH] = s_d[i][c*WCH +: WCH];
        end
        ot_meso_dsel #(.W(WCH), .DEPTH(DEPTH), .REG(1), .SPLIT(0)) u_dsel (.clk(rclk), .align(!r_rst_n), .on(r_rst_n),
            .place(RP0[AW-1:0]), .sd(sd_c), .y(rd_q[c*WCH +: WCH]));
    end
    logic r_v_c, r_lap_c, r_lap1_c;
    ot_meso_ohor #(.N(NS)) u_v   (.sel(oh), .x(pos_v),   .y(r_v_c));
    ot_meso_ohor #(.N(NS)) u_lap (.sel(oh), .x(pos_lap), .y(r_lap1_c));
    if (LAPX > 0) begin : g_tag
        // extended lap tag of every slot (written with the word); the consumed slot's tag must equal rp's upper bits
        (* mem2reg *) logic [LAPX-1:0] s_tag [DEPTH];
        always_ff @(posedge tclk) if (t_rst_n) s_tag[tc[AW-1:0]] <= tc[TW-1:PW];
        logic [LAPX-1:0] tag_c; logic w_c;
        always_comb begin
            tag_c = '0; w_c = 1'b0;
            for (int i = 0; i < DEPTH; i++) if (oh[i] || oh[i + DEPTH]) begin tag_c = tag_c | s_tag[i]; w_c = w_c | s_w[i]; end
        end
`ifdef OT_MESO_CA_MUTANT_NO_TAG
        assign r_lap_c = r_lap1_c;                                       // MUTANT: extended tag ignored
`else
        assign r_lap_c = r_lap1_c && (!w_c || tag_c == rp[TW-1:PW]);
`endif
    end else begin : g_notag
        assign r_lap_c = r_lap1_c;
    end
    logic r_v_q, r_lap_q;
`ifdef OT_MESO_CA_FV
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
        r_v_q   <= r_v_c && r_rst_n;
        r_lap_q <= r_lap_c || !r_rst_n;
    end
    assign r_d = rd_q;
`endif
    assign r_v = r_v_q; assign r_lap_ok = r_lap_q;

    // guards (as ot_meso_ring): falling read edge, then 3 rising flops
    wire [NS-1:0] oh_lo = rot(oh, GUARD_LO);
    wire [NS-1:0] oh_hi = rot(oh, GUARD_HI - 1);
    wire glo_c = |(oh_lo & {s_lap, ~s_lap} & {s_w, s_w});   // written since start, in this lap
    wire ghi_c = ~|(oh_hi & {s_lap, ~s_lap} & {s_w, s_w});  // not yet written in this lap
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
        glo0 <= glo_c;
        ghi0 <= ghi_c;
    end
`endif
    always_ff @(posedge rclk) begin
        glo1 <= glo0; glo2 <= glo1; glo3 <= glo2;
        ghi1 <= ghi0; ghi2 <= ghi1; ghi3 <= ghi2;
    end
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
