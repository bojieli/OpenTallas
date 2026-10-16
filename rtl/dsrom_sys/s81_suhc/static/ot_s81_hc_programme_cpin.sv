// Combined candidate: actual programme ROM + actual CPIN; no inherited closed view.
`timescale 1ns/1ps
module ot_s81_hc_programme_cpin #(
    parameter integer COMMAND_POST_AGES = 1,
    parameter string IMAGE = "",
    parameter integer NG = 256, NCOL = 3, GS = 8, S_RD = 2, TH = 8
) (
    input wire stream_ck,stream_rst_n,sk,srs,
    input wire[84:0]c2,
    output wire[8:0]stream_done,
    output wire programme_fault,
    output wire [639:0] n_command_post_ages,
    input wire [31:0] y_tag,
    input wire [4:0] y_row,
    output wire [31:0] n_y_tag,n_command_y_tag,n_command_done_age,n_command_ss_age,n_command_scalar_age,
    output wire [4:0] n_y_row,
    // Descriptor is held from command capture until the next command; it
    // shares the command's registered serial boundary without new cycles.
    // Disabled mode adds no state and preserves the previous parameter profile.
    // die pins
    input  wire                inp,
    output wire  [S_RD-1:0]     rq_v,
    output wire  [S_RD*14-1:0]  rq_row,
    input  wire [S_RD-1:0]     rs_v,
    input  wire [S_RD*512-1:0] rs_d,
    output wire                 flt,
    output wire                 online,
    output wire  [3:0]          fcode,
    input  wire                y_v,
    output wire                 y_rdy,
    input  wire [YS1-1:0]      y_s,
    // the outer roots: accept pulse
    (* keep = "true" *) output wire yacc_w,
    (* keep = "true" *) output wire yacc_e,
    // combine tile seam
    output wire                 n_cmd_v,
    output wire  [83:0]         n_cmd_d,
    input  wire                n_done_v,
    input  wire [7:0]          n_done_tag,
    output wire                 n_inp,
    input  wire [S_RD-1:0]     n_rq_v,
    input  wire [S_RD*14-1:0]  n_rq_row,
    output wire  [S_RD-1:0]     n_rs_v,
    output wire  [S_RD*512-1:0] n_rs_d,
    input  wire                n_flt,
    input  wire                n_online,
    input  wire [3:0]          n_fcode,
    (* keep = "true" *) output wire n_yacc,
    output wire  [YS1-1:0]      n_y,
    input  wire                n_ypop
);

    localparam integer NS = NG / GS;
    localparam integer NP = (NS + NCOL - 1) / NCOL;
    localparam integer L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0;
    localparam integer YS1 = (L1 > 0) ? L1 * GS * 32 : 1;

    wire[84:0]hc_command;wire[8:0]serial_done;
    wire[31:0]command_y_tag,command_done_age,command_ss_age,command_scalar_age;
    wire[639:0]command_post_ages;
    initial if(COMMAND_POST_AGES!=1)$fatal(1,"combined source requires explicit per-command POST ages");
    ot_s81_hc_programme_endpoint #(.IMAGE(IMAGE))u_programme(
      .stream_ck(stream_ck),.stream_rst_n(stream_rst_n),.serial_ck(sk),.serial_rst_n(srs),
      .c2(c2),.hc_command(hc_command),.hc_done_age(command_done_age),.hc_ss_age(command_ss_age),
      .hc_scalar_age(command_scalar_age),.hc_y_tag(command_y_tag),.hc_post_ages(command_post_ages),
      .serial_done(serial_done),.stream_done(stream_done),.fault(programme_fault));
    ot_s81_hc_cpin_calendar #(.NG(NG),.NCOL(NCOL),.GS(GS),.S_RD(S_RD),.TH(TH),.COMMAND_POST_AGES(1))u_cpin(
      .cck(sk),
      .crs(srs),
      .sk(sk),
      .srs(srs),
      .command_post_ages(command_post_ages),
      .n_command_post_ages(n_command_post_ages),
      .y_tag(y_tag),
      .command_y_tag(command_y_tag),
      .command_done_age(command_done_age),
      .command_ss_age(command_ss_age),
      .command_scalar_age(command_scalar_age),
      .y_row(y_row),
      .n_y_tag(n_y_tag),
      .n_command_y_tag(n_command_y_tag),
      .n_command_done_age(n_command_done_age),
      .n_command_ss_age(n_command_ss_age),
      .n_command_scalar_age(n_command_scalar_age),
      .n_y_row(n_y_row),
      .c_cmd_v(hc_command[84]),
      .c_cmd_d(hc_command[83:0]),
      .c_done_v(serial_done[8]),
      .c_done_tag(serial_done[7:0]),
      .inp(inp),
      .rq_v(rq_v),
      .rq_row(rq_row),
      .rs_v(rs_v),
      .rs_d(rs_d),
      .flt(flt),
      .online(online),
      .fcode(fcode),
      .y_v(y_v),
      .y_rdy(y_rdy),
      .y_s(y_s),
      .yacc_w(yacc_w),
      .yacc_e(yacc_e),
      .n_cmd_v(n_cmd_v),
      .n_cmd_d(n_cmd_d),
      .n_done_v(n_done_v),
      .n_done_tag(n_done_tag),
      .n_inp(n_inp),
      .n_rq_v(n_rq_v),
      .n_rq_row(n_rq_row),
      .n_rs_v(n_rs_v),
      .n_rs_d(n_rs_d),
      .n_flt(n_flt),
      .n_online(n_online),
      .n_fcode(n_fcode),
      .n_yacc(n_yacc),
      .n_y(n_y),
      .n_ypop(n_ypop)
    );
endmodule
