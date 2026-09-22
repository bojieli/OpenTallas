`timescale 1ns/1ps
// Own an operation until compute stops, transport acknowledges cancellation/
// drain, and all accepted writes complete. Completion is held under backpressure.
// transport_ack is a handshake valid ONLY in response to transport_cancel;
// it promises no future response from this generation. writes_drained must
// include all accepted output writes. Parents reset this controller together
// with transport on global reset. An abort does not roll back committed writes.
module ot_a3_runtime_operation_lifetime(
    input wire clk,rst_n,
    input wire start,
    output wire start_ready,
    input wire [31:0] command_generation,
    input wire compute_done,
    input wire [7:0] compute_error,
    input wire service_fault,abort_valid,
    input wire transport_ack,writes_drained,
    output wire transport_cancel,
    output wire [31:0] transport_generation,
    output wire service_clear,compute_abort,
    output wire busy,
    output wire completion_valid,
    input wire completion_ready,
    output wire [31:0] completion_generation,
    output reg [7:0] completion_error
);
    localparam [2:0] IDLE=0,RUN=1,DRAIN=2,COMPLETE=3;
    localparam [7:0] SERVICE_ERROR=8'hfe,ABORT_ERROR=8'hff;
    reg [2:0] state;
    reg [31:0] generation;
    reg transport_finished,aborted;
    assign start_ready=rst_n && state==IDLE;
    assign busy=rst_n && state!=IDLE;
    assign completion_valid=rst_n && state==COMPLETE;
    assign transport_cancel=rst_n && state==DRAIN && !transport_finished;
    assign transport_generation=generation;
    assign completion_generation=generation;
    assign service_clear=rst_n && (state==DRAIN || state==COMPLETE);
    assign compute_abort=rst_n && aborted && state!=IDLE;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            state<=IDLE;generation<=0;completion_error<=0;transport_finished<=0;aborted<=0;
        end else case(state)
            IDLE:if(start)begin
                generation<=command_generation;completion_error<=0;
                transport_finished<=0;aborted<=0;state<=RUN;
            end
            RUN:if(service_fault || abort_valid || compute_done)begin
                completion_error<=service_fault?SERVICE_ERROR:abort_valid?ABORT_ERROR:compute_error;
                aborted<=service_fault || abort_valid;
                state<=DRAIN;
            end
            DRAIN:begin
                if(transport_cancel && transport_ack)transport_finished<=1;
                if((transport_finished || (transport_cancel && transport_ack)) && writes_drained)state<=COMPLETE;
            end
            COMPLETE:if(completion_ready)state<=IDLE;
            default:state<=IDLE;
        endcase
    end
endmodule
