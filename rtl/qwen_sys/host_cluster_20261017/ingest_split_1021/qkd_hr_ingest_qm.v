// QKO-HROOT2 10-21: SPLIT qkd_hr_ingest_qm (same module name and ports as the generated
// rtl/qwen_sys/host_cluster_20261017/qkd_hr_ingest_qm.v; a source list takes exactly one of the two). Pure wiring of two
// hardened children: u_qm = qkd_hr_ingest_shell (multi-clock CDC shell: host / ingest / core, three dual-clock SRAMs) and
// u_eng = qkd_hr_ingest_eng (single-clock ck_ingest engine, native32 netlist). Behaviour = the unsplit block cycle for
// cycle (witness rtl/test/qwen_host/qm_split_1021).
`timescale 1ns/1ps
module qkd_hr_ingest_qm(ck_core, ck_host, ck_ingest, host_rst_n, service_faults, u_rank__qm_d, u_rank__qm_cls, u_rank__qm_v, u_rank__qm_crn, u_rank__ov, u_rank__owe, u_rank__oa, u_rank__od, u_rank__ocr, u_rank__qm_t_cr, u_rank__qm_t_d, u_rank__qm_t_v, host_upstream_quiet_core, host_upstream_quiet_host, host_upstream_quiet_ingest);
  localparam integer KW = 20;
  // QE3-HROOT 10-21: owner six-slot contract selector for BOTH children (engine stream + shell IKEY fail-closed guard).
  parameter integer SPIPE6 = 0;
  input ck_core, ck_host, ck_ingest, host_rst_n;
  output service_faults;
  input [511:0] u_rank__qm_d;
  input [1:0] u_rank__qm_cls;
  input u_rank__qm_v;
  output [4:0] u_rank__qm_crn;
  output u_rank__ov, u_rank__owe;
  output [31:0] u_rank__oa;
  output [255:0] u_rank__od;
  input u_rank__ocr, u_rank__qm_t_cr;
  output [63:0] u_rank__qm_t_d;
  output u_rank__qm_t_v;
  output host_upstream_quiet_core, host_upstream_quiet_host, host_upstream_quiet_ingest;
  wire [1:0] eng_rst_n;
  wire eng_dv, eng_inv_a, eng_inv_b, eng_wrdy, eng_drdy, eng_inrdy, eng_wv, eng_rv, eng_done, eng_done_a, eng_done_b, eng_done_c, eng_busy;
  wire [255:0] eng_ddata, eng_wdata;
  wire [511:0] eng_indata;
  wire [KW-1:0] eng_wv_c;
  wire [31:0] eng_waddr, eng_raddr, eng_nsec;
  wire [7:0] eng_tag;
  qkd_hr_ingest_shell #(.KW(KW), .SPIPE6(SPIPE6)) u_qm (
    .ck_core(ck_core), .ck_host(ck_host), .ck_ingest(ck_ingest), .host_rst_n(host_rst_n), .service_faults(service_faults),
    .u_rank__qm_d(u_rank__qm_d), .u_rank__qm_cls(u_rank__qm_cls), .u_rank__qm_v(u_rank__qm_v), .u_rank__qm_crn(u_rank__qm_crn),
    .u_rank__ov(u_rank__ov), .u_rank__owe(u_rank__owe), .u_rank__oa(u_rank__oa), .u_rank__od(u_rank__od), .u_rank__ocr(u_rank__ocr),
    .u_rank__qm_t_cr(u_rank__qm_t_cr), .u_rank__qm_t_d(u_rank__qm_t_d), .u_rank__qm_t_v(u_rank__qm_t_v),
    .host_upstream_quiet_core(host_upstream_quiet_core), .host_upstream_quiet_host(host_upstream_quiet_host),
    .host_upstream_quiet_ingest(host_upstream_quiet_ingest),
    .eng_rst_n(eng_rst_n), .eng_dv(eng_dv), .eng_ddata(eng_ddata), .eng_inv_a(eng_inv_a), .eng_inv_b(eng_inv_b),
    .eng_indata(eng_indata), .eng_wrdy(eng_wrdy), .eng_drdy(eng_drdy), .eng_inrdy(eng_inrdy), .eng_wv(eng_wv), .eng_wv_c(eng_wv_c),
    .eng_waddr(eng_waddr), .eng_wdata(eng_wdata), .eng_rv(eng_rv), .eng_raddr(eng_raddr), .eng_done(eng_done),
    .eng_done_a(eng_done_a), .eng_done_b(eng_done_b), .eng_done_c(eng_done_c), .eng_tag(eng_tag), .eng_busy(eng_busy), .eng_nsec(eng_nsec));
  qkd_hr_ingest_eng #(.KW(KW), .SPIPE6(SPIPE6)) u_eng (
    .ck_ingest(ck_ingest), .ck_rl(ck_ingest),
    .eng_rst_n(eng_rst_n), .eng_dv(eng_dv), .eng_ddata(eng_ddata), .eng_inv_a(eng_inv_a), .eng_inv_b(eng_inv_b),
    .eng_indata(eng_indata), .eng_wrdy(eng_wrdy), .eng_drdy(eng_drdy), .eng_inrdy(eng_inrdy), .eng_wv(eng_wv), .eng_wv_c(eng_wv_c),
    .eng_waddr(eng_waddr), .eng_wdata(eng_wdata), .eng_rv(eng_rv), .eng_raddr(eng_raddr), .eng_done(eng_done),
    .eng_done_a(eng_done_a), .eng_done_b(eng_done_b), .eng_done_c(eng_done_c), .eng_tag(eng_tag), .eng_busy(eng_busy), .eng_nsec(eng_nsec));
endmodule
