`timescale 1ns/1ps
// The package controller as hardened: the superset role (the SOURCE package
// that also sends HIDDEN and RESULT messages and folds a running argmax), the
// configuration of the routed record results/physical_abi3/asap7/rom/ot_rom_pkg_ctrl.
// One universal tile carries it; a tile's role is its message routing.
//
// The core-start bundle leaves through a register.  ot_rom_pkg_ctrl drives
// core_start / core_token / core_pos combinationally (timed for a core beside
// it); at the tile's floorplan core_token is a ~920 ps path, so the macro
// boundary registers it, at one cycle per token.  The core clears `done` on
// the edge after it samples start, so the controller must not see the previous
// job's `done` while its start sits in the register: that `done` is masked.
module ot_chip_pkg_ctrl (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    cfg_users,
    input  wire [15:0]   cfg_prompt_len,
    input  wire [15:0]   cfg_gen_len,
    input  wire          in_valid,
    output wire          in_ready,
    input  wire [511:0]  in_data,
    input  wire          in_last,
    output wire          out_valid,
    input  wire          out_ready,
    output wire [511:0]  out_data,
    output wire          out_last,
    output wire          core_start,
    output wire [15:0]   core_token,
    output wire [15:0]   core_pos,
    input  wire          core_done,
    input  wire [15:0]   core_next_token,
    input  wire [31:0]   core_next_val,
    output wire [23:0]   kv_base,
    output wire          vm_we,
    output wire [7:0]    vm_waddr,
    output wire [511:0]  vm_wdata,
    output wire          vm_re,
    output wire [7:0]    vm_raddr,
    input  wire [511:0]  vm_rq,
    output wire          pr_re,
    output wire [7:0]    pr_user,
    output wire [15:0]   pr_pos,
    input  wire [15:0]   pr_q,
    output wire          core_busy,
    output wire          tok_valid,
    output wire [7:0]    tok_user,
    output wire [15:0]   tok_pos,
    output wire [15:0]   tok_id,
    output wire [7:0]    users_done,
    output wire          proto_fault
);
    wire          c_start;
    wire [15:0]   c_token, c_pos;
    reg           start_r;
    reg  [15:0]   token_r, pos_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) start_r <= 1'b0; else start_r <= c_start;
    always @(posedge clk) begin token_r <= c_token; pos_r <= c_pos; end
    assign core_start = start_r;
    assign core_token = token_r;
    assign core_pos   = pos_r;

    ot_rom_pkg_ctrl #(.SOURCE(1), .RESULT_PARTS(4), .SEND_HIDDEN(1), .SEND_RESULT(1),
                      .COMBINE_IN(1), .ROW0(1024), .TXB(8)) u (
        .clk(clk), .rst_n(rst_n),
        .cfg_users(cfg_users), .cfg_prompt_len(cfg_prompt_len), .cfg_gen_len(cfg_gen_len),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(out_valid), .out_ready(out_ready), .out_data(out_data), .out_last(out_last),
        .core_start(c_start), .core_token(c_token), .core_pos(c_pos), .core_done(core_done & ~start_r),
        .core_next_token(core_next_token), .core_next_val(core_next_val), .kv_base(kv_base),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .vm_re(vm_re), .vm_raddr(vm_raddr),
        .vm_rq(vm_rq), .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
        .core_busy(core_busy), .tok_valid(tok_valid), .tok_user(tok_user), .tok_pos(tok_pos),
        .tok_id(tok_id), .users_done(users_done), .proto_fault(proto_fault));
endmodule
