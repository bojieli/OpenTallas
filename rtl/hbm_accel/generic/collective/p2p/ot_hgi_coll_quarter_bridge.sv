`timescale 1ns/1ps
`default_nettype none
// Candidate only. Every selected output has its own physical clock root.
// Sources: existing NPT qslots rail TX, CW arrival, CCW arrival.
// Outputs: NPT local PHY TX, NPT local RX ejection, CW launch, CCW launch.
// Reservation/sample edge C -> registered output C+1 -> consumer edge C+2.
// No buffering, credits, ready, arbitration, or payload-dependent timing.
module ot_hgi_coll_quarter_bridge #(
    parameter integer NPT=3, NS=NPT+2, ND=2*NPT+2, SW=$clog2(NS),
    parameter integer MUT_SELECT=0, MUT_FAULT=0
)(
    input wire [ND-1:0] clk_output,
    input wire rst_n,
    input wire [NS-1:0] src_v,
    input wire [NS*545-1:0] src_d,
    input wire [NS-1:0] expect_v,
    input wire [ND-1:0] out_slot,
    input wire [ND*SW-1:0] out_select,
    output wire [ND-1:0] out_v,
    output wire [ND*545-1:0] out_d,
    output wire [ND*2-1:0] fault
);
    for(genvar d=0;d<ND;d=d+1) begin:g_out
        ot_hgi_coll_quarter_bridge_mux #(.NS(NS),.SW(SW),
            .MUT_SELECT(MUT_SELECT),.MUT_FAULT(MUT_FAULT)) u_leaf(
            .clk(clk_output[d]),.rst_n(rst_n),.src_v(src_v),.src_d(src_d),
            .expect_v(expect_v),.slot(out_slot[d]),.select(out_select[d*SW+:SW]),
            .out_v(out_v[d]),.out_d(out_d[d*545+:545]),.fault(fault[d*2+:2]));
    end
endmodule

// Also used as NS=2 local RX face selector: local endpoint RX / bridge ejection.
// Invalid/unavailable selection still publishes at its reserved edge; fault
// prevents operation acceptance. There is no silent retry or deferred flit.
module ot_hgi_coll_quarter_bridge_mux #(
    parameter integer NS=5, SW=$clog2(NS), MUT_SELECT=0, MUT_FAULT=0
)(
    input wire clk,rst_n,
    input wire [NS-1:0] src_v,
    input wire [NS*545-1:0] src_d,
    input wire [NS-1:0] expect_v,
    input wire slot,
    input wire [SW-1:0] select,
    output reg out_v,
    output reg [544:0] out_d,
    output reg [1:0] fault
);
    reg [NS*545-1:0] data_p;
    reg [NS-1:0] valid_p;
    reg [NS-1:0] expect_p;
    reg slot_p;
    reg [SW-1:0] select_p;
    always @(posedge clk) begin data_p<=src_d; select_p<=select; end
    always @(posedge clk or negedge rst_n)
        if(!rst_n) begin valid_p<='0;expect_p<='0;slot_p<=0;out_v<=0;fault<=0;end
        else begin
            valid_p<=src_v;expect_p<=expect_v;slot_p<=slot;out_v<=slot_p;
            if(MUT_FAULT==0) begin
                if(valid_p!=expect_p) fault[0]<=1;
                if(slot_p && (int'(select_p)>=NS)) fault[1]<=1;
                else if(slot_p && !valid_p[select_p]) fault[1]<=1;
            end
        end
    always @(posedge clk) begin:select_data
        reg [544:0] picked;
        integer sel;
        picked='0;sel=int'(select_p);
        if(MUT_SELECT!=0) sel=(sel+1)%NS;
        for(integer s=0;s<NS;s=s+1)
            if(sel==s) picked=picked|data_p[s*545+:545];
        out_d<=picked;
    end
endmodule

// One physical register per real wire station; each stage must be placed
// beside its planned segment endpoint and receive its own phi-R clock.
module ot_hgi_coll_quarter_bridge_relay(
    input wire clk,rst_n,in_v,
    input wire [544:0] in_d,
    output reg out_v,
    output reg [544:0] out_d
);
    always @(posedge clk) out_d<=in_d;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) out_v<=0; else out_v<=in_v;
endmodule
`default_nettype wire
