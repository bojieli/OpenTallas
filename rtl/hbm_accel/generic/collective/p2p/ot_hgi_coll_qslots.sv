`timescale 1ns/1ps
`default_nettype none
// Compiler-reserved quadrant transport successor (HANDOFF 0an).
// Sources: SU[INJ], rail[NPT], VM[DEL], ring-result[1].
// Sinks: rail[NPT], SU[DEL], RGX[DEL], TKM[DEL], TKW[1], ring-partial[1].
// A source sampled at edge C is available to a sink instruction at C+1;
// that instruction produces its registered pin output immediately after C+1.
// Each instruction is consumed at its edge even on a schedule fault. Nothing
// stalls, retries, grants, queues or changes issue timing according to data.
// Separate input/output roots each remain below 15k sinks at production shape.
// The compiler/controller supplying the cycle words is a separate real block;
// this transport is not a replacement for TOPK/reduction arithmetic.
module ot_hgi_coll_qslots #(
    parameter integer NPT=3, INJ=2, DEL=4, PWT=545,
    parameter integer NS=INJ+NPT+DEL+1,
    parameter integer ND=NPT+3*DEL+2,
    parameter integer SELW=$clog2(NS),
    parameter integer MUT_SELECT=0, MUT_PIN_LATENCY=0
)(
    input wire clk_capture, clk_output, rst_n,
    input wire [NS-1:0] src_v,
    input wire [NS*PWT-1:0] src_d,
    input wire [NS-1:0] capture_slot,
    input wire [ND-1:0] sink_slot,
    input wire [ND*SELW-1:0] sink_select,
    output reg [ND-1:0] dst_v,
    output reg [ND*PWT-1:0] dst_d,
    output wire fault,
    output reg [3:0] fault_kind
);
    reg [NS*PWT-1:0] captured;
    reg [NS-1:0] captured_slot;
    reg ingress_fault;
    // Payload is unreset and only read when its compiler reservation is valid.
    always @(posedge clk_capture) captured <= src_d;
    always @(posedge clk_capture or negedge rst_n)
        if (!rst_n) begin captured_slot <= '0; ingress_fault <= 1'b0; end
        else begin
            captured_slot <= capture_slot;
            if (src_v != capture_slot) ingress_fault <= 1'b1;
        end
    reg select_fault, unavailable_fault;
    always @(posedge clk_output or negedge rst_n)
        if (!rst_n) begin dst_v <= '0; select_fault <= 0; unavailable_fault <= 0; end
        else begin
            dst_v <= sink_slot;
            for (integer d=0;d<ND;d=d+1) begin
                if (sink_slot[d]) begin
                    if (int'(sink_select[d*SELW+:SELW]) >= NS) select_fault <= 1;
                    else if (!captured_slot[sink_select[d*SELW+:SELW]]) unavailable_fault <= 1;
                end
            end
        end
    // Constant-source AND/OR, no data-dependent arbitration or shared bus grants.
    always @(posedge clk_output) begin : outputs
        reg [PWT-1:0] selected;
        integer sel;
        for (integer d=0;d<ND;d=d+1) begin
            selected='0;
            sel=int'(sink_select[d*SELW+:SELW]);
            if (MUT_SELECT!=0 && d==0) sel=(sel+1)%NS;
            for (integer s=0;s<NS;s=s+1)
                if (s==sel) selected=selected | (MUT_PIN_LATENCY!=0 ? src_d[s*PWT+:PWT] : captured[s*PWT+:PWT]);
            dst_d[d*PWT+:PWT] <= selected;
        end
    end
    assign fault=ingress_fault | select_fault | unavailable_fault;
    always @* fault_kind={1'b0,unavailable_fault,select_fault,ingress_fault};
endmodule
`default_nettype wire
