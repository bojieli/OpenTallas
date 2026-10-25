// Candidate persistent controller successor; original CLOSED host master unchanged.
`timescale 1ns/1ps
// Original qkd_ctrl_pc body from origin/main source plus isolated static
// column completion observer. Existing CLOSED master/source remains untouched.
// Observer retains actual controller-domain WDONE17 and crosses ordered
// static-column events to ck; output credit er259 is still an early credit.
// KVCTRL split 2026-10-16 (Q-KVSYS-DIE): qkd_ctrl_pc_host_static is now a WIRES-ONLY parent of three hardened roots
// (e1: one HBM root of 17,150 sinks at 426.8 ps insertion; e2 plateaued at native_commit_identity -58 ps):
//   u_core  qkd_ctrl_pc_host_static_core  (qkd_ctrl_pc_host_static_core.sv): scheduler, tags, CDC, observer, drain
//   u_port  qkd_ctrl_pc_port_child        (qkd_ctrl_pc_children.sv): actual ot_qfd_emb_pcport KVW2 + its data pin flops
//   u_ecc   qkd_ctrl_pc_ecc_child         (qkd_ctrl_pc_children.sv): actual ot_qfd_kv_landing_ecc
// Same ports and parameters as before. Priced edges: native commit observation +1 hclk (pin register); static write
// data +1 hclk into the port (hidden: its column follows by >= 4 edges); KV read return and write data 0.
module qkd_ctrl_pc_host_static #(
    parameter integer CORE_CLOCK = 0,
    parameter integer ROW0  = 64,          // CONTRACT map v2: HBM row of layer 0
    parameter integer CVL   = 2,           // qkd_cdc_wleaf r2 (WPIPE 1): h_cv edges after h_wcon at its pin
    parameter integer HOFF  = 3,           // cycles the hand-off head is not looked at after h_hand (>= 2)
    parameter integer WDONE = CORE_CLOCK ? 19 : 17,          // write-done edges after the WR column (>= CVL + 4)
    parameter integer LATE  = 4096,        // a held (layer-mismatch) write faults after this many cycles
    parameter integer PROFILE = 0,
    parameter integer EVMUT = 0,
    parameter integer MUT   = 0,
    // HANDOFF 0az: 1 = the PHY read return is elastic (HBM/PHY latency not
    // compile-time fixed). expected_raw_valid is then the NOMINAL (minimum)
    // raw return slot: a return earlier than the nominal count is a fault, a
    // return later is absorbed (tag queue + landing ECC are in order, and the
    // qkd_kv_hbm_elastic_front block buffer re-times the corrected sectors),
    // and an outstanding nominal return with no PHY data for RAW_WD edges is a
    // PHY-late fault (watchdog). 0 = historical exact-slot check.
    parameter integer ELASTIC = 0,
    parameter integer RAW_WD = 256,
    // In-order read tag / pcport class queue depth. The fixed RL23 calendar
    // needs 32; the elastic PHY window needs CMD 4 + RL 23 + window + ECC
    // outstanding reads, so ELASTIC uses 64 (sized in the 0az parent proof).
    parameter integer STRAP_CDC = 0, // 1: physical HBM pin capture -> two core-domain captures
    parameter integer DRAIN_PIPE = 0, // 1: conservative two-edge drain summary; no traffic latency change
    parameter integer TQD = (ELASTIC != 0) ? 64 : 32,
    parameter integer CONTEXT_DESC = 0,
    parameter integer STATIC_REFRESH = 0,
    // KV-SCHED8 2026-10-17: 1 binds the flop-first sched_s8 (po / p_w / physical / expected_sr / idle_hbm / fo / ko one hclk
    // later than s7b; see qkd_ctrl_pc_sched PINREG). Opt-in until the die adopts the s8 view and its schedule shifts.
    parameter integer SCHED_PINREG = 0
) (
    input  wire         pll_hbm,
    // Clock entries (lead 2026-10-16 option A, wires-only cluster rule: one top clock port per hard-child clock pin):
    // pll_hbm -> u_core, pll_hbm_port -> u_port, pll_hbm_ecc -> u_ecc. All three carry the SAME HBM clock; the die
    // clock tree delivers each as its own entry (phi - R_i). Data ports and module name unchanged.
    input  wire         pll_hbm_port,
    input  wire         pll_hbm_ecc,
    // KVCTRL core_s7 (lead Q-KV 2026-10-17): the core is three hardened children; each gets its own HBM clock entry:
    // pll_hbm -> u_sched, pll_hbm_cdc -> u_cdc (with ck), pll_hbm_obs -> u_obs. Same HBM clock, one die entry each.
    input  wire         pll_hbm_cdc,
    input  wire         pll_hbm_obs,
    input  wire         hrst,
    input  wire         ck,
    input  wire         rsi,
    input  wire [4:0]   pc,
    input  wire [318:0] ci,
    output wire [293:0] co,
    input  wire [287:0] es,
    output wire [260:0] er,
    output wire [327:0] po,
    input  wire [288:0] pi,
    input  wire [32:0]  ki,
    output wire [32:0]  ko,
    input  wire         fi,
    output wire         fo,
    input wire static_cmd_owner,input wire [42:0] static_cmd,input wire reserved_rd,input wire reserved_static_col,input wire reserved_write_col,
    input wire [15:0] static_epoch,input wire expected_raw_valid,
    input wire [1:0] cfg_stack,
    input wire [317:0] es_context,
    input wire es_expected_valid,input wire [60:0] es_expected_identity,
    input wire [28:0] es_expected_address,input wire [4:0] es_expected_pc,input wire [1:0] es_expected_stack,
    output wire native_commit_valid,output wire [60:0] native_commit_identity,
    output wire [28:0] native_commit_address,
    output wire [15:0] corrected_epoch,
    output wire completion_v,completion_we,completion_fault,
    // Registered observations only. A parent drain barrier must join BOTH
    // domains plus actual upstream quiet, front idle and return-ring idle.
    output wire idle_core,idle_hbm,output wire drain_fault_core,drain_fault_hbm
);

    // ---- wires only: three hardened children ----------------------------------------------------------------------
    wire         p_col_v, p_col_we, p_col_sr, p_w_v, p_kv_v, p_em_v, p_fault, e_l_v, e_fault;
    wire [255:0] p_w_d, l_data;
    wire [287:0] p_wd, p_kv_d;
    wire [257:0] p_em_d;
    wire [16:0]  e_sec, l_sec;
    wire [7:0]   e_row, l_row;
    wire [11:0]  co_c;
    // core_s7: sched / cdc / obs children (was u_core qkd_ctrl_pc_host_static_core). Seams register to register;
    // priced edges vs core_s6: static embed command +1 hclk (cdc down-FIFO output registers), embedding return +1 hclk
    // and u_ctl credit +1 hclk (cdc pin registers), native commit observation +1 hclk (obs input pin registers).
    wire [4:0]   pc_q;
    wire         s_cr, c_v, f_ecdc, physical_col_sr, expected_sr, obs_commit_valid, native_observer_fault;
    wire [286:0] c_d;
    wire [61:0]  c_context;
    wire [346:0] physical_context;
    qkd_ctrl_pc_sched #(.CORE_CLOCK(CORE_CLOCK),.ROW0(ROW0),.CVL(CVL),.HOFF(HOFF),.WDONE(WDONE),.LATE(LATE),.PROFILE(PROFILE),.EVMUT(EVMUT),.MUT(MUT),.ELASTIC(ELASTIC),.RAW_WD(RAW_WD),.STRAP_CDC(STRAP_CDC),.DRAIN_PIPE(DRAIN_PIPE),.TQD(TQD),.CONTEXT_DESC(CONTEXT_DESC),.STATIC_REFRESH(STATIC_REFRESH),.PINREG(SCHED_PINREG)) u_sched (
        .pll_hbm(pll_hbm), .hrst(hrst), .pc(pc), .ci_c({ci[318:309], ci[52:0]}), .co_c(co_c),
        .po(po), .pi_v(pi[0]), .ki(ki), .ko(ko), .fi(fi), .fo(fo),
        .static_cmd_owner(static_cmd_owner), .static_cmd(static_cmd), .reserved_rd(reserved_rd),
        .reserved_static_col(reserved_static_col), .reserved_write_col(reserved_write_col),
        .static_epoch(static_epoch), .expected_raw_valid(expected_raw_valid), .corrected_epoch(corrected_epoch),
        .idle_hbm(idle_hbm), .drain_fault_hbm(drain_fault_hbm),
        .p_col_v(p_col_v), .p_col_we(p_col_we), .p_col_sr(p_col_sr), .p_w_v(p_w_v), .p_w_d(p_w_d),
        .p_wd(p_wd), .p_kv_v(p_kv_v), .p_em_v(p_em_v), .p_fault(p_fault),
        .e_sec(e_sec), .e_row(e_row), .e_l_v(e_l_v), .e_fault(e_fault),
        .pc_q(pc_q), .s_cr_o(s_cr), .c_v(c_v), .c_d(c_d), .c_context(c_context), .f_ecdc(f_ecdc),
        .physical_context(physical_context), .physical_col_sr(physical_col_sr), .expected_sr(expected_sr),
        .obs_commit_valid(obs_commit_valid), .native_commit_valid(native_commit_valid),
        .native_observer_fault(native_observer_fault));
    qkd_ctrl_pc_cdc_child #(.WDONE(WDONE),.PROFILE(PROFILE),.EVMUT(EVMUT),.STRAP_CDC(STRAP_CDC),.DRAIN_PIPE(DRAIN_PIPE)) u_cdc (
        .pll_hbm(pll_hbm_cdc), .hrst(hrst), .ck(ck), .rsi(rsi), .pc(pc), .pc_q(pc_q),
        .es(es), .er(er), .cfg_stack(cfg_stack),
        .es_context(es_context), .es_expected_valid(es_expected_valid), .es_expected_identity(es_expected_identity),
        .es_expected_address(es_expected_address), .es_expected_pc(es_expected_pc), .es_expected_stack(es_expected_stack),
        .completion_v(completion_v), .completion_we(completion_we), .completion_fault(completion_fault),
        .idle_core(idle_core), .drain_fault_core(drain_fault_core),
        .s_cr(s_cr), .p_em_v(p_em_v), .p_em_d(p_em_d), .c_v(c_v), .c_d(c_d), .c_context(c_context), .f_ecdc(f_ecdc),
        .col_v(po[28]), .col_we(po[29]), .col_sr(physical_col_sr));
    qkd_ctrl_pc_obs_child #(.CORE_CLOCK(CORE_CLOCK),.PROFILE(PROFILE)) u_obs (
        .pll_hbm(pll_hbm_obs), .hrst(hrst), .po(po), .static_column(physical_col_sr), .expected_static_column(expected_sr),
        .context_word(physical_context), .obs_commit_valid(obs_commit_valid), .native_commit_valid(native_commit_valid),
        .native_commit_identity(native_commit_identity), .native_commit_address(native_commit_address),
        .fault(native_observer_fault));
    qkd_ctrl_pc_port_child #(.CORE_CLOCK(CORE_CLOCK),.RQD(TQD), .MUT(MUT == 2 ? 4 : 0)) u_port (
        .hclk(pll_hbm_port), .hrst(hrst), .col_v_e(p_col_v), .col_we_e(p_col_we), .col_sr_e(p_col_sr),
        .w_v(p_w_v), .w_d(p_w_d), .kw_vi(ci[28]), .kw_di(ci[308:53]), .pi(pi),
        .wd(p_wd), .kv_v(p_kv_v), .kv_d(p_kv_d), .em_v(p_em_v), .em_d(p_em_d), .fault(p_fault));
    qkd_ctrl_pc_ecc_child u_ecc (
        .hclk(pll_hbm_ecc), .hrst(hrst), .i_v(p_kv_v), .i_code(p_kv_d), .i_sec(e_sec), .i_row(e_row),
        .o_v(e_l_v), .o_data(l_data), .o_sec(l_sec), .o_row(l_row), .fault(e_fault));
    assign co = {co_c, l_data, l_row, l_sec, e_l_v};
endmodule

// Alternative (flat): the same three modules on TWO HBM clock roots (core / port+ECC), each < 15k sinks.
module qkd_ctrl_pc_host_static_r2 #(
    parameter integer CORE_CLOCK = 0,
    parameter integer ROW0  = 64,          // CONTRACT map v2: HBM row of layer 0
    parameter integer CVL   = 2,           // qkd_cdc_wleaf r2 (WPIPE 1): h_cv edges after h_wcon at its pin
    parameter integer HOFF  = 3,           // cycles the hand-off head is not looked at after h_hand (>= 2)
    parameter integer WDONE = CORE_CLOCK ? 19 : 17,          // write-done edges after the WR column (>= CVL + 4)
    parameter integer LATE  = 4096,        // a held (layer-mismatch) write faults after this many cycles
    parameter integer PROFILE = 0,
    parameter integer EVMUT = 0,
    parameter integer MUT   = 0,
    // HANDOFF 0az: 1 = the PHY read return is elastic (HBM/PHY latency not
    // compile-time fixed). expected_raw_valid is then the NOMINAL (minimum)
    // raw return slot: a return earlier than the nominal count is a fault, a
    // return later is absorbed (tag queue + landing ECC are in order, and the
    // qkd_kv_hbm_elastic_front block buffer re-times the corrected sectors),
    // and an outstanding nominal return with no PHY data for RAW_WD edges is a
    // PHY-late fault (watchdog). 0 = historical exact-slot check.
    parameter integer ELASTIC = 0,
    parameter integer RAW_WD = 256,
    // In-order read tag / pcport class queue depth. The fixed RL23 calendar
    // needs 32; the elastic PHY window needs CMD 4 + RL 23 + window + ECC
    // outstanding reads, so ELASTIC uses 64 (sized in the 0az parent proof).
    parameter integer STRAP_CDC = 0, // 1: physical HBM pin capture -> two core-domain captures
    parameter integer DRAIN_PIPE = 0, // 1: conservative two-edge drain summary; no traffic latency change
    parameter integer TQD = (ELASTIC != 0) ? 64 : 32,
    parameter integer CONTEXT_DESC = 0,
    parameter integer STATIC_REFRESH = 0
) (
    input  wire         pll_hbm,
    input  wire         pll_hbm_b,   // second HBM clock root (same PLL output): port + ECC
    input  wire         hrst,
    input  wire         ck,
    input  wire         rsi,
    input  wire [4:0]   pc,
    input  wire [318:0] ci,
    output wire [293:0] co,
    input  wire [287:0] es,
    output wire [260:0] er,
    output wire [327:0] po,
    input  wire [288:0] pi,
    input  wire [32:0]  ki,
    output wire [32:0]  ko,
    input  wire         fi,
    output wire         fo,
    input wire static_cmd_owner,input wire [42:0] static_cmd,input wire reserved_rd,input wire reserved_static_col,input wire reserved_write_col,
    input wire [15:0] static_epoch,input wire expected_raw_valid,
    input wire [1:0] cfg_stack,
    input wire [317:0] es_context,
    input wire es_expected_valid,input wire [60:0] es_expected_identity,
    input wire [28:0] es_expected_address,input wire [4:0] es_expected_pc,input wire [1:0] es_expected_stack,
    output wire native_commit_valid,output wire [60:0] native_commit_identity,
    output wire [28:0] native_commit_address,
    output wire [15:0] corrected_epoch,
    output wire completion_v,completion_we,completion_fault,
    // Registered observations only. A parent drain barrier must join BOTH
    // domains plus actual upstream quiet, front idle and return-ring idle.
    output wire idle_core,idle_hbm,output wire drain_fault_core,drain_fault_hbm
);

    // ---- wires only: three hardened children ----------------------------------------------------------------------
    wire         p_col_v, p_col_we, p_col_sr, p_w_v, p_kv_v, p_em_v, p_fault, e_l_v, e_fault;
    wire [255:0] p_w_d, l_data;
    wire [287:0] p_wd, p_kv_d;
    wire [257:0] p_em_d;
    wire [16:0]  e_sec, l_sec;
    wire [7:0]   e_row, l_row;
    wire [11:0]  co_c;
    qkd_ctrl_pc_host_static_core #(.CORE_CLOCK(CORE_CLOCK),.ROW0(ROW0),.CVL(CVL),.HOFF(HOFF),.WDONE(WDONE),.LATE(LATE),.PROFILE(PROFILE),.EVMUT(EVMUT),.MUT(MUT),.ELASTIC(ELASTIC),.RAW_WD(RAW_WD),.STRAP_CDC(STRAP_CDC),.DRAIN_PIPE(DRAIN_PIPE),.TQD(TQD),.CONTEXT_DESC(CONTEXT_DESC),.STATIC_REFRESH(STATIC_REFRESH)) u_core (
        .pll_hbm(pll_hbm), .hrst(hrst), .ck(ck), .rsi(rsi), .pc(pc), .ci_c({ci[318:309], ci[52:0]}), .co_c(co_c),
        .es(es), .er(er), .po(po), .pi_v(pi[0]), .ki(ki), .ko(ko), .fi(fi), .fo(fo),
        .static_cmd_owner(static_cmd_owner), .static_cmd(static_cmd), .reserved_rd(reserved_rd),
        .reserved_static_col(reserved_static_col), .reserved_write_col(reserved_write_col),
        .static_epoch(static_epoch), .expected_raw_valid(expected_raw_valid), .cfg_stack(cfg_stack),
        .es_context(es_context), .es_expected_valid(es_expected_valid), .es_expected_identity(es_expected_identity),
        .es_expected_address(es_expected_address), .es_expected_pc(es_expected_pc), .es_expected_stack(es_expected_stack),
        .native_commit_valid(native_commit_valid), .native_commit_identity(native_commit_identity),
        .native_commit_address(native_commit_address), .corrected_epoch(corrected_epoch),
        .completion_v(completion_v), .completion_we(completion_we), .completion_fault(completion_fault),
        .idle_core(idle_core), .idle_hbm(idle_hbm), .drain_fault_core(drain_fault_core), .drain_fault_hbm(drain_fault_hbm),
        .p_col_v(p_col_v), .p_col_we(p_col_we), .p_col_sr(p_col_sr), .p_w_v(p_w_v), .p_w_d(p_w_d),
        .p_wd(p_wd), .p_kv_v(p_kv_v), .p_em_v(p_em_v), .p_em_d(p_em_d), .p_fault(p_fault),
        .e_sec(e_sec), .e_row(e_row), .e_l_v(e_l_v), .e_fault(e_fault));
    qkd_ctrl_pc_port_child #(.CORE_CLOCK(CORE_CLOCK),.RQD(TQD), .MUT(MUT == 2 ? 4 : 0)) u_port (
        .hclk(pll_hbm_b), .hrst(hrst), .col_v_e(p_col_v), .col_we_e(p_col_we), .col_sr_e(p_col_sr),
        .w_v(p_w_v), .w_d(p_w_d), .kw_vi(ci[28]), .kw_di(ci[308:53]), .pi(pi),
        .wd(p_wd), .kv_v(p_kv_v), .kv_d(p_kv_d), .em_v(p_em_v), .em_d(p_em_d), .fault(p_fault));
    qkd_ctrl_pc_ecc_child u_ecc (
        .hclk(pll_hbm_b), .hrst(hrst), .i_v(p_kv_v), .i_code(p_kv_d), .i_sec(e_sec), .i_row(e_row),
        .o_v(e_l_v), .o_data(l_data), .o_sec(l_sec), .o_row(l_row), .fault(e_fault));
    assign co = {co_c, l_data, l_row, l_sec, e_l_v};
endmodule
