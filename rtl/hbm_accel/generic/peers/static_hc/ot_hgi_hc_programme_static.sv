`timescale 1ns/1ps
`default_nettype none
// Actual programme-SRAM issuer for the HC engine's44control pins. Word0 is
// emitted start+4 and consumed by HC start+5. Sink launch/capture are compiler
// phase-aligned consumers of these pins; neither observes a ready signal.
// Config/staging writes for bases/scales/VM operands remain separate real ports.
module ot_hgi_hc_programme_static(
    input wire clk,rst_n,
    input wire cfg_we,input wire [9:0] cfg_addr,input wire [255:0] cfg_data,
    input wire start_v,input wire [9:0] start_base,input wire [10:0] start_limit,input wire [15:0] start_loops,
    output wire clear,row_launch,row_raw_read,row_weight_slot,
    output wire [4:0] row_id,
    output wire tail_launch,sink_launch,sink_capture,
    output wire [31:0] norm_eps,
    output wire active,done,fault
);
    wire [43:0] raw;
    wire v;
    wire [43:0] c=v?raw:44'd0;
    ot_vms_calendar_static #(.W(44)) program_(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .calendar(raw),.calendar_v(v),.ordinal(),.active(active),.done(done),.fault(fault));
    assign clear=c[0];assign row_launch=c[1];assign row_raw_read=c[2];assign row_weight_slot=c[3];
    assign row_id=c[8:4];assign tail_launch=c[9];assign sink_launch=c[10];assign sink_capture=c[11];assign norm_eps=c[43:12];
endmodule
`default_nettype wire
