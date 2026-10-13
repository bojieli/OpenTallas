// Qwen ROM TP8 die (contract v3, results/arch/hier_contract_1012/qwen_rom_tp8.json): slot cell of the 128 KV write-queue
// leaves (slots wleaf_<q>_<pc>), hardened under its DIE MASTER NAME with the die's own ports so the die binds the view
// by name (LEF MACRO + lib cell = qkd_kvwq_leaf_s_w129_m; the closed route of this body was exported as
// ot_qkvd_kv_wq_leaf with RTL port names and could not bind).
//
// Body = ot_qkvd_kv_wq_leaf UNCHANGED (every port a flop at its pin, 866 sinks on the one root ck).  The wrapper is
// wiring only: each die bus is the concatenation, LSB first, of the RTL ports in tools/qwen_kv_die/kv_die.py
// BINDINGS['qkd_kvwq_leaf_s_w129_m']['ports'] order (the convention of tools/qwen_kv_die/bind_views.py pin_map):
//   c  [292:0] N  in   feed chain in    {c_tag[8:0], c_lane[2:0], c_sec[23:0], c_d[255:0], c_v}
//   n  [292:0] S  out  feed chain out   {n_tag, n_lane, n_sec, n_d, n_v}
//   dn [1:0]   S  in   done chain in    {dn_bad, dn_v}
//   dp [1:0]   N  out  done chain out   {dp_bad, dp_v}
//   w  [289:0] S  out  CDC write        {w_tag[8:0], w_data[255:0], w_sec[23:0], w_v}
//   wr [10:0]  S  in   CDC returns      {wd_tag[8:0], wd_v, w_room}
//   lane [2:0] E  in   strap,  rst_n E,  ck N
// Every die bus has ONE direction, so the contract ports are kept exactly (no slot change request).
//
// OT_QKD_KVWQ_LEAF_MUT (bench mutant only, never synthesized): one CDC write data bit inverted at the pin.
module qkd_kvwq_leaf_s_w129_m (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [2:0]   lane,
    input  wire [292:0] c,
    output wire [292:0] n,
    input  wire [1:0]   dn,
    output wire [1:0]   dp,
    output wire [289:0] w,
    input  wire [10:0]  wr
);
    wire [289:0] w_i;
    ot_qkvd_kv_wq_leaf #(.TAGW(9)) u_leaf (
        .clk(ck), .rst_n(rst_n), .lane(lane),
        .c_v(c[0]), .c_d(c[256:1]), .c_sec(c[280:257]), .c_lane(c[283:281]), .c_tag(c[292:284]),
        .n_v(n[0]), .n_d(n[256:1]), .n_sec(n[280:257]), .n_lane(n[283:281]), .n_tag(n[292:284]),
        .dn_v(dn[0]), .dn_bad(dn[1]), .dp_v(dp[0]), .dp_bad(dp[1]),
        .w_v(w_i[0]), .w_sec(w_i[24:1]), .w_data(w_i[280:25]), .w_tag(w_i[289:281]),
        .w_room(wr[0]), .wd_v(wr[1]), .wd_tag(wr[10:2])
    );
`ifdef OT_QKD_KVWQ_LEAF_MUT
    assign w = w_i ^ (290'd1 << 102);
`else
    assign w = w_i;
`endif
endmodule
