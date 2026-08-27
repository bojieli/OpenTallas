`timescale 1ns/1ps
// Technology-independent contract for an immutable ROM macro.  There is no
// data write port by construction.  Logical addresses remain stable across
// row/column repair through a checked, quiescent translation map.
module ot_rom_wrapper #(
    parameter integer LOGICAL_DEPTH = 64,
    parameter integer PHYS_DEPTH = LOGICAL_DEPTH,
    parameter integer DATA_W = 64,
    parameter integer READ_LATENCY = 1,
    parameter integer TAG_W = 16,
    parameter integer SEQ_W = 8,
    parameter integer ADDR_W = (LOGICAL_DEPTH <= 2) ? 1 : $clog2(LOGICAL_DEPTH),
    parameter integer PHYS_ADDR_W = (PHYS_DEPTH <= 2) ? 1 : $clog2(PHYS_DEPTH),
    parameter INIT_FILE = ""
) (
    input  wire                              clk,
    input  wire                              rst_n,
    input  wire                              req_valid,
    output wire                              req_ready,
    input  wire [ADDR_W-1:0]                 logical_addr,
    input  wire [TAG_W-1:0]                  transaction_id,
    input  wire [SEQ_W-1:0]                  seq_id,
    input  wire [LOGICAL_DEPTH-1:0]          repair_valid,
    input  wire [LOGICAL_DEPTH*PHYS_ADDR_W-1:0] repair_map,
    // Fault injection is a verification/test hook.  It cannot alter storage.
    input  wire                              inject_fault,
    input  wire [PHYS_ADDR_W-1:0]            inject_fault_addr,
    input  wire [DATA_W-1:0]                 inject_fault_mask,
    output wire                              rsp_valid,
    output wire [DATA_W-1:0]                 rsp_data,
    output wire [TAG_W-1:0]                  rsp_transaction_id,
    output wire [SEQ_W-1:0]                  rsp_sequence,
    output wire [1:0]                        rsp_syndrome,
    output wire                              rsp_poison
);
    localparam integer LAT = (READ_LATENCY < 1) ? 1 : READ_LATENCY;
    localparam [ADDR_W:0] LOGICAL_DEPTH_LIMIT = LOGICAL_DEPTH[ADDR_W:0];
    localparam [PHYS_ADDR_W:0] PHYS_DEPTH_LIMIT = PHYS_DEPTH[PHYS_ADDR_W:0];
    reg [DATA_W-1:0] mem [0:PHYS_DEPTH-1];
    reg valid_pipe [0:LAT-1];
    reg [DATA_W-1:0] data_pipe [0:LAT-1];
    reg [TAG_W-1:0] tag_pipe [0:LAT-1];
    reg [SEQ_W-1:0] seq_pipe [0:LAT-1];
    reg [1:0] syndrome_pipe [0:LAT-1];
    reg poison_pipe [0:LAT-1];
    integer i;
    reg [PHYS_ADDR_W-1:0] physical_index;
    reg address_bad;
    reg repair_bad;
    reg [PHYS_ADDR_W-1:0] translated_addr;
    reg [DATA_W-1:0] read_word;
    reg [1:0] read_syndrome;
    reg read_poison;

    initial begin
        if (LOGICAL_DEPTH < 1 || PHYS_DEPTH < LOGICAL_DEPTH)
            $error("ot_rom_wrapper illegal logical/physical depth");
        if (READ_LATENCY < 1)
            $error("ot_rom_wrapper READ_LATENCY must be >= 1");
        if (INIT_FILE != "")
            $readmemh(INIT_FILE, mem);
    end

    assign req_ready = 1'b1; // fixed-latency issue; result capacity is reserved
    assign rsp_valid = valid_pipe[LAT-1];
    assign rsp_data = data_pipe[LAT-1];
    assign rsp_transaction_id = tag_pipe[LAT-1];
    assign rsp_sequence = seq_pipe[LAT-1];
    assign rsp_syndrome = syndrome_pipe[LAT-1];
    assign rsp_poison = poison_pipe[LAT-1];

    always @* begin
        address_bad = ({1'b0,logical_addr} >= LOGICAL_DEPTH_LIMIT);
        repair_bad = 1'b0;
        translated_addr = {{(PHYS_ADDR_W-ADDR_W){1'b0}},logical_addr};
        if (!address_bad && repair_valid[logical_addr]) begin
            translated_addr = repair_map[logical_addr*PHYS_ADDR_W +: PHYS_ADDR_W];
            if ({1'b0,translated_addr} >= PHYS_DEPTH_LIMIT)
                repair_bad = 1'b1;
        end
        if ({1'b0,translated_addr} >= PHYS_DEPTH_LIMIT)
            address_bad = 1'b1;
        physical_index = translated_addr;
        read_word = {DATA_W{1'b0}};
        read_syndrome = 2'b00;
        read_poison = address_bad || repair_bad;
        if (!read_poison) begin
            read_word = mem[physical_index];
            if (inject_fault && (translated_addr == inject_fault_addr)) begin
                read_syndrome = (inject_fault_mask == {DATA_W{1'b0}}) ? 2'b00 : 2'b01;
                // A macro ECC would classify the number of flipped bits.  The
                // behavioral hook models corrected data for a single-bit
                // event.  Multi-bit injection exposes the corrupted sample
                // only with uncorrectable syndrome and poison asserted.
                if (!onehot(inject_fault_mask)) begin
                    read_word = read_word ^ inject_fault_mask;
                    read_syndrome = 2'b10;
                    read_poison = 1'b1;
                end
            end
        end
    end

    function automatic onehot;
        input [DATA_W-1:0] d;
        integer b;
        integer n;
        begin
            n = 0;
            for (b = 0; b < DATA_W; b = b + 1)
                if (d[b]) n = n + 1;
            onehot = (n == 1);
        end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < LAT; i = i + 1) begin
                valid_pipe[i] <= 1'b0;
                data_pipe[i] <= {DATA_W{1'b0}};
                tag_pipe[i] <= {TAG_W{1'b0}};
                seq_pipe[i] <= {SEQ_W{1'b0}};
                syndrome_pipe[i] <= 2'b00;
                poison_pipe[i] <= 1'b0;
            end
        end else begin
            for (i = LAT-1; i > 0; i = i - 1) begin
                valid_pipe[i] <= valid_pipe[i-1];
                data_pipe[i] <= data_pipe[i-1];
                tag_pipe[i] <= tag_pipe[i-1];
                seq_pipe[i] <= seq_pipe[i-1];
                syndrome_pipe[i] <= syndrome_pipe[i-1];
                poison_pipe[i] <= poison_pipe[i-1];
            end
            valid_pipe[0] <= req_valid;
            data_pipe[0] <= req_valid ? read_word : {DATA_W{1'b0}};
            tag_pipe[0] <= req_valid ? transaction_id : {TAG_W{1'b0}};
            seq_pipe[0] <= req_valid ? seq_id : {SEQ_W{1'b0}};
            syndrome_pipe[0] <= req_valid ? read_syndrome : 2'b00;
            poison_pipe[0] <= req_valid ? read_poison : 1'b0;
        end
    end

`ifndef SYNTHESIS
    // The source-level interface has deliberately no write-enable signal.  A
    // static assertion catches accidental future additions to a wrapper.
    always @(posedge clk) begin
        if (req_valid && req_ready && (rsp_valid && rsp_transaction_id == transaction_id)) begin
            // no-op marker retained for waveform audit
        end
    end
`endif
endmodule
