`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// G2 descriptor store: the 64 KiB vehicle descriptor store as two ASAP7
// macros, arbitrated between two masters.
//
// docs/CHIP_ARCHITECTURE_DESIGN.md section 11.2, decision (a): "the 64 KiB
// descriptor store is two fakeram_2048x128".  The two parts are ganged in
// WIDTH into one 256-bit x 2,048-row array (65,536 B exactly).  An ABI 3.0
// descriptor record is 192 B = 1,536 b = SIX rows, so this store holds
// floor(2048 / 6) = 341 descriptors and a read is a six-beat burst.
//
// ADAPTER, AND WHAT IT COSTS.  rtl/abi3/ot_a3_device_top.sv models the
// descriptor store as a 1,536-bit-wide array with `desc_valid <= desc_req`:
// one cycle from request to record.  Against two 128-bit macros the same read
// takes about ten cycles.  As with the program store, that is a real change
// in control-plane cycles and no figure measured against the one-cycle model
// carries over.  A one-cycle 1,536-bit port would need twelve macros ganged
// in width (384 KiB, 132,090 um^2 of macro) for a 64 KiB store; the six-beat
// burst is the reason section 11.2 could price the store at two parts.
//
// TWO MASTERS.  The sequencer reads descriptors (its own reads and, in
// S_RESOLVE, the resolver bank's).  The array issue adapter reads the operand
// TENSOR_VIEW descriptors it needs to size an operation.  Both arrive here.
// This is the arrangement rtl/abi3/ot_a3_engine_issue_bridge.sv already
// assumes -- "The descriptor port is independent of the sequencer's
// descriptor port.  A real descriptor store may arbitrate those reads" -- and
// this store is that arbitration.  The sequencer wins every tie.  Neither
// master can lose a request: both are captured into a one-deep pending
// register on the request pulse, and each master has at most one read in
// flight by construction (each waits for its own valid before requesting
// again).  A second request arriving while one is already pending would be a
// protocol violation and is counted in dropped_requests rather than ignored.
//
// FAULT.  desc_id is relative to the transaction's descriptor base; the base
// and count live in ot_a3_device_top's configuration and are not repeated
// here, so this store enforces only its own bound: an id at or beyond 341
// returns desc_fault with a zero record, which is exactly the semantics of
// `desc_data = desc_fault ? 1536'd0 : dstore_rdata` in ot_a3_device_top.
//
// HOST LOAD.  One 128-bit write port: host_row selects the 256-bit row and
// host_lane selects which of the two macros in it.  Accepted only while the
// store is idle.
// ---------------------------------------------------------------------------
module ot_a3_g2_descriptor_store (
    input  wire          clk,
    input  wire          rst_n,

    // -- master A: the microsequencer (its own reads and the resolver bank's)
    input  wire          desc_req,
    input  wire [31:0]   desc_id,
    output reg           desc_valid,
    output reg           desc_fault,
    output wire [1535:0] desc_data,

    // -- master B: the array issue adapter -----------------------------
    input  wire          aux_req,
    input  wire [31:0]   aux_id,
    output reg           aux_valid,
    output reg           aux_fault,
    output wire [1535:0] aux_data,

    // -- host load port ------------------------------------------------
    input  wire          host_we,
    input  wire [10:0]   host_row,
    input  wire          host_lane,      // 0: bits [127:0]; 1: bits [255:128]
    input  wire [127:0]  host_wdata,
    output wire          host_accept,

    // -- observation ---------------------------------------------------
    output reg  [31:0]   read_count,
    output reg  [31:0]   fault_count,
    output reg  [31:0]   dropped_requests
);
    // Six 256-bit rows per 192-byte descriptor record; floor(2048 / 6) of
    // them fit in the two-macro array.
    localparam [31:0] DESCRIPTORS = 32'd341;

    localparam [1:0] S_IDLE  = 2'd0;
    localparam [1:0] S_READ  = 2'd1;
    localparam [1:0] S_RESP  = 2'd2;
    localparam [1:0] S_FAULT = 2'd3;

    reg  [1:0]  state;
    reg  [2:0]  beat;
    /* verilator lint_off UNUSEDSIGNAL */
    reg  [11:0] base;      // bit 11 cannot be reached: 340 * 6 + 5 = 2,045
    /* verilator lint_on UNUSEDSIGNAL */
    reg         cur_is_seq;

    reg         seq_pending;
    reg  [31:0] seq_id;
    reg         aux_pending;
    reg  [31:0] aux_id_q;

    reg  [255:0] word0, word1, word2, word3, word4, word5;

    reg          ram_ce;
    reg          ram_we0;
    reg          ram_we1;
    reg  [10:0]  ram_addr;
    reg  [127:0] ram_wdata;
    wire [127:0] ram_rdata0;
    wire [127:0] ram_rdata1;
    wire [255:0] ram_row = {ram_rdata1, ram_rdata0};

    wire [1535:0] record = {word5, word4, word3, word2, word1, word0};
    assign desc_data = desc_fault ? 1536'd0 : record;
    assign aux_data  = aux_fault  ? 1536'd0 : record;

    assign host_accept = host_we && (state == S_IDLE) &&
                         !seq_pending && !aux_pending &&
                         !desc_req && !aux_req;

    fakeram_2048x128 desc_ram0 (
        .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we0),
        .wd_in(ram_wdata), .rd_out(ram_rdata0)
    );
    fakeram_2048x128 desc_ram1 (
        .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we1),
        .wd_in(ram_wdata), .rd_out(ram_rdata1)
    );

    // base = id * 6, as two shifts and an add: no multiplier.
    wire [31:0] pick_id     = seq_pending ? seq_id : aux_id_q;
    wire [11:0] pick_base   = {pick_id[8:0], 3'b000} - {2'b00, pick_id[8:0], 1'b0};
    wire        pick_in_range = (pick_id < DESCRIPTORS);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state            <= S_IDLE;
            beat             <= 3'd0;
            base             <= 12'd0;
            cur_is_seq       <= 1'b0;
            seq_pending      <= 1'b0;
            seq_id           <= 32'd0;
            aux_pending      <= 1'b0;
            aux_id_q         <= 32'd0;
            word0 <= 256'd0; word1 <= 256'd0; word2 <= 256'd0;
            word3 <= 256'd0; word4 <= 256'd0; word5 <= 256'd0;
            desc_valid       <= 1'b0;
            desc_fault       <= 1'b0;
            aux_valid        <= 1'b0;
            aux_fault        <= 1'b0;
            ram_ce           <= 1'b0;
            ram_we0          <= 1'b0;
            ram_we1          <= 1'b0;
            ram_addr         <= 11'd0;
            ram_wdata        <= 128'd0;
            read_count       <= 32'd0;
            fault_count      <= 32'd0;
            dropped_requests <= 32'd0;
        end else begin
            desc_valid <= 1'b0;
            aux_valid  <= 1'b0;
            ram_ce     <= 1'b0;
            ram_we0    <= 1'b0;
            ram_we1    <= 1'b0;

            // -- capture the request pulses --------------------------------
            if (desc_req) begin
                if (seq_pending)
                    dropped_requests <= dropped_requests + 32'd1;
                seq_pending <= 1'b1;
                seq_id      <= desc_id;
            end
            if (aux_req) begin
                if (aux_pending)
                    dropped_requests <= dropped_requests + 32'd1;
                aux_pending <= 1'b1;
                aux_id_q    <= aux_id;
            end

            case (state)
                S_IDLE: begin
                    if (seq_pending || aux_pending) begin
                        cur_is_seq <= seq_pending;
                        if (seq_pending) seq_pending <= 1'b0;
                        else             aux_pending <= 1'b0;
                        base <= pick_base;
                        beat <= 3'd0;
                        if (pick_in_range) begin
                            ram_ce   <= 1'b1;
                            ram_addr <= pick_base[10:0];
                            state    <= S_READ;
                        end else begin
                            state <= S_FAULT;
                        end
                    end else if (host_accept) begin
                        ram_ce    <= 1'b1;
                        ram_we0   <= !host_lane;
                        ram_we1   <=  host_lane;
                        ram_addr  <= host_row;
                        ram_wdata <= host_wdata;
                    end
                end

                // Beat b's address is presented in cycle b and its data is
                // valid in cycle b + 1, so the last address goes out at
                // beat 4 and the last word lands at beat 6.
                S_READ: begin
                    if (beat <= 3'd4) begin
                        ram_ce   <= 1'b1;
                        ram_addr <= base[10:0] + {8'd0, beat} + 11'd1;
                    end
                    case (beat)
                        3'd1: word0 <= ram_row;
                        3'd2: word1 <= ram_row;
                        3'd3: word2 <= ram_row;
                        3'd4: word3 <= ram_row;
                        3'd5: word4 <= ram_row;
                        3'd6: word5 <= ram_row;
                        default: ;
                    endcase
                    if (beat == 3'd6) begin
                        state <= S_RESP;
                    end else begin
                        beat <= beat + 3'd1;
                    end
                end

                S_RESP: begin
                    read_count <= read_count + 32'd1;
                    if (cur_is_seq) begin
                        desc_fault <= 1'b0;
                        desc_valid <= 1'b1;
                    end else begin
                        aux_fault <= 1'b0;
                        aux_valid <= 1'b1;
                    end
                    state <= S_IDLE;
                end

                S_FAULT: begin
                    fault_count <= fault_count + 32'd1;
                    if (cur_is_seq) begin
                        desc_fault <= 1'b1;
                        desc_valid <= 1'b1;
                    end else begin
                        aux_fault <= 1'b1;
                        aux_valid <= 1'b1;
                    end
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
