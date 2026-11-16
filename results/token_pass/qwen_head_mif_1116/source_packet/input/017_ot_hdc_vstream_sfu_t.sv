`timescale 1ns/1ps
// el1013-qwen-stalls 2026-10-13: the special-function pipelines of one vector-stream lane as HARDENED TILES.
// The ML15 lane tile (ot_hdc_vstream_lane_t at QLA 4 / QLM 5) held 51,612 flops on one clock root; 32k of them are
// these three pipelines (exp 11.3k, reciprocal 8.1k, rsqrt 12.5k).  Each becomes a leaf with its own clock root
// (<= 15k sinks), its own reset register (async assert, registered deassert) and a flop at every pin: the operand
// and its valid are captured in pin flops, the result / valid / fault leave from out flops, so a tile is the inner
// pipeline + 2 edges and the lane cluster sees only flop -> pin -> wire -> pin -> flop seams.
// Defaults = the hardened configuration (a hard child carries no parameter overrides): LA 4, LM 5.
`ifndef OT_SU_LANE_HARD   // lane cluster build: these are hard children (LEF / LIB), not RTL
module ot_hdc_sfu_exp_t #(
    parameter integer LA = 4,
    parameter integer LM = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output reg         vo,
    output reg         fault
);
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    reg qv; reg [31:0] qx;
    always @(posedge clk or negedge rt) if (!rt) qv <= 1'b0; else qv <= v;
    always @(posedge clk) qx <= x;
    wire [31:0] ny; wire nvo, nf;
    ot_hdc_exp_q #(.LA(LA), .LM(LM)) u_exp (.clk(clk), .rst_n(rt), .v(qv), .x(qx), .y(ny), .vo(nvo), .fault(nf));
    always @(posedge clk or negedge rt) if (!rt) begin vo <= 1'b0; fault <= 1'b0; end else begin vo <= nvo; fault <= nf; end
`ifdef OT_SFU_EXP_MUT   // bench mutant: this tile's result with its LSB flipped (must FAIL)
    always @(posedge clk) y <= ny ^ 32'd1;
`else
    always @(posedge clk) y <= ny;
`endif
endmodule

module ot_hdc_sfu_rcp_t #(
    parameter integer LA = 4,
    parameter integer LM = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output reg         vo,
    output reg         fault
);
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    reg qv; reg [31:0] qx;
    always @(posedge clk or negedge rt) if (!rt) qv <= 1'b0; else qv <= v;
    always @(posedge clk) qx <= x;
    wire [31:0] ny; wire nvo, nf;
    ot_hdc_recip_q #(.LA(LA), .LM(LM)) u_rcp (.clk(clk), .rst_n(rt), .v(qv), .x(qx), .y(ny), .vo(nvo), .fault(nf));
    always @(posedge clk or negedge rt) if (!rt) begin vo <= 1'b0; fault <= 1'b0; end else begin vo <= nvo; fault <= nf; end
`ifdef OT_SFU_RCP_MUT   // bench mutant: this tile's result with its LSB flipped (must FAIL)
    always @(posedge clk) y <= ny ^ 32'd1;
`else
    always @(posedge clk) y <= ny;
`endif
endmodule

module ot_hdc_sfu_rsq_t #(
    parameter integer LA = 4,
    parameter integer LM = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output reg         vo,
    output reg         fault
);
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    reg qv; reg [31:0] qx;
    always @(posedge clk or negedge rt) if (!rt) qv <= 1'b0; else qv <= v;
    always @(posedge clk) qx <= x;
    wire [31:0] ny; wire nvo, nf;
    ot_hdc_rsqrt_q #(.LA(LA), .LM(LM)) u_rsq (.clk(clk), .rst_n(rt), .v(qv), .x(qx), .y(ny), .vo(nvo), .fault(nf));
    always @(posedge clk or negedge rt) if (!rt) begin vo <= 1'b0; fault <= 1'b0; end else begin vo <= nvo; fault <= nf; end
`ifdef OT_SFU_RSQ_MUT   // bench mutant: this tile's result with its LSB flipped (must FAIL)
    always @(posedge clk) y <= ny ^ 32'd1;
`else
    always @(posedge clk) y <= ny;
`endif
endmodule
`endif  // OT_SU_LANE_HARD
