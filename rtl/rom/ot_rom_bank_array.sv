`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Dense behavioural ROM array behind the sense interface.
//
// THIS IS NOT A ROM MACRO AND IT IS NOT A DENSITY OR ENERGY MODEL.
//
// It exists so that ot_rom_read_service can be simulated and placed and routed
// against a concrete sense contract, and so that the absence of a write path is
// structural rather than asserted: this module has no write port, no write
// enable, no write data and no bidirectional pin.  ``rom_cell`` is what a foundry
// mask-ROM macro replaces, and every quantity a macro would establish -- bit
// cell area, wordline and bitline capacitance, sense-amplifier offset and
// margin, read energy, retention, defect rate -- is absent here.
//
// What it does model, because the service's behaviour depends on it:
//
//   * a wordline activation is a distinct event from a sense-granule read, and
//     ``act_count`` and ``sense_count`` are reported separately;
//   * the sensed row is held, so a second granule read of an open row does not
//     re-activate;
//   * a read takes SENSE_LATENCY cycles from acceptance to data, and an
//     activation costs ACTIVATE_LATENCY more;
//   * an address outside the built array is a defined miss (``rsp_absent``),
//     not an X and not stale data from the previously sensed row.
// ---------------------------------------------------------------------------
// Package items are referenced fully qualified; see ot_rom_read_service.
module ot_rom_bank_array #(
    parameter integer RESOURCES        = 4,
    parameter integer ROWS_PER_RESOURCE = 8,
    parameter integer SENSE_LATENCY    = 1,
    parameter integer ACTIVATE_LATENCY = 1
) (
    input  wire                      clk,
    input  wire                      rst_n,

    input  wire                      req_valid,
    output wire                      req_ready,
    input  wire [31:0]               req_resource,
    input  wire [31:0]               req_row,
    input  wire [7:0]                req_subword,
    input  wire                      req_activate,

    output reg                       rsp_valid,
    output reg  [ot_rom_pkg::ROM_SENSE_BITS-1:0] rsp_data,
    output reg                       rsp_absent,

    output reg  [63:0]               act_count,
    output reg  [63:0]               sense_count
);
    localparam integer CELLS = RESOURCES * ROWS_PER_RESOURCE
                             * ot_rom_pkg::ROM_SUBWORDS_PER_ROW;
    localparam integer LAT = (SENSE_LATENCY < 1) ? 1 : SENSE_LATENCY;

    // No write port exists for this array anywhere in this file.
    reg [ot_rom_pkg::ROM_SENSE_BITS-1:0] rom_cell [0:CELLS-1];

    reg [ot_rom_pkg::ROM_SENSE_BITS-1:0] pipe_data   [0:LAT-1];
    reg                      pipe_valid  [0:LAT-1];
    reg                      pipe_absent [0:LAT-1];

    reg [31:0] open_resource;
    reg [31:0] open_row;
    reg        open_valid;
    reg [7:0]  stall;

    wire in_range = (req_resource < RESOURCES)
                 && (req_row < ROWS_PER_RESOURCE)
                 && ({24'd0, req_subword} < ot_rom_pkg::ROM_SUBWORDS_PER_ROW);
    localparam integer CELL_IDX_W = (CELLS <= 2) ? 1 : $clog2(CELLS);
    wire [63:0] flat = (({32'd0, req_resource} * ROWS_PER_RESOURCE)
                        + {32'd0, req_row}) * ot_rom_pkg::ROM_SUBWORDS_PER_ROW
                       + {56'd0, req_subword};
    // The high bits cannot be reached: in_range bounds the request to the built
    // array before the index is used at all.
    wire _unused_flat = &{1'b0, flat[63:CELL_IDX_W], 1'b0};

    assign req_ready = (stall == 8'd0);

    integer i;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < LAT; i = i + 1) begin
                pipe_valid[i]  <= 1'b0;
                pipe_absent[i] <= 1'b0;
                pipe_data[i]   <= {ot_rom_pkg::ROM_SENSE_BITS{1'b0}};
            end
            open_valid    <= 1'b0;
            open_resource <= 32'd0;
            open_row      <= 32'd0;
            stall         <= 8'd0;
            act_count     <= 64'd0;
            sense_count   <= 64'd0;
            rsp_valid     <= 1'b0;
            rsp_data      <= {ot_rom_pkg::ROM_SENSE_BITS{1'b0}};
            rsp_absent    <= 1'b0;
        end else begin
            for (i = LAT-1; i > 0; i = i - 1) begin
                pipe_valid[i]  <= pipe_valid[i-1];
                pipe_absent[i] <= pipe_absent[i-1];
                pipe_data[i]   <= pipe_data[i-1];
            end
            pipe_valid[0]  <= 1'b0;
            pipe_absent[0] <= 1'b0;
            pipe_data[0]   <= {ot_rom_pkg::ROM_SENSE_BITS{1'b0}};

            if (stall != 8'd0) begin
                stall <= stall - 8'd1;
            end else if (req_valid) begin
                if (req_activate
                    || !open_valid
                    || (open_resource != req_resource)
                    || (open_row != req_row)) begin
                    act_count     <= act_count + 64'd1;
                    open_valid    <= 1'b1;
                    open_resource <= req_resource;
                    open_row      <= req_row;
                    stall         <= ACTIVATE_LATENCY[7:0];
                end
                sense_count    <= sense_count + 64'd1;
                pipe_valid[0]  <= 1'b1;
                pipe_absent[0] <= !in_range;
                pipe_data[0]   <= in_range ? rom_cell[flat[CELL_IDX_W-1:0]]
                                           : {ot_rom_pkg::ROM_SENSE_BITS{1'b0}};
            end

            rsp_valid  <= pipe_valid[LAT-1];
            rsp_data   <= pipe_data[LAT-1];
            rsp_absent <= pipe_absent[LAT-1];
        end
    end
endmodule
