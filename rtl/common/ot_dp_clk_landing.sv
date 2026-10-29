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
    parameter integer SETTLE = 16
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
    wire align = rst_n && !on && (count == CW'(SETTLE));
    wire rv, lap_ok, glo_ok, ghi_ok;
    wire [RW-1:0] ring_d = {{(RW-W){1'b0}}, d};
    wire [RW-1:0] ring_q;
    assign q = ring_q[W-1:0];
    reg [2:0] arm;
    reg fault_state;
    wire trip = arm[2] && (!rv || !lap_ok || !glo_ok || !ghi_ok);
    wire fault_next = fault_state || trip;
    // A private output flop drives ONLY the observed fault pin. The sticky
    // state also controls readiness, so exporting that state directly would
    // violate the dedicated registered-pin rule.
    ot_dp_landing_fault_port u_fault_port (.clk(clk), .rst_n(rst_n), .d(fault_next), .q(fault));
    // The ring write pointer is deliberately free-running across local resets.
    // SETTLE lets Gray/half-edge samples fill before placing the read pointer.
    always @(posedge clk) begin
        if (!rst_n) begin
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
                   .GUARD_HI(4), .RDREG(1)) u_ring (
        .tclk(fclk), .t_v(1'b1), .t_d(ring_d), .rclk(clk),
        .r_align(align), .r_on(on), .r_align_v({NC{align}}), .r_on_v({NC{on}}),
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
