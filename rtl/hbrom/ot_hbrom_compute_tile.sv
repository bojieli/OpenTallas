`timescale 1ns/1ps
// Synthesizable full-shape HBROM prototype. ENABLE defaults off.
// Admission: TP4 / 128 ROM pairs per tile / four tiles per cluster (2026-10-05).
// The NC1 matrix engine is the existing unprotected baseline. Feed DMR does not
// establish protection of the engine's mutable SRAM/control, or system signoff.
// Real memory blackboxes are mandatory in synthesis: never substitute zero ROM.
// Control owner must configure before descriptor/start, publish all x fragments,
// drain results, and coordinate rst_n with any canceled in-flight SM operation.
module ot_hbrom_compute_tile #(
    parameter integer ENABLE=0,
    parameter integer PAIRS=128,
    parameter integer FEED_PROTECT=1
)(
    input wire clk,rst_n,
    input wire start,
    input wire [12:0] op_rows,
    input wire [15:0] op_c,
    input wire [7:0] op_g,
    input wire op_gs,
    input wire [1:0] op_fmt,
    output wire busy,
    input wire cfg_valid,
    output wire cfg_ready,
    input wire [31:0] cfg_base_record,cfg_region_records,
    input wire [15:0] cfg_epoch,
    input wire d_valid,
    output wire d_ready,
    input wire [31:0] d_base,
    input wire [23:0] d_lines,
    input wire xw_en,
    input wire [6:0] xw_addr,xw_grp,
    input wire [2047:0] xw_data,
    output wire rv,
    output wire [11:0] rrow,
    output wire [31:0] rdata,
    output wire arrive,
    input wire release_in,
    output wire released,
    input wire cancel,
    output wire cancel_done,feed_idle,
    output wire sm_fault,feed_fault,fault
);
    generate if(ENABLE!=0) begin:g_enabled
        wire req_v,req_ready,rsp_v;
        wire [31:0] req_addr;
        wire [9:0] req_tag,rsp_tag;
        wire [1087:0] rsp_data;
        wire [2*PAIRS-1:0] rom_ce,capture_ce;
        wire [2*PAIRS*12-1:0] rom_addr;
        wire [2*PAIRS*274-1:0] rom_q;
        (* keep_hierarchy = "yes" *) ot_hbrom_rom_feed #(
            .ENABLE(1),.PAIRS(PAIRS),.PROTECT(FEED_PROTECT)
        ) feed (
            .clk(clk),.rst_n(rst_n),.cfg_valid(cfg_valid),.cfg_ready(cfg_ready),
            .cfg_fmt(op_fmt),.cfg_rows(op_rows),.cfg_groups(op_g),.cfg_group_slot(op_gs),
            .cfg_base_record(cfg_base_record),.cfg_region_records(cfg_region_records),
            .cfg_virtual_base(d_base),.cfg_epoch(cfg_epoch),
            .req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),
            .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
            .cancel(cancel),.cancel_done(cancel_done),.idle(feed_idle),.fault(feed_fault),
            .rom_ce(rom_ce),.rom_addr(rom_addr),.rom_q(rom_q),.capture_ce(capture_ce)
        );
        (* keep_hierarchy = "yes" *) ot_hbm_accel_sm_v #(
            .ENABLE(1),.SUB(4),.LBS(2),.LSB(16),.NC(1),.RMAX(4096),
            .LEV(4),.XD(128),.MAX_OUT(512),.IL(8),.DS(2),.DW(4),
            .DG(3),.PIO(2),.STK(1),.TCK(1)
        ) sm (
            .clk(clk),.rst_n(rst_n),.start(start),.op_rows(op_rows),.op_c(op_c),
            .op_g(op_g),.op_gs(op_gs),.op_fmt(op_fmt),.busy(busy),
            .d_valid(d_valid),.d_ready(d_ready),.d_base(d_base),.d_lines(d_lines),
            .req_v(req_v),.req_ready(req_ready),.req_addr(req_addr),.req_tag(req_tag),
            .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
            .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
            .rv(rv),.rrow(rrow),.rdata(rdata),.fault(sm_fault),.arrive(arrive),
            .release_in(release_in),.released(released)
        );
        for(genvar m=0;m<2*PAIRS;m=m+1) begin:g_rom
            // Stable physical identity m=8*bankgroup+2*stream+parity.
            // This blackbox has no simulation-only personalization parameters.
            (* keep = "true", dont_touch = "true" *) ot_rom_4096x274_m8 u_rom (
                .clk(clk),.ce_in(rom_ce[m]),.addr_in(rom_addr[12*m +:12]),
                .rd_out(rom_q[274*m +:274])
            );
        end
        assign fault=sm_fault|feed_fault;
    end else begin:g_disabled
        assign cfg_ready=0;
        assign d_ready=0;
        assign busy=0;
        assign rv=0;
        assign rrow=0;
        assign rdata=0;
        assign arrive=0;
        assign released=0;
        assign cancel_done=0;
        assign feed_idle=1;
        assign feed_fault=0;
        assign sm_fault=0;
        assign fault=0;
    end endgenerate
endmodule
