`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Long-reach on-wafer "express" link for the ROM wafer's collective network.
//
// A purpose-built collective network does not need a router every 0.23 mm the
// way a fine-grained compute mesh does.  It runs a W-bit bus of pipelined,
// repeated global wires straight across a reticle field and puts one small
// stage at the field boundary.  This block is exactly one such span, built to
// be placed and routed on a long, thin floorplan so the wire really covers
// LINK_UM micrometres and the post-route timing measures what it costs:
//
//   in_* --> [launch reg] --> STAGES x [repeater reg] --> [boundary stage] --> out_*
//   (west die edge)          (one every SPACING_UM)       (east die edge)   local_* --^
//
// The repeaters themselves (buffers/inverters on the wire) are not in the RTL:
// the place-and-route flow inserts and sizes them.  The RTL fixes only where
// the registers are, so LINK_UM and SPACING_UM set the register count:
//
//   STAGES = ceil(LINK_UM / SPACING_UM) - 1 intermediate registers, giving
//   STAGES + 1 register-to-register segments of about SPACING_UM each.
//
// LINK_UM must match the floorplan the flow is given; the RTL cannot enforce it.
//
// Boundary stage (the field-edge node):
//   BOUNDARY_ADD = 0  a 2-input forwarding mux, one register: the through flit
//                     or the flit injected locally at this field (local_sel).
//                     No arithmetic.  Latency 1 cycle.
//   BOUNDARY_ADD = 1  the reduction node: each 32-bit lane of the through flit
//                     and of the local flit is added once, in a fixed order
//                     (through + local), by the project's pipelined binary32
//                     adder ot_fp32_add_rne_pipe (5 stages), bit-identical to
//                     ot_fp32_rne_pkg::fp32_add_rne.  local_sel then forwards
//                     the sum; otherwise the through flit, delayed to match, so
//                     one boundary has one latency.  Latency 6 cycles (5 adder
//                     stages and the registered output).  W must
//                     be a multiple of 32.  A nonfinite/overflow lane raises
//                     out_err (fail closed, never an infinity).
//
// There is no flow control: a collective network of this kind is scheduled
// (the controller knows every transfer), so the link is a pure pipeline.  The
// valid bit is the only control, and it is reset; data registers are not.
// ---------------------------------------------------------------------------
module ot_rom_express_link #(
    parameter integer W            = 64,
    parameter integer LINK_UM      = 2000,
    parameter integer SPACING_UM   = 2000,
    parameter integer BOUNDARY_ADD = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    // West edge: the flit entering the span.
    input  wire         in_valid,
    input  wire [W-1:0] in_data,
    // East edge: the field-boundary node's local port.
    input  wire         local_valid,
    input  wire         local_sel,
    input  wire [W-1:0] local_data,
    output reg          out_valid,
    output reg  [W-1:0] out_data,
    output reg          out_err
);
    localparam integer SEGMENTS = (LINK_UM + SPACING_UM - 1) / SPACING_UM;
    localparam integer STAGES   = (SEGMENTS > 0) ? SEGMENTS - 1 : 0;
    localparam integer LANES    = W / 32;

    initial begin
        if (SPACING_UM <= 0 || LINK_UM <= 0) $fatal(1, "LINK_UM and SPACING_UM must be positive");
        if (BOUNDARY_ADD != 0 && (W % 32) != 0) $fatal(1, "BOUNDARY_ADD needs W a multiple of 32");
    end

    // ---- launch register at the west edge ------------------------------------
    reg         launch_valid;
    reg [W-1:0] launch_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) launch_valid <= 1'b0;
        else        launch_valid <= in_valid;
    end
    always @(posedge clk) launch_data <= in_data;

    // ---- STAGES repeater registers along the span ----------------------------
    wire         span_valid;
    wire [W-1:0] span_data;
    generate
        if (STAGES == 0) begin : g_direct
            assign span_valid = launch_valid;
            assign span_data  = launch_data;
        end else begin : g_chain
            reg         v [0:STAGES-1];
            reg [W-1:0] d [0:STAGES-1];
            genvar s;
            for (s = 0; s < STAGES; s = s + 1) begin : g_stage
                wire         prev_v = (s == 0) ? launch_valid : v[(s == 0) ? 0 : s-1];
                wire [W-1:0] prev_d = (s == 0) ? launch_data  : d[(s == 0) ? 0 : s-1];
                always @(posedge clk or negedge rst_n) begin
                    if (!rst_n) v[s] <= 1'b0;
                    else        v[s] <= prev_v;
                end
                always @(posedge clk) d[s] <= prev_d;
            end
            assign span_valid = v[STAGES-1];
            assign span_data  = d[STAGES-1];
        end
    endgenerate

    // ---- boundary stage at the east edge -------------------------------------
    generate
        if (BOUNDARY_ADD == 0) begin : g_mux
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    out_valid <= 1'b0;
                    out_err   <= 1'b0;
                end else begin
                    out_valid <= local_sel ? local_valid : span_valid;
                    out_err   <= 1'b0;
                end
            end
            always @(posedge clk) out_data <= local_sel ? local_data : span_data;
        end else begin : g_add
            localparam integer ADD_LATENCY = 5;
            wire [W-1:0]       sum;
            wire [2*LANES-1:0] lane_err;
            wire [LANES-1:0]   lane_valid;
            wire               both = span_valid & local_valid;
            genvar l;
            for (l = 0; l < LANES; l = l + 1) begin : g_lane
                ot_fp32_add_rne_pipe u_add (
                    .clk       (clk),
                    .rst_n     (rst_n),
                    .valid_in  (both),
                    .a         (span_data[32*l +: 32]),
                    .b         (local_data[32*l +: 32]),
                    .y         (sum[32*l +: 32]),
                    .err       (lane_err[2*l +: 2]),
                    .valid_out (lane_valid[l])
                );
            end
            // Through path delayed to the adder's latency, with the select.
            reg         dv   [0:ADD_LATENCY-1];
            reg         dsel [0:ADD_LATENCY-1];
            reg [W-1:0] dd   [0:ADD_LATENCY-1];
            integer k;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    for (k = 0; k < ADD_LATENCY; k = k + 1) begin
                        dv[k]   <= 1'b0;
                        dsel[k] <= 1'b0;
                    end
                end else begin
                    dv[0]   <= local_sel ? both : span_valid;
                    dsel[0] <= local_sel;
                    for (k = 1; k < ADD_LATENCY; k = k + 1) begin
                        dv[k]   <= dv[k-1];
                        dsel[k] <= dsel[k-1];
                    end
                end
            end
            always @(posedge clk) begin
                dd[0] <= span_data;
                for (k = 1; k < ADD_LATENCY; k = k + 1) dd[k] <= dd[k-1];
            end
            // The adder's own output register is the boundary's last stage, so
            // the forward select is the one mux after it; the output port is
            // registered once more so the pin sees a register.
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    out_valid <= 1'b0;
                    out_err   <= 1'b0;
                end else begin
                    out_valid <= dv[ADD_LATENCY-1];
                    out_err   <= dsel[ADD_LATENCY-1] & (|lane_err);
                end
            end
            always @(posedge clk) out_data <= dsel[ADD_LATENCY-1] ? sum : dd[ADD_LATENCY-1];
        end
    endgenerate
endmodule
