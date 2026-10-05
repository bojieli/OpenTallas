`timescale 1ns/1ps
// Source-bound transport proposal only; no arithmetic, backpressure or new clockgate.
// Primitive mapping must restore the inverted DFFHQN output, as priced in84b.
module ot_topk_fixed_packet_delay_prepare #(
    parameter integer WIDTH=1, EDGES=1,
    parameter [WIDTH-1:0] MASK={WIDTH{1'b0}}
) (
    input wire clk, rst_n,
    input wire [WIDTH-1:0] in_packet,
    output wire [WIDTH-1:0] out_packet
);
    reg [WIDTH-1:0] payload [0:EDGES-1];
    reg [EDGES-1:0] present;
    integer i;
    // No payload reset mux. ASR present bits fence all pre-reset payload.
    always @(posedge clk) begin
        payload[0] <= in_packet;
        for(i=1;i<EDGES;i=i+1) payload[i] <= payload[i-1];
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) present <= {EDGES{1'b0}};
        else present <= {present[EDGES-1:0]} << 1 | {{(EDGES-1){1'b0}},1'b1};
    end
    // Only valid/go/error/done/write-enable control bits are fenced. Addresses
    // and data retain reset-free payload FFs and are ignored without a strobe.
    wire permitted = rst_n && present[EDGES-1];
    genvar b;
    generate for(b=0;b<WIDTH;b=b+1) begin : g_control_fence
        if(MASK[b]) assign out_packet[b] = permitted && payload[EDGES-1][b];
        else assign out_packet[b] = payload[EDGES-1][b];
    end endgenerate
endmodule
