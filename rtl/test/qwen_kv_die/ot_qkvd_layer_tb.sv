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
// MUT: 0 base | 1 KV end one extra RES link credit (TIGHT) | 2 KV merge off | 3 one flit dropped in the PHY (ROM->KV)
//      | 4 ROM adapter early link credit | 5 Q beats 0/1 swapped on the KV die
// ---------------------------------------------------------------------------------------------------------------------
module ot_qkvd_layer_tb #(
    parameter integer HD     = 128,
    parameter integer R      = 8,
    parameter integer LINK   = 14,
    parameter integer ROM_ST = 24,
    parameter integer KV_ST  = 12,
    parameter integer PHY_LAT = 5,
    parameter integer QX     = 0,      // KV die: extra stages seq -> stack aggregators beyond LINK (placement)
    parameter integer RX     = 0,      // KV die: stages attention hub -> seq (placement)
    parameter integer KVL    = 0,
    parameter integer TIGHT  = 0,      // credit-stress sizing: RES link buffer 4, VM credits 4 (exercises back-pressure)      // KV die: stages seq -> KV landings (the posted KV rows; placement)
    parameter integer MUT    = 0,
    parameter integer DROP_AT = 300,
    parameter [31:0]  SCALE  = 32'h3DB504F3,
    parameter integer W      = 528,
    parameter integer E      = 4 * R
) (
    input  wire              clk,
    input  wire              rst_n,
    // ROM die: the r21c hub's SU / VM / sequencer faces, now at the ROM end of the link (ot_qkvd_rom_end)
    input  wire              x3_v,
    input  wire [511:0]      x3_d,
    input  wire [10:0]       x3_tag,
    output wire              x3_cr,
    input  wire              ea_v,
    input  wire              ea_kind,
    input  wire [23:0]       ea_addr,
    output wire              ea_cr,
    input  wire              dc_v,
    input  wire [W-1:0]      dc_d,
    output wire              dc_cr,
    output wire              ar_v,
    output wire [518:0]      ar_d,
    input  wire              ar_cr,
    output wire              eq_v,
    output wire [511:0]      eq_d,
    output wire              dh_v,
    output wire [W-1:0]      dh_d,
    input  wire              dh_cr,
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
    // KV end: TX RES EMBD HCTL (4-6), RX CTL Q KVN EMBQ (0-3)

    // ---------------- ROM die: SU / VM / sequencer faces -> ROM_ST relay stages -> ot_qkvd_rom_end ----------------
    wire          x3_v_r, ea_v_r, dc_v_r, x3_cr_r, ea_cr_r, dc_cr_r, ar_v_r, eq_v_r, dh_v_r, ar_cr_r, dh_cr_r;
    wire [522:0]  x3_r;
    wire [24:0]   ea_r;
    wire [W-1:0]  dc_r, dh_r;
    wire [518:0]  ar_r;
    wire [511:0]  eq_r;
    ot_hdc_delay #(.W(3), .D(ROM_ST), .RESET(1)) u_r1v (.clk(clk), .rst_n(rst_n), .d({x3_v, ea_v, dc_v}), .q({x3_v_r, ea_v_r, dc_v_r}));
    ot_hdc_delay #(.W(523 + 25 + W), .D(ROM_ST)) u_r1d (.clk(clk), .rst_n(rst_n), .d({x3_tag, x3_d, ea_kind, ea_addr, dc_d}),
                                                        .q({x3_r, ea_r, dc_r}));
    ot_hdc_delay #(.W(3), .D(ROM_ST), .RESET(1)) u_r1c (.clk(clk), .rst_n(rst_n), .d({x3_cr_r, ea_cr_r, dc_cr_r}), .q({x3_cr, ea_cr, dc_cr}));
    ot_hdc_delay #(.W(3), .D(ROM_ST), .RESET(1)) u_r2v (.clk(clk), .rst_n(rst_n), .d({ar_v_r, eq_v_r, dh_v_r}), .q({ar_v, eq_v, dh_v}));
    ot_hdc_delay #(.W(519 + 512 + W), .D(ROM_ST)) u_r2d (.clk(clk), .rst_n(rst_n), .d({ar_r, eq_r, dh_r}), .q({ar_d, eq_d, dh_d}));
    ot_hdc_delay #(.W(2), .D(ROM_ST), .RESET(1)) u_r2c (.clk(clk), .rst_n(rst_n), .d({ar_cr, dh_cr}), .q({ar_cr_r, dh_cr_r}));
    wire rom_up, rom_txv, rom_rxv, rom_lv, kv_up, kv_txv, kv_rxv, kv_lv;
    wire [FW-1:0] rom_txf, rom_rxf, rom_lf, kv_txf, kv_rxf, kv_lf;
    wire [4:0] kv_fc;
    wire [7:0] rom_fc;
    ot_qkvd_rom_end #(.XS(2 * ROM_ST + 16), .RQD(32), .OCR_AR(TIGHT ? 4 : 2 * ROM_ST + 8), .RB_RES(TIGHT ? 4 : 32),
                     .MUT(MUT == 4 ? 2 : 0)) u_rom (
        .clk(clk), .rst_n(rst_n), .x3_v(x3_v_r), .x3_d(x3_r[511:0]), .x3_tag(x3_r[522:512]), .x3_cr(x3_cr_r),
        .ar_v(ar_v_r), .ar_d(ar_r), .ar_cr(ar_cr_r), .ea_v(ea_v_r), .ea_kind(ea_r[24]), .ea_addr(ea_r[23:0]),
        .ea_cr(ea_cr_r), .eq_v(eq_v_r), .eq_d(eq_r), .dc_v(dc_v_r), .dc_d(dc_r), .dc_cr(dc_cr_r), .dh_v(dh_v_r),
        .dh_d(dh_r), .dh_cr(dh_cr_r), .tx_up(rom_up), .tx_v(rom_txv), .tx_flit(rom_txf), .rx_v(rom_rxv),
        .rx_flit(rom_rxf), .pll_fwd_pad(clk), .rst_fwd_pad(rst_n), .pll_fwd_o(), .rst_fwd_o(), .fault(faults[0]),
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
    ot_qkvd_kv_end #(.QD(KB + 8), .UCX(TIGHT ? 64 : KB + 8), .FCR_RES(TIGHT ? 4 : 32), .MUT(MUT == 1 ? 1 : 0)) u_kv (
        .clk(clk), .rst_n(rst_n), .t_v(kt_v), .t_d(kt_d), .t_cr(kt_cr), .r_v(kr_v), .r_d(kr_d), .r_cr(kr_cr),
        .tx_up(kv_up), .tx_v(kv_txv), .tx_flit(kv_txf), .rx_v(kv_rxv), .rx_flit(kv_rxf), .pll_fwd_i(clk),
        .rst_fwd_i(rst_n), .pll_fwd_pad(), .rst_fwd_pad(), .fault(faults[1]), .fault_cause(kv_fc));
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
    wire [4:0]    af;
    wire [3:0]    mf;
    ot_qkvd_kv_seq #(.HD(HD), .R(R), .W(W), .QD(KB + 8), .CD(4), .KD(8), .ED(32), .GWC(32), .UC0(TIGHT ? 64 : KB + 8), .UC1(KB + 8),
                     .UC2(4), .MUT(MUT == 5 ? 2 : 0)) u_seq (
        .clk(clk), .rst_n(rst_n), .c_v(sc_v), .c_d(sc_d), .c_cr(sc_cr), .u_v(su_tv), .u_d(su_td), .u_cr(su_tcr),
        .a_start(a_start), .a_T(a_T), .a_q_valid(a_qv), .a_q_beat(a_qb), .a_q_data(a_qd), .a_out_valid(a_ov),
        .a_out_g(a_og), .a_out_beat(a_ob), .a_out_data(a_od), .a_hub_fault(af[4]), .a_stk_fault(af[3:0]),
        .m_fault(mf), .kvw_v(kvw_v), .kvw_vg(kvw_vg), .kvw_t(kvw_t), .kvw_layer(kvw_layer), .kvw_d(kvw_d),
        .kvw_cr(kvw_cr), .emb_req_v(emb_req_v), .emb_req_d(emb_req_d), .emb_req_cr(emb_req_cr), .emb_q_v(emb_q_v),
        .emb_q_d(emb_q_d), .emb_q_cr(emb_q_cr), .hc_v(hc_v), .hc_d(hc_d), .hc_cr(hc_cr), .tok_v(tok_v),
        .tok_d(tok_d), .tok_cr(tok_cr), .fault(faults[2]), .fault_cause(seq_fc));
    // the four KV landings: the posted rows reach them over KVL relay stages; one KV merge slice per row engine
    wire       kl_v;
    wire [1:0] kl_vg;
    wire [13:0] kl_t;
    wire [HD*8-1:0] kl_d;
    ot_hdc_delay #(.W(1), .D(KVL), .RESET(1)) u_klv (.clk(clk), .rst_n(rst_n), .d(kvw_v), .q(kl_v));
    ot_hdc_delay #(.W(2 + 14 + HD*8), .D(KVL)) u_kld (.clk(clk), .rst_n(rst_n), .d({kvw_vg, kvw_t, kvw_d}), .q({kl_vg, kl_t, kl_d}));
    genvar s;
    generate for (s = 0; s < 4; s = s + 1) begin : g_land
        ot_qkvd_kv_merge #(.HD(HD), .E(R), .MUT(MUT == 2 ? 1 : 0)) u_merge (.clk(clk), .rst_n(rst_n), .kvw_v(kl_v),
            .kvw_vg(kl_vg), .kvw_t(kl_t), .kvw_d(kl_d), .e_req_valid(req_valid[R*s +: R]), .e_req_v(req_v[R*s +: R]),
            .e_req_g(req_g[R*s +: R]), .e_req_t(req_t[13*R*s +: 13*R]), .h_rsp_valid(rsp_valid[R*s +: R]),
            .h_rsp_data(rsp_data[HD*8*R*s +: HD*8*R]), .e_rsp_valid(e_rv[R*s +: R]), .e_rsp_data(e_rd[HD*8*R*s +: HD*8*R]),
            .fault(mf[s]));
    end endgenerate
    // KV-die wires seq -> aggregators (QX stages beyond the LINK the attention bench applies) and hub -> seq (RX)
    wire          x_start, x_qv, h_ov, h_og;
    wire [13:0]   x_T;
    wire [5:0]    x_qb, h_ob;
    wire [511:0]  x_qd, h_od;
    ot_hdc_delay #(.W(2), .D(QX), .RESET(1)) u_qxv (.clk(clk), .rst_n(rst_n), .d({a_start, a_qv}), .q({x_start, x_qv}));
    ot_hdc_delay #(.W(14 + 6 + 512), .D(QX)) u_qxd (.clk(clk), .rst_n(rst_n), .d({a_T, a_qb, a_qd}), .q({x_T, x_qb, x_qd}));
    ot_hdc_delay #(.W(1), .D(RX), .RESET(1)) u_rxv (.clk(clk), .rst_n(rst_n), .d(h_ov), .q(a_ov));
    ot_hdc_delay #(.W(1 + 6 + 512), .D(RX)) u_rxd (.clk(clk), .rst_n(rst_n), .d({h_og, h_ob, h_od}), .q({a_og, a_ob, a_od}));
    ot_qwen_nearhbm_attn_die_tb #(.HD(HD), .R(R), .LINK(LINK), .SCALE(SCALE)) u_attn (
        .clk(clk), .rst_n(rst_n), .start(x_start), .T(x_T), .q_valid(x_qv), .q_beat(x_qb), .q_data(x_qd),
        .req_valid(req_valid), .req_v(req_v), .req_g(req_g), .req_t(req_t), .rsp_valid(e_rv), .rsp_data(e_rd),
        .out_valid(h_ov), .out_g(h_og), .out_beat(h_ob), .out_data(h_od), .fault(af), .ev_stack(), .ev_hub());
    assign faults[3] = |af;
    assign a_start_o = a_start;
    assign a_out_valid_o = a_ov;
endmodule
