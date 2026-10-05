`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Hierarchical MAC tile: LANES instances of ot_mac_lane plus a registered
// operand broadcast tree.
//
// Same arithmetic as the flattened version and the same reference, but built the
// way large arrays are actually built -- a hardened leaf replicated, not one
// enormous flat netlist. The flow's single `abc -D` pass over a flattened design
// degrades badly with size (926 MHz at 4 lanes, 74 MHz at 64), and module
// instances give the tool a boundary it can optimise within.
//
// The broadcast tree bounds fanout per driver to GROUP lanes regardless of tile
// width, which is how an SM distributes operands across its lanes.
// ---------------------------------------------------------------------------
module ot_mac_tile_h #(
    parameter integer LANES      = 16,
    parameter integer ACC_W      = 40,
    parameter integer EXP_WINDOW = 16,
    parameter integer GROUP      = 4
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    clear,
    input  wire                    valid_in,
    input  wire [15:0]             act,
    input  wire [16*LANES-1:0]     wgt,
    input  wire [7:0]              scale_exp,
    output wire [ACC_W*LANES-1:0]  result,
    output wire [LANES-1:0]        dropped_mask,
    output reg                     result_valid
);
    localparam integer GROUPS = (LANES + GROUP - 1) / GROUP;

    // the lane is instantiated without overrides, so its defaults must match
    initial begin
        if (ACC_W != 40 || EXP_WINDOW != 16) begin
            $display("ot_mac_tile_h: ACC_W/EXP_WINDOW must match ot_mac_lane defaults");
            $finish;
        end
    end

    // ---- broadcast stage: one registered replica per GROUP lanes -----------
    reg        b_sign  [0:GROUPS-1];
    reg [7:0]  b_exp   [0:GROUPS-1];
    reg [7:0]  b_man   [0:GROUPS-1];
    reg        b_zero  [0:GROUPS-1];
    reg [7:0]  b_scale [0:GROUPS-1];
    reg        b_accept[0:GROUPS-1];

    integer bg;
    always @(posedge clk or negedge rst_n)
        if (!rst_n)
            for (bg = 0; bg < GROUPS; bg = bg + 1) begin
                b_sign[bg] <= 1'b0; b_exp[bg] <= 8'b0; b_man[bg] <= 8'b0;
                b_zero[bg] <= 1'b0; b_scale[bg] <= 8'b0; b_accept[bg] <= 1'b0;
            end
        else
            for (bg = 0; bg < GROUPS; bg = bg + 1) begin
                b_sign[bg]   <= act[15];
                b_exp[bg]    <= act[14:7];
                b_man[bg]    <= {1'b1, act[6:0]};
                b_zero[bg]   <= (act[14:0] == 15'b0);
                b_scale[bg]  <= scale_exp;
                b_accept[bg] <= valid_in;
            end

    //: The lane's accumulate must fire the cycle AFTER its aligned term is
    //: valid.  valid_in -> broadcast register (1) -> lane stage 1 multiply (2)
    //: -> lane stage 2 align (3), so the gate is three registers deep.  Two was
    //: off by one and every lane accumulated a stale term -- caught by the
    //: campaign, which reported all 16 lanes wrong rather than a subtle drift.
    reg s1_v, s2_v, s3_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1_v <= 1'b0; s2_v <= 1'b0; s3_v <= 1'b0; end
        else begin s1_v <= valid_in; s2_v <= s1_v; s3_v <= s2_v; end

    genvar g;
    generate
        for (g = 0; g < LANES; g = g + 1) begin : lane
            localparam integer MYG = g / GROUP;
            reg [15:0] w_q;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) w_q <= 16'b0; else w_q <= wgt[16*g +: 16];

            wire [ACC_W-1:0] lane_result;
            wire             lane_dropped;

            //: No parameter override on the lane.  Yosys 0.68 aborts with
            //: "modules_.count(module->name) == 0" when a -chparam top also
            //: derives parameterised submodules, so the lane relies on its own
            //: defaults, which must match this tile's.  Asserted below.
            ot_mac_lane u_lane (
                .clk(clk), .rst_n(rst_n), .clear(clear),
                .accept(s3_v),
                .a_sign(b_sign[MYG]), .a_exp(b_exp[MYG]),
                .a_man(b_man[MYG]),   .a_zero(b_zero[MYG]),
                .b(w_q), .scale_exp(b_scale[MYG]),
                .result(lane_result), .dropped(lane_dropped)
            );

            assign result[ACC_W*g +: ACC_W] = lane_result;
            assign dropped_mask[g]          = lane_dropped;
        end
    endgenerate

    reg s4_v, s5_v, s6_v;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            s4_v <= 1'b0; s5_v <= 1'b0; s6_v <= 1'b0; result_valid <= 1'b0;
        end else begin
            s4_v <= s3_v; s5_v <= s4_v; s6_v <= s5_v; result_valid <= s6_v;
        end
endmodule
