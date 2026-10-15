`timescale 1ns/1ps
// Full native arithmetic + fixed controller + physically mapped program SRAM.
// Calendar depth is an explicit capacity, never an implicit infinite C++ array.
// Default storage is 4096 x 1024 bits (128 real 64x512 macros). Actual canonical
// stage length and placement must be measured before this capacity is adopted.
module dsfd_sp_su_static_programmed #(
    parameter integer PROGRAM_DEPTH=4096,
    parameter integer AW=(PROGRAM_DEPTH>64)?$clog2(PROGRAM_DEPTH):6
)(
    input wire sk,srs,arm,
    input wire boot_we,boot_commit,
    input wire [AW-1:0] boot_addr,
    input wire [3:0] boot_lane,
    input wire [63:0] boot_data,
    output wire [31:0] cycle,
    output wire done,
    output wire [7:0] done_tag,
    output wire [15:0] rq_v,
    output wire [223:0] rq_row,
    input wire [15:0] rs_v,
    input wire [8191:0] rs_d,
    output wire [15:0] wq_v,
    output wire [223:0] wq_row,
    output wire [255:0] wq_mask,
    output wire [8191:0] wq_d,
    output wire flt,online,
    output wire [3:0] fcode
);
    wire [1023:0] cw;
    wire loaded,store_fault,core_fault;
    ot_s81_su_calendar_store #(.DEPTH(PROGRAM_DEPTH),.AW(AW)) u_store(
        .clk(sk),.rst_n(srs),.arm(arm),.running(online),.cycle(cycle),
        .boot_we(boot_we),.boot_commit(boot_commit),.boot_addr(boot_addr),
        .boot_lane(boot_lane),.boot_data(boot_data),.calendar_word(cw),
        .program_valid(loaded),.fault(store_fault));
    dsfd_sp_su_static u_su(.sk(sk),.srs(srs),.arm(arm),
        .calendar_valid(loaded),.calendar_cycle(cycle),.calendar_word(cw),
        .cycle(cycle),.done(done),.done_tag(done_tag),.rq_v(rq_v),.rq_row(rq_row),
        .rs_v(rs_v),.rs_d(rs_d),.wq_v(wq_v),.wq_row(wq_row),.wq_mask(wq_mask),
        .wq_d(wq_d),.flt(core_fault),.online(online),.fcode(fcode));
    assign flt=core_fault|store_fault;
endmodule
