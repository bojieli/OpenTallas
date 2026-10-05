`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 runtime symbol file (docs/CHIP_ARCHITECTURE_DESIGN.md section 3.3).
//
// Sixteen 64-bit entries with bound bits, written per node by the management
// processor through the host load path and read combinationally by every
// consumer in the front end: the predicate unit, the loop stack at
// LOOP_SETUP, the compatibility state controller (SPAN_TOKENS) and the six
// view-resolver lanes.  A29 values are u64 (runtime/abi3/records.py); the
// 32-bit file the verification tops used to present is widened here, and the
// bound bit -- "this request bound symbol i" -- is part of the write rather
// than a separate mask, which is what 3.3's "bound bits" means.
//
// The file is written only while no transaction runs (the device top gates
// the write on host_ready) and is never cleared by a transaction: a request
// binds its symbols before start and they persist for the whole transaction,
// exactly as runtime/sim/device.Device.run_transaction copies them once.
//
// Read side.  The whole file is presented flat (values and bound bits) and
// each consumer selects its own entry; nine 16:1 muxes of 65 bits are a small
// price for a file that never has to arbitrate.  A read of an index outside
// the registry is impossible: the index is four bits.
//
// The package is referenced by scope, never wildcard-imported [OI-43].
// ---------------------------------------------------------------------------
module ot_a3_symbol_file (
    input  wire          clk,
    input  wire          rst_n,

    // host write: lane 0 = value[31:0], 1 = value[63:32], 2 = bound bit
    input  wire          host_we,
    input  wire [3:0]    host_index,
    input  wire [1:0]    host_lane,
    input  wire [31:0]   host_wdata,

    output wire [ot_a3_pkg::A3_SYMBOL_COUNT*64-1:0] file_values,
    output wire [ot_a3_pkg::A3_SYMBOL_COUNT-1:0]    file_bound
);
    localparam integer COUNT = ot_a3_pkg::A3_SYMBOL_COUNT;

    reg [63:0] value [0:COUNT-1];
    reg [COUNT-1:0] bound;

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < COUNT; i = i + 1)
                value[i] <= 64'd0;
            bound <= {COUNT{1'b0}};
        end else if (host_we) begin
            case (host_lane)
                2'd0: value[host_index][31:0]  <= host_wdata;
                2'd1: value[host_index][63:32] <= host_wdata;
                2'd2: bound[host_index]        <= host_wdata[0];
                default: ;
            endcase
        end
    end

    genvar g;
    generate
        for (g = 0; g < COUNT; g = g + 1) begin : g_flat
            assign file_values[g*64 +: 64] = value[g];
        end
    endgenerate
    assign file_bound = bound;
endmodule
