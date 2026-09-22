`timescale 1ns/1ps
// Reserve storage before issuing arithmetic that can produce an output beat.
// used = queued beats + outstanding result reservations. Producer latency may
// vary and a stopped/faulted producer may abandon reservations. stop_producer
// releases only those unused reservations; already queued writes always drain.
// The ready path depends only on local occupancy, never downstream ready.
module ot_a3_reserved_output_queue #(
    parameter integer WIDTH=776,
    parameter integer DEPTH=4
)(
    input wire clk,rst_n,
    input wire reserve_valid,
    output wire reserve_ready,
    input wire stop_producer,
    input wire push_valid,
    input wire [WIDTH-1:0] push_data,
    output wire out_valid,
    input wire out_ready,
    output wire [WIDTH-1:0] out_data,
    output wire empty,
    output reg protocol_error
);
    localparam integer PW=(DEPTH>1)?$clog2(DEPTH):1;
    localparam integer CW=$clog2(DEPTH+1);
    localparam [PW-1:0] LAST=PW'(DEPTH-1);
    localparam [CW-1:0] CAPACITY=CW'(DEPTH);
    reg [WIDTH-1:0] data[0:DEPTH-1];
    reg [PW-1:0] rd_ptr,wr_ptr;
    reg [CW-1:0] count,used;
    wire reserve=reserve_valid && reserve_ready;
    wire pop=out_valid && out_ready;
    wire room=(count<CAPACITY);
    wire reservation=(used>count) || reserve;
    wire push=push_valid && room && reservation && !protocol_error;
    assign reserve_ready=rst_n && !stop_producer && !protocol_error && used<CAPACITY;
    assign out_valid=rst_n && count!=0;
    assign out_data=data[rd_ptr];
    assign empty=count==0;
    function automatic [PW-1:0] advance(input [PW-1:0] ptr);
        advance=(ptr==LAST)?{PW{1'b0}}:ptr+1'b1;
    endfunction
    generate if(DEPTH<1)begin : invalid_depth
        initial $error("output queue DEPTH must be positive");
    end endgenerate
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            rd_ptr<=0;wr_ptr<=0;count<=0;used<=0;protocol_error<=0;
        end else begin
            if(push_valid && (!room || !reservation))protocol_error<=1;
            if(push)begin data[wr_ptr]<=push_data;wr_ptr<=advance(wr_ptr);end
            if(pop)rd_ptr<=advance(rd_ptr);
            case({push,pop})
                2'b10:count<=count+1'b1;
                2'b01:count<=count-1'b1;
                default:;
            endcase
            if(stop_producer)begin
                // Producer promises no later result from abandoned work.
                // A final beat on this edge still belongs to the queue.
                used<=count+CW'(push)-CW'(pop);
            end else case({reserve,pop})
                2'b10:used<=used+1'b1;
                2'b01:used<=used-1'b1;
                default:;
            endcase
        end
    end
endmodule
