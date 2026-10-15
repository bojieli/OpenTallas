`timescale 1ns/1ps
`default_nettype none
// Actual native HC component. The compiler owns reserve/drain, residual read,
// programme start and result store slots. Only the off-chip PHY fetch boundary
// has ready state. On-chip missing data faults without moving any operation.
// VM SRAMs and the far HC LG tap belong to the native VM fabric outside this
// boundary. All operand/programme/prefetch memories inside are real macros.
module ot_hgi_hc_native_sys1_split_mtp_static #(
    parameter integer ROW_LOOP=1,
    parameter integer NATIVE_GATHER_READER=0,
    parameter integer TAIL_LOOP=0,
    parameter integer MAX_OUTSTANDING=8
)(
    input wire clk,reduction_clk,scalar_clk,sink_clk,rst_n,hbm_clk,hbm_rst_n,
    input wire [31:0] weight_clk,input wire [15:0] residual_clk,
    input wire [7:0] bank_clk,input wire [31:0] mac_clk,
    input wire gather_phase,gather_launch,input wire [3:0] gather_npos,
    input wire [15:0] gather_base_sector,gather_stride_sector,output wire gather_done,
    input wire cfg_we,input wire [10:0] cfg_addr,input wire [255:0] cfg_data,
    input wire start_v,input wire [10:0] start_base,input wire [11:0] start_limit,input wire [15:0] start_loops,
    input wire reserve_v,reserve_half,input wire [34:0] reserve_row_local_byte,input wire [15:0] reserve_epoch,
    output wire [3:0] reserve_ready,output wire [7:0] fetched_ready,output wire [31:0] resident_ready,
    input wire drain_v,drain_half,drain_slot,input wire [15:0] drain_epoch,
    output wire half_done,done_half,
    input wire residual_launch,input wire [3:0] residual_npos,input wire [15:0] residual_base_sector,
    output wire [135:0] local_rq,output wire [7:0] local_read,input wire [2055:0] local_rr,
    output wire residual_done,
    input wire store_slot,input wire [15:0] result_base_sector,input wire [2:0] store_position,
    output wire [2247:0] local_wq,output wire [7:0] local_write,
    input wire gathered_mix_v,input wire [4:0] gathered_mix_row,input wire [2:0] gathered_mix_pos,input wire [31:0] gathered_mix_data,
    input wire [767:0] bases,input wire [95:0] scales,
    output wire row_result_v,output wire [4:0] row_result_id,output wire [2:0] row_result_pos,output wire [31:0] row_result,
    output wire result_v,output wire [767:0] result,output wire [2:0] tail_result_pos,
    output wire tail_e_ready,program_active,program_done,fault,
    output wire [127:0] k_v,input wire [127:0] k_rdy,output wire [3839:0] k_addr,
    output wire [511:0] k_len,output wire [2175:0] k_tag,output wire [127:0] k_we,
    output wire [32767:0] k_wdata,output wire [4095:0] k_wstrb,input wire [127:0] k_wr_done,
    input wire [127:0] kr_v,output wire [127:0] kr_rdy,input wire [2175:0] kr_tag,
    input wire [511:0] kr_beat,input wire [32767:0] kr_data
);
wire [135:0] residual_rq;
wire [7:0] residual_read;
wire [2055:0] residual_rr;
wire effective_mix_v, gather_adapter_fault;
wire [4:0] effective_mix_row;
wire [2:0] effective_mix_pos;
wire [31:0] effective_mix_data;
// Change ONLY residual producer VM connections to these private wires:
// .local_rq(residual_rq),.local_read(residual_read),.local_rr(residual_rr)
ot_hgi_hc_vm_gather_adapter_static #(.ENABLE_GATHER_READER(NATIVE_GATHER_READER)) mix_reader(
 .clk(clk),.rst_n(rst_n),.gather_phase(gather_phase),.gather_launch(gather_launch),
 .gather_npos(gather_npos),.gather_base_sector(gather_base_sector),.gather_stride_sector(gather_stride_sector),
 .residual_rq(residual_rq),.residual_read(residual_read),.residual_rr(residual_rr),
 .local_rq(local_rq),.local_read(local_read),.local_rr(local_rr),
 .external_mix_v(gathered_mix_v),.external_mix_row(gathered_mix_row),
 .external_mix_pos(gathered_mix_pos),.external_mix_data(gathered_mix_data),
 .gathered_mix_v(effective_mix_v),.gathered_mix_row(effective_mix_row),
 .gathered_mix_pos(effective_mix_pos),.gathered_mix_data(effective_mix_data),
 .gather_done(gather_done),.fault(gather_adapter_fault));

    wire [2223:0] weight_ap;
    wire x_wave_v;wire [9:0] x_wave_word;wire [8191:0] x_wave;
    wire wf,xf,ef,of_;
    ot_hgi_hc_prefetch_resident_static #(.MAX_OUTSTANDING(MAX_OUTSTANDING)) weights(
        .stream_clk(clk),.stream_rst_n(rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),
        .reserve_v(reserve_v),.reserve_half(reserve_half),.reserve_row_local_byte(reserve_row_local_byte),
        .reserve_epoch(reserve_epoch),.reserve_ready(reserve_ready),.fetched_ready(fetched_ready),.resident_ready(resident_ready),
        .drain_v(drain_v),.drain_half(drain_half),.drain_slot(drain_slot),.drain_epoch(drain_epoch),
        .half_done(half_done),.done_half(done_half),.ap(weight_ap),.fault(wf),
        .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),
        .k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
        .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));
    ot_hgi_hc_residual_vm_static residuals(
        .clk(clk),.rst_n(rst_n),.launch(residual_launch),.npos(residual_npos),.base_sector(residual_base_sector),
        .local_rq(residual_rq),.local_read(residual_read),.local_rr(residual_rr),
        .x_wave_v(x_wave_v),.x_wave_word(x_wave_word),.x_wave(x_wave),.done(residual_done),.fault(xf));
    ot_hgi_hc_programmed_sys1_split_mtp_static #(.ROW_LOOP(ROW_LOOP),.TAIL_LOOP(TAIL_LOOP)) arithmetic(
        .clk(clk),.reduction_clk(reduction_clk),.scalar_clk(scalar_clk),.bank_clk(bank_clk),.weight_clk(weight_clk),.residual_clk(residual_clk),.mac_clk(mac_clk),.sink_clk(sink_clk),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .weight_ap(weight_ap),.x_wave_v(x_wave_v),.x_wave_word(x_wave_word),.x_wave(x_wave),
        .gathered_mix_v(effective_mix_v),.gathered_mix_row(effective_mix_row),.gathered_mix_pos(effective_mix_pos),.gathered_mix_data(effective_mix_data),
        .bases(bases),.scales(scales),.row_result_v(row_result_v),.row_result_id(row_result_id),.row_result_pos(row_result_pos),.row_result(row_result),
        .result_v(result_v),.result(result),.tail_result_pos(tail_result_pos),.tail_e_ready(tail_e_ready),
        .program_active(program_active),.program_done(program_done),.fault(ef));
    ot_hgi_hc_result_vm_static output_store(
        .clk(clk),.rst_n(rst_n),.store_slot(store_slot),.base_sector(result_base_sector),.store_position(store_position),
        .result_v(result_v),.result_position(tail_result_pos),.result(result),.local_wq(local_wq),.local_write(local_write),.fault(of_));
    assign fault=wf|xf|ef|of_|gather_adapter_fault;
endmodule
`default_nettype wire
