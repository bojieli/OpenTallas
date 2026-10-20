`timescale 1ns/1ps
// Same electrical read path, split output faces leave a centred clock slot.
// No data/reset cycle change; every q bit is still a direct capture-flop Q.
module qfd_dv_s5_btab_s3 (
 input wire ck,bt_re,input wire [8:0]bt_word,
 output wire [127:0]bt_ql,bt_qh,
 input wire tw_we,input wire [1:0]tw_kind,input wire [23:0]tw_addr,input wire [1023:0]tw_data
);
 qfd_dv_s5_btab_safe u_core(.ck(ck),.bt_re(bt_re),.bt_word(bt_word),.bt_q({bt_qh,bt_ql}),
 .tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data));
endmodule
