// SPIPE6 source-bound engine qualification candidate; no release view or calendar adoption.
// A unique wrapper/native namespace selects only the six-slot engine. External ports and the existing
// two-edge reset landing remain unchanged. The 35 native reset entries and both valid entries are explicit.
// ck_ingest is the 1666.667 ps engine family; ck_rl is its separate same PLL 1:1 reset landing root.
// Physical roots/spread/phase, mapped cold behavior and parent placement remain qualification obligations.
`timescale 1ns/1ps
module qkd_hr_ingest_eng_sp6 #(parameter integer KW = 20, parameter integer SPIPE6 = 1) (
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
    qkd_hr_sp6_eng_rst_leaf #(.ID(100 + r)) u_l0 (.ck(ck_rl), .rn(eng_rst_n[r]), .d(1'b1), .q(rst_l0[r]));
  end
  for (r = 0; r < 35; r = r + 1) begin : g_rst
    qkd_hr_sp6_eng_rst_leaf #(.ID(r)) u_leaf (.ck(ck_rl), .rn(rst_l0[r / 18]), .d(1'b1), .q(rst_c[r]));
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
  generate if (SPIPE6 != 1) begin : g_bad_spipe6_netlist QKD_HR_ENG_SPIPE6_REQUIRES_SIX_SLOT_SOURCE refuse(); end endgenerate
  genvar k;
  (* keep *) BUFx2_ASAP7_75t_R u_done_c (.A(eng_done_a), .Y(eng_done_c));
  wire wv_stem;
  (* keep *) BUFx4_ASAP7_75t_R u_wv_stem (.A(eng_wv), .Y(wv_stem));
  for (k = 0; k < KW; k = k + 1) begin : g_wv
    (* keep *) BUFx2_ASAP7_75t_R u_buf (.A(wv_stem), .Y(eng_wv_c[k]));
  end
  qkd_host_native_engine_sp6_n32 u_eng (
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
module qkd_hr_sp6_eng_rst_leaf #(parameter integer ID = 0) (input wire ck, rn, d, output wire q);
  (* keep *) reg r;
  always @(posedge ck or negedge rn) if (!rn) r <= 1'b0; else r <= d;
  assign q = r;
endmodule
