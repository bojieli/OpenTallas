`timescale 1ns/1ps
`default_nettype none
// Native HC component: two actual programme SRAMs drive every arithmetic
// launch/read/capture event in the actual PMAX8/80-operand-SRAM engine.
// Only host programme/configuration and operand/gathered-data staging enter
// at this boundary. No testbench or reference arithmetic issues DUT events.
module ot_hgi_hc_programmed_sys1_split_mtp_static #(parameter integer ROW_LOOP=0, parameter integer TAIL_LOOP=0)(
    input wire clk,reduction_clk,scalar_clk,sink_clk,rst_n,
    input wire [31:0] weight_clk,input wire [15:0] residual_clk,
    input wire [7:0] bank_clk,input wire [31:0] mac_clk,
    input wire cfg_we,input wire [10:0] cfg_addr,input wire [255:0] cfg_data,
    input wire start_v,input wire [10:0] start_base,input wire [11:0] start_limit,input wire [15:0] start_loops,
    input wire [2223:0] weight_ap,
    input wire x_wave_v,input wire [9:0] x_wave_word,input wire [8191:0] x_wave,
    input wire gathered_mix_v,input wire [4:0] gathered_mix_row,input wire [2:0] gathered_mix_pos,input wire [31:0] gathered_mix_data,
    input wire [767:0] bases,input wire [95:0] scales,
    output wire row_result_v,output wire [4:0] row_result_id,output wire [2:0] row_result_pos,output wire [31:0] row_result,
    output wire result_v,output wire [767:0] result,output wire [2:0] tail_result_pos,
    output wire tail_e_ready,program_active,program_done,fault
);
    wire clear,row_launch,row_raw_read,row_weight_slot,tail_launch,sink_launch,sink_capture,pf,ef;
    wire [4:0] row_id;
    wire [3:0] npos;
    wire [2:0] tail_position;
    wire [31:0] norm_eps;
    ot_hgi_hc_programme_mtp_static #(.ROW_LOOP(ROW_LOOP),.TAIL_LOOP(TAIL_LOOP)) issuer(
        .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .clear(clear),.row_launch(row_launch),.row_raw_read(row_raw_read),.row_weight_slot(row_weight_slot),
        .row_id(row_id),.row_npos(npos),.tail_position(tail_position),.norm_eps(norm_eps),
        .tail_launch(tail_launch),.sink_launch(sink_launch),.sink_capture(sink_capture),
        .active(program_active),.done(program_done),.fault(pf));
    ot_hgi_hc_engine_sys1_split_mtp_static engine(
        .clk(clk),.reduction_clk(reduction_clk),.scalar_clk(scalar_clk),.bank_clk(bank_clk),.weight_clk(weight_clk),.residual_clk(residual_clk),.mac_clk(mac_clk),.sink_clk(sink_clk),.rst_n(rst_n),.clear(clear),
        .weight_ap(weight_ap),.x_wave_v(x_wave_v),.x_wave_word(x_wave_word),.x_wave(x_wave),
        .row_launch(row_launch),.row_raw_read(row_raw_read),.row_weight_slot(row_weight_slot),
        .row_id(row_id),.row_npos(npos),.norm_eps(norm_eps),
        .gathered_mix_v(gathered_mix_v),.gathered_mix_row(gathered_mix_row),.gathered_mix_pos(gathered_mix_pos),.gathered_mix_data(gathered_mix_data),
        .tail_launch(tail_launch),.tail_position(tail_position),.sink_launch(sink_launch),.sink_capture(sink_capture),
        .bases(bases),.scales(scales),.row_result_v(row_result_v),.row_result_id(row_result_id),.row_result_pos(row_result_pos),.row_result(row_result),
        .result_v(result_v),.result(result),.tail_result_pos(tail_result_pos),.tail_e_ready(tail_e_ready),.fault(ef));
    assign fault=pf|ef;
endmodule
`default_nettype wire
