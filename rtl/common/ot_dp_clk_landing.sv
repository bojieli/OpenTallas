// Opt-in die-plan clock-region landing. The entire bus, including its epoch
// bit, is one continuously sampled word: no valid decoding or backpressure.
// fclk is forwarded from the transmitting partition beside the data bus.
// clk is the receiving partition's local clock from the same frequency source.
// The receiver's original boundary flop remains AFTER q. OFFSET=2/RDREG=1
// prices three extra cycles in the zero-phase reference; phase placement and
// its guard window still require the region-specific physical timing gate.
// rst_n is the timed receiver wavefront reset, not an asynchronous reset.
(* keep_hierarchy *)
module ot_dp_clk_landing #(
    parameter integer W = 1,
    parameter integer SETTLE = 16,
    parameter bit     WNEG = 0,    // S81-RINGHOLD-3: falling forwarded-clock write
    parameter bit     FREG = 0,    // optional rising-fclk input capture: +1 data cycle
    parameter integer DSREP = 1,   // DIE-S81-85 11-09: ring read-select copies per 64-bit chunk (ot_meso_dsel SREP); 1 = identical logic
    // CLAND-QREG-1 (COORD 11-11, KV hub_Ei ring readout -> boundary flop TT -159.5): QREG = 1 adds ONE rclk register
    // stage on q (ot_meso_q_ff, kept, no reset: data only) between the ring readout flop and the receiver's boundary
    // flop, so the long ring -> face wire gets its own cycle.  The ring, its window, K and ready/fault are unchanged;
    // q is the same word stream ONE clk later (+1 data cycle, declared by the plan key landing_output_qreg and counted
    // in the crossing's added_cycles).  Default 0 = identical logic.
    parameter bit     QREG = 0
) (
    input wire fclk,
    input wire clk,
    input wire rst_n,
    input wire [W-1:0] d,
    output wire [W-1:0] q,
    output reg ready,
    output wire fault
);
    // Keep the existing ring's selectors in 64-bit chunks even for a bus
    // carrying an extra epoch bit. Padding is internal unused capacity only.
    localparam integer RW = ((W + 63) / 64) * 64;
    localparam integer NC = RW / 64;
    localparam integer CW = $clog2(SETTLE + 1);
    reg [CW-1:0] count;
    reg on;
`ifdef OT_S81_CLAND_WCHK
    // S81-RCK-10 11-07 (vJ, CLAND class): vI probe tc(fall fclk) -> s_d -710 ps, 1363 ep: ONE ring counter decoded into
    // the slot enables of 4 x 576 flops along a 500-um pin column.  Ring WCHK = 1: one registered one-hot slot select per
    // 64-bit chunk (loaded one edge ahead with tc + 1: same slot at every edge after the first).
    // vJ: WCHKC (registered slot-index COPY per chunk, local decode) rather than WCHK's one-hot register, so the slot
    // write conditions stay a decode of one register that face_guard's hold_mux exclusivity proof accepts.
    // rrl -> align -> 9 dsel di (-260 ps): the receiver's training reset takes ONE local register here (rst_l): the
    // pointer is placed from the synchronised write samples one edge later, so the data latency is unchanged; only
    // ready rises one clk later (the free-running ring and the guards are not reset).
    reg rst_l;
    always @(posedge clk) rst_l <= rst_n;
    wire rst_i = rst_l;
    localparam bit RING_WCHKC = 1;
`else
    wire rst_i = rst_n;
    localparam bit RING_WCHKC = 0;
