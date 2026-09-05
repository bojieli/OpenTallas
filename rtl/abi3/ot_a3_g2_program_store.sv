`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// G2 program store: the 4 KiB vehicle program store as one ASAP7 macro.
//
// docs/CHIP_ARCHITECTURE_DESIGN.md section 11.2, decision (a): "the 4 KiB
// program store is one fakeram_256x128".  That part is 256 words of 128 bits.
// The microsequencer's instruction port is 256 bits wide (one 32-byte ABI 3.0
// instruction record per fetch), so ONE macro word is HALF an instruction and
// a fetch is two macro reads.  4 KiB therefore holds 128 instructions at
// addresses {index[6:0], beat}.
//
// ADAPTER, AND WHAT IT COSTS.  rtl/abi3/ot_a3_device_top.sv models the
// program store as a 256-bit-wide array with `imem_valid <= imem_req`: one
// cycle from request to record.  Against one 128-bit macro the same fetch
// takes four cycles (request captured, two macro reads pipelined, the record
// registered).  That is a real change in the front end's cycles per
// instruction and it must not be hidden: no cycle figure measured against
// the one-cycle model in ot_a3_device_top carries over to a cluster built on
// this store.  The alternative -- two fakeram_256x128 ganged in width, 8 KiB,
// one-cycle fetch -- costs one more macro and departs from the capacity
// decision recorded in section 11.2, so it is not taken here; it is the
// change to make if a later campaign needs the front end's original fetch
// cadence.
//
// The protocol this store is safe against.  ot_a3_microsequencer drives
// imem_req as a ONE-CYCLE PULSE (the default `imem_req <= 1'b0` at the head
// of its sequential block) and then waits in S_FETCH_WAIT for imem_valid, so
// a multi-cycle response is accepted; the request is latched here on the
// pulse and cannot be lost.  The sequencer never has two fetches in flight.
//
// Range.  imem_index is program_base + pc, bounded upstream by
// cfg_instruction_count; a request past the 128 instructions this store holds
// is answered from the wrapped address and counted in out_of_range_count
// rather than silently ignored, because the store has no fault line back to
// the sequencer (ot_a3_device_top has none either).
//
// Host load.  One 128-bit write port, accepted only when no fetch is in
// flight; host_accept is the acknowledgement and a write offered while busy
// is refused, not queued.
// ---------------------------------------------------------------------------
module ot_a3_g2_program_store (
    input  wire         clk,
    input  wire         rst_n,

    // -- microsequencer instruction port -------------------------------
    input  wire         imem_req,
    input  wire [31:0]  imem_index,
    output reg          imem_valid,
    output reg  [255:0] imem_data,

    // -- host load port (one macro word per write) ---------------------
    input  wire         host_we,
    input  wire [7:0]   host_row,
    input  wire [127:0] host_wdata,
    output wire         host_accept,

    // -- observation ---------------------------------------------------
    output reg  [31:0]  out_of_range_count,
    output reg  [31:0]  fetch_count
);
    localparam [1:0] S_IDLE = 2'd0;
    localparam [1:0] S_A    = 2'd1;
    localparam [1:0] S_B    = 2'd2;
    localparam [1:0] S_C    = 2'd3;

    reg  [1:0]   state;
    reg  [6:0]   index_r;
    reg  [127:0] low_word;

    reg          ram_ce;
    reg          ram_we;
    reg  [7:0]   ram_addr;
    reg  [127:0] ram_wdata;
    wire [127:0] ram_rdata;

    // The store is free for a host write only while no fetch is in flight
    // and no fetch is starting this cycle.
    assign host_accept = host_we && (state == S_IDLE) && !imem_req;

    fakeram_256x128 prog_ram (
        .clk(clk),
        .addr_in(ram_addr),
        .ce_in(ram_ce),
        .we_in(ram_we),
        .wd_in(ram_wdata),
        .rd_out(ram_rdata)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state              <= S_IDLE;
            index_r            <= 7'd0;
            low_word           <= 128'd0;
            imem_valid         <= 1'b0;
            imem_data          <= 256'd0;
            ram_ce             <= 1'b0;
            ram_we             <= 1'b0;
            ram_addr           <= 8'd0;
            ram_wdata          <= 128'd0;
            out_of_range_count <= 32'd0;
            fetch_count        <= 32'd0;
        end else begin
            imem_valid <= 1'b0;
            ram_ce     <= 1'b0;
            ram_we     <= 1'b0;

            case (state)
                S_IDLE: begin
                    if (imem_req) begin
                        if (imem_index[31:7] != 25'd0)
                            out_of_range_count <= out_of_range_count + 32'd1;
                        fetch_count <= fetch_count + 32'd1;
                        index_r     <= imem_index[6:0];
                        ram_ce      <= 1'b1;
                        ram_we      <= 1'b0;
                        ram_addr    <= {imem_index[6:0], 1'b0};
                        state       <= S_A;
                    end else if (host_accept) begin
                        ram_ce    <= 1'b1;
                        ram_we    <= 1'b1;
                        ram_addr  <= host_row;
                        ram_wdata <= host_wdata;
                    end
                end
                S_A: begin
                    // The low half is being read now; present the high half.
                    ram_ce   <= 1'b1;
                    ram_we   <= 1'b0;
                    ram_addr <= {index_r, 1'b1};
                    state    <= S_B;
                end
                S_B: begin
                    low_word <= ram_rdata;   // low half valid this cycle
                    state    <= S_C;
                end
                S_C: begin
                    imem_data  <= {ram_rdata, low_word};   // high half valid now
                    imem_valid <= 1'b1;
                    state      <= S_IDLE;
                end
                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
