`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// kv-die 2026-10-09: end-to-end ATTENTION LAYER STEP through the ROM die <-> KV die link (bench top).
//   ROM die  : the SU / VM faces (harness) -> ROM_ST on-die relay stages -> ot_qkvd_d2d (ROM end) -> PHY macro model
//   KV die   : PHY macro model -> ot_qkvd_d2d (KV end) -> KV_ST relay stages -> ot_qkvd_kv_seq -> the near-HBM attention
//              (4 stacks + hub + LINK hub<->stack stages: ot_qwen_nearhbm_attn_die_tb, built with the _p successors)
//              with the row responses through the sequencer's KV merge; RES back the same way.
// Every relay stage carries data forward and credit pulses backward (one register each way per stage).  The harness
// (tb_qkvd_layer.cpp) drives CTL / KVN / Q / EMBQ at the SU face under its credits, models HBM (t = T-1 rows POISONED:
// the crossed K / V must be merged), the embedding gateway and the host, and checks every output bit-exactly against
// the golden (tools/qwen_nearhbm_attn_ref.py vectors from tools/hdc_golden.py).
// MUT: 0 base | 1 ROM adapter one extra link credit | 2 KV merge off | 3 one flit dropped in the PHY (ROM->KV)
//      | 4 ROM adapter early link credit | 5 Q beats 0/1 swapped on the KV die
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_layer_tb #(
    parameter integer HD     = 128,
    parameter integer R      = 8,
    parameter integer LINK   = 14,
    parameter integer ROM_ST = 24,
    parameter integer KV_ST  = 12,
    parameter integer PHY_LAT = 5,
    parameter integer MUT    = 0,
    parameter integer DROP_AT = 300,
    parameter [31:0]  SCALE  = 32'h3DB504F3,
    parameter integer W      = 528,
    parameter integer E      = 4 * R
) (
    input  wire              clk,
    input  wire              rst_n,
    // ROM die: SU face (CTL, Q, KVN, EMBQ) and VM / control face (RES, EMBD, HCTL)
    input  wire [3:0]        su_v,
    input  wire [4*W-1:0]    su_d,
    output wire [3:0]        su_cr,
    output wire [2:0]        vm_v,
    output wire [3*W-1:0]    vm_d,
    input  wire [2:0]        vm_cr,
    // KV die: HBM row requests / responses, KV write, embedding gateway, host
    output wire [E-1:0]      req_valid,
    output wire [E-1:0]      req_v,
    output wire [E-1:0]      req_g,
    output wire [13*E-1:0]   req_t,
    input  wire [E-1:0]      rsp_valid,
    input  wire [E*HD*8-1:0] rsp_data,
    output wire              kvw_v,
    output wire [1:0]        kvw_vg,
    output wire [13:0]       kvw_t,
    output wire [5:0]        kvw_layer,
    output wire [HD*8-1:0]   kvw_d,
    input  wire              kvw_cr,
    output wire              emb_req_v,
    output wire [W-1:0]      emb_req_d,
    input  wire              emb_req_cr,
    input  wire              emb_q_v,
    input  wire [W-1:0]      emb_q_d,
    output wire              emb_q_cr,
    input  wire              hc_v,
    input  wire [W-1:0]      hc_d,
    output wire              hc_cr,
    output wire              tok_v,
    output wire [W-1:0]      tok_d,
    input  wire              tok_cr,
    output wire [3:0]        faults,          // {attention, KV sequencer, KV adapter, ROM adapter}
    output wire              a_start_o,
    output wire              a_out_valid_o
);
    localparam integer FW = 548;
    // credit sizing (CONTRACT.md): every buffer covers its credit loop's round trip for one word a cycle
    localparam integer RT_ROM = 2 * ROM_ST + 4;          // SU face <-> ROM adapter die-face loop
    localparam integer RT_KV  = 2 * KV_ST + 4;           // KV adapter <-> sequencer loop
    localparam integer RT_LNK = 2 * PHY_LAT + 8;         // adapter <-> adapter link loop
    localparam integer QB  = (RT_ROM + 8 > 48) ? RT_ROM + 8 : 48;
    localparam integer LB  = (RT_LNK + 4 > 32) ? RT_LNK + 4 : 32;
    localparam integer KB  = (RT_KV + 4 > 32) ? RT_KV + 4 : 32;
    // ROM end: TX CTL Q KVN EMBQ (classes 0-3), RX RES EMBD HCTL (classes 4-6)
    localparam [31:0] R_IBD = {8'd8, 8'd8, 8'(QB), 8'd8};
    localparam [31:0] R_FCR = {8'd4, 8'd8, 8'(LB), 8'd4};
    localparam [31:0] R_RBD = {8'd4, 8'd4, 8'(LB), 8'(LB)};
    localparam [31:0] R_OCR = {8'd4, 8'(RT_ROM), 8'(RT_ROM), 8'(RT_ROM + 64)};
    // KV end: TX RES EMBD HCTL (4-6), RX CTL Q KVN EMBQ (0-3)
    localparam [31:0] K_IBD = {8'd8, 8'd4, 8'(KB + 8), 8'(KB + 8)};
    localparam [31:0] K_FCR = {8'd0, 8'd4, 8'(LB), 8'(LB)};
    localparam [31:0] K_RBD = {8'd4, 8'd8, 8'(LB), 8'd4};
    localparam [31:0] K_OCR = {8'd4, 8'd8, 8'(KB + 8), 8'd4};

    // ---------------- ROM die ----------------
    wire [3:0]     rt_v;  wire [4*W-1:0] rt_d;  wire [3:0] rt_cr;
    wire [2:0]     rr_v;  wire [3*W-1:0] rr_d;  wire [2:0] rr_cr;
    ot_hdc_delay #(.W(4), .D(ROM_ST), .RESET(1)) u_r1v (.clk(clk), .rst_n(rst_n), .d(su_v), .q(rt_v));
    ot_hdc_delay #(.W(4*W), .D(ROM_ST)) u_r1d (.clk(clk), .rst_n(rst_n), .d(su_d), .q(rt_d));
    ot_hdc_delay #(.W(4), .D(ROM_ST), .RESET(1)) u_r1c (.clk(clk), .rst_n(rst_n), .d(rt_cr), .q(su_cr));
    ot_hdc_delay #(.W(3), .D(ROM_ST), .RESET(1)) u_r2v (.clk(clk), .rst_n(rst_n), .d(rr_v), .q(vm_v));
    ot_hdc_delay #(.W(3*W), .D(ROM_ST)) u_r2d (.clk(clk), .rst_n(rst_n), .d(rr_d), .q(vm_d));
    ot_hdc_delay #(.W(3), .D(ROM_ST), .RESET(1)) u_r2c (.clk(clk), .rst_n(rst_n), .d(vm_cr), .q(rr_cr));
    wire rom_up, rom_txv, rom_rxv, rom_lv, kv_up, kv_txv, kv_rxv, kv_lv;
    wire [FW-1:0] rom_txf, rom_rxf, rom_lf, kv_txf, kv_rxf, kv_lf;
    wire [4:0] rom_fc, kv_fc;
    ot_qkvd_d2d #(.NT(4), .NR(3), .TXB(0), .RXB(4), .IBD(R_IBD), .FCR(R_FCR), .RBD(R_RBD), .OCR(R_OCR),
                  .MUT(MUT == 1 ? 1 : (MUT == 4 ? 2 : 0))) u_rom (
        .clk(clk), .rst_n(rst_n), .t_v(rt_v), .t_d(rt_d), .t_cr(rt_cr), .r_v(rr_v), .r_d(rr_d), .r_cr(rr_cr),
        .tx_up(rom_up), .tx_v(rom_txv), .tx_flit(rom_txf), .rx_v(rom_rxv), .rx_flit(rom_rxf), .fault(faults[0]),
        .fault_cause(rom_fc));
    // ---------------- package: the two macros ----------------
    reg [31:0] cyc;
    always @(posedge clk or negedge rst_n) if (!rst_n) cyc <= 0; else cyc <= cyc + 1;
    wire drop = (MUT == 3) && rom_lv && (cyc == DROP_AT);
    ot_qkvd_ucie_x64_phy_model #(.LAT(PHY_LAT)) u_prom (.clk(clk), .rst_n(rst_n), .tx_up(rom_up), .tx_v(rom_txv),
        .tx_flit(rom_txf), .rx_v(rom_rxv), .rx_flit(rom_rxf), .link_v(rom_lv), .link_flit(rom_lf), .far_v(kv_lv),
        .far_flit(kv_lf));
    ot_qkvd_ucie_x64_phy_model #(.LAT(PHY_LAT)) u_pkv (.clk(clk), .rst_n(rst_n), .tx_up(kv_up), .tx_v(kv_txv),
        .tx_flit(kv_txf), .rx_v(kv_rxv), .rx_flit(kv_rxf), .link_v(kv_lv), .link_flit(kv_lf), .far_v(rom_lv && !drop),
        .far_flit(rom_lf));
    // ---------------- KV die ----------------
    wire [3:0]     kr_v;  wire [4*W-1:0] kr_d;  wire [3:0] kr_cr;
    wire [2:0]     kt_v;  wire [3*W-1:0] kt_d;  wire [2:0] kt_cr;
    ot_qkvd_d2d #(.NT(3), .NR(4), .TXB(4), .RXB(0), .IBD(K_IBD), .FCR(K_FCR), .RBD(K_RBD), .OCR(K_OCR)) u_kv (
        .clk(clk), .rst_n(rst_n), .t_v(kt_v), .t_d(kt_d), .t_cr(kt_cr), .r_v(kr_v), .r_d(kr_d), .r_cr(kr_cr),
        .tx_up(kv_up), .tx_v(kv_txv), .tx_flit(kv_txf), .rx_v(kv_rxv), .rx_flit(kv_rxf), .fault(faults[1]),
        .fault_cause(kv_fc));
    wire [3:0]     sc_v;  wire [4*W-1:0] sc_d;  wire [3:0] sc_cr;
    wire [2:0]     su_tv; wire [3*W-1:0] su_td; wire [2:0] su_tcr;
    ot_hdc_delay #(.W(4), .D(KV_ST), .RESET(1)) u_k1v (.clk(clk), .rst_n(rst_n), .d(kr_v), .q(sc_v));
    ot_hdc_delay #(.W(4*W), .D(KV_ST)) u_k1d (.clk(clk), .rst_n(rst_n), .d(kr_d), .q(sc_d));
    ot_hdc_delay #(.W(4), .D(KV_ST), .RESET(1)) u_k1c (.clk(clk), .rst_n(rst_n), .d(sc_cr), .q(kr_cr));
    ot_hdc_delay #(.W(3), .D(KV_ST), .RESET(1)) u_k2v (.clk(clk), .rst_n(rst_n), .d(su_tv), .q(kt_v));
    ot_hdc_delay #(.W(3*W), .D(KV_ST)) u_k2d (.clk(clk), .rst_n(rst_n), .d(su_td), .q(kt_d));
    ot_hdc_delay #(.W(3), .D(KV_ST), .RESET(1)) u_k2c (.clk(clk), .rst_n(rst_n), .d(kt_cr), .q(su_tcr));
    wire          a_start, a_qv, a_ov, a_og;
    wire [13:0]   a_T;
    wire [5:0]    a_qb, a_ob;
    wire [511:0]  a_qd, a_od;
    wire [E-1:0]  e_rv;
    wire [E*HD*8-1:0] e_rd;
    wire [7:0]    seq_fc;
    ot_qkvd_kv_seq #(.HD(HD), .R(R), .W(W), .QD(KB + 8), .CD(4), .KD(8), .ED(4), .UC0(KB + 8), .UC1(KB + 8),
                     .UC2(4), .MUT(MUT == 2 ? 1 : (MUT == 5 ? 2 : 0))) u_seq (
        .clk(clk), .rst_n(rst_n), .c_v(sc_v), .c_d(sc_d), .c_cr(sc_cr), .u_v(su_tv), .u_d(su_td), .u_cr(su_tcr),
        .a_start(a_start), .a_T(a_T), .a_q_valid(a_qv), .a_q_beat(a_qb), .a_q_data(a_qd), .a_out_valid(a_ov),
        .a_out_g(a_og), .a_out_beat(a_ob), .a_out_data(a_od), .e_req_valid(req_valid), .e_req_v(req_v),
        .e_req_g(req_g), .e_req_t(req_t), .h_rsp_valid(rsp_valid), .h_rsp_data(rsp_data), .e_rsp_valid(e_rv),
        .e_rsp_data(e_rd), .kvw_v(kvw_v), .kvw_vg(kvw_vg), .kvw_t(kvw_t), .kvw_layer(kvw_layer), .kvw_d(kvw_d),
        .kvw_cr(kvw_cr), .emb_req_v(emb_req_v), .emb_req_d(emb_req_d), .emb_req_cr(emb_req_cr), .emb_q_v(emb_q_v),
        .emb_q_d(emb_q_d), .emb_q_cr(emb_q_cr), .hc_v(hc_v), .hc_d(hc_d), .hc_cr(hc_cr), .tok_v(tok_v),
        .tok_d(tok_d), .tok_cr(tok_cr), .fault(faults[2]), .fault_cause(seq_fc));
    wire [4:0] af;
    ot_qwen_nearhbm_attn_die_tb #(.HD(HD), .R(R), .LINK(LINK), .SCALE(SCALE)) u_attn (
        .clk(clk), .rst_n(rst_n), .start(a_start), .T(a_T), .q_valid(a_qv), .q_beat(a_qb), .q_data(a_qd),
        .req_valid(req_valid), .req_v(req_v), .req_g(req_g), .req_t(req_t), .rsp_valid(e_rv), .rsp_data(e_rd),
        .out_valid(a_ov), .out_g(a_og), .out_beat(a_ob), .out_data(a_od), .fault(af), .ev_stack(), .ev_hub());
    assign faults[3] = |af;
    assign a_start_o = a_start;
    assign a_out_valid_o = a_ov;
endmodule