`endif
    wire align = rst_i && !on && (count == CW'(SETTLE));
`ifdef OT_S81_CLAND_LOCAL_ON
`ifndef OT_S81_CLAND_WCHK
    initial $error("CLAND_LOCAL_ON requires the registered local reset of CLAND_WCHK");
`endif
    // Exact copies of on and align, computed from their NEXT state on the
    // same edge. Reader chunks now use local flop Qs instead of one on/align
    // broadcast along the pin column. No new data or status cycle.
    reg [NC-1:0] on_c, align_c;
    (* keep = 1, dont_touch = 1 *) always @(posedge clk) begin
        on_c <= {NC{rst_i && (on || (count == CW'(SETTLE)))}};
        // rst_i is itself rst_l <= rst_n, so next-align uses next rst_i
        // (=rst_n), plus the old reset that decides count/on's next values.
        align_c <= {NC{rst_n && rst_i && !on && (count == CW'(SETTLE - 1))}};
    end
    localparam bit RING_ONV = 1;
    localparam integer RING_WCCB = 16;
    wire [NC-1:0] ring_on_v = on_c;
    wire [NC-1:0] ring_align_v = align_c;
`else
    localparam bit RING_ONV = 0;
    localparam integer RING_WCCB = 64;
    wire [NC-1:0] ring_on_v = {NC{on}};
    wire [NC-1:0] ring_align_v = {NC{align}};
`endif
    wire rv, lap_ok, glo_ok, ghi_ok;
    wire [W-1:0] d_write;
    generate if (FREG) begin : g_freg
        // A sender's rising-edge word is captured at the physical input face.
        // The free-running write pointer and receiver training are unchanged.
        ot_dp_landing_input_face #(.W(W)) u_face (.clk(fclk), .d(d), .q(d_write));
    end else begin : g_nofreg
        assign d_write = d;
    end endgenerate
`ifdef OT_LEGACY_FREG_MUTANT_BYPASS
    wire [RW-1:0] ring_d = {{(RW-W){1'b0}}, d};
`else
    wire [RW-1:0] ring_d = {{(RW-W){1'b0}}, d_write};
`endif
    wire [RW-1:0] ring_q;
    generate if (QREG) begin : g_qreg
        ot_meso_q_ff #(.W(W)) u_qreg (.clk(clk), .d(ring_q[W-1:0]), .q(q));
    end else begin : g_noqreg
        assign q = ring_q[W-1:0];
    end endgenerate
    reg [2:0] arm;
    reg fault_state;
    wire trip = arm[2] && (!rv || !lap_ok || !glo_ok || !ghi_ok);
    wire fault_next = fault_state || trip;
    // A private output flop drives ONLY the observed fault pin. The sticky
    // state also controls readiness, so exporting that state directly would
    // violate the dedicated registered-pin rule.
    ot_dp_landing_fault_port u_fault_port (.clk(clk), .rst_n(rst_i), .d(fault_next), .q(fault));
    // The ring write pointer is deliberately free-running across local resets.
    // SETTLE lets Gray/half-edge samples fill before placing the read pointer.
`ifdef OT_S81_CLAND_LOCAL_ON
    (* keep = 1, dont_touch = 1 *)
`endif
    always @(posedge clk) begin
        if (!rst_i) begin
            count <= 0;
            on <= 0;
            ready <= 0;
            fault_state <= 0;
            arm <= 0;
        end else begin
            if (!on) begin
                if (count != CW'(SETTLE)) count <= count + 1'b1;
                else on <= 1;
            end
            arm <= {arm[1:0], on};
            ready <= arm[2] && !fault_state;
            fault_state <= fault_next;
        end
    end
    ot_meso_ring #(.W(RW), .DEPTH(4), .OFFSET(2), .GUARD_LO(0),
                   .GUARD_HI(4), .RDREG(1), .TNEG(WNEG), .WCHKC(RING_WCHKC), .WCCB(RING_WCCB), .ONV(RING_ONV), .DSREP(DSREP)) u_ring (
        .tclk(fclk), .t_v(1'b1), .t_d(ring_d), .rclk(clk),
        .r_align(align), .r_on(on), .r_align_v(ring_align_v), .r_on_v(ring_on_v),
        .r_d(ring_q), .r_v(rv), .r_lap_ok(lap_ok),
        .r_glo_ok(glo_ok), .r_ghi_ok(ghi_ok)
    );
`ifndef SYNTHESIS
    initial begin
        if (W < 1) $fatal(1, "clock landing requires a nonempty bundle");
        if (SETTLE < 8) $fatal(1, "clock landing SETTLE must cover synchronizer fill");
    end
`endif
endmodule

// Separate hierarchy gives the capture an independently declared face bank.
(* keep_hierarchy, keep *)
module ot_dp_landing_input_face #(parameter integer W = 1) (
    input wire clk,
    input wire [W-1:0] d,
    output reg [W-1:0] q
);
`ifdef OT_LEGACY_FREG_MUTANT_FALL
    always @(negedge clk) q <= d;
`elsif OT_LEGACY_FREG_MUTANT_BIT
    always @(posedge clk) q <= d ^ {{(W-1){1'b0}}, 1'b1};
`else
    always @(posedge clk) q <= d;
`endif
endmodule

(* keep_hierarchy, keep *)
module ot_dp_landing_fault_port (
    input wire clk, rst_n, d,
    output reg q
);
    always @(posedge clk) if (!rst_n) q <= 0; else q <= d;
endmodule

// Active-input-only reverse wavefront reduction. Source faults are sticky;
// their registered OR remains sticky until the raw wavefront reset. No child
// pin is synthesized for an absent branch.
(* keep_hierarchy, keep *)
module ot_dp_landing_collect #(parameter integer N=1) (
    input wire clk, rst_n,
    input wire [N-1:0] ready_i, fault_i,
    output reg ready_o, fault_o
);
    always @(posedge clk) begin
        if (!rst_n) begin ready_o <= 0; fault_o <= 0; end
        else begin ready_o <= &ready_i; fault_o <= |fault_i; end
    end
endmodule

// Face capture flop of one same-region (non-seam) status input pin (DIE-S81-29, COORD DIE-S81-28-PARK (2)): the
// partition pin loads ONLY this flop's D, with no reset term (an AND2 before D would break the face rule), and the
// reduction above reads q. The sender's dedicated output register runs on the same region clock. +1 status cycle
// (boot only, priced in the collector boot budget), 0 data cycles. The collector stage after it is synchronously reset.
(* keep_hierarchy, keep *)
module ot_dp_landing_face (
    input wire clk, d,
    output reg q
);
    always @(posedge clk) q <= d;
endmodule

// CLAND-QREG-1 ring output stage (rclk): kept so synthesis does not retime it back into the ring readout or merge it
// with the receiver boundary flop; the placer puts it between the ring and the face register.
(* keep_hierarchy, keep *)
module ot_meso_q_ff #(parameter integer W = 1) (
    input wire clk,
    input wire [W-1:0] d,
    (* keep *) output reg [W-1:0] q
);
`ifdef OT_MESO_MUTANT_QREG_BYPASS
    always @(*) q = d;                  // MUTANT: stage bypassed (declared cycle missing)
`else
    always @(posedge clk) q <= d;
`endif
endmodule
