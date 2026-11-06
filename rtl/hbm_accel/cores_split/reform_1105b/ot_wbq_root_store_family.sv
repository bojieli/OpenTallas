// Optional WBQ root-store family outer shell, derived from the actual routed original shell.
// Existing WD captures live in store_face; every other face retains its old capture.
// No additional face shell is permitted on this composition. Native bindings need owner adoption.
`default_nettype none
module ot_wbq_root_store_family #(parameter integer STORE_GROUP4=0) (
    input wire hbm_clk,
    input wire fifo_clk,
    input wire stream_rst_n,
    input wire hbm_rst_n,
    input wire [1:0] root_id,
    input wire reserve_v,
    input wire reserve_bank,
    input wire [11:0] reserve_total,
    input wire [29:0] reserve_base,
    input wire fill_start,
    input wire fill_start_bank,
    input wire [255:0] wd0,
    input wire [255:0] wd1,
    input wire [255:0] wd2,
    input wire [255:0] wd3,
    input wire [255:0] wd4,
    input wire [255:0] wd5,
    input wire [255:0] wd6,
    input wire [255:0] wd7,
    input wire [7:0] wd_v,
    input wire copy_on,
    input wire copy_bank,
    input wire s_stop,
    input wire h_stop,
    input wire [1:0] g_credit,
    output wire root_ready,
    output wire [1:0] g_v,
    output wire [571:0] g_d
);
    wire [1:0] root_id__fq;
    (* keep *) ot_hbm_face_reg #(.W(2)) u_bin_root_id (.clk(fifo_clk), .d(root_id), .q(root_id__fq));
    wire [0:0] reserve_v__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_reserve_v (.clk(fifo_clk), .d(reserve_v), .q(reserve_v__fq));
    wire [0:0] reserve_bank__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_reserve_bank (.clk(fifo_clk), .d(reserve_bank), .q(reserve_bank__fq));
    wire [11:0] reserve_total__fq;
    (* keep *) ot_hbm_face_reg #(.W(12)) u_bin_reserve_total (.clk(fifo_clk), .d(reserve_total), .q(reserve_total__fq));
    wire [29:0] reserve_base__fq;
    (* keep *) ot_hbm_face_reg #(.W(30)) u_bin_reserve_base (.clk(fifo_clk), .d(reserve_base), .q(reserve_base__fq));
    wire [0:0] fill_start__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_fill_start (.clk(fifo_clk), .d(fill_start), .q(fill_start__fq));
    wire [0:0] fill_start_bank__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_fill_start_bank (.clk(fifo_clk), .d(fill_start_bank), .q(fill_start_bank__fq));
    wire [255:0] wd0__fq;
    assign wd0__fq = wd0; // WD input face resides in store child
    wire [255:0] wd1__fq;
    assign wd1__fq = wd1; // WD input face resides in store child
    wire [255:0] wd2__fq;
    assign wd2__fq = wd2; // WD input face resides in store child
    wire [255:0] wd3__fq;
    assign wd3__fq = wd3; // WD input face resides in store child
    wire [255:0] wd4__fq;
    assign wd4__fq = wd4; // WD input face resides in store child
    wire [255:0] wd5__fq;
    assign wd5__fq = wd5; // WD input face resides in store child
    wire [255:0] wd6__fq;
    assign wd6__fq = wd6; // WD input face resides in store child
    wire [255:0] wd7__fq;
    assign wd7__fq = wd7; // WD input face resides in store child
    wire [7:0] wd_v__fq;
    (* keep *) ot_hbm_face_reg #(.W(8)) u_bin_wd_v (.clk(fifo_clk), .d(wd_v), .q(wd_v__fq));
    wire [0:0] copy_on__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_copy_on (.clk(fifo_clk), .d(copy_on), .q(copy_on__fq));
    wire [0:0] copy_bank__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_copy_bank (.clk(fifo_clk), .d(copy_bank), .q(copy_bank__fq));
    wire [0:0] s_stop__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_s_stop (.clk(fifo_clk), .d(s_stop), .q(s_stop__fq));
    wire [0:0] h_stop__fq;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bin_h_stop (.clk(fifo_clk), .d(h_stop), .q(h_stop__fq));
    wire [1:0] g_credit__fq;
    (* keep *) ot_hbm_face_reg #(.W(2)) u_bin_g_credit (.clk(fifo_clk), .d(g_credit), .q(g_credit__fq));
    wire [0:0] root_ready__fc;
    (* keep *) ot_hbm_face_reg #(.W(1)) u_bout_root_ready (.clk(fifo_clk), .d(root_ready__fc), .q(root_ready));
    wire [1:0] g_v__fc;
    (* keep *) ot_hbm_face_reg #(.W(2)) u_bout_g_v (.clk(fifo_clk), .d(g_v__fc), .q(g_v));
    wire [571:0] g_d__fc;
    (* keep *) ot_hbm_face_reg #(.W(572)) u_bout_g_d (.clk(fifo_clk), .d(g_d__fc), .q(g_d));
    ot_wbq_root #(.STORE_GROUP4(STORE_GROUP4)) u_fcore (
        .hbm_clk(hbm_clk),
        .fifo_clk(fifo_clk),
        .stream_rst_n(stream_rst_n),
        .hbm_rst_n(hbm_rst_n),
        .root_id(root_id__fq),
        .reserve_v(reserve_v__fq),
        .reserve_bank(reserve_bank__fq),
        .reserve_total(reserve_total__fq),
        .reserve_base(reserve_base__fq),
        .fill_start(fill_start__fq),
        .fill_start_bank(fill_start_bank__fq),
        .wd0(wd0__fq),
        .wd1(wd1__fq),
        .wd2(wd2__fq),
        .wd3(wd3__fq),
        .wd4(wd4__fq),
        .wd5(wd5__fq),
        .wd6(wd6__fq),
        .wd7(wd7__fq),
        .wd_v(wd_v__fq),
        .copy_on(copy_on__fq),
        .copy_bank(copy_bank__fq),
        .s_stop(s_stop__fq),
        .h_stop(h_stop__fq),
        .g_credit(g_credit__fq),
        .root_ready(root_ready__fc),
        .g_v(g_v__fc),
        .g_d(g_d__fc)
    );
endmodule
`default_nettype wire
