`timescale 1ns/1ps
`default_nettype none
// hbm-forks 2026-10-09: the HGI-1 command processor (C1 of docs/HBM_GENERIC_INTERFACE.md section 6, owner Claude per the
// REVIEW_20261009 HGI-1 work-split correction): TOKEN18 core (ot_hgi_cmdproc_core[_m]) + the config master (CFG window,
// CFG_COMMIT check, config bus, settle hold-off, CFG_STATUS) + its own receiver for cp_vocab / cp_ctx_max (words 40-41).
// The CFG window rides the existing host write port: host writes with the window bit (cmd_addr[CB], a spare bit of the
// loader bus in the die wrapper) set go to the staging buffer instead of the command memory: cmd_addr[4:0] = pair index,
// and cmd_addr[CB-1:0] == CFG_COMMIT_A (all ones) with the window bit = CFG_COMMIT.
// The record sequencer (C2) replaces the LAUNCH/END list later; until then the command list path is unchanged.
module ot_hgi_cmdproc #(
    parameter integer NSM    = 16,
    parameter integer NCMD   = 256,
    parameter integer MACRO  = 1,       // 1: command memory in the ot_sram_2rw_512x64 macro (the die form), 0: flops
    parameter integer RDREG  = 2,
    parameter integer SETTLE = 64,
    parameter integer ENABLE = 1
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     cmd_we,
    input  wire [$clog2(NCMD):0]    cmd_addr,       // MSB = CFG window bit
    input  wire [63:0]              cmd_wdata,
    input  wire                     units_busy,     // any unit queue non-empty (E_BUSY), with the core's own job state
    output wire [39:0]              cfg_bus,        // to the first config-bus station
    output wire                     cfg_loaded,
    output wire [2:0]               cfg_err,
    output wire [5*32-1:0]          cfg_md_d,       // section D for the sequencer
    output wire [2*32-1:0]          cfg_cp_act,     // active words 40-41 (CF-0 read-back)
    input  wire                     db_v,
    output wire                     db_rdy,
    input  wire [17:0]              db_token,
    input  wire [19:0]              db_pos,
    input  wire [31:0]              db_job,
    input  wire [3:0]               db_generation,
    output wire [19:0]              cpl_position,
    output wire [31:0]              cpl_job,
    output wire [3:0]               cpl_generation,
    output wire [NSM-1:0]           launch_v,
    output wire [31:0]              launch_pc,
    output wire [17:0]              launch_token,
    output wire [19:0]              launch_pos,
    input  wire [NSM-1:0]           sm_done,
    input  wire [NSM-1:0]           sm_fault,
    input  wire [NSM-1:0]           res_v,
    input  wire [NSM*32-1:0]        res_data,
    output wire                     cpl_v,
    input  wire                     cpl_rdy,
    output wire [17:0]              cpl_token,
    output wire [3:0]               cpl_status,
    output wire [31:0]              cpl_cycles,
    output wire [31:0]              st_kernels,
    output wire [31:0]              st_busy
);
`include "ot_hgi_cfg_consts.svh"
    localparam integer CB = $clog2(NCMD);
    wire win = cmd_addr[CB];
    wire c_commit = cmd_we && win && (cmd_addr[CB-1:0] == {CB{1'b1}});
    wire c_wr = cmd_we && win && !c_commit;
    wire hold;
    wire core_busy = !db_rdy && !hold;              // a job between doorbell and completion retire
    ot_hgi_cfg_master #(.SETTLE(SETTLE)) u_cfg (.clk(clk), .rst_n(rst_n), .w_en(c_wr), .w_pair(cmd_addr[4:0]),
        .w_data(cmd_wdata), .commit(c_commit), .busy(units_busy || core_busy || db_v), .bus(cfg_bus),
        .st_loaded(cfg_loaded), .st_err(cfg_err), .st_hold(hold), .md_d(cfg_md_d));
    wire [2*32-1:0] cp_act;
    ot_hgi_cfg_rx #(.W0(40), .NW(2), .RST({HGI_RST_W41, HGI_RST_W40})) u_rx (.clk(clk), .rst_n(rst_n), .bus(cfg_bus),
        .act(cp_act));
    assign cfg_cp_act = cp_act;
    wire [17:0] vocab = cp_act[HGI_CP_VOCAB_L +: HGI_CP_VOCAB_N];
    wire [20:0] ctx   = cp_act[32 + HGI_CP_CTX_MAX_L +: HGI_CP_CTX_MAX_N];
    generate if (MACRO) begin : g_m
        ot_hgi_cmdproc_core_m #(.ENABLE(ENABLE), .NSM(NSM), .NCMD(NCMD), .RDREG(RDREG)) u_core (
            .clk(clk), .cfg_vocab(vocab), .cfg_ctx_max(ctx), .cfg_hold(hold), .rst_n(rst_n),
            .cmd_we(cmd_we && !win), .cmd_addr(cmd_addr[CB-1:0]), .cmd_wdata(cmd_wdata),
            .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(db_job), .db_generation(db_generation),
            .cpl_position(cpl_position), .cpl_job(cpl_job), .cpl_generation(cpl_generation),
            .launch_v(launch_v), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
            .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy),
            .cpl_token(cpl_token), .cpl_status(cpl_status), .cpl_cycles(cpl_cycles), .st_kernels(st_kernels), .st_busy(st_busy));
    end else begin : g_f
        ot_hgi_cmdproc_core #(.ENABLE(ENABLE), .NSM(NSM), .NCMD(NCMD)) u_core (
            .clk(clk), .cfg_vocab(vocab), .cfg_ctx_max(ctx), .cfg_hold(hold), .rst_n(rst_n),
            .cmd_we(cmd_we && !win), .cmd_addr(cmd_addr[CB-1:0]), .cmd_wdata(cmd_wdata),
            .db_v(db_v), .db_rdy(db_rdy), .db_token(db_token), .db_pos(db_pos), .db_job(db_job), .db_generation(db_generation),
            .cpl_position(cpl_position), .cpl_job(cpl_job), .cpl_generation(cpl_generation),
            .launch_v(launch_v), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
            .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy),
            .cpl_token(cpl_token), .cpl_status(cpl_status), .cpl_cycles(cpl_cycles), .st_kernels(st_kernels), .st_busy(st_busy));
    end endgenerate
endmodule
`default_nettype wire
