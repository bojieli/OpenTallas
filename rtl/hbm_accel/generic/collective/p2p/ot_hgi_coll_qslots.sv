`timescale 1ns/1ps
`default_nettype none
// Compiler-reserved quadrant transport successor (HANDOFF 0an).
// Sources: SU[INJ], rail[NPT], VM[DEL], ring-result[1].
// Sinks: rail[NPT], SU[DEL], RGX[DEL], TKM[DEL], ring-partial[1].
// Source sampled C -> output-leaf input capture C+1 -> registered output C+2. Both leaf clock pins are supplied
// by the die clock tree at their own phi-R; they share the logical cycle phase.
// Faults never stall/retry, and no payload-dependent arbitration exists.
// Actual hardenable capture and switch leaves have separate clock roots.
module ot_hgi_coll_qslots #(
    parameter integer NPT=3, INJ=2, DEL=4, PWT=545,
    parameter integer NS=INJ+NPT+DEL+1,
    parameter integer ND=NPT+3*DEL+1,
    parameter integer SELW=$clog2(NS),
    parameter integer MUT_SELECT=0, MUT_PIN_LATENCY=0
)(
    input wire clk_capture, clk_output, rst_n,
    input wire [NS-1:0] src_v,
    input wire [NS*PWT-1:0] src_d,
    input wire [NS-1:0] capture_slot,
    input wire [ND-1:0] sink_slot,
    input wire [ND*SELW-1:0] sink_select,
    output wire [ND-1:0] dst_v,
    output wire [ND*PWT-1:0] dst_d,
    output wire fault,
    output wire [3:0] fault_kind
);
    wire [NS*PWT-1:0] captured;
    wire [NS-1:0] captured_slot;
    wire ingress_fault, select_fault, unavailable_fault;
    ot_hgi_coll_qslots_capture #(.NS(NS),.PWT(PWT)) u_capture(
        .clk(clk_capture),.rst_n(rst_n),.src_v(src_v),.src_d(src_d),.capture_slot(capture_slot),
        .captured(captured),.captured_slot(captured_slot),.fault(ingress_fault));
    ot_hgi_coll_qslots_output #(.NS(NS),.ND(ND),.PWT(PWT),.SELW(SELW),.MUT_SELECT(MUT_SELECT)) u_output(
        .clk(clk_output),.rst_n(rst_n),.captured(MUT_PIN_LATENCY!=0?src_d:captured),
        .captured_slot(captured_slot),.sink_slot(sink_slot),.sink_select(sink_select),
        .dst_v(dst_v),.dst_d(dst_d),.select_fault(select_fault),.unavailable_fault(unavailable_fault));
    assign fault=ingress_fault | select_fault | unavailable_fault;
    assign fault_kind={1'b0,unavailable_fault,select_fault,ingress_fault};
endmodule

// Payload is not reset. Its compiler reservation must be present before use.
module ot_hgi_coll_qslots_capture #(
    parameter integer NS=10,PWT=545
)(
    input wire clk,rst_n,
    input wire [NS-1:0] src_v,capture_slot,
    input wire [NS*PWT-1:0] src_d,
    output reg [NS*PWT-1:0] captured,
    output reg [NS-1:0] captured_slot,
    output reg fault
);
    always @(posedge clk) captured <= src_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin captured_slot <= '0; fault <= 1'b0; end
        else begin
            captured_slot <= capture_slot;
            if (src_v != capture_slot) fault <= 1'b1;
        end
endmodule

module ot_hgi_coll_qslots_output #(
    parameter integer NS=10,ND=16,PWT=545,SELW=$clog2(NS),MUT_SELECT=0
)(
    input wire clk,rst_n,
    input wire [NS*PWT-1:0] captured,
    input wire [NS-1:0] captured_slot,
    input wire [ND-1:0] sink_slot,
    input wire [ND*SELW-1:0] sink_select,
    output reg [ND-1:0] dst_v,
    output reg [ND*PWT-1:0] dst_d,
    output reg select_fault,unavailable_fault
);
    reg [NS*PWT-1:0] captured_p;
    reg [NS-1:0] captured_slot_p;
    reg [ND-1:0] sink_slot_p;
    reg [ND*SELW-1:0] sink_select_p;
    // Every hardened input face is captured before the switch logic. Payload
    // remains unreset; reservations initialize validity and control timing.
    always @(posedge clk) begin captured_p<=captured; sink_select_p<=sink_select; end
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin captured_slot_p<='0; sink_slot_p<='0; end
        else begin captured_slot_p<=captured_slot; sink_slot_p<=sink_slot; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin dst_v <= '0; select_fault <= 0; unavailable_fault <= 0; end
        else begin
            dst_v <= sink_slot_p;
            for (integer d=0;d<ND;d=d+1) begin
                if (sink_slot_p[d]) begin
                    if (int'(sink_select_p[d*SELW+:SELW]) >= NS) select_fault <= 1;
                    else if (!captured_slot_p[sink_select_p[d*SELW+:SELW]]) unavailable_fault <= 1;
                end
            end
        end
    // Constant-source AND/OR: no dynamic arbitration or shared-bus grant.
    always @(posedge clk) begin : outputs
        reg [PWT-1:0] selected;
        integer sel;
        for (integer d=0;d<ND;d=d+1) begin
            selected='0;
            sel=int'(sink_select_p[d*SELW+:SELW]);
            if (MUT_SELECT!=0 && d==0) sel=(sel+1)%NS;
            for (integer s=0;s<NS;s=s+1)
                if (s==sel) selected=selected | captured_p[s*PWT+:PWT];
            dst_d[d*PWT+:PWT] <= selected;
        end
    end
endmodule
`default_nettype wire
