`timescale 1ns/1ps
`default_nettype none
module hfd_hgi_vm_calendar_SW_quant (
    input wire clk,rst_n,cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [15:0] client_seq,
    output wire [7:0] response_enable,
    output wire [15:0] response_seq,
    output wire [7:0] bank_enable,
    output wire [23:0] bank_client,
    output wire [1:0] hub_ring_enable,
    output wire [5:0] hub_ring_client,
    output wire [7:0] rslot_v,
    output wire [7:0] wslot_v,
    output wire [23:0] rslot,
    output wire [23:0] wslot,
    output wire [1:0] ring_tx_enable,
    output wire [5:0] ring_tx_source,
    output wire replay_enable,
    output wire replay_source,
    output wire [23:0] lg_local_read,
    output wire [23:0] lg_local_write
);
    wire [201:0] calendar;
    ot_vms_calendar_static #(.W(202)) u_programme (
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(calendar),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
    assign client_seq=calendar[0+:16];
    assign response_enable=calendar[16+:8];
    assign response_seq=calendar[24+:16];
    assign bank_enable=calendar[40+:8];
    assign bank_client=calendar[48+:24];
    assign hub_ring_enable=calendar[72+:2];
    assign hub_ring_client=calendar[74+:6];
    assign rslot_v=calendar[80+:8];
    assign wslot_v=calendar[88+:8];
    assign rslot=calendar[96+:24];
    assign wslot=calendar[120+:24];
    assign ring_tx_enable=calendar[144+:2];
    assign ring_tx_source=calendar[146+:6];
    assign replay_enable=calendar[152+:1];
    assign replay_source=calendar[153+:1];
    assign lg_local_read=calendar[154+:24];
    assign lg_local_write=calendar[178+:24];
endmodule
`default_nettype wire
