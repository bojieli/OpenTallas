`timescale 1ns/1ps
`default_nettype none
// mtp-lead 2026-10-09: the MTP master of the generic HBM die (R25G, key mtp_master='hgi_native').
//
// = the native full-context DSpark controller in its checked CP-result form (hfd_mtp_x_cp_stop, EXTERNAL_AM=1:
//   gamma 5, 40 layers, WR 256 / RLOG 16'h0111 / SR 10 / CKMAX 2^20, XSEL router selections, STOP/EOS/1M context,
//   registered pins + skids) behind the 197/517-bit CP facade that hfd_cmdproc_s_mtp_native_mx1 (t_mtp / f_mtp)
//   drives, minus the 523-bit su_red logit bus.
//
// Why no logit bus: on the generic die the argmax is a program record.  ARGMAX.LOCAL runs in the ARGMAX unit
// (ot_hgi_argmax18_m, unit 7, in this slot, dispatched over hgi_argmax_cmd) and COLL.ARGMAX_MERGE in hfd_coll; the
// merged id of each verify row reaches the CP (MX1 f_am) and enters this master as cp_am_v / cp_am_idx
// (f_cmdproc[179], [180 +: 17]).  With EXTERNAL_AM=1 the master's local argmax leaf is not elaborated; lg_* only
// gate am_v (= cp_am_v && !lg_v) and feed their pin flops, so they are bound to constant 0 here (no functional path
// is removed: the same rows are produced by the ARGMAX unit once, not twice).  657 -> 0 die tracks to su_red.
//
// Token width: 17 bits (DS vocab 129,280 < 2^17).  The generic interface carries 18-bit ids; the CP range-checks
// every completion / AMAX id against cp_vocab before it reaches f_am, so bit 17 is 0 for DS.  Qwen MTP is reserved
// (HBM_GENERIC_INTERFACE 10.3); its 18-bit controller is hgi-takeover's ot_hgi_mtp_core18 lineage.
module hgi_mtp_native (
  input  wire         clk,
  input  wire         rst_n,
  input  wire [196:0] f_cmdproc,
  output wire [516:0] t_cmdproc,
  input  wire [58:0]  f_router,
  output wire [57:0]  t_router,
  output wire [18:0]  t_coll,
  input  wire [0:0]   f_coll
);
  hfd_mtp_native_cp_stop #(.ENABLE(1)) u_native (
    .clk(clk), .rst_n(rst_n),
    .f_cmdproc(f_cmdproc), .t_cmdproc(t_cmdproc),
    .f_su_red(523'b0),
    .f_router(f_router), .t_router(t_router),
    .t_coll(t_coll), .f_coll(f_coll));
endmodule
`default_nettype wire
