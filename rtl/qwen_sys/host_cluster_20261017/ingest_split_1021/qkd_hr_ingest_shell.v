// QKO-HROOT2 10-21: CDC shell tile of the split qkd_hr_ingest_qm (scratch/qko-hroot/INGEST_PLAN.txt). Same host / die /
// quiet / fault ports as qkd_hr_ingest_qm (gen_cluster.py names) plus the ck_ingest-domain engine face eng_* to the
// single-clock engine tile qkd_hr_ingest_eng (touching tile, direct wires). Instance name u_rank__u_qm kept, so the
// reviewed CDC synchroniser paths of the qkd_hr_ingest_qm kits are unchanged.
`timescale 1ns/1ps
// QE3-HROOT 10-21: SPIPE6 (default 0 = unchanged) selects the owner's six-slot engine contract; the shell then fails
// malformed IKEY descriptors closed (cdc shell IKEY_GUARD, fault code 8) before the engine.
module qkd_hr_ingest_shell #(parameter integer KW = 20, parameter integer SPIPE6 = 0) (
  input  wire         ck_core, ck_host, ck_ingest, host_rst_n,
  output wire         service_faults,
  input  wire [511:0] u_rank__qm_d,
  input  wire [1:0]   u_rank__qm_cls,
  input  wire         u_rank__qm_v,
  output wire [4:0]   u_rank__qm_crn,
  output wire         u_rank__ov, u_rank__owe,
  output wire [31:0]  u_rank__oa,
  output wire [255:0] u_rank__od,
  input  wire         u_rank__ocr, u_rank__qm_t_cr,
  output wire [63:0]  u_rank__qm_t_d,
  output wire         u_rank__qm_t_v,
  output wire         host_upstream_quiet_core, host_upstream_quiet_host, host_upstream_quiet_ingest,
  // engine face (ck_ingest)
  output wire [1:0]   eng_rst_n,
  output wire         eng_dv,
  output wire [255:0] eng_ddata,
  output wire         eng_inv_a, eng_inv_b,
  output wire [511:0] eng_indata,
  output wire         eng_wrdy,
  input  wire         eng_drdy, eng_inrdy, eng_wv,
  input  wire [KW-1:0] eng_wv_c,
  input  wire [31:0]  eng_waddr,
  input  wire [255:0] eng_wdata,
  input  wire         eng_rv,
  input  wire [31:0]  eng_raddr,
  input  wire         eng_done, eng_done_a, eng_done_b, eng_done_c,
  input  wire [7:0]   eng_tag,
  input  wire         eng_busy,
  input  wire [31:0]  eng_nsec
);
  qkd_hr_ingest_cdc_shell #(.AW(32), .HDMAX(128), .KVHMAX(2), .RMW_EN(0), .MUT(0), .NATIVE_ROWS(1), .QPIPE(2), .KW(KW), .IKEY_GUARD(SPIPE6)) u_rank__u_qm (
    .rst_n(host_rst_n), .clk_h(ck_host), .h_v(u_rank__qm_v), .h_cls(u_rank__qm_cls), .h_d(u_rank__qm_d), .h_crn(u_rank__qm_crn),
    .t_v(u_rank__qm_t_v), .t_d(u_rank__qm_t_d), .t_cr(u_rank__qm_t_cr),
    .clk_i(ck_ingest),
    .e_rst_n(eng_rst_n), .e_dv(eng_dv), .e_ddata(eng_ddata), .e_inv_a(eng_inv_a), .e_inv_b(eng_inv_b), .e_indata(eng_indata),
    .e_wrdy_o(eng_wrdy), .e_drdy(eng_drdy), .e_inrdy(eng_inrdy), .e_wv(eng_wv), .e_wv_c(eng_wv_c), .e_waddr(eng_waddr),
    .e_wdata(eng_wdata), .e_rv(eng_rv), .e_raddr(eng_raddr), .e_done(eng_done), .e_done_a(eng_done_a), .e_done_b(eng_done_b), .e_done_c(eng_done_c),
    .e_tag(eng_tag), .e_busy(eng_busy), .e_nsec(eng_nsec),
    .ck(ck_core), .o_v(u_rank__ov), .o_we(u_rank__owe), .o_addr(u_rank__oa), .o_d(u_rank__od), .o_cr(u_rank__ocr),
    .i_rv(1'b0), .i_rd(256'd0), .fault(service_faults),
    .quiet_h(host_upstream_quiet_host), .quiet_i(host_upstream_quiet_ingest), .quiet_c(host_upstream_quiet_core));
endmodule
