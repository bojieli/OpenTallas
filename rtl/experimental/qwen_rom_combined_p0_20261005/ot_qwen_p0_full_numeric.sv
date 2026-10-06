// Numerical full36+head vehicle only. Real finite protected transport and
// Descartes' timed HBM3E checker/backing are connected at literal PHY pins.
// One Vdie per actual TP rank, each with all36 layers; no physical claim.
`timescale 1ns/1ps
module ot_qwen_p0_full_numeric #(


    parameter integer PROTECTED_STREAM4 = 0, // source candidate, opt-in until owner gates pass
    // Descartes' source-only protected port join. Does not select or qualify
    // Claude's raw RSEL CDC; actual protected physical binding remains open.
    parameter integer PARALLEL_TRANSPORT = 0,
    parameter integer CDC_CONSUMER_JOIN = 0,
    parameter integer LANDING_RSEL = 0, // owner implemented protected full504 r9 read
    parameter integer BASELINE_AR = 0, // explicit owner selection; off by default
    parameter integer CORE_FS = 833333, CTL_FS = 1024000,
    parameter integer G = 6144,
    parameter integer NW = 18,
    parameter integer SNW = 18,
    parameter integer QWEN_FULLSHAPE = 1,
    parameter integer ME_IDLE_GATE = 1,
    parameter integer SW = 64,
    parameter integer LV = 7,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer TCUT = 7,
    parameter integer BD = 1,
    parameter integer XVM = 0,
    parameter integer NWS = 0,
    parameter integer TWS = 0,
    parameter integer ORD = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer MEM_EXTRA = 0,
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer MUL_LAT = 5,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer ENABLE_AR256 = 0,
    parameter integer D = 4,
    // REAL_MEM
    parameter integer REAL_MEM = 1,
    parameter integer SCALE_BANKS = 13,      // 4096-word macros per scale port (>= scale words / 4096)
    parameter integer CROM_WORDS = 1048576,
    parameter integer VM_ELEMS = 177808,
    parameter integer NSTK = 4,                // HBM3E stacks a die
    parameter integer NPC = 32 * NSTK,
    parameter integer HBM_LAYERS = 3,
    parameter integer FILL_LAT = 8,
    parameter integer NRD = 256,
    parameter integer LKA = 512,              // unused (fill-service parameter, kept for the driver)
    parameter integer WBW = 1,                // token write-backs a cycle (distinct PCs)
    parameter integer HBM_PHASE = 0,          // refresh phase of the stack's REFpb schedule
    parameter integer HBM_PULLIN = 0,         // controller refresh pull-in (ot_hbm_r14_stream_pc PULLIN)
    parameter integer EMBED_ROM = 1         // the token's X from the INT8 embedding ROM (stage E); 0: X preloaded
) (
    output wire [15:0] numeric_fault_code,
    output wire [383:0] h_cred_ret,
    output wire [3:0] h_desc_commit, h_go_commit,
    output wire [11:0] h_desc_ordinal, h_go_ordinal,
    output wire transport_quiet,
    input  wire              clk,
    input  wire              hclk, // independent periodic 1024ps controller root
    input  wire              warm_rst_n, // admission pause only; cold POR is rt_rst_n
    output reg               rt_rst_n,
    output reg  [31:0]       cyc,
    output reg               start,
    input  wire [SNW-1:0]    tp_token,
    input  wire [SNW-1:0]    tp_pos,
    input  wire              rm_kv_ideal,       // A/B reference: KV service HBM bypassed (run-time strap)
    input  wire [7:0]        rm_layer,          // the stage's layer (its HBM KV region); 255: no KV (embedding stage)
    input  wire [7:0]        rm_next_layer,     // the layer of the next stage (notice); 255: none
    input  wire              rm_early_go,       // strap: release the next layer's stream at this layer's kv_free
    input  wire              rm_posted_wb,      // strap: posted token write-back
    output wire              kv_wb_busy,        // write-backs outstanding (the host drains before reading HBM)
    input  wire              h_start,
    output wire              me_clk_en,
    output wire              s_done,
    output wire              s_fault,
    output wire              core_fault,
    output wire [SNW-1:0]    seq_ntok,
    output wire [31:0]       seq_nval,
    output wire [31:0]       core_cycles,
    output wire              c_valid,
    input  wire              c_ready,
    output wire [511:0]      c_data,
    output wire              c_last,
    output wire              c_mode,
    output wire [31:0]       c_tag,
    input  wire              r_valid,
    input  wire [511:0]      r_data,
    input  wire              r_last,
    input  wire [((D > 2) ? 2 : 1)-1:0] r_rank,
    input  wire              r_err,
    output wire [11:0]       prog_base,
    // array spine: tile fabric
    output wire              tgo,
    output wire [3*NW+13*24+13-1:0] tb,
    output wire [(1<<SMAX)*32-1:0] xl_d,
    input  wire [(G >> TCUT)*16*32-1:0] t_lvl,
    input  wire              fab_fault,
    // tile KV slice write ports (to ot_qwen_rom_tile_w12 kvw_*)
    output wire [G/4-1:0]     kvw_ce,
    output wire [G/4*7-1:0]   kvw_addr,
    output wire [G/4*512-1:0] kvw_data,
    output wire [G/4*512-1:0] kvw_mask,
    // memory-service status
    output wire              mem_fault,
    output wire [15:0]       kv_fault_code,
    output wire              kv_ok_o,
    output wire              kv_drained_o,
    output wire [31:0]       st_fill_cycles, st_fill_sectors, st_wr_sectors, st_rsp_stall,
    output wire [31:0]       st_kvok_low_desc, st_drain_low, st_wr_lat_max, st_fill_exposed,
    output reg  [31:0]       st_stall_kv, st_stall_drain, st_stall_bridge, st_stall_retire, st_stall_mem
);
    wire [127:0] h_lv, h_av;
    wire [128*17-1:0] h_lsec;
    wire [128*8-1:0] h_lrow;
    wire [128*256-1:0] h_ldata;
    wire [128*9-1:0] h_atag;
    wire phy_fault;
    wire [127:0] row_v, col_v, col_we, busy;
    wire [128*3-1:0] row_op;
    wire [128*5-1:0] row_bank, col_bank, col_col;
    wire [128*19-1:0] row_row;
    wire [127:0] h_cv;
    wire [128*24-1:0] h_csec;
    wire [128*256-1:0] h_cdata;
    wire [128*9-1:0] h_ctag;
    ot_qwen_p0_full_transport_join #(
        .PROTECTED_STREAM4(PROTECTED_STREAM4),
        .PARALLEL_TRANSPORT(PARALLEL_TRANSPORT),
        .CDC_CONSUMER_JOIN(CDC_CONSUMER_JOIN),
        .LANDING_RSEL(LANDING_RSEL),
        .BASELINE_AR(BASELINE_AR),
        .CORE_FS(CORE_FS),
        .CTL_FS(CTL_FS),
        .G(G),
        .NW(NW),
        .SNW(SNW),
        .QWEN_FULLSHAPE(QWEN_FULLSHAPE),
        .ME_IDLE_GATE(ME_IDLE_GATE),
        .SW(SW),
        .LV(LV),
        .SMIN(SMIN),
        .SMAX(SMAX),
        .TCUT(TCUT),
        .BD(BD),
        .XVM(XVM),
        .NWS(NWS),
        .TWS(TWS),
        .ORD(ORD),
        .SCALE_LOCAL(SCALE_LOCAL),
        .MEM_EXTRA(MEM_EXTRA),
        .ACC_LAT(ACC_LAT),
        .TREE_LAT(TREE_LAT),
        .MUL_LAT(MUL_LAT),
        .FAST_ISSUE(FAST_ISSUE),
        .KV_PREP(KV_PREP),
        .ENABLE_AR256(ENABLE_AR256),
        .D(D),
        .REAL_MEM(REAL_MEM),
        .SCALE_BANKS(SCALE_BANKS),
        .CROM_WORDS(CROM_WORDS),
        .VM_ELEMS(VM_ELEMS),
        .NSTK(NSTK),
        .NPC(NPC),
        .HBM_LAYERS(HBM_LAYERS),
        .FILL_LAT(FILL_LAT),
        .NRD(NRD),
        .LKA(LKA),
        .WBW(WBW),
        .HBM_PHASE(HBM_PHASE),
        .HBM_PULLIN(HBM_PULLIN),
        .EMBED_ROM(EMBED_ROM)
    ) u_join (
        .h_lv(h_lv),
        .h_av(h_av),
        .h_lsec(h_lsec),
        .h_lrow(h_lrow),
        .h_ldata(h_ldata),
        .h_atag(h_atag),
        .phy_fault(phy_fault),
        .row_v(row_v),
        .col_v(col_v),
        .col_we(col_we),
        .busy(busy),
        .row_op(row_op),
        .row_bank(row_bank),
        .col_bank(col_bank),
        .col_col(col_col),
        .row_row(row_row),
        .h_cv(h_cv),
        .h_csec(h_csec),
        .h_cdata(h_cdata),
        .h_ctag(h_ctag),
        .h_cred_ret(h_cred_ret),
        .h_desc_commit(h_desc_commit),
        .h_go_commit(h_go_commit),
        .h_desc_ordinal(h_desc_ordinal),
        .h_go_ordinal(h_go_ordinal),
        .transport_quiet(transport_quiet),
        .clk(clk),
        .hclk(hclk),
        .warm_rst_n(warm_rst_n),
        .rt_rst_n(rt_rst_n),
        .cyc(cyc),
        .start(start),
        .tp_token(tp_token),
        .tp_pos(tp_pos),
        .rm_kv_ideal(rm_kv_ideal),
        .rm_layer(rm_layer),
        .rm_next_layer(rm_next_layer),
        .rm_early_go(rm_early_go),
        .rm_posted_wb(rm_posted_wb),
        .kv_wb_busy(kv_wb_busy),
        .h_start(h_start),
        .me_clk_en(me_clk_en),
        .s_done(s_done),
        .s_fault(s_fault),
        .core_fault(core_fault),
        .seq_ntok(seq_ntok),
        .seq_nval(seq_nval),
        .core_cycles(core_cycles),
        .c_valid(c_valid),
        .c_ready(c_ready),
        .c_data(c_data),
        .c_last(c_last),
        .c_mode(c_mode),
        .c_tag(c_tag),
        .r_valid(r_valid),
        .r_data(r_data),
        .r_last(r_last),
        .r_rank(r_rank),
        .r_err(r_err),
        .prog_base(prog_base),
        .tgo(tgo),
        .tb(tb),
        .xl_d(xl_d),
        .t_lvl(t_lvl),
        .fab_fault(fab_fault),
        .kvw_ce(kvw_ce),
        .kvw_addr(kvw_addr),
        .kvw_data(kvw_data),
        .kvw_mask(kvw_mask),
        .mem_fault(mem_fault),
        .kv_fault_code(kv_fault_code),
        .kv_ok_o(kv_ok_o),
        .kv_drained_o(kv_drained_o),
        .st_fill_cycles(st_fill_cycles),
        .st_fill_sectors(st_fill_sectors),
        .st_wr_sectors(st_wr_sectors),
        .st_rsp_stall(st_rsp_stall),
        .st_kvok_low_desc(st_kvok_low_desc),
        .st_drain_low(st_drain_low),
        .st_wr_lat_max(st_wr_lat_max),
        .st_fill_exposed(st_fill_exposed),
        .st_stall_kv(st_stall_kv),
        .st_stall_drain(st_stall_drain),
        .st_stall_bridge(st_stall_bridge),
        .st_stall_retire(st_stall_retire),
        .st_stall_mem(st_stall_mem)
    );
    ot_qwen_s4_numeric_memory #(.MEM_WORDS(HBM_LAYERS*131072),
        .PHASE(HBM_PHASE),.PULLIN(HBM_PULLIN)) u_numeric (
        .hclk(hclk),
        .rst_n(rt_rst_n),
        .row_v(row_v),
        .col_v(col_v),
        .col_we(col_we),
        .row_op(row_op),
        .row_bank(row_bank),
        .col_bank(col_bank),
        .col_col(col_col),
        .row_row(row_row),
        .h_cv(h_cv),
        .h_csec(h_csec),
        .h_cdata(h_cdata),
        .h_ctag(h_ctag),
        .h_lv(h_lv),
        .h_av(h_av),
        .h_lsec(h_lsec),
        .h_lrow(h_lrow),
        .h_ldata(h_ldata),
        .h_atag(h_atag),
        .phy_fault(phy_fault),
        .cred_ret(h_cred_ret),
        .fault_code(numeric_fault_code)
    );
endmodule
