`timescale 1ns/1ps
// S81-SLICE xs lockstep REFERENCE (bench only): the unmodified production static PQ column slot, canonical produced
// profile -- the paired calendar ROM reader (ot_s81_pq_calendar_rom, PINREG) + dsfd_sp_pq_n (ot_s81_pq_core_native with
// OT_PQ_CTL_STATIC / STATE_PINS / INCAP / CALCAP / AQ_PIN_LAUNCH, QB_PIPE + PINREAD + split leaves, BC_SLICED,
// DSFD_PQ_ROM4, DSFD_PQ_STATIC_X2) + its six ROM macros (phase 0/1, stream 0..3; images by INSTANCE from +OT_ROM_DIR).
// The bench plays the hub VM (x responses on the calendar's VM-response rows) and the twelve return groups (row counts
// before each retire); everything between the issuer / calendar and the lane word xw is production RTL.
module tb_s81sl_xs_ref (
    input  wire          clk,
    input  wire          rst,
    input  wire          prime,
    input  wire          start,
    input  wire [11:0]   cal_base,
    input  wire [12:0]   cal_len,
    input  wire [92:0]   f_iss,
    input  wire [2048:0] f_vm,
    input  wire [203:0]  f_cnt,
    output wire [1100:0] xw,
    output wire [38:0]   t_iss,
    output wire          cal_fault,
    output wire [74:0]   cal_action
);
    wire cal_active, cal_primed;
    ot_s81_pq_calendar_rom #(.ACTION_BITS(75), .PINREG(1)) u_calendar (
        .ck(clk), .rst_n(rst), .prime(prime), .stage_start(start), .base(cal_base), .length(cal_len),
        .action(cal_action), .active(cal_active), .primed(cal_primed), .fault(cal_fault));
    wire cal_v = cal_primed || cal_active || (|cal_action);
    wire [11:0] ra0, ra1, ra2; wire [3:0] rc2; wire [71:0] raw0, raw1, raw2 [0:3];
    ot_rom_4096x72_m8 #(.INSTANCE("pq_phase0")) u_phase0 (.clk(clk), .ce_in(1'b1), .addr_in(ra0), .rd_out(raw0));
    ot_rom_4096x72_m8 #(.INSTANCE("pq_phase1")) u_phase1 (.clk(clk), .ce_in(1'b1), .addr_in(ra1), .rd_out(raw1));
    ot_rom_4096x72_m8 #(.INSTANCE("pq_stream0")) u_stream0 (.clk(clk), .ce_in(rc2[0]), .addr_in(ra2), .rd_out(raw2[0]));
    ot_rom_4096x72_m8 #(.INSTANCE("pq_stream1")) u_stream1 (.clk(clk), .ce_in(rc2[1]), .addr_in(ra2), .rd_out(raw2[1]));
    ot_rom_4096x72_m8 #(.INSTANCE("pq_stream2")) u_stream2 (.clk(clk), .ce_in(rc2[2]), .addr_in(ra2), .rd_out(raw2[2]));
    ot_rom_4096x72_m8 #(.INSTANCE("pq_stream3")) u_stream3 (.clk(clk), .ce_in(rc2[3]), .addr_in(ra2), .rd_out(raw2[3]));
    wire [1100:0] xe;
    wire stream_end_v; wire [1:0] stream_end_tag; wire [19:0] t_vm; wire [457:0] t_cnt;
    dsfd_sp_pq_n u_pq (
        .ck_ctl(clk), .ck_qb(clk), .ck_fault(clk), .ck_qb_align(clk), .ck_qb_aux({4{clk}}), .ck_aq({2{clk}}),
        .ck_aq_aux({16{clk}}), .ck_ix({4{clk}}), .ck_ix_read({32{clk}}), .ck_bc({16{clk}}), .ck_lane(clk), .rst(rst),
        .f_iss(f_iss), .calendar_v(cal_v), .calendar_action(cal_action),
        .stream_end_v(stream_end_v), .stream_end_tag(stream_end_tag),
        .t_iss(t_iss), .t_vm(t_vm), .f_vm(f_vm), .ra0(ra0), .ra1(ra1), .ra2(ra2), .rc0(), .rc1(), .rc2(rc2),
        .rq0(raw0[63:0]), .rq1(raw1[63:0]),
        .rq2({raw2[3][47:0], raw2[2][47:0], raw2[1][47:0], raw2[0][47:0]}),
        .t_cnt(t_cnt), .f_cnt(f_cnt), .xw(xw), .xe(xe), .xws(3'b011), .xes(3'b011));
endmodule
