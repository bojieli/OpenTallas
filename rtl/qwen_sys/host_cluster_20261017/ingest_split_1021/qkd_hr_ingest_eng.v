// QKO-HROOT2 10-21: single-clock (ck_ingest, 1.667 ns) engine tile of the split qkd_hr_ingest_qm. u_eng = the native32
// primitive copy qkd_host_native_engine_n32 (Codex codex/hroot-address-factor-1021, address-factor successor generated sha256 14e2316d..., census
// max 32, 32 bank SRAMs). RMW_EN 0 configuration
// of the shell (the engine's clk / clk_bank / clk_out entries are all ck_ingest, exactly as qkd_hr_ingest_qm ties them): r_rdy / rd_v / rd_data are the constants 0 exactly as in qkd_hr_native_qm_cdc (e_rrdy = 0, rx_pop = 0).
// Fan-out of the boundary nets (<= 32 loads per driver):
//   reset: eng_rst_n[1:0] (two shell u_rsi leaves) -> 2-stage face landing (u_l0 per pin, then 18/17 kept leaves;
//          async assert with the pin, release 2 ck_ingest edges later) -> the 35 engine reset ports (rst_n,
//          rst_n__c1..34, <= 32 loads each). The engine leaves its reset state 2 edges after the shell's rn_i, before
//          the first possible host word (u_hx Gray synchroniser + head), so behaviour is unchanged
//          (cycle-exact miter rtl/test/qwen_host/qm_split_1021 runs this same bank);
//   in_v / in_v__c1 <- eng_inv_a / eng_inv_b (the shell's two kept copies); done_v / __c1 / __c2 -> eng_done / _a / _b, eng_done_c = kept BUF of __c1;
//   w_v -> 1 kept BUF stem -> KW kept BUFs (keep only, NOT dont_touch: e1a GPL RSZ-3006 could not buffer the dont_touch stem load) -> eng_wv_c[KW-1:0] (the shell's ox_w chunk selects).
// QKD_HR_ENG_RTL (benches only): the behavioural qkd_host_native_engine with the same configuration instead of the netlist.
`timescale 1ns/1ps
// QE3-HROOT 10-21: SPIPE6 (default 0 = unchanged) passes the owner's six-slot stream contract to the behavioural engine.
// The native32 netlist branch is the OLD 539 source: SPIPE6 != 0 there is refused (no old-view alias); a SPIPE6 native
// netlist exists only after owner approval of the pre-build packet and its own regeneration/census.
module qkd_hr_ingest_eng #(parameter integer KW = 20, parameter integer SPIPE6 = 0) (
  input  wire         ck_ingest,
  input  wire         ck_rl,       // engine-region reset landing clock (same 600 MHz ingest family, own small CTS root;
                                   // the cluster ties it to ck_ingest): clocks only the 35 reset leaves
  input  wire [1:0]   eng_rst_n,
  input  wire         eng_dv,
  input  wire [255:0] eng_ddata,
  input  wire         eng_inv_a, eng_inv_b,
  input  wire [511:0] eng_indata,
  input  wire         eng_wrdy,
  output wire         eng_drdy, eng_inrdy, eng_wv,
  output wire [KW-1:0] eng_wv_c,
  output wire [31:0]  eng_waddr,
  output wire [255:0] eng_wdata,
  output wire         eng_rv,
  output wire [31:0]  eng_raddr,
  output wire         eng_done, eng_done_a, eng_done_b, eng_done_c,
  output wire [7:0]   eng_tag,
  output wire         eng_busy,
  output wire [31:0]  eng_nsec
);
  wire [31:0] nbeat_unused;
  // 2-stage face landing: eng_rst_n[j] -> landing flop u_l0[j] (the ONLY sink of the pin) -> 18/17 kept leaves async-reset by
  // rst_l0[j] (assert = pin assert through u_l0 clear-to-Q, release 1 edge after u_l0 = 2 edges after the pin: same cycles)
  wire [1:0] rst_l0;
  wire [34:0] rst_c;
  genvar r;
  for (r = 0; r < 2; r = r + 1) begin : g_l0
    qkd_hr_eng_rst_leaf #(.ID(100 + r)) u_l0 (.ck(ck_rl), .rn(eng_rst_n[r]), .d(1'b1), .q(rst_l0[r]));
  end
  for (r = 0; r < 35; r = r + 1) begin : g_rst
    qkd_hr_eng_rst_leaf #(.ID(r)) u_leaf (.ck(ck_rl), .rn(rst_l0[r / 18]), .d(1'b1), .q(rst_c[r]));
  end
`ifdef QKD_HR_ENG_RTL
  qkd_host_native_engine #(.AW(32), .HDMAX(128), .KVHMAX(2), .QKV(1), .APIPE(0), .SPIPE6(SPIPE6), .QPIPE(2), .NATIVE_ROWS(1), .QMUT(0)) u_eng (
    .clk(ck_ingest), .clk_bank({ck_ingest, ck_ingest}), .clk_out(ck_ingest), .rst_n(rst_c[0]),
    .d_v(eng_dv), .d_rdy(eng_drdy), .d_data(eng_ddata), .in_v(eng_inv_a), .in_rdy(eng_inrdy), .in_data(eng_indata),
    .w_v(eng_wv), .w_rdy(eng_wrdy), .w_addr(eng_waddr), .w_data(eng_wdata),
    .r_v(eng_rv), .r_rdy(1'b0), .r_addr(eng_raddr), .rd_v(1'b0), .rd_data(256'd0),
    .done_v(eng_done), .done_tag(eng_tag), .busy(eng_busy), .n_sectors(eng_nsec), .n_beats(nbeat_unused));
  assign eng_done_a = eng_done;
  assign eng_done_b = eng_done;
  assign eng_done_c = eng_done;
  assign eng_wv_c = {KW{eng_wv}};
