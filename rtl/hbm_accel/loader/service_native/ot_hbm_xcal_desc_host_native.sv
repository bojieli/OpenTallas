`timescale 1ns/1ps
`default_nettype none
// Opt-in two-native-tile prototype; explicit actual clock roots, no timing exceptions.
module ot_hbm_xcal_desc_host_native #(parameter integer MUT = 0, parameter integer PAW = 11, parameter integer PREL = 1,
    parameter integer DD = 256, parameter integer DAW = (DD > 128) ? 8 : 7) (
    input  wire          clk_desc,
    input  wire          rst_n,
    input  wire [7:0]    tgt,
    input  wire          cfg_v,
    input  wire [7:0]    cfg_target,
    input  wire [11:0]   cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_v,
    input  wire [11:0]   desc_base,
    input  wire [12:0]   desc_limit,
    input  wire [15:0]   desc_loops,
    input  wire          launch_v,
    input wire pdone,pfault,
    output wire cw,sv,output wire [PAW-1:0] ca,sb,
    output wire [255:0] cd,output wire [PAW:0] sl,
    output wire [15:0] sn,output wire [4:0] sx,
    output wire          done,
    output wire          configured,
    output wire          fault,
    output wire          active
);
    (* keep = 1 *) reg [1:0] reset_landing;
    always @(posedge clk_desc or negedge rst_n)
      if(!rst_n)reset_landing<=0;else reset_landing<={reset_landing[0],1'b1};
    wire rst_q=reset_landing[1];
    wire a_we, b_we, run_v, x_active, x_fault;
    wire [PAW-1:0] a_addr; wire [DAW-1:0] b_addr; wire [255:0] a_data, b_data;
    wire [DAW-1:0] run_base; wire [DAW:0] run_count; wire [7:0] run_arg;
    ot_hbm_xcal_target_native #(.TARGET(8'hff), .AWA(PAW), .AWB(DAW), .RBW(DAW), .RCW(DAW + 1), .NA(1), .NF(1),
        .MUT((MUT == 5) ? 2 : 0), .TGT_PIN(1)) u_tgt (
        .clk(clk_desc), .rst_n(rst_q), .rst_raw_n(rst_n), .reset_phase0(reset_landing[0]), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr),
        .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops),
        .launch_v(launch_v), .tgt_active(x_active), .tgt_fault(x_fault),
        .a_we(a_we), .a_addr(a_addr), .a_data(a_data), .b_we(b_we), .b_addr(b_addr), .b_data(b_data),
        .run_v(run_v), .run_base(run_base), .run_count(run_count), .run_arg(run_arg),
        .configured(configured), .fault(fault), .active(active));
    ot_hbm_xcal_desc_native #(.MUT(MUT),.PAW(PAW),.DD(DD),.DAW(DAW)) u_desc(
      .clk(clk_desc),.rst_n(rst_n),.cfg_we(a_we),.cfg_addr(a_addr),.cfg_data(a_data),
      .desc_we(b_we),.desc_addr(b_addr),.desc_data(b_data),.run_v(run_v),.run_base(run_base),.run_count(run_count),
      .prog_done(pdone),.prog_fault(pfault),.cfg_we_o(cw),.cfg_addr_o(ca),.cfg_data_o(cd),
      .start_v_o(sv),.start_base_o(sb),.start_limit_o(sl),.start_loops_o(sn),.start_ctx_o(sx),
      .active(x_active),.done(done),.fault(x_fault));
    wire unused_arg = &{1'b0,run_arg};
endmodule
`default_nettype wire
