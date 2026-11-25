`timescale 1ns/1ps
// Same electrical read path, split output faces leave a centred clock slot.
// No data/reset cycle change; every q bit is still a direct capture-flop Q.
module qfd_dv_s5_btab_s4 (
 input wire ck,bt_re,input wire [8:0]bt_word,
 output wire [127:0]bt_ql,bt_qh,
 input wire tw_we,input wire [1:0]tw_kind,input wire [23:0]tw_addr,input wire [511:0]tw_lo,tw_hi
);
// QC-RC97-BT2 11-24 (rc97): OT_BTAB_S4R (per-type verilog define, default off) selects the registered-read core
// qfd_dv_s5_btab_safe_r: +1 edge on bt_q, same SRAM instances u_core.g_btb[k].u_m; consumers then bind BT_LAT = 2.
// QC-STA-BTLAT3 11-25 (FABLE-RC-QC 00:14 st_a (b)): OT_BTAB_RQ (with OT_BTAB_S4R; default off) adds the REQUEST-LEG
// register at the SRAM stack: bt_re / bt_word (the read request from u_r0) and the table-write leg are captured in rq_*
// flops in front of the same registered-read core, so the u_r0 -> SRAM r_addr / r_ce hop ends at a flop seated by the
// stack.  The write leg takes the same edge, so every read / write keeps its order: bt_q(t+3) here == bt_q(t+1) of
// qfd_dv_s5_btab_safe (+2 edges on the bt round trip; consumers bind BT_LAT = 3).
`ifdef OT_BTAB_RQ
`ifndef OT_BTAB_S4R
 OT_BTAB_RQ_needs_OT_BTAB_S4R u_refuse();
`endif
 reg rq_re, rq_we; reg [8:0] rq_word; reg [1:0] rq_kind; reg [23:0] rq_addr; reg [511:0] rq_lo, rq_hi;
 always @(posedge ck) begin
  rq_re <= bt_re; rq_word <= bt_word;
  rq_we <= tw_we; rq_kind <= tw_kind; rq_addr <= tw_addr; rq_lo <= tw_lo; rq_hi <= tw_hi;
 end
 qfd_dv_s5_btab_safe_r u_core(.ck(ck),.bt_re(rq_re),.bt_word(rq_word),.bt_q({bt_qh,bt_ql}),
 .tw_we(rq_we),.tw_kind(rq_kind),.tw_addr(rq_addr),.tw_data({rq_hi,rq_lo}));
`elsif OT_BTAB_S4R
 qfd_dv_s5_btab_safe_r u_core(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_q({bt_qh,bt_ql}),
 .tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data({tw_hi,tw_lo}));
`else
 qfd_dv_s5_btab_safe u_core(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_q({bt_qh,bt_ql}),
 .tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data({tw_hi,tw_lo}));
`endif
endmodule
