`timescale 1ns/1ps
// Route-record checker and two-entry tagged route-context FIFO.  The decoder
// intentionally keeps the first occurrence of a legal expert ID and reports
// duplicate slots separately; downstream logic therefore sees deterministic
// wordline enables even when a router emits duplicate top-k IDs.
module ot_route_mask #(
    parameter integer NUM_EXPERTS = 16,
    parameter integer TOP_K = 6,
    parameter integer EXPERT_ID_W = 10,
    parameter integer FIFO_DEPTH = 2,
    parameter integer CHECK_CRC = 1
) (
    input  wire                                  clk,
    input  wire                                  rst_n,
    input  wire                                  route_valid,
    output wire                                  route_ready,
    input  wire [223:0]                          route_record,
    output wire                                  ctx_valid,
    input  wire                                  ctx_ready,
    output wire [NUM_EXPERTS-1:0]                ctx_mask,
    output wire [15:0]                           ctx_transaction_id,
    output wire [7:0]                            ctx_epoch_id,
    output wire [6:0]                            ctx_layer_id,
    output wire [4:0]                            ctx_top_k_count,
    output wire                                  ctx_poison,
    output wire [15:0]                           ctx_duplicate_slots,
    output reg                                   bad_crc_seen,
    output reg                                   bad_field_seen
);
    localparam integer CNT_W = (FIFO_DEPTH < 2) ? 1 : $clog2(FIFO_DEPTH+1);
    reg [NUM_EXPERTS-1:0] mask_mem [0:FIFO_DEPTH-1];
    reg [15:0] txn_mem [0:FIFO_DEPTH-1];
    reg [7:0] epoch_mem [0:FIFO_DEPTH-1];
    reg [6:0] layer_mem [0:FIFO_DEPTH-1];
    reg [4:0] topk_mem [0:FIFO_DEPTH-1];
    reg poison_mem [0:FIFO_DEPTH-1];
    reg [15:0] dup_mem [0:FIFO_DEPTH-1];
    reg [CNT_W-1:0] count;
    integer wr_ptr;
    integer rd_ptr;
    integer slot;
    integer selected;
    reg [NUM_EXPERTS-1:0] decoded_mask;
    reg [15:0] decoded_dup;
    reg decoded_poison;
    reg crc_bad;
    reg field_bad;
    reg [15:0] supplied_crc;
    reg [15:0] calculated_crc;
    reg [4:0] route_topk;
    reg [9:0] route_id;
    wire push = route_valid && route_ready;
    wire pop = ctx_valid && ctx_ready;

    // Package function takes a wide argument for compatibility with the
    // installed open simulators; only the low 208 bits are covered here.
    always @* begin
        decoded_mask = {NUM_EXPERTS{1'b0}};
        decoded_dup = 16'b0;
        decoded_poison = 1'b0;
        field_bad = 1'b0;
        route_topk = route_record[191 +: 5];
        supplied_crc = route_record[208 +: 16];
        calculated_crc = 16'b0;
        // A local implementation avoids package-width casts in synthesis
        // frontends that do not support unsized function arguments.
        calculated_crc = crc16_record(route_record[207:0]);
        if (CHECK_CRC && (supplied_crc != calculated_crc)) begin
            crc_bad = 1'b1;
            decoded_poison = 1'b1;
        end else begin
            crc_bad = 1'b0;
        end
        if (route_record[207:200] != 8'b0) begin
            field_bad = 1'b1;
            decoded_poison = 1'b1;
        end
        if ((route_topk == 0) || (route_topk > TOP_K) ||
            (route_topk > 16) || (TOP_K > NUM_EXPERTS)) begin
            field_bad = 1'b1;
            decoded_poison = 1'b1;
        end
        for (slot = 0; slot < 16; slot = slot + 1) begin
            route_id = route_record[slot*EXPERT_ID_W +: EXPERT_ID_W];
            selected = route_id;
            if (slot < route_topk) begin
                if (selected >= NUM_EXPERTS) begin
                    field_bad = 1'b1;
                    decoded_poison = 1'b1;
                end else if (decoded_mask[selected]) begin
                    decoded_dup[slot] = 1'b1;
                end else begin
                    decoded_mask[selected] = 1'b1;
                end
            end
        end
    end

    function automatic [15:0] crc16_record;
        input [207:0] d;
        integer byte_i;
        integer bit_i;
        reg [15:0] c;
        reg fb;
        begin
            c = 16'hffff;
            for (byte_i = 0; byte_i < 26; byte_i = byte_i + 1) begin
                for (bit_i = 7; bit_i >= 0; bit_i = bit_i - 1) begin
                    fb = c[15] ^ d[byte_i*8 + bit_i];
                    c = {c[14:0],1'b0};
                    if (fb)
                        c = c ^ 16'h1021;
                end
            end
            crc16_record = c;
        end
    endfunction

    assign route_ready = (count < FIFO_DEPTH);
    assign ctx_valid = (count != 0);
    assign ctx_mask = mask_mem[rd_ptr];
    assign ctx_transaction_id = txn_mem[rd_ptr];
    assign ctx_epoch_id = epoch_mem[rd_ptr];
    assign ctx_layer_id = layer_mem[rd_ptr];
    assign ctx_top_k_count = topk_mem[rd_ptr];
    assign ctx_poison = poison_mem[rd_ptr];
    assign ctx_duplicate_slots = dup_mem[rd_ptr];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= {CNT_W{1'b0}};
            wr_ptr <= 0;
            rd_ptr <= 0;
            bad_crc_seen <= 1'b0;
            bad_field_seen <= 1'b0;
        end else begin
            if (push) begin
                mask_mem[wr_ptr] <= decoded_mask;
                txn_mem[wr_ptr] <= route_record[160 +: 16];
                epoch_mem[wr_ptr] <= route_record[176 +: 8];
                layer_mem[wr_ptr] <= route_record[184 +: 7];
                topk_mem[wr_ptr] <= route_topk;
                poison_mem[wr_ptr] <= decoded_poison;
                dup_mem[wr_ptr] <= decoded_dup;
                if (crc_bad)
                    bad_crc_seen <= 1'b1;
                if (field_bad)
                    bad_field_seen <= 1'b1;
                if (wr_ptr == FIFO_DEPTH-1)
                    wr_ptr <= 0;
                else
                    wr_ptr <= wr_ptr + 1;
            end
            if (pop) begin
                if (rd_ptr == FIFO_DEPTH-1)
                    rd_ptr <= 0;
                else
                    rd_ptr <= rd_ptr + 1;
            end
            case ({push,pop})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: count <= count;
            endcase
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (NUM_EXPERTS < 1 || NUM_EXPERTS > 1024)
            $error("ot_route_mask NUM_EXPERTS outside architectural limit");
        if (TOP_K < 1 || TOP_K > 16 || TOP_K > NUM_EXPERTS)
            $error("ot_route_mask TOP_K illegal");
        if (FIFO_DEPTH < 2)
            $error("ot_route_mask FIFO_DEPTH must be at least two");
    end
`endif
endmodule
