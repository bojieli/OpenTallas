`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// LEAD2-S81/TOK2 (2026-10-19): ot_s81sl_cap_ld = static delay of ONE 70-bit CAP return lane before the capture tree.
// Why: the CAP-ED23 fullsix rerun (tok2-capd/fullsix_capd23) still faulted (0002 at 1801): the W tree carries FOUR frames
// (lanes 0..3 = L01 L02 L03 R01; R01 is W lane 3), so an E-only delay cannot separate them (exact packing: NONE for any D).
// Exact packing (cap_ed_calendar/root_pack_nosym.py, s_16_24.json): W lane 3 +16 and the E column +24 give a legal
// six-frame calendar (44 words, 1773..1820).  This leaf delays W lane 3 by D = 16 (ot_s81sl_cap #(.WL3DLY(16))).
// Structure: ot_hdc_delay_rf 70 x (D-2) register-file ring (pin in reg -> RF -> pin out reg; 980 b at D = 16 < 2 kb), the
// lane's valid bit (bit 0) masked until the line is primed (no stale word is ever valid).  Static: the compiler owns D.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cap_ld #(
    parameter integer D = 16
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [69:0] i_w,
    output wire [69:0] o_w
);
    wire [1:0] rsv;
    ot_rst_relay #(.REGIONS(2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    // S81-CORE-LAT-R20 10-27 (RAW face_guard 'unregistered' on the valid output): the valid bit leaves through its OWN
    // pin flop, masked BEFORE that flop instead of after the line's output register.  The valid bit runs a (D-1)-edge
    // register-file line, its output flop takes it AND the primed flag's next state -> o_v(t) = i_v(t-D) & primed(t),
    // edge for edge the old q[0] && primed (0 cycles).  The other bits keep the D-edge line.
    wire [69:0] q;
    ot_hdc_delay_rf #(.W(69), .D(D)) u_dl (.clk(clk), .rst_n(rsv[0]), .d(i_w[69:1]), .q(q[69:1]));
    wire v1;
    ot_hdc_delay_rf #(.W(1), .D(D - 1)) u_dv (.clk(clk), .rst_n(rsv[0]), .d(i_w[0]), .q(v1));
    localparam integer CW = $clog2(D + 2);
    reg [CW-1:0] cnt; reg primed;
    always @(posedge clk or negedge rsv[1])
        if (!rsv[1]) begin cnt <= {CW{1'b0}}; primed <= 1'b0; end
        else if (!primed) begin cnt <= cnt + 1'b1; primed <= (cnt == D[CW-1:0]); end
    wire primed_n = primed || (cnt == D[CW-1:0]);              // next state of primed (out of reset)
    reg o_v_q;
    always @(posedge clk or negedge rsv[1]) if (!rsv[1]) o_v_q <= 1'b0; else o_v_q <= v1 && primed_n;
    assign q[0] = 1'b0;                                         // unused (valid: o_v_q)
    assign o_w = {q[69:1], o_v_q};
endmodule
`default_nettype wire
