// One native implementation for parameterized forwarded register-slice views.
// Existing die sizing reserves four captures per station (hbm_accel_die_fp.py
// stn_size). Every capture uses the real kept forwarding inverter. This wrapper
// does not claim that clustering the captures validates a 1722.24um route.
// No ready: the source MUST reserve destination capacity before issuing. The
// existing payload includes any upstream protection; this block neither adds
// protection nor claims that unprotected control can be adopted. Invalid data
// is unspecified, as in the source leaf; valid-qualified output is registered.
(* keep_hierarchy *)
module ot_hbm_native_register_slice #(
    parameter integer W = 512,
    parameter integer STAGES = 4,
    parameter bit ENABLE = 0,
    parameter integer SPAN_NM = 430560
) (
    input wire fclk_i,
    // Each reset is synchronous to its own forwarded stage clock. A parent
    // must supply the actual reset crossing/holding implementation.
    input wire [STAGES-1:0] rst_n,
    input wire i_v,
    input wire [W-1:0] i_d,
    output wire fclk_o,
    output wire o_v,
    output wire [W-1:0] o_d
);
    initial begin
        if (W < 1 || STAGES < 1) $error("invalid native register slice size");
    end
    wire [STAGES:0] clk_chain, valid_chain;
    wire [W-1:0] data_chain [0:STAGES];
    assign clk_chain[0] = fclk_i;
    assign valid_chain[0] = i_v;
    assign data_chain[0] = i_d;
    for (genvar s = 0; s < STAGES; s = s+1) begin : g_stage
        (* keep_hierarchy *) ot_fwd_link_stage #(
            .W(W), .ENABLE(ENABLE), .SPAN_NM(SPAN_NM)
        ) u_stage (
            .fclk_i(clk_chain[s]), .rst_n(rst_n[s]),
            .i_v(valid_chain[s]), .i_d(data_chain[s]),
            .fclk_o(clk_chain[s+1]), .o_v(valid_chain[s+1]),
            .o_d(data_chain[s+1])
        );
    end
    assign fclk_o = clk_chain[STAGES];
    assign o_v = valid_chain[STAGES];
    assign o_d = data_chain[STAGES];
endmodule