`else
  generate if (SPIPE6 != 0) begin : g_bad_spipe6_netlist QKD_HR_ENG_SPIPE6_NETLIST_NOT_REGENERATED refuse(); end endgenerate
  genvar k;
  (* keep *) BUFx2_ASAP7_75t_R u_done_c (.A(eng_done_a), .Y(eng_done_c));
  wire wv_stem;
  (* keep *) BUFx4_ASAP7_75t_R u_wv_stem (.A(eng_wv), .Y(wv_stem));
  for (k = 0; k < KW; k = k + 1) begin : g_wv
    (* keep *) BUFx2_ASAP7_75t_R u_buf (.A(wv_stem), .Y(eng_wv_c[k]));
  end
  qkd_host_native_engine_n32 u_eng (
    .clk(ck_ingest), .clk_bank({ck_ingest, ck_ingest}), .clk_out(ck_ingest), .rst_n(rst_c[0]),
    .rst_n__c1(rst_c[1]), .rst_n__c2(rst_c[2]), .rst_n__c3(rst_c[3]), .rst_n__c4(rst_c[4]), .rst_n__c5(rst_c[5]),
    .rst_n__c6(rst_c[6]), .rst_n__c7(rst_c[7]), .rst_n__c8(rst_c[8]), .rst_n__c9(rst_c[9]), .rst_n__c10(rst_c[10]),
    .rst_n__c11(rst_c[11]), .rst_n__c12(rst_c[12]), .rst_n__c13(rst_c[13]), .rst_n__c14(rst_c[14]), .rst_n__c15(rst_c[15]),
    .rst_n__c16(rst_c[16]), .rst_n__c17(rst_c[17]), .rst_n__c18(rst_c[18]), .rst_n__c19(rst_c[19]), .rst_n__c20(rst_c[20]),
    .rst_n__c21(rst_c[21]), .rst_n__c22(rst_c[22]), .rst_n__c23(rst_c[23]), .rst_n__c24(rst_c[24]), .rst_n__c25(rst_c[25]),
    .rst_n__c26(rst_c[26]), .rst_n__c27(rst_c[27]), .rst_n__c28(rst_c[28]), .rst_n__c29(rst_c[29]), .rst_n__c30(rst_c[30]),
    .rst_n__c31(rst_c[31]), .rst_n__c32(rst_c[32]), .rst_n__c33(rst_c[33]), .rst_n__c34(rst_c[34]),
    .d_v(eng_dv), .d_rdy(eng_drdy), .d_data(eng_ddata),
    .in_v(eng_inv_a), .in_v__c1(eng_inv_b), .in_rdy(eng_inrdy), .in_data(eng_indata),
    .w_v(eng_wv), .w_rdy(eng_wrdy), .w_addr(eng_waddr), .w_data(eng_wdata),
    .r_v(eng_rv), .r_rdy(1'b0), .r_addr(eng_raddr), .rd_v(1'b0), .rd_data(256'd0),
    .done_v(eng_done), .done_v__c1(eng_done_a), .done_v__c2(eng_done_b),
    .done_tag(eng_tag), .busy(eng_busy), .n_sectors(eng_nsec), .n_beats(nbeat_unused));
`endif
endmodule

// Engine-region reset landing leaf: async assert with rn, release on the next ck edge. Distinct ID per copy = separate
// kept hierarchies, so synthesis never merges the 35 copies back (same scheme as ot_pl_land_rst_copy).
(* keep_hierarchy = "yes" *)
module qkd_hr_eng_rst_leaf #(parameter integer ID = 0) (input wire ck, rn, d, output wire q);
  (* keep *) reg r;
  always @(posedge ck or negedge rn) if (!rn) r <= 1'b0; else r <= d;
  assign q = r;
endmodule
