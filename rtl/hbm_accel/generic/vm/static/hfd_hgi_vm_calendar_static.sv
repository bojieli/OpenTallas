`timescale 1ns/1ps
`default_nettype none
module hfd_hgi_vm_calendar_SW (
    input wire clk,rst_n,cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [7:0] client_seq,
    output wire [3:0] response_enable,
    output wire [7:0] response_seq,
    output wire [7:0] bank_enable,
    output wire [15:0] bank_client,
    output wire [1:0] hub_ring_enable,
    output wire [3:0] hub_ring_client,
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
    wire [171:0] calendar;
    ot_vms_calendar_static #(.W(172)) u_programme (
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(calendar),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
    assign client_seq=calendar[0+:8];
    assign response_enable=calendar[8+:4];
    assign response_seq=calendar[12+:8];
    assign bank_enable=calendar[20+:8];
    assign bank_client=calendar[28+:16];
    assign hub_ring_enable=calendar[44+:2];
    assign hub_ring_client=calendar[46+:4];
    assign rslot_v=calendar[50+:8];
    assign wslot_v=calendar[58+:8];
    assign rslot=calendar[66+:24];
    assign wslot=calendar[90+:24];
    assign ring_tx_enable=calendar[114+:2];
    assign ring_tx_source=calendar[116+:6];
    assign replay_enable=calendar[122+:1];
    assign replay_source=calendar[123+:1];
    assign lg_local_read=calendar[124+:24];
    assign lg_local_write=calendar[148+:24];
endmodule
module hfd_hgi_vm_calendar_SE (
    input wire clk,rst_n,cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [1:0] client_seq,
    output wire response_enable,
    output wire [1:0] response_seq,
    output wire [7:0] bank_enable,
    output wire [7:0] bank_client,
    output wire [1:0] hub_ring_enable,
    output wire [1:0] hub_ring_client,
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
    wire [146:0] calendar;
    ot_vms_calendar_static #(.W(147)) u_programme (
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(calendar),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
    assign client_seq=calendar[0+:2];
    assign response_enable=calendar[2+:1];
    assign response_seq=calendar[3+:2];
    assign bank_enable=calendar[5+:8];
    assign bank_client=calendar[13+:8];
    assign hub_ring_enable=calendar[21+:2];
    assign hub_ring_client=calendar[23+:2];
    assign rslot_v=calendar[25+:8];
    assign wslot_v=calendar[33+:8];
    assign rslot=calendar[41+:24];
    assign wslot=calendar[65+:24];
    assign ring_tx_enable=calendar[89+:2];
    assign ring_tx_source=calendar[91+:6];
    assign replay_enable=calendar[97+:1];
    assign replay_source=calendar[98+:1];
    assign lg_local_read=calendar[99+:24];
    assign lg_local_write=calendar[123+:24];
endmodule
module hfd_hgi_vm_calendar_NW (
    input wire clk,rst_n,cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [9:0] client_seq,
    output wire [4:0] response_enable,
    output wire [9:0] response_seq,
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
    wire [186:0] calendar;
    ot_vms_calendar_static #(.W(187)) u_programme (
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(calendar),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
    assign client_seq=calendar[0+:10];
    assign response_enable=calendar[10+:5];
    assign response_seq=calendar[15+:10];
    assign bank_enable=calendar[25+:8];
    assign bank_client=calendar[33+:24];
    assign hub_ring_enable=calendar[57+:2];
    assign hub_ring_client=calendar[59+:6];
    assign rslot_v=calendar[65+:8];
    assign wslot_v=calendar[73+:8];
    assign rslot=calendar[81+:24];
    assign wslot=calendar[105+:24];
    assign ring_tx_enable=calendar[129+:2];
    assign ring_tx_source=calendar[131+:6];
    assign replay_enable=calendar[137+:1];
    assign replay_source=calendar[138+:1];
    assign lg_local_read=calendar[139+:24];
    assign lg_local_write=calendar[163+:24];
endmodule
module hfd_hgi_vm_calendar_NE (
    input wire clk,rst_n,cfg_we,
    input wire [9:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [9:0] start_base,
    input wire [10:0] start_limit,
    input wire [15:0] start_loops,
    output wire calendar_v,active,done,fault,
    output wire [31:0] ordinal,
    output wire [1:0] client_seq,
    output wire response_enable,
    output wire [1:0] response_seq,
    output wire [7:0] bank_enable,
    output wire [7:0] bank_client,
    output wire [1:0] hub_ring_enable,
    output wire [1:0] hub_ring_client,
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
    wire [146:0] calendar;
    ot_vms_calendar_static #(.W(147)) u_programme (
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(calendar),.calendar_v(calendar_v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
    assign client_seq=calendar[0+:2];
    assign response_enable=calendar[2+:1];
    assign response_seq=calendar[3+:2];
    assign bank_enable=calendar[5+:8];
    assign bank_client=calendar[13+:8];
    assign hub_ring_enable=calendar[21+:2];
    assign hub_ring_client=calendar[23+:2];
    assign rslot_v=calendar[25+:8];
    assign wslot_v=calendar[33+:8];
    assign rslot=calendar[41+:24];
    assign wslot=calendar[65+:24];
    assign ring_tx_enable=calendar[89+:2];
    assign ring_tx_source=calendar[91+:6];
    assign replay_enable=calendar[97+:1];
    assign replay_source=calendar[98+:1];
    assign lg_local_read=calendar[99+:24];
    assign lg_local_write=calendar[123+:24];
endmodule
`default_nettype wire
